"""Repository pattern for database operations."""

import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import (
    Article,
    ArticleCategory,
    Category,
    SavedArticle,
    Source,
    UserPreference,
)
from app.processors.deduplicator import normalize_url

logger = logging.getLogger(__name__)


def compute_url_hash(url: str) -> str:
    """Generate a consistent SHA-256 hash from a normalized URL."""
    canonical = normalize_url(url)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class Repository:
    """Async database repository implementing business data access."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------ Sources ------------------

    async def get_sources(self, active_only: bool = True) -> List[Source]:
        """Fetch all configured news/paper sources."""
        stmt = select(Source)
        if active_only:
            stmt = stmt.where(Source.is_active.is_(True))
        stmt = stmt.order_by(Source.name.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_source_by_slug(self, slug: str) -> Optional[Source]:
        """Fetch a specific source by unique slug."""
        stmt = select(Source).where(Source.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_source(self, name: str, slug: str, url: str, source_type: str = "rss") -> Source:
        """Register a new source."""
        source = Source(name=name, slug=slug, url=url, source_type=source_type, is_active=True)
        self.session.add(source)
        await self.session.commit()
        await self.session.refresh(source)
        return source

    async def update_source_health(
        self, source_id: int, success: bool, error_message: Optional[str] = None
    ) -> None:
        """Update last collection time and error telemetry for a source."""
        stmt = select(Source).where(Source.id == source_id)
        result = await self.session.execute(stmt)
        source = result.scalar_one_or_none()
        if source:
            if success:
                source.last_collected_at = datetime.now(timezone.utc)
                source.last_error = None
                source.error_count = 0
            else:
                source.last_error = error_message
                source.error_count += 1
            await self.session.commit()

    # ------------------ Categories ------------------

    async def get_categories(self) -> List[Category]:
        """Fetch all STEM categories."""
        stmt = select(Category).order_by(Category.name.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_category_by_slug(self, slug: str) -> Optional[Category]:
        """Fetch a category by slug."""
        stmt = select(Category).where(Category.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------ Articles & Deduplication ------------------

    async def article_exists(self, url: str) -> bool:
        """Check if an article already exists by URL hash."""
        url_hash = compute_url_hash(url)
        stmt = select(Article.id).where(Article.url_hash == url_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def save_article(
        self,
        title: str,
        url: str,
        source_id: int,
        description: Optional[str] = None,
        content: Optional[str] = None,
        published_at=None,
        category_ids: Optional[List[int]] = None,
        commit: bool = True,
    ) -> Tuple[Optional[Article], bool]:
        """Save a new article with duplicate detection.
        Returns: (Article, created: bool)
        """
        canonical_url = normalize_url(url)
        url_hash = compute_url_hash(canonical_url)

        # Check for existing article by unique URL hash
        stmt = select(Article).where(Article.url_hash == url_hash)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing, False

        article = Article(
            title=title.strip(),
            url=canonical_url,
            url_hash=url_hash,
            description=description.strip() if description else None,
            content=content.strip() if content else None,
            source_id=source_id,
            published_at=published_at,
        )
        self.session.add(article)
        await self.session.flush()

        # Link categories if provided
        if category_ids:
            for cat_id in category_ids:
                link = ArticleCategory(article_id=article.id, category_id=cat_id, confidence=1.0)
                self.session.add(link)

        if commit:
            await self.session.commit()

            # Reload with relationships
            stmt_full = (
                select(Article)
                .where(Article.id == article.id)
                .options(selectinload(Article.source), selectinload(Article.categories))
            )
            res_full = await self.session.execute(stmt_full)
            return res_full.scalar_one(), True

        return article, True

    async def get_recent_articles(
        self,
        limit: int = 10,
        offset: int = 0,
        category_slug: Optional[str] = None,
        source_slug: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> List[Article]:
        """Fetch recent articles sorted by published_at or collected_at."""
        stmt = select(Article).options(selectinload(Article.source), selectinload(Article.categories))

        if category_slug:
            stmt = stmt.join(Article.categories).where(Category.slug == category_slug)

        if source_slug or source_type:
            stmt = stmt.join(Article.source)
            if source_slug:
                stmt = stmt.where(Source.slug == source_slug)
            if source_type:
                stmt = stmt.where(Source.source_type == source_type)

        stmt = (
            stmt.order_by(
                Article.published_at.desc().nulls_last(),
                Article.collected_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_article_by_id(self, article_id: int) -> Optional[Article]:
        """Fetch a single article by ID."""
        stmt = (
            select(Article)
            .where(Article.id == article_id)
            .options(selectinload(Article.source), selectinload(Article.categories))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_articles(self, query: str, limit: int = 10) -> List[Article]:
        """Search articles by keyword in title or description."""
        search_pattern = f"%{query.strip()}%"
        stmt = (
            select(Article)
            .where(
                or_(
                    Article.title.ilike(search_pattern),
                    Article.description.ilike(search_pattern),
                )
            )
            .options(selectinload(Article.source), selectinload(Article.categories))
            .order_by(desc(Article.collected_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------ Bookmarks / Saved Articles ------------------

    async def toggle_save_article(self, user_id: int, article_id: int) -> bool:
        """Toggle bookmark status for a user. Returns True if saved, False if removed."""
        stmt = select(SavedArticle).where(SavedArticle.user_id == user_id, SavedArticle.article_id == article_id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            await self.session.delete(existing)
            await self.session.commit()
            return False

        saved = SavedArticle(user_id=user_id, article_id=article_id)
        self.session.add(saved)
        await self.session.commit()
        return True

    async def get_saved_articles(self, user_id: int, limit: int = 10) -> List[Article]:
        """Fetch articles bookmarked by user."""
        stmt = (
            select(Article)
            .join(SavedArticle, SavedArticle.article_id == Article.id)
            .where(SavedArticle.user_id == user_id)
            .options(selectinload(Article.source), selectinload(Article.categories))
            .order_by(desc(SavedArticle.saved_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------ User Preferences ------------------

    async def get_or_create_preference(self, user_id: int) -> UserPreference:
        """Fetch or create default user preferences."""
        stmt = select(UserPreference).where(UserPreference.user_id == user_id)
        result = await self.session.execute(stmt)
        pref = result.scalar_one_or_none()
        if not pref:
            pref = UserPreference(user_id=user_id)
            self.session.add(pref)
            await self.session.commit()
            await self.session.refresh(pref)
        return pref
