import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.base import BaseRepository
from src.models.categories import RegulatoryCategory
from src.models.products import Product


class ProductRepository(BaseRepository[Product]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Product, db)

    async def search_by_name(
        self, user_id: uuid.UUID, query: str, limit: int = 5
    ) -> list[Product]:
        """Search user's own products by name (ILIKE)."""
        result = await self.db.execute(
            select(Product)
            .where(
                Product.user_id == user_id,
                Product.is_active,
                Product.name.ilike(f"%{query}%"),
            )
            .order_by(Product.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_barcode(self, barcode: str) -> Product | None:
        result = await self.db.execute(
            select(Product).where(Product.barcode == barcode, Product.is_active)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self, user_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[Product], int]:
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Product)
            .where(Product.user_id == user_id, Product.is_active)
        )
        total = count_result.scalar_one()
        result = await self.db.execute(
            select(Product)
            .where(Product.user_id == user_id, Product.is_active)
            .order_by(Product.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return items, total

    async def filter_by_category(
        self, category_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[Product], int]:
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Product)
            .where(Product.category_id == category_id, Product.is_active)
        )
        total = count_result.scalar_one()
        result = await self.db.execute(
            select(Product)
            .where(Product.category_id == category_id, Product.is_active)
            .order_by(Product.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return items, total

    async def get_multi_for_user_or_admin(
        self,
        user_id: uuid.UUID | None,
        is_admin: bool,
        offset: int = 0,
        limit: int = 20,
        sector: str | None = None,
    ) -> tuple[list[Product], int]:
        if sector is None:
            if is_admin:
                return await self.get_multi(offset=offset, limit=limit)
            return await self.get_by_user(user_id=user_id, offset=offset, limit=limit)

        # Sector filter requires JOIN with regulatory_categories
        base_conditions = [
            Product.is_active,
            RegulatoryCategory.sector == sector,
        ]
        if not is_admin:
            base_conditions.append(Product.user_id == user_id)

        count_result = await self.db.execute(
            select(func.count())
            .select_from(Product)
            .join(RegulatoryCategory, Product.category_id == RegulatoryCategory.id)
            .where(*base_conditions)
        )
        total = count_result.scalar_one()
        result = await self.db.execute(
            select(Product)
            .join(RegulatoryCategory, Product.category_id == RegulatoryCategory.id)
            .where(*base_conditions)
            .order_by(Product.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return items, total
