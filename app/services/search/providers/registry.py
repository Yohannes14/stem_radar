"""Registry and coordinator for active external search providers."""

import asyncio
import logging
from typing import List, Optional, Set, Tuple

from app.processors.deduplicator import normalize_url
from app.services.search.models import SearchResultItem
from app.services.search.providers.base import BaseSearchProvider
from app.services.search.providers.brave import BraveSearchProvider
from app.services.search.providers.duckduckgo import DuckDuckGoProvider
from app.services.search.providers.google import GoogleSearchProvider
from app.services.search.providers.semantic_scholar import SemanticScholarProvider
from app.services.search.providers.wikipedia import WikipediaProvider

logger = logging.getLogger(__name__)


class ExternalSearchRegistry:
    """Manages discovery, concurrent querying, and result deduplication across external providers."""

    def __init__(self, providers: Optional[List[BaseSearchProvider]] = None) -> None:
        self.providers: List[BaseSearchProvider] = providers or [
            SemanticScholarProvider(),
            WikipediaProvider(),
            BraveSearchProvider(),
            GoogleSearchProvider(),
            DuckDuckGoProvider(),
        ]

    def get_available_providers(self) -> List[BaseSearchProvider]:
        """Return list of providers with valid credentials or active status."""
        return [p for p in self.providers if p.is_available()]

    async def search_all_external(
        self,
        query: str,
        category: Optional[str] = "all",
        sort_by: str = "relevance",
        limit: int = 10,
        offset: int = 0,
    ) -> Tuple[List[SearchResultItem], int]:
        """Concurrently query all available external search providers and deduplicate results."""
        active = self.get_available_providers()
        if not active:
            return [], 0

        tasks = [p.search(query=query, category=category, sort_by=sort_by, limit=limit, offset=offset) for p in active]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        merged: List[SearchResultItem] = []
        seen_urls: Set[str] = set()
        total_count = 0

        for r in results:
            if isinstance(r, Exception):
                logger.warning("External search provider task failed: %s", r)
                continue
            items, count = r
            total_count += count
            for item in items:
                canon_url = normalize_url(item.url)
                if canon_url in seen_urls:
                    continue
                seen_urls.add(canon_url)
                merged.append(item)

        # Sort according to sort_by
        if sort_by == "date":
            merged.sort(
                key=lambda x: (x.published_at.timestamp() if x.published_at else 0.0, x.score),
                reverse=True,
            )
        else:
            merged.sort(key=lambda x: x.score, reverse=True)

        return merged[:limit], total_count
