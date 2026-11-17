"""Search providers module."""

from app.services.search.providers.base import BaseSearchProvider
from app.services.search.providers.brave import BraveSearchProvider
from app.services.search.providers.duckduckgo import DuckDuckGoProvider
from app.services.search.providers.external import ExternalSearchProvider
from app.services.search.providers.google import GoogleSearchProvider
from app.services.search.providers.internal import InternalSearchProvider
from app.services.search.providers.registry import ExternalSearchRegistry
from app.services.search.providers.semantic_scholar import SemanticScholarProvider
from app.services.search.providers.wikipedia import WikipediaProvider

__all__ = [
    "BaseSearchProvider",
    "InternalSearchProvider",
    "ExternalSearchProvider",
    "SemanticScholarProvider",
    "WikipediaProvider",
    "BraveSearchProvider",
    "GoogleSearchProvider",
    "DuckDuckGoProvider",
    "ExternalSearchRegistry",
]
