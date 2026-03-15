"""API token management endpoints."""

import math
import uuid

from fastapi import APIRouter, Query

from src.core.dependencies import CurrentActiveUser, DbSession
from src.schemas.api_token import (
    ApiTokenCreate,
    ApiTokenCreatedResponse,
    ApiTokenResponse,
    ApiTokenUpdate,
)
from src.schemas.pagination import PaginatedResponse
from src.schemas.usage import UsageLogResponse
from src.services import api_token_service, usage_service

router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.post("", response_model=ApiTokenCreatedResponse, status_code=201)
async def create_token(
    data: ApiTokenCreate, db: DbSession, current_user: CurrentActiveUser
):
    """Create a new API token. The raw token is only returned once."""
    result = await api_token_service.create_token(current_user, data, db)
    await db.commit()
    return result


@router.get("", response_model=PaginatedResponse[ApiTokenResponse])
async def list_tokens(
    db: DbSession,
    current_user: CurrentActiveUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """List tokens for the current user (admin sees all)."""
    offset = (page - 1) * page_size
    items, total = await api_token_service.list_tokens(current_user, db, offset=offset, limit=page_size)
    pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/{token_id}", response_model=ApiTokenResponse)
async def get_token(token_id: uuid.UUID, db: DbSession, current_user: CurrentActiveUser):
    """Get a specific token."""
    return await api_token_service.get_token(token_id, current_user, db)


@router.put("/{token_id}", response_model=ApiTokenResponse)
async def update_token(
    token_id: uuid.UUID,
    data: ApiTokenUpdate,
    db: DbSession,
    current_user: CurrentActiveUser,
):
    """Update a token."""
    token = await api_token_service.update_token(token_id, current_user, data, db)
    await db.commit()
    await db.refresh(token)
    return token


@router.delete("/{token_id}", status_code=204)
async def revoke_token(token_id: uuid.UUID, db: DbSession, current_user: CurrentActiveUser):
    """Revoke (deactivate) a token."""
    await api_token_service.revoke_token(token_id, current_user, db)
    await db.commit()


@router.get("/{token_id}/usage", response_model=PaginatedResponse[UsageLogResponse])
async def get_token_usage(
    token_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentActiveUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Get usage logs for a specific token."""
    # Verify ownership first
    await api_token_service.get_token(token_id, current_user, db)
    offset = (page - 1) * page_size
    items, total = await usage_service.get_usage_by_token(token_id, db, offset=offset, limit=page_size)
    pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)
