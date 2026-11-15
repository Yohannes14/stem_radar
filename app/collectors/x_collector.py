"""Official X (formerly Twitter) API Collector."""

import logging
import os
from typing import List

import httpx

from app.collectors.base import BaseCollector, CollectedArticle

logger = logging.getLogger(__name__)


class XCollector(BaseCollector):
    """Collects technology posts using the official X API v2."""

    def __init__(
        self,
        source_name: str = "X Tech Intelligence",
        source_slug: str = "x-tech",
        url: str = "https://api.twitter.com/2/tweets/search/recent",
    ) -> None:
        super().__init__(source_name=source_name, source_slug=source_slug, url=url)
        self.bearer_token = os.getenv("X_API_BEARER_TOKEN", "").strip()

    async def collect(self) -> List[CollectedArticle]:
        if not self.bearer_token:
            logger.info("X API integration is disabled: X_API_BEARER_TOKEN is not configured.")
            return []

        logger.info("Collecting technology posts from X API...")
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "User-Agent": self.headers["User-Agent"],
        }
        params = {
            "query": "(AI OR robotics OR quantum OR 'machine learning' OR STEM) -is:retweet lang:en",
            "max_results": 10,
            "tweet.fields": "created_at,author_id,public_metrics",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.url, headers=headers, params=params)
                if resp.status_code == 429:
                    logger.warning("X API rate limit reached. Skipping gracefully.")
                    return []
                if resp.status_code != 200:
                    logger.warning("X API returned HTTP %d: %s", resp.status_code, resp.text)
                    return []
                # Process tweets when enabled
                return []
        except Exception as exc:
            logger.warning("Error collecting from X API: %s", exc)
            return []
