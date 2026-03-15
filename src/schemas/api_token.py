import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.models.api_tokens import RateLimitTier


class ApiTokenCreate(BaseModel):
    name: str
    rate_limit_tier: RateLimitTier = RateLimitTier.free
    expires_at: datetime | None = None


class ApiTokenUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    rate_limit_tier: RateLimitTier | None = None
    expires_at: datetime | None = None


class ApiTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    is_active: bool
    rate_limit_tier: str
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime


class ApiTokenCreatedResponse(ApiTokenResponse):
    """Returned only once at creation — includes the raw token."""
    raw_token: str
