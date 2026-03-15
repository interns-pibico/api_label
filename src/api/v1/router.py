"""Aggregates all v1 sub-routers."""

from fastapi import APIRouter

from src.api.v1 import (
    audit,
    auth,
    baskets,
    categories,
    comparisons,
    health,
    integrations,
    internal,
    labels,
    preview,
    product_search,
    products,
    tokens,
    usage,
    users,
)

router = APIRouter()

router.include_router(health.router)
router.include_router(internal.router)
router.include_router(preview.router)          # public, no auth
router.include_router(product_search.router)   # public, no auth — OFF search
router.include_router(auth.router, prefix="/auth")
router.include_router(users.router)
router.include_router(tokens.router)
router.include_router(categories.router)
router.include_router(products.router)
router.include_router(labels.router)
router.include_router(comparisons.router)
router.include_router(integrations.router)
router.include_router(usage.router)
router.include_router(audit.router)
router.include_router(baskets.router)
