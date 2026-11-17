"""Pydantic request and response schemas for News API."""

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

    model_config = ConfigDict(from_attributes=True)


class PaginatedNewsResponse(BaseModel):
    """Paginated list of articles."""

    items: List[ArticleResponse] = Field(..., description="List of articles for the requested page")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")

