"""Subscription management service.

Handles assigning, updating, and removing subscriptions for users.
Only admins can manage subscriptions via the API.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import BadRequestException, NotFoundException
from src.db.repositories.user_repository import UserRepository
from src.models.users import User
from src.schemas.user import SubscriptionPlan, SubscriptionUpdate
from src.services.audit_service import AuditService


# ---------------------------------------------------------------------------
# Plan duration mapping
# ---------------------------------------------------------------------------

PLAN_DURATIONS: dict[str, timedelta] = {
    "monthly": timedelta(days=30),
    "semiannual": timedelta(days=182),
    "annual": timedelta(days=365),
}


def _calculate_end_date(plan: str, start: datetime) -> datetime:
    """Calculate subscription end date from plan type and start date."""
    delta = PLAN_DURATIONS.get(plan)
    if delta is None:
        raise BadRequestException(detail=f"Unknown subscription plan: {plan}")
    return start + delta


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

async def set_subscription(
    user_id: uuid.UUID,
    data: SubscriptionUpdate,
    db: AsyncSession,
    admin_user: User | None = None,
    ip: str | None = None,
) -> User:
    """Assign or update a user's subscription.

    If start is not provided, defaults to now.
    If end is not provided, auto-calculated from plan duration.
    """
    repo = UserRepository(db)
    user = await repo.get(user_id)
    if user is None:
        raise NotFoundException(detail="User not found")

    if user.is_admin:
        raise BadRequestException(
            detail="Admin users have unlimited access and do not need a subscription"
        )

    now = datetime.now(timezone.utc)
    start = data.start or now
    end = data.end or _calculate_end_date(data.plan.value, start)

    if end <= start:
        raise BadRequestException(detail="Subscription end must be after start date")

    update_fields = {
        "subscription_plan": data.plan.value,
        "subscription_start": start,
        "subscription_end": end,
    }

    updated_user = await repo.update(user, update_fields)

    await AuditService.log(
        db,
        action="subscription_updated",
        username=admin_user.username if admin_user else "system",
        user_id=admin_user.id if admin_user else None,
        resource_type="user",
        resource_id=str(user_id),
        ip=ip,
        success=True,
        details={
            "target_username": user.username,
            "plan": data.plan.value,
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
    )

    return updated_user


async def remove_subscription(
    user_id: uuid.UUID,
    db: AsyncSession,
    admin_user: User | None = None,
    ip: str | None = None,
) -> User:
    """Remove a user's subscription (set all subscription fields to None)."""
    repo = UserRepository(db)
    user = await repo.get(user_id)
    if user is None:
        raise NotFoundException(detail="User not found")

    previous_plan = user.subscription_plan

    update_fields = {
        "subscription_plan": None,
        "subscription_start": None,
        "subscription_end": None,
    }

    updated_user = await repo.update(user, update_fields)

    await AuditService.log(
        db,
        action="subscription_removed",
        username=admin_user.username if admin_user else "system",
        user_id=admin_user.id if admin_user else None,
        resource_type="user",
        resource_id=str(user_id),
        ip=ip,
        success=True,
        details={
            "target_username": user.username,
            "previous_plan": previous_plan,
        },
    )

    return updated_user
