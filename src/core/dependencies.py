"""Dependency injection helpers for FastAPI routes."""

import uuid
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import CredentialsException, ForbiddenException
from src.core.security import decode_token
from src.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.ROOT_PATH}/api/v1/auth/login", auto_error=False
)


# ---------------------------------------------------------------------------
# Database session
# ---------------------------------------------------------------------------

DbSession = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# JWT user authentication
# ---------------------------------------------------------------------------

async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
):
    """Decode JWT and return the authenticated User."""
    from src.db.repositories.user_repository import UserRepository
    from src.services.auth_service import is_token_blacklisted

    if token is None:
        raise CredentialsException()

    if await is_token_blacklisted(token):
        raise CredentialsException(detail="Token has been revoked")

    payload = decode_token(token)
    if payload is None:
        raise CredentialsException()

    user_id_str: str | None = payload.get("sub")
    if user_id_str is None:
        raise CredentialsException()

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise CredentialsException()

    repo = UserRepository(db)
    user = await repo.get(user_id)
    if user is None:
        raise CredentialsException(detail="User not found")
    return user


async def get_current_active_user(
    user=Depends(get_current_user),
):
    from src.core.exceptions import ForbiddenException
    if not user.is_active:
        raise ForbiddenException(detail="Inactive user")
    return user


async def get_current_admin_user(
    user=Depends(get_current_active_user),
):
    if not user.is_admin:
        raise ForbiddenException(detail="Admin access required")
    return user


async def get_current_subscribed_user(
    user=Depends(get_current_active_user),
):
    """Require active subscription OR admin status.

    Admins always pass. Normal users must have a non-expired subscription.
    """
    if user.has_access:
        return user
    raise ForbiddenException(
        detail="Active subscription required. Visit the pricing page to subscribe."
    )


# ---------------------------------------------------------------------------
# X-API-Key token authentication
# ---------------------------------------------------------------------------

async def get_token_from_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    db: AsyncSession = Depends(get_db),
):
    """Validate X-API-Key header and return the associated ApiToken."""
    from src.services.api_token_service import validate_api_key

    if x_api_key is None:
        raise ForbiddenException(detail="X-API-Key header is required")

    return await validate_api_key(x_api_key, db)


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

from src.models.users import User
from src.models.api_tokens import ApiToken

CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentAdminUser = Annotated[User, Depends(get_current_admin_user)]
CurrentSubscribedUser = Annotated[User, Depends(get_current_subscribed_user)]
ApiKeyAuth = Annotated[ApiToken, Depends(get_token_from_api_key)]
