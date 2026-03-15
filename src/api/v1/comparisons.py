"""Label comparison endpoints."""

import math
import uuid

from fastapi import APIRouter, Query

from src.core.dependencies import CurrentActiveUser, DbSession
from src.schemas.comparison import (
    ComparisonCreate,
    ComparisonResponse,
    ComplianceStatsResponse,
)
from src.schemas.pagination import PaginatedResponse
from src.services import comparison_service

router = APIRouter(tags=["comparisons"])


@router.post("/comparisons", response_model=ComparisonResponse, status_code=201)
async def create_comparison(
    data: ComparisonCreate, db: DbSession, current_user: CurrentActiveUser
):
    """Create a label comparison (scanned data vs label data)."""
    comparison = await comparison_service.create_comparison(data, current_user, db)
    await db.commit()
    await db.refresh(comparison)
    return comparison


@router.get("/comparisons/{comparison_id}", response_model=ComparisonResponse)
async def get_comparison(
    comparison_id: uuid.UUID, db: DbSession, current_user: CurrentActiveUser
):
    """Get a comparison by ID."""
    return await comparison_service.get_comparison(comparison_id, current_user, db)


@router.get(
    "/products/{product_id}/comparisons",
    response_model=PaginatedResponse[ComparisonResponse],
)
async def get_comparisons_for_product(
    product_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentActiveUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """List comparisons for a product."""
    offset = (page - 1) * page_size
    items, total = await comparison_service.get_comparisons_for_product(
        product_id, current_user, db, offset=offset, limit=page_size
    )
    pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.get(
    "/products/{product_id}/compliance-stats",
    response_model=ComplianceStatsResponse,
)
async def get_compliance_stats(
    product_id: uuid.UUID, db: DbSession, current_user: CurrentActiveUser
):
    """Get compliance statistics for a product."""
    return await comparison_service.get_compliance_stats(product_id, current_user, db)
