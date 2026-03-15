"""External integration endpoints — barcode lookup."""

from pydantic import BaseModel

from fastapi import APIRouter

from src.core.dependencies import CurrentActiveUser, DbSession
from src.services import integration_service

router = APIRouter(prefix="/integrations", tags=["integrations"])


class ScanRequest(BaseModel):
    code: str


@router.get("/offers", summary="Check if offers exist for a barcode")
async def offers_by_barcode(barcode: str, _user: CurrentActiveUser) -> dict:
    """
    Returns {has_offers: bool, url: str | null} for the given barcode.
    Calls api_offer; fails silently (returns has_offers=false) if the service is down.
    """
    has_offers = await integration_service.check_offers_by_barcode(barcode)
    offer_url = f"https://raquel.pibico.es/offer/ofertas?barcode={barcode}" if has_offers else None
    return {"has_offers": has_offers, "url": offer_url}


@router.get("/barcode/{code}")
async def lookup_barcode(code: str, _user: CurrentActiveUser):
    """
    Look up a barcode via the external api.pibico.es/barcode registry
    and return normalized product data.
    """
    return await integration_service.lookup_and_transform_barcode(code)


@router.post("/scan")
async def scan_barcode(payload: ScanRequest, db: DbSession, _user: CurrentActiveUser):
    """
    Scan a barcode, look it up externally, and check if it exists locally.
    """
    return await integration_service.scan_and_suggest(payload.code, db)
