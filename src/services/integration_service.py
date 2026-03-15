"""Integration service — orchestrates external barcode API calls."""

import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.services.integrations.barcode_client import lookup_barcode, transform_barcode_response

logger = logging.getLogger(__name__)


async def notify_offer_enrich() -> None:
    """Tell api_offer to run barcode enrichment. Fire-and-forget (errors are silent)."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            from src.core.config import settings as _s
            await client.post(
                f"{_s.OFFER_API_URL}/api/v1/offers/enrich",
                headers={"X-API-Key": _s.OFFER_ADMIN_API_KEY},
            )
    except Exception as exc:
        logger.debug("notify_offer_enrich failed (non-critical): %s", exc)


async def check_offers_by_barcode(ean: str) -> bool:
    """Returns True if api_offer has active offers for this EAN barcode."""
    if not ean:
        return False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                f"{settings.OFFER_API_URL}/api/v1/offers/barcode/{ean}"
            )
            if resp.status_code == 200:
                data = resp.json()
                return isinstance(data, list) and len(data) > 0
    except Exception as exc:
        logger.debug("offer check failed for barcode %s: %s", ean, exc)
    return False


async def lookup_and_transform_barcode(code: str) -> dict:
    """
    Look up a barcode in the external registry and return normalized data
    ready to be used as product creation input.
    """
    raw = await lookup_barcode(code)
    return transform_barcode_response(raw)


async def scan_and_suggest(code: str, db: AsyncSession) -> dict:
    """
    Scan a barcode and suggest product data.
    Also checks if the product already exists in the local DB.
    """
    from src.db.repositories.product_repository import ProductRepository

    transformed = await lookup_and_transform_barcode(code)

    repo = ProductRepository(db)
    existing = await repo.get_by_barcode(code)

    return {
        "barcode": code,
        "external_data": transformed,
        "local_product": {
            "id": str(existing.id) if existing else None,
            "name": existing.name if existing else None,
            "exists": existing is not None,
        },
    }
