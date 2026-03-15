import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.base import BaseRepository
from src.models.labels import Label


class LabelRepository(BaseRepository[Label]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Label, db)

    async def get_by_product(
        self, product_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[Label], int]:
        count_result = await self.db.execute(
            select(func.count()).select_from(Label).where(Label.product_id == product_id)
        )
        total = count_result.scalar_one()
        result = await self.db.execute(
            select(Label)
            .where(Label.product_id == product_id)
            .order_by(Label.generated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return items, total

    async def get_latest_for_product(self, product_id: uuid.UUID) -> Label | None:
        result = await self.db.execute(
            select(Label)
            .where(Label.product_id == product_id)
            .order_by(Label.generated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
