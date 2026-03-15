"""User management service with audit logging."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import BadRequestException, ConflictException, NotFoundException
from src.core.security import get_password_hash, verify_password
from src.db.repositories.user_repository import UserRepository
from src.models.users import User
from src.schemas.user import UserCreate, UserUpdate
from src.services.audit_service import AuditService


async def get_user(user_id: uuid.UUID, db: AsyncSession) -> User:
    repo = UserRepository(db)
    user = await repo.get(user_id)
    if user is None:
        raise NotFoundException(detail="User not found")
    return user


async def get_users(db: AsyncSession, offset: int = 0, limit: int = 20) -> tuple[list[User], int]:
    repo = UserRepository(db)
    return await repo.get_multi(offset=offset, limit=limit)


async def create_user(
    data: UserCreate,
    db: AsyncSession,
    admin_user: User | None = None,
    ip: str | None = None,
) -> User:
    repo = UserRepository(db)
    if await repo.get_by_email(data.email):
        raise ConflictException(detail="Email already registered")
    if await repo.get_by_username(data.username):
        raise ConflictException(detail="Username already taken")

    user = User(
        id=uuid.uuid4(),
        email=data.email,
        username=data.username,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        is_active=True,
        is_admin=data.is_admin,
    )
    created = await repo.create(user)

    await AuditService.log(
        db,
        action="user_created",
        username=admin_user.username if admin_user else "system",
        user_id=admin_user.id if admin_user else None,
        resource_type="user",
        resource_id=str(created.id),
        ip=ip,
        success=True,
        details={"new_username": data.username, "is_admin": data.is_admin},
    )

    return created


async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: AsyncSession,
    admin_user: User | None = None,
    ip: str | None = None,
) -> User:
    repo = UserRepository(db)
    user = await repo.get(user_id)
    if user is None:
        raise NotFoundException(detail="User not found")

    update_data = data.model_dump(exclude_none=True)
    if "email" in update_data:
        existing = await repo.get_by_email(update_data["email"])
        if existing and existing.id != user_id:
            raise ConflictException(detail="Email already in use")
    if "username" in update_data:
        existing = await repo.get_by_username(update_data["username"])
        if existing and existing.id != user_id:
            raise ConflictException(detail="Username already in use")

    updated = await repo.update(user, update_data)

    await AuditService.log(
        db,
        action="user_updated",
        username=admin_user.username if admin_user else "system",
        user_id=admin_user.id if admin_user else None,
        resource_type="user",
        resource_id=str(user_id),
        ip=ip,
        success=True,
        details={"fields_changed": list(update_data.keys())},
    )

    return updated


async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession,
    admin_user: User | None = None,
    ip: str | None = None,
) -> None:
    repo = UserRepository(db)
    user = await repo.get(user_id)
    if user is None:
        raise NotFoundException(detail="User not found")

    deleted_username = user.username
    await repo.delete(user)

    await AuditService.log(
        db,
        action="user_deleted",
        username=admin_user.username if admin_user else "system",
        user_id=admin_user.id if admin_user else None,
        resource_type="user",
        resource_id=str(user_id),
        ip=ip,
        success=True,
        details={"deleted_username": deleted_username},
    )


async def deactivate_user(user_id: uuid.UUID, db: AsyncSession) -> User:
    repo = UserRepository(db)
    user = await repo.get(user_id)
    if user is None:
        raise NotFoundException(detail="User not found")
    return await repo.update(user, {"is_active": False})


async def activate_user(user_id: uuid.UUID, db: AsyncSession) -> User:
    repo = UserRepository(db)
    user = await repo.get(user_id)
    if user is None:
        raise NotFoundException(detail="User not found")
    return await repo.update(user, {"is_active": True})


async def change_password(
    user: User,
    current_password: str,
    new_password: str,
    db: AsyncSession,
    ip: str | None = None,
) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise BadRequestException(detail="Current password is incorrect")
    repo = UserRepository(db)
    await repo.update(user, {"hashed_password": get_password_hash(new_password)})

    await AuditService.log(
        db,
        action="password_changed",
        username=user.username,
        user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        ip=ip,
        success=True,
    )
