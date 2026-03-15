"""Pydantic schemas for audit log responses."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    username: str
    action: str
    resource_type: str | None
    resource_id: str | None
    details: Any | None
    ip_address: str | None
    success: bool
    created_at: datetime
