"""Pydantic schemas for scientific and research paper endpoints."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.schemas.common import PaginationMeta
from app.api.v1.schemas.news import CategorySummary


class ResearchPaperResponse(BaseModel):
    """Normalized research paper record."""

    id: int = Field(..., description="Unique paper record ID")
    title: str = Field(..., description="Paper title")
    url: str = Field(..., description="Canonical paper URL (e.g. arXiv entry)")
    abstract: Optional[str] = Field(default=None, description="Paper abstract / synopsis")
    published_at: Optional[datetime] = Field(default=None, description="Publication timestamp")
    collected_at: datetime = Field(..., description="Timestamp ingested into STEM RADAR")
    source_name: str = Field(..., description="Research repository source name")
    categories: List[CategorySummary] = Field(default_factory=list, description="Associated STEM categories")
    ai_analysis: Optional[str] = Field(default=None, description="AI-generated research paper methodology breakdown")

    model_config = ConfigDict(from_attributes=True)


class PaginatedResearchResponse(BaseModel):
    """Paginated collection of research papers."""

    items: List[ResearchPaperResponse] = Field(..., description="List of research papers")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")

