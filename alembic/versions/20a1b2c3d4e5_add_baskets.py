"""add_baskets

Revision ID: 20a1b2c3d4e5
Revises: 10423e67cc42
Create Date: 2026-03-12 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20a1b2c3d4e5"
down_revision: Union[str, None] = "10423e67cc42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "baskets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_baskets_user_id", "baskets", ["user_id"])

    op.create_table(
        "basket_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("basket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(500), nullable=False),
        sa.Column("barcode", sa.String(100), nullable=True),
        sa.Column("search_query", sa.String(200), nullable=True),
        sa.Column("imagen_url", sa.Text, nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["basket_id"], ["baskets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_basket_items_basket_id", "basket_items", ["basket_id"])


def downgrade() -> None:
    op.drop_index("ix_basket_items_basket_id", table_name="basket_items")
    op.drop_table("basket_items")
    op.drop_index("ix_baskets_user_id", table_name="baskets")
    op.drop_table("baskets")
