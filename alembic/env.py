"""Alembic environment configuration for api_label."""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# -- Import Base and all models so autogenerate picks them up --
from src.db.session import Base
import src.models.users  # noqa: F401
import src.models.api_tokens  # noqa: F401
import src.models.categories  # noqa: F401
import src.models.products  # noqa: F401
import src.models.labels  # noqa: F401
import src.models.comparisons  # noqa: F401
import src.models.usage_logs  # noqa: F401
import src.models.audit_logs  # noqa: F401
import src.models.baskets  # noqa: F401

# Alembic Config object
config = context.config

# Set up logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Read DATABASE_URL from environment (set by .env or CI)
database_url = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://root:psql4Pibi@localhost:5432/api_label_psql",
)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection required)."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode (async engine)."""
    engine = create_async_engine(database_url, echo=False)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
