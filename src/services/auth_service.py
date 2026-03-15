"""Authentication service — login, register, logout, JWT validation.

Implements ISO 27001 A.9 / ENS op.acc controls:
- Login lockout: 5 failed attempts -> 15 min lockout (Redis-based)
- Audit logging: login_success, login_failed, login_blocked, logout
- JWT blacklist: revoke tokens on logout via Redis
"""

import hashlib
import uuid
from datetime import timedelta

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import BadRequestException, ConflictException, CredentialsException
from src.core.security import create_access_token, get_password_hash, verify_password
from src.db.repositories.user_repository import UserRepository
from src.models.users import User
from src.schemas.auth import RegisterRequest, TokenResponse
from src.services.audit_service import AuditService


_JWT_BLACKLIST_PREFIX = "jwt_blacklist:"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def login(
    username: str, password: str, db: AsyncSession, ip: str | None = None
) -> TokenResponse:
    """Authenticate user with lockout protection and audit logging."""
    repo = UserRepository(db)
    redis = await _get_redis()

    try:
        locked_key = f"login_locked:{username}"
        fail_key = f"login_failed:{username}"

        # Check if account is locked
        if await redis.exists(locked_key):
            ttl = await redis.ttl(locked_key)
            minutes_left = max(1, (ttl + 59) // 60)
            await AuditService.log(
                db,
                action="login_blocked",
                username=username,
                ip=ip,
                success=False,
                details={"reason": "account_locked", "ttl_seconds": ttl},
            )
            raise CredentialsException(
                detail=f"Account temporarily locked. Try again in {minutes_left} minute(s)."
            )

        # Look up user by username or email
        user: User | None = await repo.get_by_username(username)
        if user is None:
            user = await repo.get_by_email(username)

        if user is None or not verify_password(password, user.hashed_password):
            # Increment failure count
            count = await redis.incr(fail_key)
            await redis.expire(fail_key, settings.LOGIN_LOCKOUT_MINUTES * 60)

            if count >= settings.LOGIN_MAX_ATTEMPTS:
                await redis.set(
                    locked_key, "1", ex=settings.LOGIN_LOCKOUT_MINUTES * 60
                )
                await redis.delete(fail_key)

            await AuditService.log(
                db,
                action="login_failed",
                username=username,
                user_id=user.id if user else None,
                ip=ip,
                success=False,
                details={"attempt": count},
            )
            raise CredentialsException(detail="Incorrect username or password")

        if not user.is_active:
            await AuditService.log(
                db,
                action="login_failed",
                username=user.username,
                user_id=user.id,
                ip=ip,
                success=False,
                details={"reason": "inactive_user"},
            )
            raise CredentialsException(detail="User account is inactive")

        # Successful login — clear lockout state
        await redis.delete(fail_key)
        await redis.delete(locked_key)

        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        await AuditService.log(
            db,
            action="login_success",
            username=user.username,
            user_id=user.id,
            ip=ip,
            success=True,
        )

        return TokenResponse(access_token=access_token, token_type="bearer")
    finally:
        await redis.aclose()


async def register(data: RegisterRequest, db: AsyncSession) -> User:
    repo = UserRepository(db)

    if await repo.get_by_email(data.email):
        raise ConflictException(detail="Email already registered")
    if await repo.get_by_username(data.username):
        raise ConflictException(detail="Username already taken")

    user = User(
        id=uuid.uuid4(),
        email=data.email,
        username=data.username,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        is_active=True,
        is_admin=False,
    )
    return await repo.create(user)


async def logout(token: str, db: AsyncSession | None = None, user: User | None = None, ip: str | None = None) -> None:
    """Blacklist the JWT token in Redis and log the action."""
    redis = await _get_redis()
    key = f"{_JWT_BLACKLIST_PREFIX}{_token_hash(token)}"
    # TTL = access token expire time + 60s buffer
    ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 + 60
    await redis.setex(key, ttl, "1")
    await redis.aclose()

    if db is not None and user is not None:
        await AuditService.log(
            db,
            action="logout",
            username=user.username,
            user_id=user.id,
            ip=ip,
            success=True,
        )


async def is_token_blacklisted(token: str) -> bool:
    redis = await _get_redis()
    key = f"{_JWT_BLACKLIST_PREFIX}{_token_hash(token)}"
    result = await redis.get(key)
    await redis.aclose()
    return result is not None
