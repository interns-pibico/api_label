
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.base import BaseRepository
from src.models.users import User


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_active_users(self, offset: int = 0, limit: int = 20) -> tuple[list[User], int]:
        count_result = await self.db.execute(
            select(func.count()).select_from(User).where(User.is_active)
        )
        total = count_result.scalar_one()
        result = await self.db.execute(
            select(User).where(User.is_active).offset(offset).limit(limit)
        )
        items = list(result.scalars().all())
        return items, total
