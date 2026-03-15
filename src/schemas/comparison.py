import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ComparisonCreate(BaseModel):
    product_id: uuid.UUID
    label_id: uuid.UUID | None = None
    scanned_data: dict


class ComparisonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    label_id: uuid.UUID | None
    scanned_data: dict | None
    discrepancies: dict | None
    compliance_score: float | None
    compared_at: datetime


class ComplianceStatsResponse(BaseModel):
    product_id: uuid.UUID
    total_comparisons: int
    avg_compliance_score: float | None
    min_compliance_score: float | None
    max_compliance_score: float | None
