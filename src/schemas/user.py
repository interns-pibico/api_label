import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from src.schemas.auth import _validate_password_strength


# ---------------------------------------------------------------------------
# Subscription plan enum (used in schemas only — DB stores the string value)
# ---------------------------------------------------------------------------

class SubscriptionPlan(str, Enum):
    monthly = "monthly"
    semiannual = "semiannual"
    annual = "annual"


# ---------------------------------------------------------------------------
# User CRUD schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str | None = None
    is_admin: bool = False

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    full_name: str | None = None
    is_active: bool | None = None
    is_admin: bool | None = None


class UserPatch(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return _validate_password_strength(v)


# ---------------------------------------------------------------------------
# Subscription management (admin only)
# ---------------------------------------------------------------------------

class SubscriptionUpdate(BaseModel):
    """Schema for admin to assign/modify a user's subscription."""
    plan: SubscriptionPlan
    start: datetime | None = None  # defaults to now if not provided
    end: datetime | None = None    # auto-calculated from plan if not provided


class SubscriptionRemove(BaseModel):
    """Schema for admin to remove a user's subscription."""
    pass


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subscription_plan: str | None
    subscription_start: datetime | None
    subscription_end: datetime | None
    is_subscription_active: bool


# ---------------------------------------------------------------------------
# User response
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    full_name: str | None
    is_active: bool
    is_admin: bool
    totp_enabled: bool
    subscription_plan: str | None
    subscription_start: datetime | None
    subscription_end: datetime | None
    is_subscription_active: bool
    created_at: datetime
    updated_at: datetime
