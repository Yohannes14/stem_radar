"""Unified Search Service package."""

from app.services.search.models import (
    SearchAISummary,
    SearchCategory,
    SearchResultItem,
    SearchSort,
    SearchSource,
    SourceCitation,
    SourceComparison,
    UnifiedSearchResponse,
)
from app.services.search.providers.base import BaseSearchProvider
from app.services.search.providers.external import ExternalSearchProvider
from app.services.search.providers.internal import InternalSearchProvider
from app.services.search.service import SearchService, search_service

__all__ = [
    "SearchService",
    "search_service",
    "SearchResultItem",
    "UnifiedSearchResponse",
    "SearchCategory",
    "SearchSort",
    "SearchSource",
    "SourceCitation",
    "SearchAISummary",
    "SourceComparison",
    "BaseSearchProvider",
    "InternalSearchProvider",
    "ExternalSearchProvider",
]
