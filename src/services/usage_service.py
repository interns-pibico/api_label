"""Usage logging and stats service."""

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ForbiddenException, NotFoundException
from src.db.repositories.usage_log_repository import UsageLogRepository
from src.models.usage_logs import UsageLog
from src.models.users import User
from src.schemas.usage import UsageLogResponse, UsageStatsResponse

# Rate limit daily quotas per tier (requests/day)
TIER_DAILY_LIMITS: dict[str, int] = {
    "free": 100,
    "standard": 1_000,
    "premium": 10_000,
}


async def log_usage(
    endpoint: str,
    method: str,
    status_code: int | None,
    response_time_ms: int | None,
    ip_address: str | None,
    db: AsyncSession,
    user_id: uuid.UUID | None = None,
    token_id: uuid.UUID | None = None,
) -> None:
    log = UsageLog(
        id=uuid.uuid4(),
        user_id=user_id,
        token_id=token_id,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        response_time_ms=response_time_ms,
        ip_address=ip_address,
    )
    repo = UsageLogRepository(db)
    await repo.create(log)


async def get_usage_logs(
    db: AsyncSession, offset: int = 0, limit: int = 20
) -> tuple[list[UsageLog], int]:
    repo = UsageLogRepository(db)
    return await repo.get_multi(offset=offset, limit=limit)


async def get_usage_by_user(
    user_id: uuid.UUID, db: AsyncSession, offset: int = 0, limit: int = 20
) -> tuple[list[UsageLog], int]:
    repo = UsageLogRepository(db)
    return await repo.get_by_user(user_id, offset=offset, limit=limit)


async def get_usage_by_token(
    token_id: uuid.UUID, db: AsyncSession, offset: int = 0, limit: int = 20
) -> tuple[list[UsageLog], int]:
    repo = UsageLogRepository(db)
    return await repo.get_by_token(token_id, offset=offset, limit=limit)


async def get_aggregated_stats(
    db: AsyncSession,
    user_id: uuid.UUID | None = None,
    token_id: uuid.UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> UsageStatsResponse:
    repo = UsageLogRepository(db)
    stats = await repo.get_stats_aggregated(
        user_id=user_id, token_id=token_id, since=since, until=until
    )
    return UsageStatsResponse(**stats)
