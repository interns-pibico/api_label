from sqlalchemy import select, func, outerjoin
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.base import BaseRepository
from src.models.categories import RegulatoryCategory
from src.models.products import Product


class CategoryRepository(BaseRepository[RegulatoryCategory]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(RegulatoryCategory, db)

    async def get_by_code(self, code: str) -> RegulatoryCategory | None:
        result = await self.db.execute(
            select(RegulatoryCategory).where(RegulatoryCategory.code == code)
        )
        return result.scalar_one_or_none()

    async def get_active(
        self, offset: int = 0, limit: int = 20, sector: str | None = None
    ) -> tuple[list[RegulatoryCategory], int]:
        base_where = [RegulatoryCategory.is_active == True]
        if sector is not None:
            base_where.append(RegulatoryCategory.sector == sector)

        count_result = await self.db.execute(
            select(func.count())
            .select_from(RegulatoryCategory)
            .where(*base_where)
        )
        total = count_result.scalar_one()
        result = await self.db.execute(
            select(RegulatoryCategory)
            .where(*base_where)
            .order_by(RegulatoryCategory.code)
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return items, total

    async def get_distinct_sectors_with_count(self) -> list[tuple[str, int]]:
        """Return (sector, product_count) pairs counting active products per sector."""
        result = await self.db.execute(
            select(
                RegulatoryCategory.sector,
                func.count(Product.id).label("cnt"),
            )
            .join(Product, Product.category_id == RegulatoryCategory.id, isouter=True)
            .where(RegulatoryCategory.is_active == True)
            .where((Product.is_active == True) | (Product.id == None))
            .group_by(RegulatoryCategory.sector)
            .order_by(RegulatoryCategory.sector)
        )
        return [(row.sector, row.cnt) for row in result.all()]
