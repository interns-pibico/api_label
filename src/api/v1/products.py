"""Product endpoints."""

import math
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from src.core.dependencies import CurrentActiveUser, DbSession
from src.schemas.category import SectorInfo
from src.schemas.pagination import PaginatedResponse
from src.schemas.product import ProductCreate, ProductPatch, ProductResponse, ProductUpdate
from src.services import category_service, product_service
from src.services.integrations import openfoodfacts as off_client
from src.services.integrations.open_beauty_facts import fetch_by_barcode as obf_fetch

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/sectors", response_model=List[SectorInfo])
async def list_sectors(
    db: DbSession,
    _user: CurrentActiveUser,
):
    """Return available sectors (only those with at least one active category)."""
    return await category_service.list_sectors(db)


@router.get("", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    db: DbSession,
    current_user: CurrentActiveUser,
    sector: Optional[str] = Query(default=None, description="Filter products by sector"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """List products (own products for regular users; all for admins), optionally filtered by sector."""
    offset = (page - 1) * page_size
    items, total = await product_service.list_products(
        current_user, db, offset=offset, limit=page_size, sector=sector
    )
    pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    data: ProductCreate, db: DbSession, current_user: CurrentActiveUser
):
    """Create a new product."""
    product = await product_service.create_product(data, current_user, db)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("/lookup")
async def lookup_food_product(
    _user: CurrentActiveUser,
    barcode: str = Query(..., description="EAN barcode to look up on Open Food Facts"),
):
    """Look up a food product by EAN on Open Food Facts.

    Returns pre-fill data for the nutrition label form (Reg. CE 1169/2011).
    Returns 404 if the product is not found in Open Food Facts.
    """
    product = await off_client.lookup_barcode(barcode)
    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Producto no encontrado en Open Food Facts. Introduce los datos manualmente.",
        )
    return {
        "found": True,
        "barcode": barcode,
        "sector": "alimentacion",
        "fuente": "openfoodfacts",
        "datos": product.to_dict(),
    }


@router.get("/lookup-cosmetic")
async def lookup_cosmetic_product(
    _user: CurrentActiveUser,
    barcode: str = Query(..., description="EAN barcode to look up on Open Beauty Facts"),
):
    """Look up a cosmetic product by EAN on Open Beauty Facts.

    Returns pre-fill data for the cosmetic label form (Reglamento CE 1223/2009).
    Only for use with cosmetic products (sector: cosmetica).
    Returns 404 if the product is not found in Open Beauty Facts.
    """
    datos = await obf_fetch(barcode)
    if datos is None:
        raise HTTPException(
            status_code=404,
            detail="Producto no encontrado en Open Beauty Facts. Introduce los datos manualmente.",
        )
    return {
        "found": True,
        "barcode": barcode,
        "sector": "cosmetica",
        "fuente": "openbeautyfacts",
        "datos": datos,
    }


@router.get("/barcode/{barcode}", response_model=ProductResponse)
async def get_product_by_barcode(
    barcode: str, db: DbSession, _user: CurrentActiveUser
):
    """Look up a product by barcode."""
    return await product_service.get_product_by_barcode(barcode, db)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: uuid.UUID, db: DbSession, current_user: CurrentActiveUser
):
    """Get a product by ID."""
    return await product_service.get_product(product_id, current_user, db)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    db: DbSession,
    current_user: CurrentActiveUser,
):
    """Full update of a product."""
    product = await product_service.update_product(product_id, data, current_user, db)
    await db.commit()
    await db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def patch_product(
    product_id: uuid.UUID,
    data: ProductPatch,
    db: DbSession,
    current_user: CurrentActiveUser,
):
    """Partial update of a product."""
    product = await product_service.patch_product(product_id, data, current_user, db)
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: uuid.UUID, db: DbSession, current_user: CurrentActiveUser
):
    """Soft-delete a product."""
    await product_service.delete_product(product_id, current_user, db)
    await db.commit()
