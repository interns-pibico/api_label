"""Product service."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from src.db.repositories.category_repository import CategoryRepository
from src.db.repositories.product_repository import ProductRepository
from src.models.products import Product
from src.models.users import User
from src.schemas.product import ProductCreate, ProductPatch, ProductUpdate
from src.services.label_engine.registry import get_generator


async def _validate_regulatory_data(
    category_id: uuid.UUID, regulatory_data: dict | None, db: AsyncSession
) -> None:
    """Validate regulatory_data against the category's schema / generator."""
    if regulatory_data is None:
        return
    cat_repo = CategoryRepository(db)
    category = await cat_repo.get(category_id)
    if category is None:
        raise NotFoundException(detail="Category not found")

    generator = get_generator(category.code)
    if generator is not None:
        errors = generator.validate_data(regulatory_data)
        if errors:
            raise BadRequestException(
                detail=f"regulatory_data validation failed: {'; '.join(errors)}"
            )


async def get_product(product_id: uuid.UUID, user: User, db: AsyncSession) -> Product:
    repo = ProductRepository(db)
    product = await repo.get(product_id)
    if product is None or not product.is_active:
        raise NotFoundException(detail="Product not found")
    if not user.is_admin and product.user_id != user.id:
        raise ForbiddenException(detail="Access to this product is forbidden")
    return product


async def list_products(
    user: User,
    db: AsyncSession,
    offset: int = 0,
    limit: int = 20,
    sector: str | None = None,
) -> tuple[list[Product], int]:
    repo = ProductRepository(db)
    return await repo.get_multi_for_user_or_admin(
        user_id=user.id, is_admin=user.is_admin, offset=offset, limit=limit, sector=sector
    )


async def get_product_by_barcode(barcode: str, db: AsyncSession) -> Product:
    repo = ProductRepository(db)
    product = await repo.get_by_barcode(barcode)
    if product is None:
        raise NotFoundException(detail=f"Product with barcode '{barcode}' not found")
    return product


async def create_product(data: ProductCreate, user: User, db: AsyncSession) -> Product:
    await _validate_regulatory_data(data.category_id, data.regulatory_data, db)

    # Verify category exists
    cat_repo = CategoryRepository(db)
    if not await cat_repo.get(data.category_id):
        raise NotFoundException(detail="Category not found")

    repo = ProductRepository(db)
    product = Product(
        id=uuid.uuid4(),
        user_id=user.id,
        category_id=data.category_id,
        name=data.name,
        brand=data.brand,
        barcode=data.barcode,
        description=data.description,
        regulatory_data=data.regulatory_data,
        image_url=data.image_url,
        is_active=True,
    )
    created = await repo.create(product)

    if data.barcode:
        import asyncio
        from src.services.integration_service import notify_offer_enrich
        asyncio.create_task(notify_offer_enrich())

    return created


async def update_product(
    product_id: uuid.UUID, data: ProductUpdate, user: User, db: AsyncSession
) -> Product:
    repo = ProductRepository(db)
    product = await repo.get(product_id)
    if product is None or not product.is_active:
        raise NotFoundException(detail="Product not found")
    if not user.is_admin and product.user_id != user.id:
        raise ForbiddenException(detail="Access to this product is forbidden")

    update_data = data.model_dump(exclude_none=True)
    category_id = update_data.get("category_id", product.category_id)
    regulatory_data = update_data.get("regulatory_data", None)
    if regulatory_data is not None:
        await _validate_regulatory_data(category_id, regulatory_data, db)

    updated = await repo.update(product, update_data)

    if update_data.get("barcode"):
        import asyncio
        from src.services.integration_service import notify_offer_enrich
        asyncio.create_task(notify_offer_enrich())

    return updated


async def patch_product(
    product_id: uuid.UUID, data: ProductPatch, user: User, db: AsyncSession
) -> Product:
    repo = ProductRepository(db)
    product = await repo.get(product_id)
    if product is None or not product.is_active:
        raise NotFoundException(detail="Product not found")
    if not user.is_admin and product.user_id != user.id:
        raise ForbiddenException(detail="Access to this product is forbidden")

    update_data = data.model_dump(exclude_none=True)
    return await repo.update(product, update_data)


async def delete_product(product_id: uuid.UUID, user: User, db: AsyncSession) -> None:
    repo = ProductRepository(db)
    product = await repo.get(product_id)
    if product is None or not product.is_active:
        raise NotFoundException(detail="Product not found")
    if not user.is_admin and product.user_id != user.id:
        raise ForbiddenException(detail="Access to this product is forbidden")
    # Soft delete
    await repo.update(product, {"is_active": False})
