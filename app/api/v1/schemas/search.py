"""Pydantic schemas for the unified multi-domain search API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.schemas.common import PaginationMeta


class SearchResultItemResponse(BaseModel):
    """Normalized single search result schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique composite entity identifier")
    title: str = Field(..., description="Result title")
    snippet: str = Field(default="", description="Snippet or brief description excerpt")
    source_name: str = Field(..., description="Publishing organization or institution")
    published_at: Optional[datetime] = Field(None, description="Publication or verified date")
    category: str = Field(..., description="Domain content category")
    is_verified: bool = Field(default=False, description="Whether source is officially verified")
    url: str = Field(..., description="Original URL or access portal")
    score: float = Field(default=0.0, description="Computed relevance rank score")
    item_type: str = Field(..., description="Entity type: news, paper, scholarship, university, course")
    original_id: Optional[int] = Field(None, description="Primary key ID in database if applicable")
    slug: Optional[str] = Field(None, description="Unique slug if applicable")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary domain attributes")


class UnifiedSearchResponseSchema(BaseModel):
    """Unified search response model with pagination metadata."""

    query: str = Field(..., description="Original search query string")
    category: str = Field(..., description="Category filter applied")
    sort_by: str = Field(..., description="Sorting method used: relevance or date")
    source: str = Field(default="all", description="Source scope used: all, internal, or external")
    items: List[SearchResultItemResponse] = Field(..., description="Ranked search result items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


class SearchHistoryItemResponse(BaseModel):
    """Single search history record."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Log ID")
    query: str = Field(..., description="Search keyword")
    category: Optional[str] = Field(None, description="Category filter used")
    results_count: int = Field(0, description="Results count returned")
    created_at: datetime = Field(..., description="Timestamp of search execution")


class SearchHistoryListResponse(BaseModel):
    """List of recent search history items for user."""

    items: List[SearchHistoryItemResponse] = Field(..., description="Recent search queries")
    total: int = Field(..., description="Total history records")


class SourceCitationSchema(BaseModel):
    """Cited source item in an AI search synthesis."""

    model_config = ConfigDict(from_attributes=True)

    index: int = Field(..., description="Citation index reference e.g. 1")
    title: str = Field(..., description="Title of document or opportunity")
    url: str = Field(..., description="Source destination or portal URL")
    source_name: str = Field(..., description="Publishing organization or institution")
    published_at: Optional[datetime] = Field(None, description="Publication timestamp")
    category: str = Field(default="STEM", description="Domain category")
    is_verified: bool = Field(default=False, description="Whether from verified source")


class SearchAISummarySchema(BaseModel):
    """Synthesized AI search overview with source citations and follow-up guidance."""

    model_config = ConfigDict(from_attributes=True)

    query: str = Field(..., description="Queried subject or term")
    executive_summary: str = Field(..., description="High-level factual synthesis")
    sourced_facts: List[str] = Field(default_factory=list, description="Findings with citation references [1], [2]")
    analytical_implications: List[str] = Field(
        default_factory=list, description="Practical and architectural deductions"
    )
    source_citations: List[SourceCitationSchema] = Field(default_factory=list, description="Referenced sources")
    related_questions: List[str] = Field(default_factory=list, description="Follow-up exploration questions")
    research_recommendations: List[str] = Field(default_factory=list, description="Actionable next research avenues")
    disclaimer: str = Field(..., description="Accuracy and attribution disclaimer")


class SourceComparisonRequest(BaseModel):
    """Request payload to compare two search result items."""

    topic: Optional[str] = Field(None, description="Topic or comparison focal point")
    item_a: SearchResultItemResponse = Field(..., description="First item to compare")
    item_b: SearchResultItemResponse = Field(..., description="Second item to compare")


class SourceComparisonSchema(BaseModel):
    """Comparative analysis response between two distinct sources."""

    model_config = ConfigDict(from_attributes=True)

    topic: str = Field(..., description="Subject domain of comparison")
    source_a: SourceCitationSchema = Field(..., description="First source")
    source_b: SourceCitationSchema = Field(..., description="Second source")
    common_ground: List[str] = Field(default_factory=list, description="Agreed consensus or common principles")
    divergent_points: List[str] = Field(
        default_factory=list, description="Points of divergence or contrasting methodology"
    )
    synthesis: str = Field(..., description="Unbiased objective synthesis")
    recommended_context: str = Field(..., description="Recommended application context")
