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

# Fields we request from OFF — comprehensive list for maximum auto-fill
_FIELDS = (
    "code,product_name,brands,image_front_small_url,"
    "image_front_url,image_nutrition_url,image_ingredients_url,"
    "nutrition_grades,nutriscore_grade,nova_group,nutriments,"
    "ingredients_text,ingredients_text_es,"
    "allergens_tags,allergens_from_ingredients_tags,"
    "traces_tags,additives_tags,additives_n,"
    "quantity,serving_size,serving_quantity,"
    "manufacturing_places,origins,countries_tags,"
    "stores,labels_tags,categories_tags_es,categories_tags,"
    "conservation_conditions,customer_service,"
    "packaging_text,packaging_tags,product_quantity,"
    "producer_version_id,emb_codes,"
    "ecoscore_grade,ecoscore_score,ingredients_analysis_tags,"
    "compared_to_category"
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

    # Extended fields (auto-fill helpers)
    net_weight: str | None = None          # e.g. "500 g", "1 L"
    serving_size: str | None = None        # e.g. "30 g"
    serving_size_g: float | None = None    # numeric serving in grams
    manufacturer: str | None = None        # manufacturing places / producer
    country_of_origin: str | None = None   # origins or countries
    storage_conditions: str | None = None  # conservation conditions
    nova_group: int | None = None          # NOVA 1-4
    categories: str | None = None          # product categories
    labels: str | None = None              # Bio, Sans gluten, etc.
    ecoscore: str | None = None            # a-e
    is_vegan: bool | None = None
    is_vegetarian: bool | None = None
    is_palm_oil_free: bool | None = None
    # Traces and additives
    traces: str | None = None              # "frutos secos, soja"
    additives: str | None = None           # "E322, E150a"
    additives_count: int | None = None     # number of additives
    # Category comparison
    compared_to_category: str | None = None  # e.g. "Mantequillas de cacahuete"
    # Extra images
    image_front_large_url: str | None = None
    image_nutrition_url: str | None = None
    image_ingredients_url: str | None = None
    # Packaging
    packaging: str | None = None           # "Plastico, Vidrio"
    # Extra minerals/vitamins
    sodium_mg: float | None = None
    vitamin_c_mg: float | None = None
    calcium_mg: float | None = None
    iron_mg: float | None = None

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
        if self.serving_size_g is not None:
            rd["serving_size_g"] = self.serving_size_g
        if self.ingredients:
            rd["ingredients"] = self.ingredients
        if self.allergens:
            rd["allergens"] = self.allergens
        if self.net_weight:
            rd["net_weight"] = self.net_weight
        if self.manufacturer:
            rd["manufacturer"] = self.manufacturer
        if self.country_of_origin:
            rd["country_of_origin"] = self.country_of_origin
        if self.storage_conditions:
            rd["storage_conditions"] = self.storage_conditions
        if self.traces:
            rd["traces"] = self.traces
        if self.sodium_mg is not None:
            rd["sodium_mg"] = self.sodium_mg
        if self.vitamin_c_mg is not None:
            rd["vitamin_c_mg"] = self.vitamin_c_mg
        if self.calcium_mg is not None:
            rd["calcium_mg"] = self.calcium_mg
        if self.iron_mg is not None:
            rd["iron_mg"] = self.iron_mg
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


_PACKAGING_TRANSLATIONS: dict[str, str] = {
    # English → Spanish
    "plastic": "plástico", "glass": "vidrio", "cardboard": "cartón",
    "metal": "metal", "aluminium": "aluminio", "aluminum": "aluminio",
    "paper": "papel", "wood": "madera", "tin": "lata",
    "box": "caja", "bag": "bolsa", "bottle": "botella", "can": "lata",
    "jar": "tarro", "pot": "bote", "pouch": "bolsa", "tray": "bandeja",
    "container": "envase", "wrapper": "envoltorio", "film": "film",
    "lid": "tapa", "cap": "tapón", "cork": "corcho", "seal": "precinto",
    "sleeve": "funda", "label": "etiqueta", "tube": "tubo",
    "tetra pak": "tetra pak", "brick": "brik",
    "non corrugated cardboard": "cartón liso",
    "corrugated cardboard": "cartón corrugado",
    "green dot": "punto verde",
    "to recycle": "reciclable", "to discard": "no reciclable",
    "recyclable": "reciclable", "non-recyclable": "no reciclable",
    # French → Spanish
    "plastique": "plástico", "verre": "vidrio", "carton": "cartón",
    "métal": "metal", "papier": "papel", "bois": "madera",
    "boîte": "caja", "bouteille": "botella", "sachet": "bolsa",
    "pot": "bote", "barquette": "bandeja", "couvercle": "tapa",
    "bouchon": "tapón", "opercule": "precinto", "film": "film",
    "à recycler": "reciclable", "à jeter": "no reciclable",
    "blanc": "blanco", "opaque": "opaco", "transparent": "transparente",
    "non corrugated": "liso", "drinks": "",
    "plaque": "placa", "en ": "de ",
}


def _translate_packaging(text: str) -> str:
    """Translate common packaging terms from English/French to Spanish."""
    result = text
    for foreign, spanish in _PACKAGING_TRANSLATIONS.items():
        # Case-insensitive replacement, whole word when possible
        import re
        result = re.sub(re.escape(foreign), spanish, result, flags=re.IGNORECASE)
    return result


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

    # Net weight: prefer "quantity" ("500 g"), fall back to "product_quantity"
    net_weight = raw.get("quantity") or raw.get("product_quantity") or None
    if net_weight:
        net_weight = str(net_weight).strip()

    # Serving size
    serving_size = raw.get("serving_size") or None
    serving_size_g = _safe_float(nutriments.get("serving_size"))  # sometimes numeric
    # Try to parse serving_size string like "30 g" → 30.0
    if serving_size_g is None and serving_size:
        import re
        m = re.match(r"([\d.,]+)\s*g", str(serving_size))
        if m:
            serving_size_g = _safe_float(m.group(1).replace(",", "."))

    # Manufacturer / producer
    manufacturer = raw.get("manufacturing_places") or None
    if manufacturer:
        manufacturer = str(manufacturer).strip()

    # Country of origin
    origins = raw.get("origins") or None
    if not origins:
        countries = raw.get("countries_tags") or []
        if countries:
            origins = ", ".join(
                tag.split(":", 1)[-1].replace("-", " ").title()
                for tag in countries[:3]
            )
    if origins:
        origins = str(origins).strip()

    # Storage / conservation conditions
    storage = raw.get("conservation_conditions") or None
    if storage:
        storage = str(storage).strip()

    # NOVA group
    nova_raw = raw.get("nova_group")
    nova_group = int(nova_raw) if nova_raw and str(nova_raw).isdigit() else None

    # Categories
    cat_tags = raw.get("categories_tags_es") or raw.get("categories_tags") or []
    categories = None
    if cat_tags:
        names = [tag.split(":", 1)[-1].replace("-", " ") for tag in cat_tags[:5]]
        categories = ", ".join(names)

    # Labels (Bio, Gluten-free, etc.)
    label_tags = raw.get("labels_tags") or []
    labels_str = None
    if label_tags:
        names = [tag.split(":", 1)[-1].replace("-", " ") for tag in label_tags[:8]]
        labels_str = ", ".join(names)

    # Eco-Score
    ecoscore_raw = raw.get("ecoscore_grade") or None
    ecoscore = None
    if ecoscore_raw:
        ecoscore = str(ecoscore_raw).lower().strip()
        if ecoscore not in ("a", "b", "c", "d", "e"):
            ecoscore = None

    # Ingredient analysis tags
    analysis_tags = raw.get("ingredients_analysis_tags") or []
    is_vegan: bool | None = None
    is_vegetarian: bool | None = None
    is_palm_oil_free: bool | None = None
    for tag in analysis_tags:
        tag_lower = tag.lower().strip()
        if tag_lower == "en:vegan":
            is_vegan = True
        elif tag_lower == "en:non-vegan":
            is_vegan = False
        elif tag_lower == "en:vegetarian":
            is_vegetarian = True
        elif tag_lower == "en:non-vegetarian":
            is_vegetarian = False
        elif tag_lower == "en:palm-oil-free":
            is_palm_oil_free = True
        elif tag_lower == "en:palm-oil":
            is_palm_oil_free = False

    # Traces
    traces_tags = raw.get("traces_tags") or []
    traces = None
    if traces_tags:
        trace_names = [
            tag.split(":", 1)[-1].replace("-", " ")
            for tag in traces_tags
            if tag.split(":", 1)[-1].lower() not in ("none", "")
        ]
        if trace_names:
            traces = ", ".join(trace_names)

    # Additives
    additives_tags = raw.get("additives_tags") or []
    additives = None
    if additives_tags:
        add_names = [tag.split(":", 1)[-1].upper() for tag in additives_tags]
        additives = ", ".join(add_names)
    additives_count_raw = raw.get("additives_n")
    additives_count = int(additives_count_raw) if additives_count_raw is not None and str(additives_count_raw).isdigit() else (len(additives_tags) if additives_tags else None)

    # Compared to category
    compared_raw = raw.get("compared_to_category") or None
    compared_to_category = None
    if compared_raw:
        compared_to_category = str(compared_raw).split(":", 1)[-1].replace("-", " ").title()

    # Extra images
    image_front_large_url = raw.get("image_front_url") or None
    image_nutrition_url = raw.get("image_nutrition_url") or None
    image_ingredients_url = raw.get("image_ingredients_url") or None

    # Packaging — translate common terms to Spanish
    packaging_text = raw.get("packaging_text") or None
    if not packaging_text:
        pkg_tags = raw.get("packaging_tags") or []
        if pkg_tags:
            pkg_names = [tag.split(":", 1)[-1].replace("-", " ").title() for tag in pkg_tags[:5]]
            packaging_text = ", ".join(pkg_names)
    if packaging_text:
        packaging_text = _translate_packaging(str(packaging_text).strip())

    # Extra minerals/vitamins (OFF stores values in g per 100g for most)
    sodium_mg = _safe_float(nutriments.get("sodium_100g"))
    if sodium_mg is not None:
        # OFF stores sodium in grams; convert to mg
        sodium_mg = round(sodium_mg * 1000, 1)
    vitamin_c_mg = _safe_float(nutriments.get("vitamin-c_100g"))
    if vitamin_c_mg is not None:
        # OFF stores vitamin C in mg already (nutriments are per 100g)
        vitamin_c_mg = round(vitamin_c_mg, 2)
    calcium_mg = _safe_float(nutriments.get("calcium_100g"))
    if calcium_mg is not None:
        # OFF stores calcium in mg already
        calcium_mg = round(calcium_mg, 1)
    iron_mg = _safe_float(nutriments.get("iron_100g"))
    if iron_mg is not None:
        # OFF stores iron in mg already
        iron_mg = round(iron_mg, 2)

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
        net_weight=net_weight,
        serving_size=serving_size,
        serving_size_g=serving_size_g,
        manufacturer=manufacturer,
        country_of_origin=origins,
        storage_conditions=storage,
        nova_group=nova_group,
        categories=categories,
        labels=labels_str,
        ecoscore=ecoscore,
        is_vegan=is_vegan,
        is_vegetarian=is_vegetarian,
        is_palm_oil_free=is_palm_oil_free,
        traces=traces,
        additives=additives,
        additives_count=additives_count,
        compared_to_category=compared_to_category,
        image_front_large_url=image_front_large_url,
        image_nutrition_url=image_nutrition_url,
        image_ingredients_url=image_ingredients_url,
        packaging=packaging_text,
        sodium_mg=sodium_mg,
        vitamin_c_mg=vitamin_c_mg,
        calcium_mg=calcium_mg,
        iron_mg=iron_mg,
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
