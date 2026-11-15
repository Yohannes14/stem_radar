"""GitHub Trending & Repository Intelligence Collector."""

import logging
from datetime import datetime, timezone
from typing import List

from app.collectors.base import BaseCollector, CollectedArticle

logger = logging.getLogger(__name__)


class GitHubCollector(BaseCollector):
    """Fetches trending and newly popular STEM repositories via GitHub's public API."""

    def __init__(
        self,
        source_name: str = "GitHub Trending",
        source_slug: str = "github-trending",
        url: str = "",
    ) -> None:
        if not url:
            url = "https://api.github.com/search/repositories?q=stars:>1000&sort=stars&order=desc&per_page=15"
        super().__init__(source_name=source_name, source_slug=source_slug, url=url)
        self.headers["Accept"] = "application/vnd.github.v3+json"
        self.http_client.headers["Accept"] = "application/vnd.github.v3+json"

    async def collect(self) -> List[CollectedArticle]:
        articles: List[CollectedArticle] = []
        logger.info("Collecting trending repositories from GitHub API...")

        try:
            resp = await self.http_client.get(self.url)
            if resp.status_code == 403:
                logger.warning("GitHub API rate limit encountered. Skipping GitHub collection gracefully.")
                return []
            if resp.status_code != 200:
                logger.warning("GitHub API error HTTP %d", resp.status_code)
                return []

            data = resp.json()
        except Exception as exc:
            logger.warning("Failed to collect GitHub repositories: %s", exc)
            return []

        items = data.get("items", [])
        for item in items:
            name = item.get("full_name") or item.get("name")
            html_url = item.get("html_url")
            desc = item.get("description") or "No description provided."
            stars = item.get("stargazers_count", 0)
            lang = item.get("language") or "General"

            if not name or not html_url:
                continue

            full_desc = f"Language: {lang} | Stars: ⭐ {stars:,}\n\n{desc}"

            published_at = None
            if item.get("created_at"):
                try:
                    published_at = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
                except Exception:
                    published_at = datetime.now(timezone.utc)

            collected = CollectedArticle(
                title=f"[Repo] {name} ({lang})",
                url=html_url,
                source_slug=self.source_slug,
                source_name=self.source_name,
                description=full_desc,
                published_at=published_at,
            )
            collected.clean_text()
            articles.append(collected)

        logger.info("Successfully fetched %d repositories from GitHub", len(articles))
        return articles
