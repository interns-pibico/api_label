"""User management endpoints (admin only for most operations)."""

import math
import uuid

from fastapi import APIRouter, Query, Request

from src.core.dependencies import CurrentAdminUser, CurrentActiveUser, DbSession
from src.schemas.pagination import PaginatedResponse
from src.schemas.user import (
    ChangePasswordRequest,
    SubscriptionResponse,
    SubscriptionUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from src.services import subscription_service, user_service

router = APIRouter(prefix="/users", tags=["users"])


def _get_client_ip(request: Request) -> str | None:
    ip = request.headers.get("X-Real-IP")
    if not ip and request.client:
        ip = request.client.host
    return ip


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    db: DbSession,
    _admin: CurrentAdminUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """List all users (admin only)."""
    offset = (page - 1) * page_size
    items, total = await user_service.get_users(db, offset=offset, limit=page_size)
    pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate, db: DbSession, admin: CurrentAdminUser, request: Request
):
    """Create a new user (admin only)."""
    user = await user_service.create_user(
        data, db, admin_user=admin, ip=_get_client_ip(request)
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: uuid.UUID, db: DbSession, _admin: CurrentAdminUser):
    """Get user by ID (admin only)."""
    return await user_service.get_user(user_id, db)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: DbSession,
    admin: CurrentAdminUser,
    request: Request,
):
    """Update a user (admin only)."""
    user = await user_service.update_user(
        user_id, data, db, admin_user=admin, ip=_get_client_ip(request)
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID, db: DbSession, admin: CurrentAdminUser, request: Request
):
    """Delete a user (admin only)."""
    await user_service.delete_user(
        user_id, db, admin_user=admin, ip=_get_client_ip(request)
    )
    await db.commit()


@router.post("/me/change-password", status_code=204)
async def change_password(
    data: ChangePasswordRequest,
    db: DbSession,
    current_user: CurrentActiveUser,
    request: Request,
):
    """Change the current user's password."""
    await user_service.change_password(
        current_user,
        data.current_password,
        data.new_password,
        db,
        ip=_get_client_ip(request),
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Subscription management (admin only)
# ---------------------------------------------------------------------------

@router.put("/{user_id}/subscription", response_model=UserResponse, tags=["subscriptions"])
async def set_user_subscription(
    user_id: uuid.UUID,
    data: SubscriptionUpdate,
    db: DbSession,
    admin: CurrentAdminUser,
    request: Request,
):
    """Assign or update a user's subscription (admin only).

    Plan options: monthly (30 days), semiannual (182 days), annual (365 days).
    If start/end are not provided, defaults to now + plan duration.
    """
    user = await subscription_service.set_subscription(
        user_id, data, db, admin_user=admin, ip=_get_client_ip(request)
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}/subscription", response_model=UserResponse, tags=["subscriptions"])
async def remove_user_subscription(
    user_id: uuid.UUID,
    db: DbSession,
    admin: CurrentAdminUser,
    request: Request,
):
    """Remove a user's subscription (admin only)."""
    user = await subscription_service.remove_subscription(
        user_id, db, admin_user=admin, ip=_get_client_ip(request)
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{user_id}/subscription", response_model=SubscriptionResponse, tags=["subscriptions"])
async def get_user_subscription(
    user_id: uuid.UUID,
    db: DbSession,
    _admin: CurrentAdminUser,
):
    """Get a user's subscription status (admin only)."""
    user = await user_service.get_user(user_id, db)
    return user
