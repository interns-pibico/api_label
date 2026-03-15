"""Authentication endpoints."""

from fastapi import APIRouter, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends

from src.core.dependencies import CurrentActiveUser, DbSession
from src.core.limiter import limiter
from src.schemas.auth import RegisterRequest, TokenResponse
from src.schemas.user import UserResponse
from src.services import auth_service

router = APIRouter(tags=["auth"])


def _get_client_ip(request: Request) -> str | None:
    """Extract client IP from X-Real-IP header or request client."""
    ip = request.headers.get("X-Real-IP")
    if not ip and request.client:
        ip = request.client.host
    return ip


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    db: DbSession,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """Authenticate user and return JWT access token.

    Lockout: 5 failed attempts -> 15 min lock.
    Rate limit: 10 requests/minute.
    """
    return await auth_service.login(
        username=form_data.username,
        password=form_data.password,
        db=db,
        ip=_get_client_ip(request),
    )


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: RegisterRequest, db: DbSession):
    """Register a new user account."""
    user = await auth_service.register(data, db)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    db: DbSession,
    current_user: CurrentActiveUser,
):
    """Invalidate the current JWT token."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    if token:
        await auth_service.logout(
            token,
            db=db,
            user=current_user,
            ip=_get_client_ip(request),
        )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentActiveUser):
    """Return the currently authenticated user."""
    return current_user
