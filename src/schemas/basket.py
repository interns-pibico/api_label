"""Pydantic schemas for the Basket / BasketItem domain."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class OfertaInfo(BaseModel):
    supermarket: str
    product_name: str
    price: float
    original_price: Optional[float] = None
    discount_percent: Optional[float] = None
    barcode: Optional[str] = None
    imagen_url: Optional[str] = None
    offer_url: Optional[str] = None
    scraped_at: Optional[datetime] = None


class BasketCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío")
        return v


class BasketRename(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre no puede estar vacío")
        return v


class BasketSummary(BaseModel):
    id: UUID
    name: str
    item_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BasketItemCreate(BaseModel):
    product_name: str
    barcode: Optional[str] = None
    search_query: Optional[str] = None
    imagen_url: Optional[str] = None
    notes: Optional[str] = None


class BasketItemResponse(BaseModel):
    id: UUID
    basket_id: UUID
    product_name: str
    barcode: Optional[str] = None
    search_query: Optional[str] = None
    imagen_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    best_offer: Optional[OfertaInfo] = None
    all_offers: list[OfertaInfo] = []

    model_config = ConfigDict(from_attributes=True)


class BasketDetailResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    items: list[BasketItemResponse]
    total_estimated: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class BasketSearchResult(BaseModel):
    product_name: str
    barcode: Optional[str] = None
    imagen_url: Optional[str] = None
    supermarket: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    discount_percent: Optional[float] = None
    source: Optional[str] = None  # "mis_productos" | "ofertas"
