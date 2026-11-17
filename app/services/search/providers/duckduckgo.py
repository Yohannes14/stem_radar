"""DuckDuckGo instant search provider for zero-configuration live web discovery."""

import html
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from app.config import settings
from app.services.search.models import SearchResultItem
from app.services.search.providers.base import BaseSearchProvider
from app.services.search.providers.internal import calculate_relevance_score

logger = logging.getLogger(__name__)

DUCKDUCKGO_API_URL = "https://api.duckduckgo.com/"
DUCKDUCKGO_HTML_URL = "https://html.duckduckgo.com/html/"


class DuckDuckGoProvider(BaseSearchProvider):
    """Zero-configuration live web search provider querying DuckDuckGo open knowledge graph & web."""

    def __init__(self, timeout_seconds: Optional[float] = None) -> None:
        self.timeout_seconds = timeout_seconds or settings.external_search_timeout_seconds

    @property
    def name(self) -> str:
        return "duckduckgo"

    def is_available(self) -> bool:
        """Available whenever external search is enabled (requires zero API keys)."""
        return bool(settings.external_search_enabled)

    async def search(
        self,
        query: str,
        category: Optional[str] = "all",
        sort_by: str = "relevance",
        limit: int = 10,
        offset: int = 0,
    ) -> Tuple[List[SearchResultItem], int]:
        """Query DuckDuckGo for live web information, topics, and references."""
        if not self.is_available():
            return [], 0

        clean_query = query.strip()
        if not clean_query:
            return [], 0

        params = {
            "q": clean_query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "0",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(DUCKDUCKGO_API_URL, params=params)
                items: List[SearchResultItem] = []

                if resp.status_code == 200:
                    data: Dict[str, Any] = resp.json()

                    # 1. Primary abstract result (e.g. Wikipedia / direct knowledge card)
                    abstract_url = data.get("AbstractURL")
                    abstract_text = data.get("AbstractText")
                    heading = data.get("Heading") or clean_query.title()

                    if abstract_url and abstract_text:
                        domain = urlparse(abstract_url).netloc or "DuckDuckGo Web"
                        score = calculate_relevance_score(clean_query, heading, abstract_text, is_verified=False)
                        items.append(
                            SearchResultItem(
                                id=f"ddg:{abs(hash(abstract_url)) % 10000000}",
                                title=heading,
                                snippet=abstract_text[:280],
                                source_name=domain,
                                category="Web Discovery",
                                is_verified=False,
                                url=abstract_url,
                                score=max(score, 3.5),
                                item_type="external",
                                metadata={"provider": "DuckDuckGo", "domain": domain},
                            )
                        )

                    # 2. Related web topics & deep links
                    related = data.get("RelatedTopics", [])
                    for entry in related:
                        sub_topics = entry.get("Topics") if isinstance(entry, dict) and "Topics" in entry else [entry]
                        for top in sub_topics:
                            if not isinstance(top, dict):
                                continue
                            url = top.get("FirstURL", "")
                            text = top.get("Text", "")
                            if not url or not text:
                                continue

                            parts = text.split(" - ", 1)
                            title = parts[0] if parts else text[:60]
                            snippet = parts[1] if len(parts) > 1 else text
                            domain = urlparse(url).netloc or "Web"
                            score = calculate_relevance_score(clean_query, title, snippet, is_verified=False)

                            items.append(
                                SearchResultItem(
                                    id=f"ddg:{abs(hash(url)) % 10000000}",
                                    title=title,
                                    snippet=snippet[:280],
                                    source_name=domain,
                                    category="Web Discovery",
                                    is_verified=False,
                                    url=url,
                                    score=max(score, 2.0),
                                    item_type="external",
                                    metadata={"provider": "DuckDuckGo", "domain": domain},
                                )
                            )

                # 3. Fallback to live HTML web search if Instant Answer returned 0 results
                if not items:
                    html_items, html_count = await self._search_html(client, clean_query, limit=limit, offset=offset)
                    if html_items:
                        return html_items, html_count

                # Slice to requested limit and offset
                sliced = items[offset : offset + limit] if offset < len(items) else []
                return sliced, len(items)

        except httpx.TimeoutException:
            logger.warning("DuckDuckGo API request timed out after %.1fs", self.timeout_seconds)
            return [], 0
        except Exception as exc:
            logger.warning("Error calling DuckDuckGo API: %s", exc)
            return [], 0

    async def _search_html(
        self,
        client: httpx.AsyncClient,
        query: str,
        limit: int = 10,
        offset: int = 0,
    ) -> Tuple[List[SearchResultItem], int]:
        """Query DuckDuckGo HTML web search for live web articles and deep links."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        try:
            resp = await client.post(
                DUCKDUCKGO_HTML_URL,
                data={"q": query},
                headers=headers,
            )
            if resp.status_code != 200:
                return [], 0

            text_html = resp.text
            title_matches = list(
                re.finditer(
                    r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', text_html, re.DOTALL
                )
            )
            snip_matches = list(
                re.finditer(r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>', text_html, re.DOTALL)
            )

            items: List[SearchResultItem] = []
            for tm, sm in zip(title_matches, snip_matches, strict=False):
                raw_href = tm.group(1)
                raw_title = tm.group(2)
                raw_snip = sm.group(1)

                parsed = urlparse(raw_href)
                qs = parse_qs(parsed.query)
                target_url = unquote(qs.get("uddg", [raw_href])[0])
                if target_url.startswith("//"):
                    target_url = "https:" + target_url

                if not target_url.startswith("http"):
                    continue

                clean_title = html.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip()
                clean_snip = html.unescape(re.sub(r"<[^>]+>", "", raw_snip)).strip()
                domain = urlparse(target_url).netloc or "Web"
                score = calculate_relevance_score(query, clean_title, clean_snip, is_verified=False)

                items.append(
                    SearchResultItem(
                        id=f"ddg:{abs(hash(target_url)) % 10000000}",
                        title=clean_title,
                        snippet=clean_snip[:280],
                        source_name=domain,
                        category="Web Discovery",
                        is_verified=False,
                        url=target_url,
                        score=max(score, 2.5),
                        item_type="external",
                        metadata={"provider": "DuckDuckGo Web", "domain": domain},
                    )
                )

            sliced = items[offset : offset + limit] if offset < len(items) else []
            return sliced, len(items)
        except Exception as exc:
            logger.debug("DuckDuckGo HTML fallback exception: %s", exc)
            return [], 0
