import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regulatory_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    regulatory_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    image_nutrition_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    image_ingredients_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    nutriscore: Mapped[str | None] = mapped_column(String(1), nullable=True)  # a-e
    nova_group: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)  # 1-4
    ecoscore: Mapped[str | None] = mapped_column(String(1), nullable=True)  # a-e
    is_vegan: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_vegetarian: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_palm_oil_free: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
