"""Top-level aggregation router for API v1."""

from fastapi import APIRouter

from app.api.v1.endpoints import ai, categories, health, news, research, trending

v1_router = APIRouter(prefix="/api/v1")

# Mount endpoints
v1_router.include_router(health.router)
v1_router.include_router(news.router)
v1_router.include_router(trending.router)
v1_router.include_router(research.router)
v1_router.include_router(categories.router)
v1_router.include_router(ai.router)
