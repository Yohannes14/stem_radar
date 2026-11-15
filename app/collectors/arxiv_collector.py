"""ArXiv API collector for research papers."""

import logging
from typing import List

import feedparser

from app.collectors.base import BaseCollector, CollectedArticle
from app.collectors.rss_collector import parse_feed_date

logger = logging.getLogger(__name__)


class ArxivCollector(BaseCollector):
    """Fetches research papers from the official arXiv API using resilient HTTP policies."""

    async def collect(self) -> List[CollectedArticle]:
        articles: List[CollectedArticle] = []
        logger.info("Collecting research papers from arXiv: %s", self.source_name)

        try:
            response = await self.http_client.get(self.url)
            if response.status_code != 200:
                logger.warning("arXiv API returned HTTP %d for %s", response.status_code, self.source_name)
                return []
            content = response.text
        except Exception as exc:
            logger.warning("Error fetching from arXiv (%s): %s", self.source_name, exc)
            return []

        parsed = feedparser.parse(content)
        for entry in parsed.entries:
            title = entry.get("title", "").replace("\n", " ").strip()
            link = entry.get("link", "").strip()

            if not title or not link:
                continue

            summary = entry.get("summary", "").replace("\n", " ").strip()
            authors = [a.get("name") for a in entry.get("authors", []) if a.get("name")]
            authors_str = f"Authors: {', '.join(authors[:3])}" if authors else ""
            if len(authors) > 3:
                authors_str += " et al."

            full_desc = f"{authors_str}\n\nAbstract: {summary}" if authors_str else summary

            item = CollectedArticle(
                title=f"[Paper] {title}",
                url=link,
                source_slug=self.source_slug,
                source_name=self.source_name,
                description=full_desc,
                published_at=parse_feed_date(entry),
            )
            item.clean_text()
            articles.append(item)

        logger.info("Successfully parsed %d research papers from %s", len(articles), self.source_name)
        return articles
