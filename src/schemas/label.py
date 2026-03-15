import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.models.labels import LabelFormat, LabelLanguage


class LabelGenerateRequest(BaseModel):
    product_id: uuid.UUID
    format: LabelFormat = LabelFormat.html
    language: LabelLanguage = LabelLanguage.es


class LabelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    format: str
    label_data: dict | None
    rendered_html: str | None
    regulation_version: str | None
    language: str
    generated_at: datetime


class LabelSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    format: str
    language: str
    regulation_version: str | None
    generated_at: datetime
