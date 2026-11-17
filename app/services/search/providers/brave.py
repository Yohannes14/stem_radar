"""Brave Search API provider for authorized live web search."""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.services.search.models import SearchResultItem
from app.services.search.providers.base import BaseSearchProvider
from app.services.search.providers.internal import calculate_relevance_score

logger = logging.getLogger(__name__)

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


class BraveSearchProvider(BaseSearchProvider):
    """Brave Search API integration for real-time web discovery across STEM topics."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        self.api_key = api_key or settings.brave_search_api_key
        self.timeout_seconds = timeout_seconds or settings.external_search_timeout_seconds

    @property
    def name(self) -> str:
        return "brave_search"

    def is_available(self) -> bool:
        """Available only when legitimate Brave Search API subscription key is present."""
        return bool(settings.external_search_enabled and self.api_key)

    async def search(
        self,
        query: str,
        category: Optional[str] = "all",
        sort_by: str = "relevance",
        limit: int = 10,
        offset: int = 0,
    ) -> Tuple[List[SearchResultItem], int]:
        """Execute web query via Brave Search and normalize into SearchResultItem records."""
        if not self.is_available():
            return [], 0

        clean_query = query.strip()
        params = {
            "q": clean_query,
            "count": min(limit, 20),
            "offset": offset,
            "text_decorations": "false",
            "search_lang": "en",
        }
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(BRAVE_SEARCH_URL, params=params, headers=headers)
                if resp.status_code == 429:
                    logger.warning("Brave Search API rate limit reached (429).")
                    return [], 0
                if resp.status_code != 200:
                    logger.warning("Brave Search API returned error %d: %s", resp.status_code, resp.text[:150])
                    return [], 0

                data = resp.json()
                web_results = data.get("web", {}).get("results", [])
                total_estimated = data.get("web", {}).get("total", len(web_results))

                items: List[SearchResultItem] = []
                for res in web_results:
                    url = res.get("url", "")
                    title = res.get("title", "Web Discovery")
                    snippet = res.get("description", "")
                    domain = urlparse(url).netloc or "Web"
                    page_age = res.get("page_age")

                    pub_dt = None
                    if page_age:
                        try:
                            pub_dt = datetime.fromisoformat(page_age)
                            if pub_dt.tzinfo is None:
                                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                        except Exception:
                            pub_dt = None

                    score = calculate_relevance_score(
                        clean_query, title, snippet, is_verified=False, published_at=pub_dt
                    )

                    items.append(
                        SearchResultItem(
                            id=f"brave:{abs(hash(url)) % 10000000}",
                            title=title,
                            snippet=snippet[:250],
                            source_name=domain,
                            published_at=pub_dt,
                            category="Web Discovery",
                            is_verified=False,
                            url=url,
                            score=max(score, 2.0),
                            item_type="external",
                            metadata={"provider": "Brave Search", "domain": domain},
                        )
                    )
                return items, total_estimated

        except httpx.TimeoutException:
            logger.warning("Brave Search API request timed out after %.1fs", self.timeout_seconds)
            return [], 0
        except Exception as exc:
            logger.error("Error calling Brave Search API: %s", exc)
            return [], 0
