import uuid
from typing import Any, Generic, Type, TypeVar

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    async def get(self, id: uuid.UUID) -> ModelType | None:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(self, offset: int = 0, limit: int = 20) -> tuple[list[ModelType], int]:
        count_result = await self.db.execute(select(func.count()).select_from(self.model))
        total = count_result.scalar_one()
        result = await self.db.execute(select(self.model).offset(offset).limit(limit))
        items = list(result.scalars().all())
        return items, total

    async def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelType, data: dict[str, Any]) -> ModelType:
        for key, value in data.items():
            if value is not None or key in data:
                setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        await self.db.delete(obj)
        await self.db.flush()
