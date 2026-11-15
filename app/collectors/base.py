"""Abstract Base Collector and standardized data transfer models."""

import abc
import html
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.collectors.client import ResilientHTTPClient

logger = logging.getLogger(__name__)


class CollectedArticle(BaseModel):
    """Standardized schema for an article or research paper collected from any source."""

    title: str = Field(..., min_length=1)
    url: str = Field(..., min_length=5)
    source_slug: str = Field(..., min_length=1)
    source_name: str = Field(..., min_length=1)
    description: Optional[str] = None
    content: Optional[str] = None
    published_at: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None

    def clean_text(self) -> None:
        """Strip HTML tags and unescape entities from title and description."""
        clean_re = re.compile(r"<[^>]+>")
        if self.title:
            cleaned = clean_re.sub("", self.title)
            self.title = html.unescape(cleaned).strip()
        if self.description:
            cleaned = clean_re.sub("", self.description)
            # Remove excessive whitespace
            cleaned = re.sub(r"\s+", " ", cleaned)
            self.description = html.unescape(cleaned).strip()


class BaseCollector(abc.ABC):
    """Abstract base class that all information collectors must implement."""

    def __init__(self, source_name: str, source_slug: str, url: str) -> None:
        self.source_name = source_name
        self.source_slug = source_slug
        self.url = url
        self.timeout = 15.0  # seconds
        self.headers = {
            "User-Agent": "StemRadar/1.0 (+https://github.com/stem-radar; research & intelligence)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        }
        self.http_client = ResilientHTTPClient(timeout=self.timeout, headers=self.headers)

    @abc.abstractmethod
    async def collect(self) -> List[CollectedArticle]:
        """Fetch, parse, validate, and return normalized articles."""
        pass
