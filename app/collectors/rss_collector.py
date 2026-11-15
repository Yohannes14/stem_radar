"""RSS and Atom feed collector."""

import logging
import time
from datetime import datetime, timezone
from typing import List, Optional

import feedparser

from app.collectors.base import BaseCollector, CollectedArticle

logger = logging.getLogger(__name__)


def parse_feed_date(entry: feedparser.FeedParserDict) -> Optional[datetime]:
    """Parse publication or update date from a feed entry into a UTC datetime."""
    parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed_time:
        try:
            return datetime.fromtimestamp(time.mktime(parsed_time), tz=timezone.utc)
        except Exception:
            pass
    return None


class RSSCollector(BaseCollector):
    """Fetches and parses standard RSS and Atom feeds using resilient HTTP policies."""

    async def collect(self) -> List[CollectedArticle]:
        articles: List[CollectedArticle] = []
        logger.info("Collecting from RSS source: %s (%s)", self.source_name, self.url)

        try:
            response = await self.http_client.get(self.url)
            if response.status_code != 200:
                logger.warning("RSS fetch failed for %s with HTTP %d", self.source_name, response.status_code)
                return []
            content = response.text
        except Exception as exc:
            logger.warning("Error fetching RSS feed from %s (%s): %s", self.source_name, self.url, exc)
            return []

        # Parse feed content
        parsed = feedparser.parse(content)
        if parsed.bozo and not parsed.entries:
            logger.warning("Malformed XML / Bozo flag in %s: %s", self.source_name, parsed.get("bozo_exception"))
            return []

        for entry in parsed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()

            if not title or not link:
                continue

            description = entry.get("summary") or entry.get("description") or ""
            published_at = parse_feed_date(entry)

            item = CollectedArticle(
                title=title,
                url=link,
                source_slug=self.source_slug,
                source_name=self.source_name,
                description=description,
                published_at=published_at,
            )
            item.clean_text()
            articles.append(item)

        logger.info("Successfully parsed %d articles from %s", len(articles), self.source_name)
        return articles
