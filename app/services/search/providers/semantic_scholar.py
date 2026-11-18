"""Semantic Scholar Academic API search provider for live scientific paper discovery."""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import httpx

from app.config import settings
from app.services.search.models import SearchResultItem
from app.services.search.providers.base import BaseSearchProvider

logger = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


class SemanticScholarProvider(BaseSearchProvider):
    """Scientific research paper provider querying the Semantic Scholar Academic Graph API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        self.api_key = api_key or settings.semantic_scholar_api_key
        self.timeout_seconds = timeout_seconds or settings.external_search_timeout_seconds

    @property
    def name(self) -> str:
        return "semantic_scholar"

    def is_available(self) -> bool:
        """Available for research queries (works on both free open tier and authenticated tier)."""
        return settings.external_search_enabled

    async def search(
        self,
        query: str,
        category: Optional[str] = "all",
        sort_by: str = "relevance",
        limit: int = 10,
        offset: int = 0,
    ) -> Tuple[List[SearchResultItem], int]:
        """Query scientific papers and normalize into verified academic search items."""
        cat = (category or "all").lower()
        # Semantic Scholar specializes in scientific research and technical computing papers
        if cat not in ("all", "research", "technology", "programming"):
            return [], 0

        clean_query = query.strip()
        params = {
            "query": clean_query,
            "offset": offset,
            "limit": min(limit, 20),
            "fields": "paperId,title,abstract,venue,year,publicationDate,openAccessPdf,url,citationCount,authors",
        }
        headers = {
            "User-Agent": "STEM-RADAR-Bot/2.0 (Academic Discovery)",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(SEMANTIC_SCHOLAR_SEARCH_URL, params=params, headers=headers)
                if resp.status_code == 429:
                    logger.warning("Semantic Scholar API rate limit hit (429); returning empty.")
                    return [], 0
                if resp.status_code != 200:
                    logger.warning("Semantic Scholar API returned status %d: %s", resp.status_code, resp.text[:150])
                    return [], 0

                data = resp.json()
                raw_papers = data.get("data", [])
                total_estimated = data.get("total", len(raw_papers))

                items: List[SearchResultItem] = []
                for p in raw_papers:
                    paper_id = p.get("paperId", "")
                    title = p.get("title", "").strip()
                    if not title:
                        continue

                    abstract = (p.get("abstract") or "").strip()
                    venue = p.get("venue") or "Academic Repository"
                    year = p.get("year")
                    pub_date_str = p.get("publicationDate")
                    citations = p.get("citationCount", 0)

                    # Determine primary URL: open-access PDF preferred
                    open_access = p.get("openAccessPdf")
                    paper_url = ""
                    if open_access and isinstance(open_access, dict):
                        paper_url = open_access.get("url") or ""
                    if not paper_url:
                        paper_url = p.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}"

                    # Parse publication date
                    pub_dt = None
                    if pub_date_str:
                        try:
                            pub_dt = datetime.fromisoformat(pub_date_str)
                            if pub_dt.tzinfo is None:
                                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                        except Exception:
                            pub_dt = None
                    if not pub_dt and year:
                        try:
                            pub_dt = datetime(year=year, month=1, day=1, tzinfo=timezone.utc)
                        except Exception:
                            pub_dt = None

                    authors = [a.get("name") for a in p.get("authors", []) if a.get("name")]
                    author_str = f"By {', '.join(authors[:2])}" if authors else ""
                    citation_str = f" · {citations} citations" if citations > 0 else ""
                    snippet_prefix = f"[{venue}{citation_str}] {author_str}".strip()
                    full_snippet = f"{snippet_prefix}\n{abstract}" if abstract else snippet_prefix

                    items.append(
                        SearchResultItem(
                            id=f"s2:{paper_id[:16]}",
                            title=f"[Paper] {title}",
                            snippet=full_snippet[:250],
                            source_name=f"Semantic Scholar ({venue})",
                            published_at=pub_dt,
                            category="Research Papers",
                            is_verified=True,
                            url=paper_url,
                            score=3.5 + min(citations * 0.05, 5.0),
                            item_type="paper",
                            metadata={
                                "authors": authors,
                                "year": year,
                                "citations": citations,
                                "is_open_access": bool(open_access),
                            },
                        )
                    )
                return items, total_estimated

        except httpx.TimeoutException:
            logger.warning("Semantic Scholar request timed out after %.1fs", self.timeout_seconds)
            return [], 0
        except Exception as exc:
            logger.error("Error querying Semantic Scholar: %s", exc)
            return [], 0
