"""Async client for Open Beauty Facts API.

Provides barcode lookup for cosmetic products, mapping the OBF response
to a pre-fill dict suitable for the label form (Reglamento CE 1223/2009).

API docs: https://world.openbeautyfacts.org/data
Rate limits: 100 req/min for barcode lookups (well within api_label usage).
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger("api_label.obf")

_BASE_URL = "https://world.openbeautyfacts.org"
_USER_AGENT = "api_label/1.0 (https://api.pibico.es/label; contact@pibico.es)"
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# Fields we request from OBF to keep the response payload small
_FIELDS = ",".join([
    "code",
    "product_name",
    "product_name_es",
    "generic_name",
    "brands",
    "quantity",
    "product_quantity",
    "product_quantity_unit",
    "ingredients_text",
    "ingredients_text_es",
    "periods_after_opening",
    "periods_after_opening_tags",
    "expiration_date",
    "manufacturing_places",
    "countries_tags",
    "categories",
    "categories_tags",
    "labels_tags",
    "image_front_url",
    "image_ingredients_url",
    "conservation_conditions",
    "warning",
    "preparation",
    "customer_service",
    "other_information",
    "completeness",
    "states_tags",
])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_pao_months(pao_tags: list) -> int | None:
    """Parse PAO months from OBF tags like ['en:12-months'] -> 12."""
    for tag in pao_tags or []:
        parts = str(tag).split(":")
        if len(parts) == 2:
            numeric_part = parts[1].split("-")[0]
            try:
                return int(numeric_part)
            except ValueError:
                continue
    return None


def _map_product(product: dict, barcode: str) -> dict:
    """Map an OBF product dict to a pre-fill dict for CE 1223/2009 label form.

    Fields that OBF never has (lot_number, responsible_person_eu, product_function)
    are set to None and must be entered manually by the user.
    """
    # Prefer Spanish name if available
    nombre = (
        product.get("product_name_es")
        or product.get("product_name")
        or None
    )

    # Take first brand if multiple are comma-separated
    brands_raw = product.get("brands") or ""
    marca = brands_raw.split(",")[0].strip() or None

    # INCI: prefer Spanish version
    ingredientes_inci = (
        product.get("ingredients_text_es")
        or product.get("ingredients_text")
        or None
    )

    # PAO: parse from tags (rarely available)
    pao_meses = _parse_pao_months(product.get("periods_after_opening_tags") or [])

    # Manufacturing places: can be comma-separated
    mfg_raw = product.get("manufacturing_places") or ""
    paises_fabricacion = [p.strip() for p in mfg_raw.split(",") if p.strip()]
    pais_fabricacion = paises_fabricacion[0] if paises_fabricacion else None

    return {
        # Pre-fillable fields from OBF
        "nombre": nombre,
        "marca": marca,
        "ingredientes_inci": ingredientes_inci,
        "contenido_neto": product.get("quantity") or None,
        "contenido_neto_valor": product.get("product_quantity") or None,
        "contenido_neto_unidad": product.get("product_quantity_unit") or None,
        "pao_meses": pao_meses,
        "fecha_caducidad": product.get("expiration_date") or None,
        "pais_fabricacion": pais_fabricacion,
        "condiciones_conservacion": product.get("conservation_conditions") or None,
        "instrucciones_uso": product.get("preparation") or None,
        "advertencias": product.get("warning") or None,
        "categorias": product.get("categories") or None,
        "imagen_url": (
            product.get("image_front_url")
            or product.get("image_ingredients_url")
            or None
        ),
        "imagen_ingredientes_url": product.get("image_ingredients_url") or None,
        "completitud_obf": product.get("completeness"),

        # Always manual — OBF does not have these (CE 1223/2009 Art. 19)
        "numero_lote": None,            # OBLIGATORIO — Art. 19.1.g
        "responsable_ue": None,         # OBLIGATORIO — Art. 19.1.a
        "funcion_producto": None,       # OBLIGATORIO — Art. 19.1.d

        # Source metadata
        "fuente": "openbeautyfacts",
        "barcode": barcode,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def fetch_by_barcode(barcode: str) -> dict | None:
    """Look up a cosmetic product by barcode on Open Beauty Facts.

    Returns a pre-fill dict mapped to CE 1223/2009 label form fields,
    or None if the product is not found or a network error occurs.

    Args:
        barcode: EAN-13 or EAN-8 barcode string.

    Returns:
        Pre-fill dict or None.
    """
    url = f"{_BASE_URL}/api/v2/product/{barcode}.json"
    params = {"fields": _FIELDS}
    headers = {"User-Agent": _USER_AGENT}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, httpx.TimeoutException, Exception) as exc:
        logger.warning("OBF barcode lookup failed for %r: %s", barcode, exc)
        return None

    # OBF v2: status 1 = found, status 0 = not found
    if data.get("status") != 1:
        return None

    raw_product = data.get("product")
    if not raw_product:
        return None

    return _map_product(raw_product, barcode)
