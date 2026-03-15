import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.base import BaseRepository
from src.models.usage_logs import UsageLog


class UsageLogRepository(BaseRepository[UsageLog]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(UsageLog, db)

    async def get_by_user(
        self, user_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[UsageLog], int]:
        count_result = await self.db.execute(
            select(func.count()).select_from(UsageLog).where(UsageLog.user_id == user_id)
        )
        total = count_result.scalar_one()
        result = await self.db.execute(
            select(UsageLog)
            .where(UsageLog.user_id == user_id)
            .order_by(UsageLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return items, total

    async def get_by_token(
        self, token_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[UsageLog], int]:
        count_result = await self.db.execute(
            select(func.count()).select_from(UsageLog).where(UsageLog.token_id == token_id)
        )
        total = count_result.scalar_one()
        result = await self.db.execute(
            select(UsageLog)
            .where(UsageLog.token_id == token_id)
            .order_by(UsageLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return items, total

    async def get_stats_aggregated(
        self,
        user_id: uuid.UUID | None = None,
        token_id: uuid.UUID | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> dict:
        query = select(
            func.count().label("total"),
            func.sum(
                sa.cast(
                    sa.case(
                        (
                            (UsageLog.status_code >= 200) & (UsageLog.status_code < 400),
                            1,
                        ),
                        else_=0,
                    ),
                    sa.Integer,
                )
            ).label("success"),
            func.avg(UsageLog.response_time_ms).label("avg_rt"),
        )
        if user_id:
            query = query.where(UsageLog.user_id == user_id)
        if token_id:
            query = query.where(UsageLog.token_id == token_id)
        if since:
            query = query.where(UsageLog.created_at >= since)
        if until:
            query = query.where(UsageLog.created_at <= until)

        result = await self.db.execute(query)
        row = result.one()
        total = row.total or 0
        success = int(row.success) if row.success is not None else 0
        return {
            "total_requests": total,
            "success_requests": success,
            "error_requests": total - success,
            "avg_response_time_ms": float(row.avg_rt) if row.avg_rt is not None else None,
            "period_start": since,
            "period_end": until,
        }
