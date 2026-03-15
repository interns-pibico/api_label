"""add ofertas table

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-03-05 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6g7h8i9"
down_revision: Union[str, None] = "c3d4e5f6g7h8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ofertas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("producto_nombre", sa.String(500), nullable=False),
        sa.Column("precio_original", sa.Float(), nullable=True),
        sa.Column("precio_oferta", sa.Float(), nullable=True),
        sa.Column("descuento_porcentaje", sa.Float(), nullable=True),
        sa.Column("imagen_url", sa.Text(), nullable=True),
        sa.Column("producto_url", sa.Text(), nullable=True),
        sa.Column("fuente", sa.String(255), nullable=False),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ofertas_id"), "ofertas", ["id"], unique=False)
    op.create_index(
        op.f("ix_ofertas_producto_nombre"), "ofertas", ["producto_nombre"], unique=False
    )
    op.create_index(
        op.f("ix_ofertas_producto_url"), "ofertas", ["producto_url"], unique=False
    )
    op.create_index(
        op.f("ix_ofertas_fuente"), "ofertas", ["fuente"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ofertas_fuente"), table_name="ofertas")
    op.drop_index(op.f("ix_ofertas_producto_url"), table_name="ofertas")
    op.drop_index(op.f("ix_ofertas_producto_nombre"), table_name="ofertas")
    op.drop_index(op.f("ix_ofertas_id"), table_name="ofertas")
    op.drop_table("ofertas")
