"""Official arXiv API collector for STEM research papers."""

import logging
import re
from typing import Any, Dict, List, Optional

import feedparser

from app.collectors.base import BaseCollector, CollectedArticle
from app.collectors.rss_collector import is_valid_url, parse_feed_date

logger = logging.getLogger(__name__)

ARXIV_API_BASE = "https://export.arxiv.org/api/query"


class ArxivCollector(BaseCollector):
    """Fetches research papers from the official arXiv API across STEM categories."""

    def __init__(
        self,
        source_name: str,
        source_slug: str,
        url: Optional[str] = None,
        categories: Optional[List[str]] = None,
        max_results: int = 15,
    ) -> None:
        # Build query URL if only categories are supplied or fallback to default
        if not url:
            cats = categories or ["cs.AI", "cs.RO", "quant-ph", "cs.CR"]
            query = "+OR+".join(f"cat:{c}" for c in cats)
            url = (
                f"{ARXIV_API_BASE}?search_query={query}"
                f"&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
            )

        super().__init__(source_name=source_name, source_slug=source_slug, url=url)
        self.headers.update({
            "User-Agent": "StemRadar/1.0 (+https://github.com/stem-radar; academic & research intelligence)",
            "Accept": "application/atom+xml, application/xml, text/xml",
        })

    async def collect(self) -> List[CollectedArticle]:
        """Fetch and parse research papers from the official arXiv query API."""
        if not is_valid_url(self.url):
            logger.error("Invalid arXiv API URL for source '%s': '%s'", self.source_name, self.url)
            return []

        logger.info("Collecting research papers from arXiv: %s (%s)", self.source_name, self.url)

        try:
            response = await self.http_client.get(self.url)
            if response.status_code != 200:
                logger.warning(
                    "arXiv API returned HTTP %d for %s",
                    response.status_code,
                    self.source_name,
                )
                return []
            content = response.text
        except Exception as exc:
            logger.warning("Error fetching from arXiv (%s): %s", self.source_name, exc)
            return []

        if not content or not content.strip():
            logger.warning("Empty response received from arXiv (%s)", self.source_name)
            return []

        try:
            parsed = feedparser.parse(content)
        except Exception as exc:
            logger.warning("Failed to parse arXiv Atom response: %s", exc)
            return []

        if parsed.bozo and not parsed.entries:
            logger.warning(
                "Malformed arXiv XML response for %s: %s",
                self.source_name,
                parsed.get("bozo_exception"),
            )
            return []

        articles: List[CollectedArticle] = []
        for entry in parsed.entries:
            try:
                title = entry.get("title", "")
                if not isinstance(title, str) or not title.strip():
                    continue

                # arXiv titles frequently contain inline newlines and LaTeX spacing
                title = re.sub(r"\s+", " ", title).strip()

                # Canonical abstract page URL
                link = entry.get("link", "").strip()
                if not link and entry.get("id"):
                    link = str(entry.get("id")).strip()

                # Look for alternate html link in links list if needed
                for lk in entry.get("links", []):
                    if isinstance(lk, dict) and lk.get("rel") == "alternate" and lk.get("href"):
                        link = lk["href"].strip()
                        break

                if not link or not is_valid_url(link):
                    continue

                # Format author list
                authors = [
                    a.get("name").strip()
                    for a in entry.get("authors", [])
                    if isinstance(a, dict) and a.get("name")
                ]
                if authors:
                    if len(authors) > 3:
                        author_str = f"Authors: {', '.join(authors[:3])} et al."
                    else:
                        author_str = f"Authors: {', '.join(authors)}"
                else:
                    author_str = ""

                # Format primary category
                category = entry.get("arxiv_primary_category", {}).get("term", "")
                cat_str = f"Category: {category}" if category else ""

                # Extract and clean abstract
                raw_summary = entry.get("summary", "")
                cleaned_summary = re.sub(r"\s+", " ", raw_summary).strip()

                # Build structured description
                desc_parts = [p for p in (author_str, cat_str) if p]
                if cleaned_summary:
                    desc_parts.append(f"Abstract: {cleaned_summary}")
                full_description = "\n\n".join(desc_parts)

                # Find PDF download link if present
                pdf_link = None
                for lk in entry.get("links", []):
                    if isinstance(lk, dict) and (
                        lk.get("title") == "pdf" or lk.get("type") == "application/pdf"
                    ):
                        pdf_link = lk.get("href")
                        break

                raw_data: Dict[str, Any] = {
                    "authors": authors,
                    "primary_category": category,
                    "pdf_url": pdf_link,
                }

                item = CollectedArticle(
                    title=f"[Paper] {title}",
                    url=link,
                    source_slug=self.source_slug,
                    source_name=self.source_name,
                    description=full_description,
                    published_at=parse_feed_date(entry),
                    raw_data=raw_data,
                )
                item.clean_text()
                articles.append(item)
            except Exception as entry_exc:
                logger.debug("Skipping unparseable arXiv entry: %s", entry_exc)
                continue

        logger.info(
            "Successfully parsed %d research papers from %s",
            len(articles),
            self.source_name,
        )
        return articles
