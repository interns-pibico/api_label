import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LabelFormat(str, Enum):
    html = "html"
    pdf = "pdf"
    json = "json"


class LabelLanguage(str, Enum):
    es = "es"
    en = "en"


class Label(Base):
    __tablename__ = "labels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    format: Mapped[str] = mapped_column(String(10), nullable=False, default=LabelFormat.html.value)
    label_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rendered_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    regulation_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(
        String(5), nullable=False, default=LabelLanguage.es.value
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
