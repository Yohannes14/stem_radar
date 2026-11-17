"""Domain models and shared data structures for STEM RADAR unified search."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SearchCategory(str, Enum):
    """Supported unified search domain categories."""

    ALL = "all"
    NEWS = "news"
    RESEARCH = "research"
    SCHOLARSHIPS = "scholarships"
    UNIVERSITIES = "universities"
    COURSES = "courses"
    STUDY_MATERIALS = "study_materials"
    TECHNOLOGY = "technology"
    PROGRAMMING = "programming"
    PROJECTS = "projects"


class SearchSort(str, Enum):
    """Sort criteria for search rankings."""

    RELEVANCE = "relevance"
    DATE = "date"


class SearchResultItem(BaseModel):
    """Normalized search result item across all indexable domains."""

    id: str = Field(..., description="Unique composite identifier (e.g. 'news:42', 'opp:12')")
    title: str = Field(..., description="Result title")
    snippet: str = Field(default="", description="Snippet or description excerpt")
    source_name: str = Field(..., description="Publisher, provider, or university name")
    published_at: Optional[datetime] = Field(None, description="Original publication or verified date")
    category: str = Field(..., description="Content category tag")
    is_verified: bool = Field(default=False, description="Whether item is from an officially verified source")
    url: str = Field(..., description="Original URL or access destination")
    score: float = Field(default=0.0, description="Computed relevance rank score")
    item_type: str = Field(..., description="Core entity type: news, paper, scholarship, university, course")
    original_id: Optional[int] = Field(None, description="Underlying database primary key ID")
    slug: Optional[str] = Field(None, description="Unique slug if available")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Domain-specific supplementary attributes")


class UnifiedSearchResponse(BaseModel):
    """Aggregated and paginated unified search results response."""

    items: List[SearchResultItem] = Field(default_factory=list, description="Ranked search results")
    total_items: int = Field(default=0, description="Total matching items across queried categories")
    page: int = Field(default=1, description="Current page number (1-indexed)")
    page_size: int = Field(default=10, description="Items returned per page")
    total_pages: int = Field(default=1, description="Total calculated pages")
    query: str = Field(..., description="Original search query string")
    category: str = Field(default="all", description="Category filter applied")
    sort_by: str = Field(default="relevance", description="Sorting method used: relevance or date")

