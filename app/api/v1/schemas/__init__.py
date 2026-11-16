"""Common schemas for v1 API."""

from app.api.v1.schemas.ai import (
    AIExplainRequest,
    AIExplainResponse,
    AISummarizeRequest,
    AISummarizeResponse,
)
from app.api.v1.schemas.categories import CategoryDetailResponse, CategoryListResponse
from app.api.v1.schemas.common import ErrorDetail, ErrorResponse, HealthResponse, PaginationMeta
from app.api.v1.schemas.news import ArticleResponse, CategorySummary, PaginatedNewsResponse, SourceSummary
from app.api.v1.schemas.research import PaginatedResearchResponse, ResearchPaperResponse
from app.api.v1.schemas.trending import TrendingItemResponse, TrendingListResponse

__all__ = [
    "HealthResponse",
    "ErrorDetail",
    "ErrorResponse",
    "PaginationMeta",
    "ArticleResponse",
    "PaginatedNewsResponse",
    "SourceSummary",
    "CategorySummary",
    "CategoryDetailResponse",
    "CategoryListResponse",
    "ResearchPaperResponse",
    "PaginatedResearchResponse",
    "TrendingItemResponse",
    "TrendingListResponse",
    "AISummarizeRequest",
    "AISummarizeResponse",
    "AIExplainRequest",
    "AIExplainResponse",
]
