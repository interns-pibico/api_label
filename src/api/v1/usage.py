"""Usage log endpoints (admin only)."""

import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Query

from src.core.dependencies import CurrentAdminUser, DbSession
from src.schemas.pagination import PaginatedResponse
from src.schemas.usage import UsageLogResponse, UsageStatsResponse
from src.services import usage_service

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("", response_model=PaginatedResponse[UsageLogResponse])
async def list_usage(
    db: DbSession,
    _admin: CurrentAdminUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """List all usage logs (admin only)."""
    offset = (page - 1) * page_size
    items, total = await usage_service.get_usage_logs(db, offset=offset, limit=page_size)
    pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/stats", response_model=UsageStatsResponse)
async def get_global_stats(
    db: DbSession,
    _admin: CurrentAdminUser,
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
):
    """Get aggregated usage statistics (admin only)."""
    return await usage_service.get_aggregated_stats(db, since=since, until=until)


@router.get("/users/{user_id}", response_model=PaginatedResponse[UsageLogResponse])
async def get_usage_by_user(
    user_id: uuid.UUID,
    db: DbSession,
    _admin: CurrentAdminUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Get usage logs for a specific user (admin only)."""
    offset = (page - 1) * page_size
    items, total = await usage_service.get_usage_by_user(user_id, db, offset=offset, limit=page_size)
    pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/tokens/{token_id}", response_model=PaginatedResponse[UsageLogResponse])
async def get_usage_by_token(
    token_id: uuid.UUID,
    db: DbSession,
    _admin: CurrentAdminUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Get usage logs for a specific API token (admin only)."""
    offset = (page - 1) * page_size
    items, total = await usage_service.get_usage_by_token(token_id, db, offset=offset, limit=page_size)
    pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)
