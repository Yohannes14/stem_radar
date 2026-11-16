"""Health check endpoint evaluating application and database status."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.api.v1.schemas.common import HealthResponse
from app.database.repository import Repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthResponse,
    summary="Application & Database Health Status",
    description="Check the runtime health, database connectivity, and baseline statistics of STEM RADAR.",
)
async def get_health(session: AsyncSession = Depends(get_db_session)) -> HealthResponse | JSONResponse:
    """Verify application health and database connection."""
    now = datetime.now(timezone.utc)
    try:
        # Ping database with lightweight statement
        await session.execute(text("SELECT 1"))
        repo = Repository(session)
        stats = await repo.get_platform_stats()

        return HealthResponse(
            status="healthy",
            version="0.1.0",
            database="connected",
            timestamp=now,
            details={
                "environment": "active",
                "active_sources": stats.get("active_sources", 0),
                "total_articles": stats.get("total_articles", 0),
                "stem_categories": stats.get("stem_categories", 0),
            },
        )
    except Exception as exc:
        logger.error("Health check failed: database connectivity error: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "degraded",
                "version": "0.1.0",
                "database": "disconnected",
                "timestamp": now.isoformat(),
                "details": {
                    "error": "Database connectivity check failed.",
                },
            },
        )
