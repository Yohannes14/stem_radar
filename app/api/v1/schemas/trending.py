"""Pydantic schemas for trending technological breakthroughs."""

from typing import List

from pydantic import BaseModel, Field

from app.api.v1.schemas.news import ArticleResponse


class TrendingItemResponse(BaseModel):
    """Ranked high-impact technological development."""

    rank: int = Field(..., description="Rank in trending hierarchy (1-indexed)")
    score: float = Field(..., description="Composite intelligence score (0.0 to 100.0)")
    impact_level: str = Field(..., description="Classification: 'breakthrough', 'high', or 'standard'")
    article: ArticleResponse = Field(..., description="Underlying article details")


class TrendingListResponse(BaseModel):
    """Top trending technological developments feed."""

    items: List[TrendingItemResponse] = Field(..., description="Ranked list of developments")
    total: int = Field(..., description="Total items returned")
