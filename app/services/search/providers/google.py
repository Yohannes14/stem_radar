"""Google Custom Search JSON API provider for authorized web discovery."""

import logging
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.services.search.models import SearchResultItem
from app.services.search.providers.base import BaseSearchProvider
from app.services.search.providers.internal import calculate_relevance_score

logger = logging.getLogger(__name__)

GOOGLE_SEARCH_URL = "https://customsearch.googleapis.com/customsearch/v1"


class GoogleSearchProvider(BaseSearchProvider):
    """Google Programmable Search Engine provider for accredited web discovery."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        cx: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        self.api_key = api_key or settings.google_search_api_key
        self.cx = cx or settings.google_search_engine_id
        self.timeout_seconds = timeout_seconds or settings.external_search_timeout_seconds

    @property
    def name(self) -> str:
        return "google_search"

    def is_available(self) -> bool:
        """Available only when both Google API key and search engine ID (cx) are configured."""
        return bool(settings.external_search_enabled and self.api_key and self.cx)

    async def search(
        self,
        query: str,
        category: Optional[str] = "all",
        sort_by: str = "relevance",
        limit: int = 10,
        offset: int = 0,
    ) -> Tuple[List[SearchResultItem], int]:
        """Execute query against Google Programmable Search."""
        if not self.is_available():
            return [], 0

        clean_query = query.strip()
        start_index = offset + 1  # Google search uses 1-indexed start
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": clean_query,
            "num": min(limit, 10),
            "start": start_index,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(GOOGLE_SEARCH_URL, params=params)
                if resp.status_code != 200:
                    logger.warning("Google Search API error %d: %s", resp.status_code, resp.text[:150])
                    return [], 0

                data = resp.json()
                raw_items = data.get("items", [])
                total_estimated = int(data.get("searchInformation", {}).get("totalResults", len(raw_items)))

                items: List[SearchResultItem] = []
                for it in raw_items:
                    url = it.get("link", "")
                    title = it.get("title", "")
                    snippet = it.get("snippet", "")
                    domain = urlparse(url).netloc or "Google Web"
                    score = calculate_relevance_score(clean_query, title, snippet, is_verified=False)

                    items.append(
                        SearchResultItem(
                            id=f"goog:{abs(hash(url)) % 10000000}",
                            title=title,
                            snippet=snippet[:250],
                            source_name=domain,
                            category="Web Discovery",
                            is_verified=False,
                            url=url,
                            score=max(score, 2.0),
                            item_type="external",
                            metadata={"provider": "Google Custom Search", "domain": domain},
                        )
                    )
                return items, total_estimated

        except httpx.TimeoutException:
            logger.warning("Google Search API request timed out after %.1fs", self.timeout_seconds)
            return [], 0
        except Exception as exc:
            logger.error("Error calling Google Search API: %s", exc)
            return [], 0
