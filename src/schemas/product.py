import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProductCreate(BaseModel):
    category_id: uuid.UUID
    name: str
    brand: str | None = None
    barcode: str | None = None
    description: str | None = None
    regulatory_data: dict | None = None
    image_url: str | None = None
    image_nutrition_url: str | None = None
    image_ingredients_url: str | None = None
    nutriscore: str | None = None
    nova_group: int | None = None
    ecoscore: str | None = None
    is_vegan: bool | None = None
    is_vegetarian: bool | None = None
    is_palm_oil_free: bool | None = None


class ProductUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    name: str | None = None
    brand: str | None = None
    barcode: str | None = None
    description: str | None = None
    regulatory_data: dict | None = None
    image_url: str | None = None
    image_nutrition_url: str | None = None
    image_ingredients_url: str | None = None
    nutriscore: str | None = None
    nova_group: int | None = None
    ecoscore: str | None = None
    is_vegan: bool | None = None
    is_vegetarian: bool | None = None
    is_palm_oil_free: bool | None = None
    is_active: bool | None = None


class ProductPatch(BaseModel):
    name: str | None = None
    brand: str | None = None
    barcode: str | None = None
    description: str | None = None
    image_url: str | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    category_id: uuid.UUID
    name: str
    brand: str | None
    barcode: str | None
    description: str | None
    regulatory_data: dict | None
    image_url: str | None
    image_nutrition_url: str | None = None
    image_ingredients_url: str | None = None
    nutriscore: str | None = None
    nova_group: int | None = None
    ecoscore: str | None = None
    is_vegan: bool | None = None
    is_vegetarian: bool | None = None
    is_palm_oil_free: bool | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
