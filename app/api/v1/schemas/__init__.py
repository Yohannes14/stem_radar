"""Common schemas for v1 API."""

from app.api.v1.schemas.common import ErrorDetail, ErrorResponse, HealthResponse, PaginationMeta
from app.api.v1.schemas.news import ArticleResponse, CategorySummary, PaginatedNewsResponse, SourceSummary

__all__ = [
    "HealthResponse",
    "ErrorDetail",
    "ErrorResponse",
    "PaginationMeta",
    "ArticleResponse",
    "PaginatedNewsResponse",
    "SourceSummary",
    "CategorySummary",
]

