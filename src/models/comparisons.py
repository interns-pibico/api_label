import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LabelComparison(Base):
    __tablename__ = "label_comparisons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("labels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scanned_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    discrepancies: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    compliance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    compared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
