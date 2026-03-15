"""Regulatory category service."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import BadRequestException, ConflictException, NotFoundException
from src.db.repositories.category_repository import CategoryRepository
from src.models.categories import RegulatoryCategory
from src.schemas.category import CategoryCreate, CategoryUpdate, SectorInfo

_SECTOR_META: dict[str, tuple[str, str]] = {
    "alimentacion": ("Alimentación", "🥗"),
    "cosmetica": ("Cosmética", "💄"),
    "ferreteria": ("Ferretería", "🔧"),
    "electronica": ("Electrónica", "💡"),
}


async def get_category(category_id: uuid.UUID, db: AsyncSession) -> RegulatoryCategory:
    repo = CategoryRepository(db)
    category = await repo.get(category_id)
    if category is None:
        raise NotFoundException(detail="Category not found")
    return category


async def get_category_by_code(code: str, db: AsyncSession) -> RegulatoryCategory:
    repo = CategoryRepository(db)
    category = await repo.get_by_code(code)
    if category is None:
        raise NotFoundException(detail=f"Category with code '{code}' not found")
    return category


async def list_categories(
    db: AsyncSession,
    active_only: bool = True,
    offset: int = 0,
    limit: int = 20,
    sector: str | None = None,
) -> tuple[list[RegulatoryCategory], int]:
    repo = CategoryRepository(db)
    if active_only:
        return await repo.get_active(offset=offset, limit=limit, sector=sector)
    return await repo.get_multi(offset=offset, limit=limit)


async def list_sectors(db: AsyncSession) -> list[SectorInfo]:
    """Return sectors that have at least one active category."""
    repo = CategoryRepository(db)
    rows = await repo.get_distinct_sectors_with_count()
    result: list[SectorInfo] = []
    for sector_code, count in rows:
        meta = _SECTOR_META.get(sector_code, (sector_code.capitalize(), "📦"))
        result.append(
            SectorInfo(sector=sector_code, label=meta[0], icon=meta[1], count=count)
        )
    return result


def _validate_schema_definition(schema_definition: dict | None) -> None:
    """Basic structural validation of a JSON schema definition."""
    if schema_definition is None:
        return
    if not isinstance(schema_definition, dict):
        raise BadRequestException(detail="schema_definition must be a JSON object")
    # Accept any valid dict — callers may use JSON Schema or a custom format


async def create_category(data: CategoryCreate, db: AsyncSession) -> RegulatoryCategory:
    repo = CategoryRepository(db)
    if await repo.get_by_code(data.code):
        raise ConflictException(detail=f"Category with code '{data.code}' already exists")

    _validate_schema_definition(data.schema_definition)

    category = RegulatoryCategory(
        id=uuid.uuid4(),
        code=data.code,
        name=data.name,
        description=data.description,
        schema_definition=data.schema_definition,
        regulations_reference=data.regulations_reference,
        is_active=data.is_active,
        sector=data.sector,
    )
    return await repo.create(category)


async def update_category(
    category_id: uuid.UUID, data: CategoryUpdate, db: AsyncSession
) -> RegulatoryCategory:
    repo = CategoryRepository(db)
    category = await repo.get(category_id)
    if category is None:
        raise NotFoundException(detail="Category not found")

    update_data = data.model_dump(exclude_none=True)
    if "schema_definition" in update_data:
        _validate_schema_definition(update_data["schema_definition"])

    return await repo.update(category, update_data)


async def delete_category(category_id: uuid.UUID, db: AsyncSession) -> None:
    repo = CategoryRepository(db)
    category = await repo.get(category_id)
    if category is None:
        raise NotFoundException(detail="Category not found")
    await repo.delete(category)
