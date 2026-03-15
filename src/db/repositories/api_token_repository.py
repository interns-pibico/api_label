import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.base import BaseRepository
from src.models.api_tokens import ApiToken


class ApiTokenRepository(BaseRepository[ApiToken]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(ApiToken, db)

    async def get_by_hash(self, token_hash: str) -> ApiToken | None:
        result = await self.db.execute(
            select(ApiToken).where(ApiToken.token_hash == token_hash, ApiToken.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self, user_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[ApiToken], int]:
        count_result = await self.db.execute(
            select(func.count()).select_from(ApiToken).where(ApiToken.user_id == user_id)
        )
        total = count_result.scalar_one()
        result = await self.db.execute(
            select(ApiToken)
            .where(ApiToken.user_id == user_id)
            .order_by(ApiToken.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return items, total

    async def revoke(self, token: ApiToken) -> ApiToken:
        token.is_active = False
        await self.db.flush()
        await self.db.refresh(token)
        return token

    async def update_last_used(self, token: ApiToken) -> None:
        token.last_used_at = datetime.now(timezone.utc)
        await self.db.flush()
