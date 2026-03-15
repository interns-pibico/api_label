import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CategoryCreate(BaseModel):
    code: str
    name: str
    description: str | None = None
    schema_definition: dict | None = None
    regulations_reference: str | None = None
    is_active: bool = True
    sector: str = "alimentacion"


class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    schema_definition: dict | None = None
    regulations_reference: str | None = None
    is_active: bool | None = None
    sector: str | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    schema_definition: dict | None
    regulations_reference: str | None
    is_active: bool
    sector: str
    created_at: datetime
    updated_at: datetime


class SectorInfo(BaseModel):
    sector: str
    label: str
    icon: str
    count: int
