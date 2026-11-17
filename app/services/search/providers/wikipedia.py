"""Wikipedia open search provider for authoritative STEM definitions, concepts, and encyclopedia articles."""

import logging
from typing import Any, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.services.search.models import SearchResultItem
from app.services.search.providers.base import BaseSearchProvider
from app.services.search.providers.internal import calculate_relevance_score

logger = logging.getLogger(__name__)

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"


class WikipediaProvider(BaseSearchProvider):
    """Authoritative encyclopedia and scientific definitions provider using Wikipedia OpenSearch API."""

    def __init__(self, timeout_seconds: Optional[float] = None) -> None:
        self.timeout_seconds = timeout_seconds or settings.external_search_timeout_seconds

    @property
    def name(self) -> str:
        return "wikipedia"

    def is_available(self) -> bool:
        """Available whenever external search is enabled (zero API keys required)."""
        return bool(settings.external_search_enabled)

    async def search(
        self,
        query: str,
        category: Optional[str] = "all",
        sort_by: str = "relevance",
        limit: int = 5,
        offset: int = 0,
    ) -> Tuple[List[SearchResultItem], int]:
        """Query Wikipedia OpenSearch API for definitions, encyclopedia articles, and reference links."""
        if not self.is_available():
            return [], 0

        clean_query = query.strip()
        if not clean_query:
            return [], 0

        params = {
            "action": "opensearch",
            "search": clean_query,
            "limit": str(min(limit, 10)),
            "namespace": "0",
            "format": "json",
        }
        headers = {
            "User-Agent": "STEM-RADAR/2.0 (Intelligence Bot; contact@stemradar.org)",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(WIKIPEDIA_API_URL, params=params, headers=headers)
                if resp.status_code != 200:
                    logger.warning("Wikipedia API returned status %d", resp.status_code)
                    return [], 0

                data: List[Any] = resp.json()
                if not isinstance(data, list) or len(data) < 4:
                    return [], 0

                _, titles, descriptions, urls = data[0], data[1], data[2], data[3]
                items: List[SearchResultItem] = []

                for title, desc, url in zip(titles, descriptions, urls, strict=False):
                    if not url or not title:
                        continue
                    # Skip empty descriptions or bare disambiguations
                    if not desc or "may refer to:" in desc:
                        continue

                    domain = urlparse(url).netloc or "en.wikipedia.org"
                    score = calculate_relevance_score(clean_query, title, desc, is_verified=True)

                    items.append(
                        SearchResultItem(
                            id=f"wiki:{abs(hash(url)) % 10000000}",
                            title=title,
                            snippet=desc[:280],
                            source_name="Wikipedia",
                            category="Reference & Concept",
                            is_verified=True,
                            url=url,
                            score=max(score, 3.8),
                            item_type="external",
                            metadata={"provider": "Wikipedia", "domain": domain},
                        )
                    )

                sliced = items[offset : offset + limit] if offset < len(items) else []
                return sliced, len(items)

        except httpx.TimeoutException:
            logger.warning("Wikipedia API request timed out after %.1fs", self.timeout_seconds)
            return [], 0
        except Exception as exc:
            logger.warning("Error querying Wikipedia API: %s", exc)
            return [], 0
