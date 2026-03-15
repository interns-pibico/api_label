"""Label generation orchestration service."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from src.db.repositories.category_repository import CategoryRepository
from src.db.repositories.label_repository import LabelRepository
from src.db.repositories.product_repository import ProductRepository
from src.models.labels import Label, LabelFormat, LabelLanguage
from src.models.users import User
from src.schemas.label import LabelGenerateRequest
from src.services.label_engine.registry import get_generator
from src.services.translation_service import translate_regulatory_data


async def generate_label(
    data: LabelGenerateRequest, user: User, db: AsyncSession
) -> Label:
    product_repo = ProductRepository(db)
    product = await product_repo.get(data.product_id)
    if product is None or not product.is_active:
        raise NotFoundException(detail="Product not found")
    if not user.is_admin and product.user_id != user.id:
        raise ForbiddenException(detail="Access to this product is forbidden")

    cat_repo = CategoryRepository(db)
    category = await cat_repo.get(product.category_id)
    if category is None:
        raise NotFoundException(detail="Product category not found")

    generator = get_generator(category.code)
    if generator is None:
        raise BadRequestException(
            detail=f"No label generator available for category '{category.code}'"
        )

    regulatory_data = product.regulatory_data or {}
    lang = data.language.value

    # Translate text fields when target language differs from storage language
    if lang != settings.DEFAULT_LANGUAGE:
        regulatory_data = await translate_regulatory_data(
            regulatory_data,
            source_lang=settings.DEFAULT_LANGUAGE,
            target_lang=lang,
        )

    product_dict = {
        "name": product.name,
        "brand": product.brand,
        "barcode": product.barcode,
        "description": product.description,
        "regulatory_data": regulatory_data,
    }

    label_json = generator.generate_json(product_dict, lang=lang)
    rendered_html: str | None = None
    if data.format in (LabelFormat.html, LabelFormat.pdf):
        rendered_html = generator.generate_html(product_dict, lang=lang)

    label_repo = LabelRepository(db)
    label = Label(
        id=uuid.uuid4(),
        product_id=product.id,
        format=data.format.value,
        label_data=label_json,
        rendered_html=rendered_html,
        regulation_version=generator.REGULATION_VERSION,
        language=lang,
    )
    saved = await label_repo.create(label)

    # Queue PDF generation if format is pdf
    if data.format == LabelFormat.pdf:
        from src.workers.tasks.label_tasks import generate_label_pdf
        generate_label_pdf.apply_async(args=[str(saved.id)])

    return saved


async def get_label(label_id: uuid.UUID, user: User, db: AsyncSession) -> Label:
    label_repo = LabelRepository(db)
    label = await label_repo.get(label_id)
    if label is None:
        raise NotFoundException(detail="Label not found")

    # Verify product ownership
    product_repo = ProductRepository(db)
    product = await product_repo.get(label.product_id)
    if product is None:
        raise NotFoundException(detail="Associated product not found")
    if not user.is_admin and product.user_id != user.id:
        raise ForbiddenException(detail="Access to this label is forbidden")

    return label


async def get_labels_for_product(
    product_id: uuid.UUID, user: User, db: AsyncSession, offset: int = 0, limit: int = 20
) -> tuple[list[Label], int]:
    product_repo = ProductRepository(db)
    product = await product_repo.get(product_id)
    if product is None or not product.is_active:
        raise NotFoundException(detail="Product not found")
    if not user.is_admin and product.user_id != user.id:
        raise ForbiddenException(detail="Access to this product is forbidden")

    label_repo = LabelRepository(db)
    return await label_repo.get_by_product(product_id, offset=offset, limit=limit)
