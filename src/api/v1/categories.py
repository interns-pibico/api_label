"""Regulatory category endpoints."""

import math
import uuid
from typing import Optional

from fastapi import APIRouter, Query

from src.core.dependencies import CurrentActiveUser, CurrentAdminUser, DbSession
from src.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from src.schemas.pagination import PaginatedResponse
from src.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=PaginatedResponse[CategoryResponse])
async def list_categories(
    db: DbSession,
    _user: CurrentActiveUser,
    active_only: bool = Query(default=True),
    sector: Optional[str] = Query(default=None, description="Filter categories by sector"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """List regulatory categories, optionally filtered by sector."""
    offset = (page - 1) * page_size
    items, total = await category_service.list_categories(
        db, active_only=active_only, offset=offset, limit=page_size, sector=sector
    )
    pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(data: CategoryCreate, db: DbSession, _admin: CurrentAdminUser):
    """Create a new regulatory category (admin only)."""
    category = await category_service.create_category(data, db)
    await db.commit()
    await db.refresh(category)
    return category


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: uuid.UUID, db: DbSession, _user: CurrentActiveUser
):
    """Get a category by ID."""
    return await category_service.get_category(category_id, db)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    db: DbSession,
    _admin: CurrentAdminUser,
):
    """Update a category (admin only)."""
    category = await category_service.update_category(category_id, data, db)
    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: uuid.UUID, db: DbSession, _admin: CurrentAdminUser
):
    """Delete a category (admin only)."""
    await category_service.delete_category(category_id, db)
    await db.commit()
