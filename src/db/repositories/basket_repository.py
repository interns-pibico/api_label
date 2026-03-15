"""Repository for Basket and BasketItem models."""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.base import BaseRepository
from src.models.baskets import Basket, BasketItem


class BasketRepository(BaseRepository[Basket]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Basket, db)

    async def get_by_user(self, user_id: UUID) -> list[tuple[Basket, int]]:
        """Return all baskets for a user with their item counts."""
        count_subq = (
            select(BasketItem.basket_id, func.count(BasketItem.id).label("cnt"))
            .group_by(BasketItem.basket_id)
            .subquery()
        )
        stmt = (
            select(Basket, func.coalesce(count_subq.c.cnt, 0).label("item_count"))
            .outerjoin(count_subq, Basket.id == count_subq.c.basket_id)
            .where(Basket.user_id == user_id)
            .order_by(Basket.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return [(row.Basket, row.item_count) for row in result.all()]

    async def count_by_user(self, user_id: UUID) -> int:
        """Return the number of baskets owned by a user."""
        stmt = select(func.count(Basket.id)).where(Basket.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def count_items(self, basket_id: UUID) -> int:
        """Return the number of items in a basket."""
        stmt = select(func.count(BasketItem.id)).where(BasketItem.basket_id == basket_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_items(self, basket_id: UUID) -> list[BasketItem]:
        """Return all items in a basket ordered by creation date."""
        stmt = (
            select(BasketItem)
            .where(BasketItem.basket_id == basket_id)
            .order_by(BasketItem.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_item(self, item_id: UUID) -> BasketItem | None:
        """Return a single BasketItem by its id."""
        stmt = select(BasketItem).where(BasketItem.id == item_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def add_item(self, item: BasketItem) -> BasketItem:
        """Persist a new BasketItem and return the refreshed instance."""
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_item(self, item: BasketItem) -> None:
        """Delete a BasketItem."""
        await self.db.delete(item)
        await self.db.commit()

    async def clear_items(self, basket_id: UUID) -> None:
        """Delete all items belonging to a basket."""
        stmt = delete(BasketItem).where(BasketItem.basket_id == basket_id)
        await self.db.execute(stmt)
        await self.db.commit()
