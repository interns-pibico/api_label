"""Add product image columns (nutrition, ingredients).

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-03-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f6g7h8i9j0k1"
down_revision = "e5f6g7h8i9j0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("image_nutrition_url", sa.String(1000), nullable=True))
    op.add_column("products", sa.Column("image_ingredients_url", sa.String(1000), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "image_ingredients_url")
    op.drop_column("products", "image_nutrition_url")
