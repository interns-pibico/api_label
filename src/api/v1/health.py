"""Health check endpoints."""

from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter
from sqlalchemy import text

from src.core.config import settings
from src.core.dependencies import DbSession

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Basic liveness check."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready")
async def ready(db: DbSession):
    """Readiness check — verifies DB and Redis connectivity."""
    errors: list[str] = []

    # Check PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        errors.append(f"database: {exc}")

    # Check Redis
    try:
        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis.ping()
        await redis.aclose()
    except Exception as exc:
        errors.append(f"redis: {exc}")

    if errors:
        return {
            "status": "degraded",
            "errors": errors,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "status": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
