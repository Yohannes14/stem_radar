"""Common schemas for v1 API."""

from app.api.v1.schemas.academic_resources import AcademicResourceResponse, PaginatedAcademicResourcesResponse
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
from app.api.v1.schemas.scholarships import OpportunityResponse, PaginatedScholarshipsResponse
from app.api.v1.schemas.search import (
    SearchHistoryItemResponse,
    SearchHistoryListResponse,
    SearchResultItemResponse,
    UnifiedSearchResponseSchema,
)
from app.api.v1.schemas.trending import TrendingItemResponse, TrendingListResponse
from app.api.v1.schemas.universities import PaginatedUniversitiesResponse, UniversityProfileResponse

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
    "OpportunityResponse",
    "PaginatedScholarshipsResponse",
    "UniversityProfileResponse",
    "PaginatedUniversitiesResponse",
    "AcademicResourceResponse",
    "PaginatedAcademicResourcesResponse",
    "SearchResultItemResponse",
    "UnifiedSearchResponseSchema",
    "SearchHistoryItemResponse",
    "SearchHistoryListResponse",
    "TrendingItemResponse",
    "TrendingListResponse",
    "AISummarizeRequest",
    "AISummarizeResponse",
    "AIExplainRequest",
    "AIExplainResponse",
]
