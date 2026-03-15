"""Internal endpoints — machine-to-machine, no user auth required.

Only accessible from localhost (enforced at nginx level; no sensitive user data exposed).
"""

import logging

from fastapi import APIRouter
from sqlalchemy import select

from src.core.dependencies import DbSession
from src.models.products import Product

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get(
    "/products",
    response_model=list[dict],
    summary="Products with barcode (for api_offer enrichment)",
    include_in_schema=False,
)
async def get_products_with_barcode(db: DbSession) -> list[dict]:
    """Return active products that have a barcode set.

    Used by api_offer to enrich offer records with EAN barcodes via name matching.
    No user auth required — this endpoint is for internal service communication only.
    """
    result = await db.execute(
        select(Product.name, Product.brand, Product.barcode)
        .where(
            Product.is_active == True,  # noqa: E712
            Product.barcode.isnot(None),
            Product.barcode != "",
        )
        .order_by(Product.name)
    )
    rows = result.fetchall()
    logger.debug("internal/products: returning %d products with barcode", len(rows))
    return [{"name": r.name, "brand": r.brand or "", "barcode": r.barcode} for r in rows]
