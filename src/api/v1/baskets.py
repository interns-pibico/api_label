"""REST endpoints for the Cesta de la Compra (Shopping Basket) feature.

All routes require an active subscription (CurrentSubscribedUser).
The /search route MUST remain before /{basket_id} to avoid path conflicts.
"""

from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from src.core.dependencies import CurrentSubscribedUser, DbSession
from src.schemas.basket import (
    BasketCreate,
    BasketDetailResponse,
    BasketItemCreate,
    BasketItemResponse,
    BasketRename,
    BasketSearchResult,
    BasketSummary,
)
from src.services.basket_service import BasketService

router = APIRouter(prefix="/baskets", tags=["baskets"])


def _svc(db: DbSession) -> BasketService:
    return BasketService(db)


# ── Basket CRUD ────────────────────────────────────────────────────────────────


@router.get("", response_model=list[BasketSummary])
async def list_baskets(current_user: CurrentSubscribedUser, db: DbSession):
    """Return all baskets for the authenticated user."""
    return await _svc(db).list_baskets(current_user.id)


@router.post("", response_model=BasketSummary, status_code=201)
async def create_basket(
    data: BasketCreate, current_user: CurrentSubscribedUser, db: DbSession
):
    """Create a new basket (max 3 per user)."""
    return await _svc(db).create_basket(current_user.id, data)


# NOTE: /search MUST come before /{basket_id} — FastAPI resolves routes in order.


@router.get("/search", response_model=list[BasketSearchResult])
async def search_products(
    current_user: CurrentSubscribedUser,
    db: DbSession,
    q: str = Query(..., min_length=2),
):
    """Search user products and api_offer, return up to 10 unique results."""
    return await _svc(db).search_products(q, current_user.id)


@router.get("/{basket_id}", response_model=BasketDetailResponse)
async def get_basket(
    basket_id: UUID, current_user: CurrentSubscribedUser, db: DbSession
):
    """Return basket detail with enriched offer data for all items."""
    return await _svc(db).get_basket_detail(basket_id, current_user.id)


@router.put("/{basket_id}", response_model=BasketSummary)
async def rename_basket(
    basket_id: UUID,
    data: BasketRename,
    current_user: CurrentSubscribedUser,
    db: DbSession,
):
    """Rename a basket."""
    return await _svc(db).rename_basket(basket_id, current_user.id, data)


@router.delete("/{basket_id}", status_code=204)
async def delete_basket(
    basket_id: UUID, current_user: CurrentSubscribedUser, db: DbSession
):
    """Delete a basket and all its items."""
    await _svc(db).delete_basket(basket_id, current_user.id)


# ── Item CRUD ──────────────────────────────────────────────────────────────────


@router.post("/{basket_id}/items", response_model=BasketItemResponse, status_code=201)
async def add_item(
    basket_id: UUID,
    data: BasketItemCreate,
    current_user: CurrentSubscribedUser,
    db: DbSession,
):
    """Add a product to a basket and return it enriched with offer data."""
    return await _svc(db).add_item(basket_id, current_user.id, data)


@router.delete("/{basket_id}/items/{item_id}", status_code=204)
async def remove_item(
    basket_id: UUID,
    item_id: UUID,
    current_user: CurrentSubscribedUser,
    db: DbSession,
):
    """Remove a single item from a basket."""
    await _svc(db).remove_item(basket_id, item_id, current_user.id)


@router.delete("/{basket_id}/items", status_code=204)
async def clear_items(
    basket_id: UUID, current_user: CurrentSubscribedUser, db: DbSession
):
    """Remove all items from a basket."""
    await _svc(db).clear_items(basket_id, current_user.id)


# ── PDF ────────────────────────────────────────────────────────────────────────


@router.get("/{basket_id}/pdf")
async def download_pdf(
    basket_id: UUID, current_user: CurrentSubscribedUser, db: DbSession
):
    """Generate and return a PDF for the basket."""
    service = _svc(db)
    detail = await service.get_basket_detail(basket_id, current_user.id)
    pdf_path = service.generate_pdf(
        basket_id, detail.name, current_user.username, detail.items
    )
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"cesta_{detail.name.replace(' ', '_')}.pdf",
    )
