import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Basket(Base):
    __tablename__ = "baskets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    items: Mapped[list["BasketItem"]] = relationship(
        "BasketItem", back_populates="basket", cascade="all, delete-orphan"
    )


class BasketItem(Base):
    __tablename__ = "basket_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    basket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("baskets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_name: Mapped[str] = mapped_column(String(500), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(100), nullable=True)
    search_query: Mapped[str | None] = mapped_column(String(200), nullable=True)
    imagen_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    basket: Mapped["Basket"] = relationship("Basket", back_populates="items")
