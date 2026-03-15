"""Label comparison service — scan vs label field-by-field comparison."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ForbiddenException, NotFoundException
from src.db.repositories.comparison_repository import ComparisonRepository
from src.db.repositories.label_repository import LabelRepository
from src.db.repositories.product_repository import ProductRepository
from src.models.comparisons import LabelComparison
from src.models.users import User
from src.schemas.comparison import ComparisonCreate, ComplianceStatsResponse


def _compare_fields(label_data: dict, scanned_data: dict) -> tuple[dict, float]:
    """
    Compare scanned_data against label_data field-by-field.
    Returns (discrepancies, compliance_score 0-100).
    """
    if not label_data or not scanned_data:
        return {}, 0.0

    # Flatten one level from label_data
    nutrition = label_data.get("nutrition_per_100g") or {}
    product_info = label_data.get("product") or {}
    reference = {**nutrition, **product_info}

    discrepancies: dict = {}
    total_fields = 0
    matching_fields = 0

    for field, label_value in reference.items():
        if label_value is None:
            continue
        total_fields += 1
        scanned_value = scanned_data.get(field)
        if scanned_value is None:
            discrepancies[field] = {
                "label": label_value,
                "scanned": None,
                "status": "missing",
            }
        else:
            # Numeric tolerance: allow ±5%
            try:
                lv = float(label_value)
                sv = float(scanned_value)
                if abs(lv - sv) / max(abs(lv), 0.001) <= 0.05:
                    matching_fields += 1
                else:
                    discrepancies[field] = {
                        "label": label_value,
                        "scanned": scanned_value,
                        "status": "mismatch",
                        "delta": round(sv - lv, 4),
                    }
            except (TypeError, ValueError):
                if str(label_value).lower() == str(scanned_value).lower():
                    matching_fields += 1
                else:
                    discrepancies[field] = {
                        "label": label_value,
                        "scanned": scanned_value,
                        "status": "mismatch",
                    }

    score = (matching_fields / total_fields * 100.0) if total_fields > 0 else 100.0
    return discrepancies, round(score, 2)


async def create_comparison(
    data: ComparisonCreate, user: User, db: AsyncSession
) -> LabelComparison:
    product_repo = ProductRepository(db)
    product = await product_repo.get(data.product_id)
    if product is None or not product.is_active:
        raise NotFoundException(detail="Product not found")
    if not user.is_admin and product.user_id != user.id:
        raise ForbiddenException(detail="Access to this product is forbidden")

    label_data: dict = {}
    label_id: uuid.UUID | None = data.label_id

    if label_id is not None:
        label_repo = LabelRepository(db)
        label = await label_repo.get(label_id)
        if label is None:
            raise NotFoundException(detail="Label not found")
        label_data = label.label_data or {}
    else:
        # Use the latest label for this product
        label_repo = LabelRepository(db)
        latest = await label_repo.get_latest_for_product(data.product_id)
        if latest is not None:
            label_id = latest.id
            label_data = latest.label_data or {}

    discrepancies, compliance_score = _compare_fields(label_data, data.scanned_data)

    comparison = LabelComparison(
        id=uuid.uuid4(),
        product_id=data.product_id,
        label_id=label_id,
        scanned_data=data.scanned_data,
        discrepancies=discrepancies,
        compliance_score=compliance_score,
        compared_at=datetime.now(timezone.utc),
    )
    repo = ComparisonRepository(db)
    return await repo.create(comparison)


async def get_comparison(
    comparison_id: uuid.UUID, user: User, db: AsyncSession
) -> LabelComparison:
    repo = ComparisonRepository(db)
    comparison = await repo.get(comparison_id)
    if comparison is None:
        raise NotFoundException(detail="Comparison not found")

    product_repo = ProductRepository(db)
    product = await product_repo.get(comparison.product_id)
    if product is None:
        raise NotFoundException(detail="Associated product not found")
    if not user.is_admin and product.user_id != user.id:
        raise ForbiddenException(detail="Access to this comparison is forbidden")

    return comparison


async def get_comparisons_for_product(
    product_id: uuid.UUID, user: User, db: AsyncSession, offset: int = 0, limit: int = 20
) -> tuple[list[LabelComparison], int]:
    product_repo = ProductRepository(db)
    product = await product_repo.get(product_id)
    if product is None or not product.is_active:
        raise NotFoundException(detail="Product not found")
    if not user.is_admin and product.user_id != user.id:
        raise ForbiddenException(detail="Access to this product is forbidden")

    repo = ComparisonRepository(db)
    return await repo.get_by_product(product_id, offset=offset, limit=limit)


async def get_compliance_stats(
    product_id: uuid.UUID, user: User, db: AsyncSession
) -> ComplianceStatsResponse:
    product_repo = ProductRepository(db)
    product = await product_repo.get(product_id)
    if product is None or not product.is_active:
        raise NotFoundException(detail="Product not found")
    if not user.is_admin and product.user_id != user.id:
        raise ForbiddenException(detail="Access to this product is forbidden")

    repo = ComparisonRepository(db)
    stats = await repo.get_compliance_stats(product_id)
    return ComplianceStatsResponse(product_id=product_id, **stats)
