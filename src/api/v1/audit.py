"""Audit log endpoint (admin only) — ISO 27001 A.12.4 / ENS op.exp.8."""

import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Query

from src.core.dependencies import CurrentAdminUser, DbSession
from src.db.repositories.audit_log_repository import AuditLogRepository
from src.schemas.audit_log import AuditLogResponse
from src.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def get_audit_logs(
    db: DbSession,
    _admin: CurrentAdminUser,
    user_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    success: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    """Query audit logs (admin only).

    Filterable by user_id, action, resource_type, time range, and success status.
    Actions: login_success, login_failed, login_blocked, logout,
             user_created, user_updated, user_deleted, password_changed,
             token_created, token_revoked.
    """
    repo = AuditLogRepository(db)
    offset = (page - 1) * page_size
    items, total = await repo.query(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        start_time=start_time,
        end_time=end_time,
        success=success,
        skip=offset,
        limit=page_size,
    )
    pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size, pages=pages
    )
