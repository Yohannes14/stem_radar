"""RSS and Atom feed collector with feed validation and resilience."""

import email.utils
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import feedparser

from app.collectors.base import BaseCollector, CollectedArticle

logger = logging.getLogger(__name__)


def is_valid_url(url: str) -> bool:
    """Validate that a URL has a valid HTTP/HTTPS scheme and network location."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def parse_feed_date(entry: Dict[str, Any]) -> Optional[datetime]:
    """Parse publication or update date from a feed entry into a UTC datetime.

    Checks structured time tuples first, falling back to RFC-822 / ISO-8601 string parsing.
    """
    # 1. Feedparser parsed time structures (time.struct_time)
    for date_field in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed_time = entry.get(date_field)
        if parsed_time:
            try:
                return datetime.fromtimestamp(time.mktime(parsed_time), tz=timezone.utc)
            except Exception:
                pass

    # 2. String fallbacks (RFC-822 / RFC-2822 or ISO-8601)
    for str_field in ("published", "updated", "pubDate", "date"):
        raw_val = entry.get(str_field)
        if isinstance(raw_val, str) and raw_val.strip():
            # Try RFC-2822
            try:
                dt = email.utils.parsedate_to_datetime(raw_val.strip())
                if dt:
                    return dt.astimezone(timezone.utc)
            except Exception:
                pass
            # Try ISO format
            try:
                dt = datetime.fromisoformat(raw_val.strip().replace("Z", "+00:00"))
                return dt.astimezone(timezone.utc)
            except Exception:
                pass

    return None


def extract_original_url(entry: Dict[str, Any]) -> Optional[str]:
    """Extract canonical or original article URL, handling FeedBurner and Atom alternates."""
    # 1. FeedBurner original link tag
    feedburner_link = entry.get("feedburner_origlink") or entry.get("feedburner:origlink")
    if feedburner_link and is_valid_url(feedburner_link):
        return feedburner_link.strip()

    # 2. Direct entry link attribute
    link = entry.get("link")
    if link and isinstance(link, str) and is_valid_url(link):
        return link.strip()

    # 3. Atom links list - find alternate or html link
    links = entry.get("links", [])
    if isinstance(links, list):
        for candidate in links:
            if not isinstance(candidate, dict):
                continue
            href = candidate.get("href")
            rel = candidate.get("rel", "alternate")
            content_type = candidate.get("type", "")

            if rel == "alternate" and href and is_valid_url(href):
                return href.strip()
            if "html" in content_type and href and is_valid_url(href):
                return href.strip()

        # Fallback to any valid href in links list
        for candidate in links:
            if isinstance(candidate, dict):
                href = candidate.get("href")
                if href and is_valid_url(href):
                    return href.strip()

    return None


class RSSCollector(BaseCollector):
    """Fetches and parses standard RSS and Atom feeds using resilient HTTP policies."""

    async def collect(self) -> List[CollectedArticle]:
        """Fetch, validate, parse, and normalize articles from an RSS or Atom feed."""
        if not is_valid_url(self.url):
            logger.error("Invalid feed URL for source '%s': '%s'", self.source_name, self.url)
            return []

        logger.info("Collecting from RSS source: %s (%s)", self.source_name, self.url)

        try:
            response = await self.http_client.get(self.url)
            if response.status_code != 200:
                logger.warning(
                    "RSS fetch failed for %s with HTTP %d",
                    self.source_name,
                    response.status_code,
                )
                return []
            content = response.text
        except Exception as exc:
            logger.warning(
                "Error fetching RSS feed from %s (%s): %s",
                self.source_name,
                self.url,
                exc,
            )
            return []

        if not content or not content.strip():
            logger.warning("Empty response body from %s (%s)", self.source_name, self.url)
            return []

        # Parse feed XML/Atom
        try:
            parsed = feedparser.parse(content)
        except Exception as exc:
            logger.warning("Feedparser failed to parse content from %s: %s", self.source_name, exc)
            return []

        # Handle bozo flag (malformed XML)
        if parsed.bozo:
            bozo_exc = parsed.get("bozo_exception", "Unknown XML issue")
            if not parsed.entries:
                logger.warning(
                    "Malformed feed from %s with no recoverable entries: %s",
                    self.source_name,
                    bozo_exc,
                )
                return []
            logger.debug(
                "Malformed XML warning in feed from %s, but %d entries recovered: %s",
                self.source_name,
                len(parsed.entries),
                bozo_exc,
            )

        articles: List[CollectedArticle] = []
        for entry in parsed.entries:
            try:
                title = entry.get("title", "")
                if not isinstance(title, str) or not title.strip():
                    continue
                title = title.strip()

                link = extract_original_url(entry)
                if not link:
                    continue

                # Extract description or content snippet
                description = ""
                if entry.get("summary"):
                    description = str(entry.get("summary"))
                elif entry.get("description"):
                    description = str(entry.get("description"))
                elif entry.get("content") and isinstance(entry["content"], list):
                    first_content = entry["content"][0]
                    if isinstance(first_content, dict):
                        description = first_content.get("value", "")

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
            except Exception as entry_exc:
                logger.debug(
                    "Skipping unparseable entry in %s: %s",
                    self.source_name,
                    entry_exc,
                )
                continue

        logger.info("Successfully parsed %d articles from %s", len(articles), self.source_name)
        return articles
