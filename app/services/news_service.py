"""News service coordinating collectors, classification, deduplication, and persistence."""

import logging
from typing import Dict, List, Optional

from app.collectors.base import CollectedArticle
from app.collectors.registry import CollectorRegistry
from app.database.database import get_session_factory
from app.database.models import Article, Source
from app.database.repository import Repository
from app.processors.classifier import classifier
from app.processors.deduplicator import normalize_url

logger = logging.getLogger(__name__)


class NewsService:
    """Core service for managing technology news and research paper ingestion."""

    def __init__(self, session_factory=None) -> None:
        self.session_factory = session_factory or get_session_factory()

    async def collect_from_all_sources(self) -> Dict[str, int]:
        """Run collection across all active configured sources.

        Returns a dict mapping source slug to number of newly saved articles.
        Guarantees isolation: failure in one source never stops other collectors.
        """
        results: Dict[str, int] = {}

        async with self.session_factory() as session:
            repo = Repository(session)
            sources = await repo.get_sources(active_only=True)
            categories = await repo.get_categories()
            cat_map: Dict[str, int] = {c.slug: c.id for c in categories}

        logger.info("Found %d active sources to collect from.", len(sources))

        for source in sources:
            try:
                saved_count = await self.collect_from_source(source, cat_map)
                results[source.slug] = saved_count
            except Exception as exc:
                logger.error("Unhandled error collecting from %s: %s", source.name, exc, exc_info=True)
                results[source.slug] = 0

        return results

    async def collect_from_source(self, source: Source, cat_map: Optional[Dict[str, int]] = None) -> int:
        """Run collector for a single source, classify articles, and persist to database."""
        collector = CollectorRegistry.create_collector(source)
        try:
            items: List[CollectedArticle] = await collector.collect()
        except Exception as exc:
            logger.error("Failed to collect from %s: %s", source.name, exc, exc_info=True)
            async with self.session_factory() as session:
                repo = Repository(session)
                await repo.update_source_health(source.id, success=False, error_message=str(exc))
            return 0

        saved_count = 0
        async with self.session_factory() as session:
            repo = Repository(session)
            if not cat_map:
                categories = await repo.get_categories()
                cat_map = {c.slug: c.id for c in categories}

            try:
                for item in items:
                    canonical_url = normalize_url(item.url)
                    if not canonical_url:
                        continue

                    # Deduplication check
                    if await repo.article_exists(canonical_url):
                        continue

                    # Classify article text into STEM categories
                    combined_text = f"{item.title} {item.description or ''}"
                    classification_matches = classifier.classify(combined_text, max_categories=2)
                    matched_cat_ids = [cat_map[slug] for slug, _ in classification_matches if slug in cat_map]

                    # Save article in batch (commit=False for batch performance)
                    _, created = await repo.save_article(
                        title=item.title,
                        url=canonical_url,
                        source_id=source.id,
                        description=item.description,
                        content=item.content,
                        published_at=item.published_at,
                        category_ids=matched_cat_ids,
                        commit=False,
                    )
                    if created:
                        saved_count += 1

                await session.commit()
                # Update source health telemetry on success
                await repo.update_source_health(source.id, success=True)
            except Exception as exc:
                await session.rollback()
                logger.error("Error persisting batch from %s: %s", source.name, exc, exc_info=True)
                await repo.update_source_health(source.id, success=False, error_message=str(exc))
                return 0

        logger.info("Source %s: saved %d new articles.", source.name, saved_count)
        return saved_count

    async def get_recent_news(
        self,
        limit: int = 5,
        offset: int = 0,
        category_slug: Optional[str] = None,
        source_slug: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> List[Article]:
        """Fetch latest news articles with optional category, source, or type filters."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.get_recent_articles(
                limit=limit,
                offset=offset,
                category_slug=category_slug,
                source_slug=source_slug,
                source_type=source_type,
            )

    async def search_news(self, query: str, limit: int = 5) -> List[Article]:
        """Search news articles by keyword."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.search_articles(query=query, limit=limit)

    async def get_sources_list(self) -> List[Source]:
        """Fetch all registered sources with health status."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.get_sources(active_only=False)

    async def toggle_save_article(self, user_id: int, article_id: int) -> bool:
        """Toggle bookmark for user."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.toggle_save_article(user_id, article_id)

    async def get_saved_articles(self, user_id: int, limit: int = 5) -> List[Article]:
        """Fetch saved articles for user."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.get_saved_articles(user_id=user_id, limit=limit)
