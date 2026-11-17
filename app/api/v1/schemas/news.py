"""Pydantic request and response schemas for News API."""

import math
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.schemas.common import PaginationMeta


class SourceSummary(BaseModel):
    """Source summary metadata."""

    id: int
    name: str
    slug: str
    source_type: str

    model_config = ConfigDict(from_attributes=True)


class CategorySummary(BaseModel):
    """Category summary metadata."""

    id: int
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


class ArticleResponse(BaseModel):
    """Structured article payload."""

    id: int = Field(..., description="Unique article ID")
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Original article canonical URL")
    description: Optional[str] = Field(default=None, description="Article summary or preview excerpt")
    content: Optional[str] = Field(default=None, description="Full article text or paper abstract")
    published_at: Optional[datetime] = Field(default=None, description="Original publication timestamp")
    collected_at: datetime = Field(..., description="Collection timestamp in STEM RADAR")
    source: Optional[SourceSummary] = Field(default=None, description="Originating source metadata")
    categories: List[CategorySummary] = Field(default_factory=list, description="Associated STEM categories")
    ai_summary: Optional[str] = Field(default=None, description="Pre-computed or cached AI executive summary")
    ai_analysis: Optional[str] = Field(default=None, description="Pre-computed or cached AI technical analysis")
    reading_time_minutes: int = Field(default=1, description="Estimated reading time in minutes (~200 wpm)")
    why_it_matters: Optional[str] = Field(
        default=None, description="Concise assessment of why this breakthrough matters"
    )
    tags: List[str] = Field(default_factory=list, description="Extracted technology and STEM domain tags")
    is_paper: bool = Field(default=False, description="Whether article is an academic/scientific research paper")

    model_config = ConfigDict(from_attributes=True)


def build_article_response(article) -> ArticleResponse:
    """Helper constructing an ArticleResponse model populated with reading time, tags, and paper flags."""
    raw_text = (article.content or article.description or article.title or "").strip()
    words = len(raw_text.split())
    reading_time = max(1, math.ceil(words / 200)) if words > 0 else 1

    is_paper = bool(article.source and article.source.source_type == "arxiv")

    tags = []
    if article.categories:
        tags.extend([f"#{c.slug.replace('-', '')}" for c in article.categories])

    why_matters = None
    if article.description:
        first_sentence = article.description.strip().split(". ")[0].strip()
        why_matters = f"{first_sentence}." if not first_sentence.endswith(".") else first_sentence

    return ArticleResponse(
        id=article.id,
        title=article.title,
        url=article.url,
        description=article.description,
        content=article.content,
        published_at=article.published_at,
        collected_at=article.collected_at,
        source=SourceSummary.model_validate(article.source) if article.source else None,
        categories=[CategorySummary.model_validate(c) for c in article.categories] if article.categories else [],
        ai_summary=article.ai_summary,
        ai_analysis=article.ai_analysis,
        reading_time_minutes=reading_time,
        why_it_matters=why_matters,
        tags=tags,
        is_paper=is_paper,
    )


class PaginatedNewsResponse(BaseModel):
    """Paginated list of articles."""

    items: List[ArticleResponse] = Field(..., description="List of articles for the requested page")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
