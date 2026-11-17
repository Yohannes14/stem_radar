"""Provider adapter for authorized external search APIs (Stage B architecture)."""

import logging
import os
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import httpx

from app.services.search.models import SearchResultItem
from app.services.search.providers.base import BaseSearchProvider

logger = logging.getLogger(__name__)


class ExternalSearchProvider(BaseSearchProvider):
    """External API search provider supporting pluggable search backends with strict safety gates."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.api_key = api_key or os.getenv("EXTERNAL_SEARCH_API_KEY")
        self.endpoint_url = endpoint_url or os.getenv("EXTERNAL_SEARCH_ENDPOINT")
        self.timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "external_api"

    def is_available(self) -> bool:
        """Provider is active only when legitimate external API credentials and endpoint are set."""
        return bool(self.api_key and self.endpoint_url)

    async def search(
        self,
        query: str,
        category: Optional[str] = "all",
        sort_by: str = "relevance",
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[SearchResultItem], int]:
        """Query external search API with timeout safety, credential isolation, and normalization."""
        if not self.is_available():
            logger.debug("External search provider skipped: credentials not configured in environment.")
            return [], 0

        params = {
            "q": query.strip(),
            "category": category or "all",
            "sort": sort_by,
            "limit": limit,
            "offset": offset,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "STEM-RADAR-SearchBot/2.0",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(self.endpoint_url, params=params, headers=headers)
                if response.status_code != 200:
                    logger.warning(
                        "External search provider returned status %d: %s",
                        response.status_code,
                        response.text[:200],
                    )
                    return [], 0

                data = response.json()
                raw_items = data.get("results", [])
                total_count = data.get("total", len(raw_items))

                normalized: List[SearchResultItem] = []
                for item in raw_items:
                    # Parse timestamp safely if provided
                    pub_dt = None
                    if item.get("published_at"):
                        try:
                            pub_dt = datetime.fromisoformat(item["published_at"])
                        except Exception:
                            pub_dt = datetime.now(timezone.utc)

                    normalized.append(
                        SearchResultItem(
                            id=f"ext:{item.get('id', hash(item.get('url', '')))}",
                            title=item.get("title", "Untitled"),
                            snippet=item.get("snippet", "")[:250],
                            source_name=item.get("source_name", "External Web"),
                            published_at=pub_dt,
                            category=item.get("category", "STEM News"),
                            is_verified=bool(item.get("is_verified", False)),
                            url=item.get("url", ""),
                            score=float(item.get("score", 1.0)),
                            item_type="external",
                            metadata=item.get("metadata", {}),
                        )
                    )
                return normalized, total_count

        except httpx.TimeoutException:
            logger.warning("External search provider request timed out after %.1fs", self.timeout_seconds)
            return [], 0
        except Exception as exc:
            logger.error("External search provider encountered failure: %s", exc)
            return [], 0

