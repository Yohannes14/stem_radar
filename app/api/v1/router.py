"""Top-level aggregation router for API v1."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    categories,
    health,
    news,
    radar,
    research,
    resources,
    scholarships,
    search,
    trending,
    universities,
    user,
)

v1_router = APIRouter(prefix="/api/v1")

# Mount endpoints
v1_router.include_router(health.router)
v1_router.include_router(news.router)
v1_router.include_router(search.router)
v1_router.include_router(scholarships.router)
v1_router.include_router(universities.router)
v1_router.include_router(resources.router)
v1_router.include_router(trending.router)
v1_router.include_router(research.router)
v1_router.include_router(categories.router)
v1_router.include_router(ai.router)
v1_router.include_router(radar.router)
v1_router.include_router(user.router)
