"""Async client for Open Food Facts API.

Provides text search and barcode lookup for food products,
normalising nutriment data into a consistent schema suitable
for the label_engine nutrition generator.

API docs: https://wiki.openfoodfacts.org/API
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict

import httpx

logger = logging.getLogger("api_label.off")

_TIMEOUT = httpx.Timeout(25.0, connect=10.0)

# Base URLs
_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
_PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product"

# Fields we request from OFF (keeps response small)
_FIELDS = (
    "code,product_name,brands,image_front_small_url,"
    "nutrition_grades,nutriscore_grade,nutriments,"
    "ingredients_text,ingredients_text_es,"
    "allergens_tags,allergens_from_ingredients_tags"
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class OFFProduct:
    """Normalised product data from Open Food Facts."""

    barcode: str
    name: str
    brand: str | None = None
    image_url: str | None = None
    nutriscore: str | None = None  # "a" .. "e" or None

    # Nutritional values per 100 g
    energy_kj: float | None = None
    energy_kcal: float | None = None
    fat_g: float | None = None
    saturated_fat_g: float | None = None
    carbohydrates_g: float | None = None
    sugars_g: float | None = None
    protein_g: float | None = None
    salt_g: float | None = None
    fiber_g: float | None = None
    ingredients: str | None = None
    allergens: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    def has_required_nutrition(self) -> bool:
        """Return True if minimum EU 1169/2011 mandatory fields are present."""
        return all(
            v is not None
            for v in [
                self.energy_kj,
                self.energy_kcal,
                self.fat_g,
                self.saturated_fat_g,
                self.carbohydrates_g,
                self.sugars_g,
                self.protein_g,
                self.salt_g,
            ]
        )

    def to_regulatory_data(self) -> dict:
        """Convert to the dict format expected by label_engine."""
        rd: dict = {}
        if self.energy_kj is not None:
            rd["energy_kj"] = self.energy_kj
        if self.energy_kcal is not None:
            rd["energy_kcal"] = self.energy_kcal
        if self.fat_g is not None:
            rd["fat_g"] = self.fat_g
        if self.saturated_fat_g is not None:
            rd["saturated_fat_g"] = self.saturated_fat_g
        if self.carbohydrates_g is not None:
            rd["carbohydrates_g"] = self.carbohydrates_g
        if self.sugars_g is not None:
            rd["sugars_g"] = self.sugars_g
        if self.protein_g is not None:
            rd["protein_g"] = self.protein_g
        if self.salt_g is not None:
            rd["salt_g"] = self.salt_g
        if self.fiber_g is not None:
            rd["fiber_g"] = self.fiber_g
        if self.ingredients:
            rd["ingredients"] = self.ingredients
        if self.allergens:
            rd["allergens"] = self.allergens
        return rd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(value) -> float | None:
    """Coerce a value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _extract_product(raw: dict) -> OFFProduct:
    """Parse a single OFF product dict into an OFFProduct."""
    nutriments = raw.get("nutriments") or {}

    nutriscore = (
        raw.get("nutriscore_grade")
        or raw.get("nutrition_grades")
        or None
    )
    if nutriscore:
        nutriscore = nutriscore.lower().strip()
        if nutriscore not in ("a", "b", "c", "d", "e"):
            nutriscore = None

    # Ingredients: prefer Spanish version, fall back to generic text
    ingredients = (
        raw.get("ingredients_text_es")
        or raw.get("ingredients_text")
        or None
    )

    # Allergens: prefer explicit tags, fall back to auto-detected from ingredients
    allergen_tags = raw.get("allergens_tags") or raw.get("allergens_from_ingredients_tags") or []
    allergens = None
    if allergen_tags:
        names = [tag.split(":", 1)[-1].replace("-", " ") for tag in allergen_tags]
        allergens = ", ".join(names)

    return OFFProduct(
        barcode=str(raw.get("code") or ""),
        name=raw.get("product_name") or "",
        brand=raw.get("brands") or None,
        image_url=raw.get("image_front_small_url") or None,
        nutriscore=nutriscore,
        energy_kj=_safe_float(nutriments.get("energy-kj_100g")),
        energy_kcal=_safe_float(nutriments.get("energy-kcal_100g")),
        fat_g=_safe_float(nutriments.get("fat_100g")),
        saturated_fat_g=_safe_float(nutriments.get("saturated-fat_100g")),
        carbohydrates_g=_safe_float(nutriments.get("carbohydrates_100g")),
        sugars_g=_safe_float(nutriments.get("sugars_100g")),
        protein_g=_safe_float(nutriments.get("proteins_100g")),
        salt_g=_safe_float(nutriments.get("salt_100g")),
        fiber_g=_safe_float(nutriments.get("fiber_100g")),
        ingredients=ingredients,
        allergens=allergens,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def search_products(query: str, page_size: int = 6) -> list[OFFProduct]:
    """Search Open Food Facts by text query.

    Returns up to *page_size* products (default 6).
    Returns an empty list on network errors or if no results found.
    """
    params = {
        "search_terms": query,
        "search_simple": "1",
        "action": "process",
        "json": "1",
        "page_size": str(page_size),
        "fields": _FIELDS,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(_SEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, httpx.TimeoutException, Exception) as exc:
        logger.warning("OFF search failed for %r: %s", query, exc)
        return []

    raw_products = data.get("products") or []
    results: list[OFFProduct] = []
    for raw in raw_products:
        product = _extract_product(raw)
        # Skip products without a name
        if product.name:
            results.append(product)
    return results[:page_size]


async def lookup_barcode(barcode: str) -> OFFProduct | None:
    """Look up a single product by barcode on Open Food Facts.

    Returns an OFFProduct or None if not found / error.
    """
    url = f"{_PRODUCT_URL}/{barcode}.json"
    params = {"fields": _FIELDS}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, httpx.TimeoutException, Exception) as exc:
        logger.warning("OFF barcode lookup failed for %r: %s", barcode, exc)
        return None

    # OFF returns status 1 on success, 0 on not found
    if data.get("status") == 0:
        return None

    raw_product = data.get("product")
    if not raw_product:
        return None

    product = _extract_product(raw_product)
    if not product.name:
        return None

    return product
