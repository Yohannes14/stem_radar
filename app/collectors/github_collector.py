"""GitHub API collector for tracking STEM and emerging technology repositories."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.collectors.base import BaseCollector, CollectedArticle
from app.collectors.rss_collector import is_valid_url
from app.core.config import settings

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com/search/repositories"
DEFAULT_STEM_TOPICS = [
    "artificial-intelligence",
    "machine-learning",
    "robotics",
    "quantum-computing",
    "cybersecurity",
    "biotechnology",
]


class GitHubCollector(BaseCollector):
    """Fetches trending and newly updated STEM repositories via the official GitHub REST API."""

    def __init__(
        self,
        source_name: str = "GitHub Trending",
        source_slug: str = "github-trending",
        url: Optional[str] = None,
        topics: Optional[List[str]] = None,
        min_stars: int = 500,
        per_page: int = 15,
    ) -> None:
        if not url:
            selected_topics = topics or DEFAULT_STEM_TOPICS
            topic_query = "+OR+".join(f"topic:{t}" for t in selected_topics)
            url = f"{GITHUB_API_BASE}?q=stars:>{min_stars}+{topic_query}&sort=updated&order=desc&per_page={per_page}"

        super().__init__(source_name=source_name, source_slug=source_slug, url=url)
        self.headers["Accept"] = "application/vnd.github.v3+json"
        if settings.github_token:
            self.headers["Authorization"] = f"Bearer {settings.github_token}"
        self.http_client.headers = self.headers

    async def collect(self) -> List[CollectedArticle]:
        """Fetch, validate, parse, and normalize repositories from GitHub Search API."""
        if not is_valid_url(self.url):
            logger.error("Invalid GitHub API URL for source '%s': '%s'", self.source_name, self.url)
            return []

        logger.info("Collecting STEM repositories from GitHub: %s (%s)", self.source_name, self.url)

        try:
            resp = await self.http_client.get(self.url)

            # Check rate limit headers
            rate_remaining = resp.headers.get("x-ratelimit-remaining")
            rate_reset = resp.headers.get("x-ratelimit-reset")

            if resp.status_code == 403 or (rate_remaining is not None and rate_remaining == "0"):
                reset_msg = ""
                if rate_reset:
                    try:
                        reset_dt = datetime.fromtimestamp(int(rate_reset), tz=timezone.utc)
                        reset_msg = f" (resets at {reset_dt.strftime('%Y-%m-%d %H:%M:%S UTC')})"
                    except Exception:
                        pass
                logger.warning(
                    "GitHub API rate limit reached for %s%s. Gracefully skipping.",
                    self.source_name,
                    reset_msg,
                )
                return []

            if resp.status_code != 200:
                logger.warning(
                    "GitHub API error HTTP %d for %s: %s",
                    resp.status_code,
                    self.source_name,
                    resp.text[:200],
                )
                return []

            data = resp.json()
        except Exception as exc:
            logger.warning("Failed to collect GitHub repositories from %s: %s", self.source_name, exc)
            return []

        if not isinstance(data, dict):
            logger.warning("Unexpected non-dict JSON response from GitHub API for %s", self.source_name)
            return []

        items = data.get("items", [])
        if not isinstance(items, list):
            logger.warning("Missing or non-list 'items' key in GitHub response for %s", self.source_name)
            return []

        articles: List[CollectedArticle] = []
        for item in items:
            try:
                name = item.get("full_name") or item.get("name")
                html_url = item.get("html_url")

                if not name or not html_url or not is_valid_url(html_url):
                    continue

                desc = item.get("description") or "No description provided."
                stars = item.get("stargazers_count", 0)
                forks = item.get("forks_count", 0)
                lang = item.get("language") or "General"
                repo_topics = item.get("topics", [])

                # Parse update date (prefer updated_at or pushed_at)
                updated_at_dt: Optional[datetime] = None
                raw_update_str = item.get("updated_at") or item.get("pushed_at") or item.get("created_at")
                if raw_update_str and isinstance(raw_update_str, str):
                    try:
                        updated_at_dt = datetime.fromisoformat(raw_update_str.replace("Z", "+00:00"))
                    except Exception:
                        pass

                # Build structured description
                desc_lines = [
                    f"Language: {lang} | Stars: {stars:,} | Forks: {forks:,}",
                ]
                if repo_topics:
                    desc_lines.append(f"Topics: {', '.join(repo_topics[:5])}")
                if updated_at_dt:
                    desc_lines.append(f"Last Updated: {updated_at_dt.strftime('%Y-%m-%d %H:%M UTC')}")
                desc_lines.append(f"\n{desc}")
                full_desc = "\n".join(desc_lines)

                raw_data: Dict[str, Any] = {
                    "full_name": name,
                    "stars": stars,
                    "forks": forks,
                    "language": lang,
                    "topics": repo_topics,
                    "html_url": html_url,
                    "updated_at": raw_update_str,
                }

                collected = CollectedArticle(
                    title=f"[Repo] {name} ({lang})",
                    url=html_url,
                    source_slug=self.source_slug,
                    source_name=self.source_name,
                    description=full_desc,
                    published_at=updated_at_dt,
                    raw_data=raw_data,
                )
                collected.clean_text()
                articles.append(collected)
            except Exception as item_exc:
                logger.debug("Skipping unparseable GitHub repo item: %s", item_exc)
                continue

        logger.info("Successfully fetched %d repositories from %s", len(articles), self.source_name)
        return articles
