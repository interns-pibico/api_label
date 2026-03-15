"""API token (X-API-Key) management service."""

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from src.db.repositories.api_token_repository import ApiTokenRepository
from src.models.api_tokens import ApiToken, RateLimitTier
from src.models.users import User
from src.schemas.api_token import ApiTokenCreate, ApiTokenCreatedResponse, ApiTokenUpdate


def _generate_raw_token(token_id: uuid.UUID) -> str:
    """Generate a raw token in format pak{token_id_short}_{hex32}."""
    random_hex = secrets.token_hex(32)
    return f"pak{str(token_id)[:8]}_{random_hex}"


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def create_token(
    user: User, data: ApiTokenCreate, db: AsyncSession
) -> ApiTokenCreatedResponse:
    repo = ApiTokenRepository(db)

    token_id = uuid.uuid4()
    raw_token = _generate_raw_token(token_id)
    token_hash = _hash_token(raw_token)

    token = ApiToken(
        id=token_id,
        user_id=user.id,
        name=data.name,
        token_hash=token_hash,
        is_active=True,
        rate_limit_tier=data.rate_limit_tier.value,
        expires_at=data.expires_at,
    )
    saved = await repo.create(token)

    return ApiTokenCreatedResponse(
        id=saved.id,
        user_id=saved.user_id,
        name=saved.name,
        is_active=saved.is_active,
        rate_limit_tier=saved.rate_limit_tier,
        expires_at=saved.expires_at,
        last_used_at=saved.last_used_at,
        created_at=saved.created_at,
        raw_token=raw_token,
    )


async def get_token(token_id: uuid.UUID, user: User, db: AsyncSession) -> ApiToken:
    repo = ApiTokenRepository(db)
    token = await repo.get(token_id)
    if token is None:
        raise NotFoundException(detail="Token not found")
    if not user.is_admin and token.user_id != user.id:
        raise ForbiddenException(detail="Access to this token is forbidden")
    return token


async def list_tokens(
    user: User, db: AsyncSession, offset: int = 0, limit: int = 20
) -> tuple[list[ApiToken], int]:
    repo = ApiTokenRepository(db)
    if user.is_admin:
        return await repo.get_multi(offset=offset, limit=limit)
    return await repo.get_by_user(user.id, offset=offset, limit=limit)


async def update_token(
    token_id: uuid.UUID, user: User, data: ApiTokenUpdate, db: AsyncSession
) -> ApiToken:
    repo = ApiTokenRepository(db)
    token = await repo.get(token_id)
    if token is None:
        raise NotFoundException(detail="Token not found")
    if not user.is_admin and token.user_id != user.id:
        raise ForbiddenException(detail="Access to this token is forbidden")
    update_data = data.model_dump(exclude_none=True)
    return await repo.update(token, update_data)


async def revoke_token(token_id: uuid.UUID, user: User, db: AsyncSession) -> None:
    repo = ApiTokenRepository(db)
    token = await repo.get(token_id)
    if token is None:
        raise NotFoundException(detail="Token not found")
    if not user.is_admin and token.user_id != user.id:
        raise ForbiddenException(detail="Access to this token is forbidden")
    await repo.revoke(token)


async def validate_api_key(raw_token: str, db: AsyncSession) -> ApiToken:
    """Validate a raw X-API-Key and return the associated ApiToken."""
    repo = ApiTokenRepository(db)
    token_hash = _hash_token(raw_token)
    token = await repo.get_by_hash(token_hash)

    if token is None:
        raise ForbiddenException(detail="Invalid or inactive API key")

    # Check expiry
    if token.expires_at is not None:
        if datetime.now(timezone.utc) > token.expires_at:
            raise ForbiddenException(detail="API key has expired")

    await repo.update_last_used(token)
    return token
