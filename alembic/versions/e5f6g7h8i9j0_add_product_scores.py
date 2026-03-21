"""Add product scores (nutriscore, nova, ecoscore, ingredient analysis).

Revision ID: e5f6g7h8i9j0
Revises: 20a1b2c3d4e5
Create Date: 2026-03-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e5f6g7h8i9j0"
down_revision = "20a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("nutriscore", sa.String(1), nullable=True))
    op.add_column("products", sa.Column("nova_group", sa.SmallInteger(), nullable=True))
    op.add_column("products", sa.Column("ecoscore", sa.String(1), nullable=True))
    op.add_column("products", sa.Column("is_vegan", sa.Boolean(), nullable=True))
    op.add_column("products", sa.Column("is_vegetarian", sa.Boolean(), nullable=True))
    op.add_column("products", sa.Column("is_palm_oil_free", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "is_palm_oil_free")
    op.drop_column("products", "is_vegetarian")
    op.drop_column("products", "is_vegan")
    op.drop_column("products", "ecoscore")
    op.drop_column("products", "nova_group")
    op.drop_column("products", "nutriscore")
