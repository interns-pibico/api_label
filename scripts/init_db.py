"""
Initialize the database with required seed data.

Usage (from project root with venv active):
    python scripts/init_db.py
"""

import asyncio
import sys
import os

# Add project root to PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main() -> None:
    from src.db.session import engine, Base
    from src.core.config import settings

    # Import all models to ensure they are registered with Base
    import src.models.users  # noqa: F401
    import src.models.api_tokens  # noqa: F401
    import src.models.categories  # noqa: F401
    import src.models.products  # noqa: F401
    import src.models.labels  # noqa: F401
    import src.models.comparisons  # noqa: F401
    import src.models.usage_logs  # noqa: F401

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from src.models.categories import RegulatoryCategory
    import uuid

    print(f"Connecting to: {settings.DATABASE_URL}")

    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created (or already exist).")

    # Seed regulatory categories
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        from sqlalchemy import select

        existing = await db.execute(
            select(RegulatoryCategory).where(RegulatoryCategory.code == "nutrition_eu")
        )
        if existing.scalar_one_or_none() is None:
            category = RegulatoryCategory(
                id=uuid.uuid4(),
                code="nutrition_eu",
                name="Etiquetado nutricional UE",
                description=(
                    "Categoría de etiquetado nutricional conforme al Reglamento "
                    "(UE) nº 1169/2011 del Parlamento Europeo y del Consejo."
                ),
                schema_definition={
                    "required": [
                        "energy_kj",
                        "energy_kcal",
                        "fat_g",
                        "saturated_fat_g",
                        "carbohydrates_g",
                        "sugars_g",
                        "protein_g",
                        "salt_g",
                    ],
                    "optional": [
                        "fiber_g",
                        "ingredients",
                        "allergens",
                        "net_weight",
                        "manufacturer",
                        "best_before",
                        "storage_conditions",
                        "serving_size_g",
                    ],
                },
                regulations_reference="Reglamento (UE) nº 1169/2011",
                is_active=True,
            )
            db.add(category)
            await db.commit()
            print("Seeded: regulatory category 'nutrition_eu'")
        else:
            print("Seed already exists: 'nutrition_eu' — skipping.")

    await engine.dispose()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
