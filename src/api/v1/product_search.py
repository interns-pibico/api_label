"""Public product search endpoints — Open Food Facts.

These endpoints are public (no auth required) and rate-limited.
They do NOT consume trial credits — only the preview-by-barcode
endpoint in preview.py counts against the trial limit.
"""

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from src.core.limiter import limiter
from src.services.integrations.openfoodfacts import (
    OFFProduct,
    lookup_barcode,
    search_products,
)

router = APIRouter(prefix="/off", tags=["product-search"])


def _product_summary(p: OFFProduct) -> dict:
    """Return a lightweight summary dict for search results."""
    return {
        "barcode": p.barcode,
        "name": p.name,
        "brand": p.brand,
        "image_url": p.image_url,
        "nutriscore": p.nutriscore,
    }


def _product_full(p: OFFProduct) -> dict:
    """Return full product data including nutrition.

    Structure: top-level basic fields (name, brand, image_url, barcode)
    + regulatory_data dict with all nutrition/label fields for form auto-fill.
    """
    return {
        "name": p.name,
        "brand": p.brand,
        "image_url": p.image_url,
        "barcode": p.barcode,
        "nutriscore": p.nutriscore,
        "nova_group": p.nova_group,
        "ecoscore": p.ecoscore,
        "is_vegan": p.is_vegan,
        "is_vegetarian": p.is_vegetarian,
        "is_palm_oil_free": p.is_palm_oil_free,
        "categories": p.categories,
        "labels": p.labels,
        "traces": p.traces,
        "additives": p.additives,
        "additives_count": p.additives_count,
        "compared_to_category": p.compared_to_category,
        "image_front_large_url": p.image_front_large_url,
        "image_nutrition_url": p.image_nutrition_url,
        "image_ingredients_url": p.image_ingredients_url,
        "packaging": p.packaging,
        "regulatory_data": p.to_regulatory_data(),
    }


@router.get("/search")
@limiter.limit("30/minute")
async def search_off_products(
    request: Request,
    q: str = Query(..., min_length=2, max_length=200, description="Search query"),
):
    """Search Open Food Facts by text.

    Returns up to 6 products with name, brand, image and Nutriscore.
    Does NOT consume trial credits.
    Rate limited: 30 requests/hour per IP.
    """
    results = await search_products(q, page_size=6)
    return [_product_summary(p) for p in results]


@router.get("/barcode-search/{barcode}")
@limiter.limit("30/minute")
async def search_off_barcode(
    request: Request,
    barcode: str,
):
    """Look up a product on Open Food Facts by barcode.

    Returns a single product or 404 if not found.
    Does NOT consume trial credits.
    Rate limited: 30 requests/hour per IP.
    """
    product = await lookup_barcode(barcode)
    if product is None:
        return JSONResponse(
            status_code=404,
            content={"detail": "Producto no encontrado en Open Food Facts"},
        )
    return _product_full(product)
