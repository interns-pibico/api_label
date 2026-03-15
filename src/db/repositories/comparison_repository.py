import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.base import BaseRepository
from src.models.comparisons import LabelComparison


class ComparisonRepository(BaseRepository[LabelComparison]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(LabelComparison, db)

    async def get_by_product(
        self, product_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[LabelComparison], int]:
        count_result = await self.db.execute(
            select(func.count())
            .select_from(LabelComparison)
            .where(LabelComparison.product_id == product_id)
        )
        total = count_result.scalar_one()
        result = await self.db.execute(
            select(LabelComparison)
            .where(LabelComparison.product_id == product_id)
            .order_by(LabelComparison.compared_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return items, total

    async def get_compliance_stats(self, product_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(
                func.count().label("total"),
                func.avg(LabelComparison.compliance_score).label("avg_score"),
                func.min(LabelComparison.compliance_score).label("min_score"),
                func.max(LabelComparison.compliance_score).label("max_score"),
            ).where(LabelComparison.product_id == product_id)
        )
        row = result.one()
        return {
            "total_comparisons": row.total,
            "avg_compliance_score": float(row.avg_score) if row.avg_score is not None else None,
            "min_compliance_score": float(row.min_score) if row.min_score is not None else None,
            "max_compliance_score": float(row.max_score) if row.max_score is not None else None,
        }
