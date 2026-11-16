"""Repository pattern for database operations."""

import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import (
    Article,
    ArticleCategory,
    Category,
    NotificationLog,
    SavedArticle,
    Source,
    UserLearningProgress,
    UserPreference,
    UserWatchlist,
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

    # ------------------ Learning Progress ------------------

    async def get_or_create_learning_progress(
        self, user_id: int, topic: str, level: str = "beginner"
    ) -> UserLearningProgress:
        """Fetch or initialize learning progress for a user on a given topic."""
        clean_topic = topic.strip().lower()
        stmt = select(UserLearningProgress).where(
            UserLearningProgress.user_id == user_id,
            UserLearningProgress.topic == clean_topic,
        )
        result = await self.session.execute(stmt)
        progress = result.scalar_one_or_none()
        if not progress:
            progress = UserLearningProgress(
                user_id=user_id,
                topic=clean_topic,
                level=level,
            )
            self.session.add(progress)
            await self.session.commit()
            await self.session.refresh(progress)
        return progress

    async def record_lesson_completion(
        self, user_id: int, topic: str, level: str = "beginner"
    ) -> UserLearningProgress:
        """Increment completed lesson count and update level for a topic."""
        progress = await self.get_or_create_learning_progress(user_id, topic, level)
        progress.lessons_completed += 1
        progress.level = level
        progress.last_studied_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(progress)
        return progress

    async def record_quiz_completion(
        self, user_id: int, topic: str, score: int, max_score: int
    ) -> UserLearningProgress:
        """Record quiz attempt, accumulate scores, and update last studied timestamp."""
        progress = await self.get_or_create_learning_progress(user_id, topic)
        progress.quizzes_taken += 1
        progress.quiz_score_total += score
        progress.quiz_score_max += max_score
        progress.last_studied_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(progress)
        return progress

    async def get_user_learning_history(self, user_id: int) -> List[UserLearningProgress]:
        """Fetch all learning progress records for a user sorted by most recently studied."""
        stmt = (
            select(UserLearningProgress)
            .where(UserLearningProgress.user_id == user_id)
            .order_by(desc(UserLearningProgress.last_studied_at))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------ Watchlists ------------------

    async def add_watchlist_keyword(self, user_id: int, keyword: str) -> Tuple[UserWatchlist, bool]:
        """Add a keyword/technology to the user's watchlist.
        Returns (UserWatchlist, created: bool).
        """
        clean_kw = keyword.strip().lower()
        if not clean_kw:
            raise ValueError("Watchlist keyword cannot be empty")

        stmt = select(UserWatchlist).where(
            UserWatchlist.user_id == user_id,
            UserWatchlist.keyword == clean_kw,
        )
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            return existing, False

        item = UserWatchlist(user_id=user_id, keyword=clean_kw)
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item, True

    async def remove_watchlist_keyword(self, user_id: int, keyword: str) -> bool:
        """Remove a keyword from user's watchlist. Returns True if deleted, False if not found."""
        clean_kw = keyword.strip().lower()
        stmt = select(UserWatchlist).where(
            UserWatchlist.user_id == user_id,
            UserWatchlist.keyword == clean_kw,
        )
        res = await self.session.execute(stmt)
        item = res.scalar_one_or_none()
        if item:
            await self.session.delete(item)
            await self.session.commit()
            return True
        return False

    async def get_user_watchlist(self, user_id: int) -> List[UserWatchlist]:
        """Fetch all watchlist items for a user ordered by keyword."""
        stmt = (
            select(UserWatchlist)
            .where(UserWatchlist.user_id == user_id)
            .order_by(UserWatchlist.keyword.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def clear_user_watchlist(self, user_id: int) -> int:
        """Clear all watchlist keywords for a user. Returns count of deleted items."""
        stmt = select(UserWatchlist).where(UserWatchlist.user_id == user_id)
        res = await self.session.execute(stmt)
        items = list(res.scalars().all())
        count = len(items)
        for item in items:
            await self.session.delete(item)
        if count > 0:
            await self.session.commit()
        return count

    async def get_all_watchlists(self) -> List[UserWatchlist]:
        """Fetch all user watchlist items across the system."""
        stmt = select(UserWatchlist)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def increment_watchlist_matches(self, watchlist_id: int) -> None:
        """Increment match count for a watchlist item."""
        stmt = select(UserWatchlist).where(UserWatchlist.id == watchlist_id)
        res = await self.session.execute(stmt)
        item = res.scalar_one_or_none()
        if item:
            item.match_count += 1
            await self.session.commit()

    # ------------------ Notification Logs & Duplicate Prevention ------------------

    async def has_notification_been_sent(
        self, user_id: int, article_id: Optional[int], notification_type: str
    ) -> bool:
        """Check if a specific notification was already dispatched to a user to prevent duplicates."""
        stmt = select(NotificationLog.id).where(
            NotificationLog.user_id == user_id,
            NotificationLog.notification_type == notification_type,
        )
        if article_id is not None:
            stmt = stmt.where(NotificationLog.article_id == article_id)
        else:
            stmt = stmt.where(NotificationLog.article_id.is_(None))

        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def log_notification(
        self,
        user_id: int,
        article_id: Optional[int],
        notification_type: str,
        status: str = "delivered",
    ) -> NotificationLog:
        """Record notification delivery status."""
        log_entry = NotificationLog(
            user_id=user_id,
            article_id=article_id,
            notification_type=notification_type,
            status=status,
            delivered_at=datetime.now(timezone.utc),
        )
        self.session.add(log_entry)
        try:
            await self.session.commit()
            await self.session.refresh(log_entry)
        except Exception:
            await self.session.rollback()
            stmt = select(NotificationLog).where(
                NotificationLog.user_id == user_id,
                NotificationLog.article_id == article_id,
                NotificationLog.notification_type == notification_type,
            )
            res = await self.session.execute(stmt)
            existing = res.scalar_one_or_none()
            if existing:
                return existing
            raise
        return log_entry

    async def get_user_notification_logs(self, user_id: int, limit: int = 20) -> List[NotificationLog]:
        """Fetch delivery logs for a user."""
        stmt = (
            select(NotificationLog)
            .where(NotificationLog.user_id == user_id)
            .order_by(desc(NotificationLog.delivered_at))
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # ------------------ Preferences Update & Bulk Query ------------------

    async def update_user_preference(self, user_id: int, **kwargs) -> UserPreference:
        """Update user preferences."""
        pref = await self.get_or_create_preference(user_id)
        for key, val in kwargs.items():
            if hasattr(pref, key):
                setattr(pref, key, val)
        pref.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(pref)
        return pref

    async def get_all_active_preferences(self) -> List[UserPreference]:
        """Fetch all user preferences with notifications enabled."""
        stmt = select(UserPreference).where(UserPreference.notifications_enabled.is_(True))
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # ------------------ Platform & Telemetry Statistics ------------------

    async def get_platform_stats(self, user_id: Optional[int] = None) -> dict:
        """Compute system telemetry and optionally user-specific intelligence statistics."""
        articles_count = (await self.session.execute(select(func.count(Article.id)))).scalar_one() or 0
        sources_count = (await self.session.execute(
            select(func.count(Source.id)).where(Source.is_active.is_(True))
        )).scalar_one() or 0
        categories_count = (await self.session.execute(select(func.count(Category.id)))).scalar_one() or 0
        total_delivered = (await self.session.execute(select(func.count(NotificationLog.id)))).scalar_one() or 0

        stats = {
            "total_articles": articles_count,
            "active_sources": sources_count,
            "stem_categories": categories_count,
            "total_notifications_sent": total_delivered,
        }

        if user_id is not None:
            user_saved = (await self.session.execute(
                select(func.count(SavedArticle.id)).where(SavedArticle.user_id == user_id)
            )).scalar_one() or 0
            user_watchlist_count = (await self.session.execute(
                select(func.count(UserWatchlist.id)).where(UserWatchlist.user_id == user_id)
            )).scalar_one() or 0
            user_notifications = (await self.session.execute(
                select(func.count(NotificationLog.id)).where(NotificationLog.user_id == user_id)
            )).scalar_one() or 0
            user_quizzes = (await self.session.execute(
                select(func.sum(UserLearningProgress.quizzes_taken)).where(UserLearningProgress.user_id == user_id)
            )).scalar_one() or 0

            stats["user_saved_articles"] = user_saved
            stats["user_watchlist_keywords"] = user_watchlist_count
            stats["user_notifications_received"] = user_notifications
            stats["user_quizzes_taken"] = user_quizzes

        return stats
