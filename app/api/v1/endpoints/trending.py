"""Trending developments endpoint powered by ArticleRanker."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_automation_service, get_db_session
from app.api.v1.schemas.news import ArticleResponse
from app.api.v1.schemas.trending import TrendingItemResponse, TrendingListResponse
from app.services.automation_service import AutomationService

router = APIRouter(prefix="/trending", tags=["Intelligence"])


@router.get(
    "",
    response_model=TrendingListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Trending Technological Breakthroughs",
    description="Retrieve recent developments scored and ranked by composite technological milestone keywords.",
)
async def get_trending(
    limit: int = Query(default=10, ge=1, le=50, description="Max trending items to retrieve"),
    session: AsyncSession = Depends(get_db_session),
    automation: AutomationService = Depends(get_automation_service),
) -> TrendingListResponse:
    """Retrieve top trending STEM breakthroughs."""
    scored_items = await automation.get_trending_developments(limit=limit, session=session)

    items = []
    for rank, (article, score) in enumerate(scored_items, start=1):
        if score >= 80.0:
            impact = "breakthrough"
        elif score >= 65.0:
            impact = "high"
        else:
            impact = "standard"

        items.append(
            TrendingItemResponse(
                rank=rank,
                score=score,
                impact_level=impact,
                article=ArticleResponse.model_validate(article),
            )
        )

    return TrendingListResponse(items=items, total=len(items))
