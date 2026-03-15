"""Label generation and retrieval endpoints."""

import math
import uuid

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from src.core.dependencies import CurrentActiveUser, DbSession
from src.core.exceptions import BadRequestException, NotFoundException
from src.schemas.label import LabelGenerateRequest, LabelResponse, LabelSummaryResponse
from src.schemas.pagination import PaginatedResponse
from src.services import label_service

router = APIRouter(tags=["labels"])


@router.post("/labels/generate", response_model=LabelResponse, status_code=201)
async def generate_label(
    data: LabelGenerateRequest, db: DbSession, current_user: CurrentActiveUser
):
    """Generate a new label for a product."""
    label = await label_service.generate_label(data, current_user, db)
    await db.commit()
    await db.refresh(label)
    return label


@router.get("/labels/{label_id}", response_model=LabelResponse)
async def get_label(
    label_id: uuid.UUID, db: DbSession, current_user: CurrentActiveUser
):
    """Get a label by ID."""
    return await label_service.get_label(label_id, current_user, db)


@router.get("/labels/{label_id}/html", response_class=HTMLResponse)
async def get_label_html(
    label_id: uuid.UUID, db: DbSession, current_user: CurrentActiveUser
):
    """Get the rendered HTML of a label."""
    label = await label_service.get_label(label_id, current_user, db)
    if label.rendered_html is None:
        raise NotFoundException(detail="HTML not available for this label format")
    return HTMLResponse(content=label.rendered_html, status_code=200)


@router.get("/labels/{label_id}/pdf")
async def get_label_pdf(
    label_id: uuid.UUID, db: DbSession, current_user: CurrentActiveUser
):
    """Get the PDF of a label (triggers generation if not ready)."""
    from fastapi.responses import JSONResponse
    label = await label_service.get_label(label_id, current_user, db)
    if label.format != "pdf":
        raise BadRequestException(detail="This label was not generated in PDF format")

    pdf_path = (label.label_data or {}).get("pdf_path")
    if pdf_path is None:
        return JSONResponse(
            status_code=202,
            content={"detail": "PDF generation in progress, please retry shortly"},
        )

    import os
    from fastapi.responses import FileResponse
    if not os.path.exists(pdf_path):
        return JSONResponse(
            status_code=202,
            content={"detail": "PDF not yet ready, please retry shortly"},
        )
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"label_{label_id}.pdf",
    )


@router.get(
    "/products/{product_id}/labels",
    response_model=PaginatedResponse[LabelSummaryResponse],
)
async def get_labels_for_product(
    product_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentActiveUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """List all labels for a specific product."""
    offset = (page - 1) * page_size
    items, total = await label_service.get_labels_for_product(
        product_id, current_user, db, offset=offset, limit=page_size
    )
    pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)
