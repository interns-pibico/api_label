import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UsageLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    token_id: uuid.UUID | None
    endpoint: str
    method: str
    status_code: int | None
    response_time_ms: int | None
    ip_address: str | None
    created_at: datetime


class UsageStatsResponse(BaseModel):
    total_requests: int
    success_requests: int
    error_requests: int
    avg_response_time_ms: float | None
    period_start: datetime | None
    period_end: datetime | None
