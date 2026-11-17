"""Repository pattern for database operations."""

import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database.models import (
    AcademicResource,
    Article,
    ArticleCategory,
    Category,
    NotificationLog,
    Opportunity,
    OpportunityReport,
    SavedArticle,
    SearchQueryLog,
    Source,
    UniversityProfile,
    User,
    UserFeedback,
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

    async def update_source_health(self, source_id: int, success: bool, error_message: Optional[str] = None) -> None:
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
        category_slugs: Optional[List[str]] = None,
        source_slug: Optional[str] = None,
        source_type: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[Article]:
        """Fetch recent articles sorted by published_at or collected_at with optional filtering."""
        stmt = select(Article).options(selectinload(Article.source), selectinload(Article.categories))

        # Support single category, comma-delimited string, or list of category slugs
        slugs_to_filter = []
        if category_slugs:
            slugs_to_filter.extend([s.strip() for s in category_slugs if s.strip()])
        elif category_slug and category_slug != "all":
            slugs_to_filter.extend([s.strip() for s in category_slug.split(",") if s.strip()])

        if slugs_to_filter:
            stmt = stmt.join(Article.categories).where(Category.slug.in_(slugs_to_filter)).distinct()

        if source_slug or source_type:
            stmt = stmt.join(Article.source)
            if source_slug:
                stmt = stmt.where(Source.slug == source_slug)
            if source_type:
                stmt = stmt.where(Source.source_type == source_type)

        if query and query.strip():
            search_pattern = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Article.title.ilike(search_pattern),
                    Article.description.ilike(search_pattern),
                )
            )

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

    async def count_articles(
        self,
        category_slug: Optional[str] = None,
        category_slugs: Optional[List[str]] = None,
        source_slug: Optional[str] = None,
        source_type: Optional[str] = None,
        query: Optional[str] = None,
    ) -> int:
        """Count total articles matching optional category, source, or search criteria."""
        stmt = select(func.count(Article.id.distinct()))

        slugs_to_filter = []
        if category_slugs:
            slugs_to_filter.extend([s.strip() for s in category_slugs if s.strip()])
        elif category_slug and category_slug != "all":
            slugs_to_filter.extend([s.strip() for s in category_slug.split(",") if s.strip()])

        if slugs_to_filter:
            stmt = stmt.join(Article.categories).where(Category.slug.in_(slugs_to_filter)).distinct()

        if source_slug or source_type:
            stmt = stmt.join(Article.source)
            if source_slug:
                stmt = stmt.where(Source.slug == source_slug)
            if source_type:
                stmt = stmt.where(Source.source_type == source_type)

        if query and query.strip():
            search_pattern = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Article.title.ilike(search_pattern),
                    Article.description.ilike(search_pattern),
                )
            )

        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def get_article_by_id(self, article_id: int) -> Optional[Article]:
        """Fetch a single article by ID."""
        stmt = (
            select(Article)
            .where(Article.id == article_id)
            .options(selectinload(Article.source), selectinload(Article.categories))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_articles(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        category_slug: Optional[str] = None,
        is_paper: Optional[bool] = None,
    ) -> List[Article]:
        """Search articles by keyword in title or description with optional category/paper filters."""
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
        )
        if category_slug and category_slug != "all":
            stmt = stmt.join(Article.categories).where(Category.slug == category_slug).distinct()
        if is_paper is True:
            stmt = stmt.join(Article.source).where(Source.source_type == "arxiv")
        elif is_paper is False:
            stmt = stmt.join(Article.source).where(Source.source_type != "arxiv")

        stmt = stmt.order_by(desc(Article.collected_at)).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_search_articles(
        self,
        query: str,
        category_slug: Optional[str] = None,
        is_paper: Optional[bool] = None,
    ) -> int:
        """Count total articles matching search keyword and optional filters."""
        search_pattern = f"%{query.strip()}%"
        stmt = select(func.count(Article.id.distinct())).where(
            or_(
                Article.title.ilike(search_pattern),
                Article.description.ilike(search_pattern),
            )
        )
        if category_slug and category_slug != "all":
            stmt = stmt.join(Article.categories).where(Category.slug == category_slug).distinct()
        if is_paper is True:
            stmt = stmt.join(Article.source).where(Source.source_type == "arxiv")
        elif is_paper is False:
            stmt = stmt.join(Article.source).where(Source.source_type != "arxiv")

        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

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

    async def save_article_bookmark(self, user_id: int, article_id: int) -> bool:
        """Explicitly add a bookmark for a user. Returns True if newly saved, False if already exists."""
        stmt = select(SavedArticle).where(SavedArticle.user_id == user_id, SavedArticle.article_id == article_id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return False
        saved = SavedArticle(user_id=user_id, article_id=article_id)
        self.session.add(saved)
        await self.session.commit()
        return True

    async def remove_saved_article(self, user_id: int, article_id: int) -> bool:
        """Remove a bookmark for a user. Returns True if removed, False if not found."""
        stmt = select(SavedArticle).where(SavedArticle.user_id == user_id, SavedArticle.article_id == article_id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            await self.session.delete(existing)
            await self.session.commit()
            return True
        return False

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

    async def toggle_user_interest_category(self, user_id: int, category_slug: str) -> Tuple[List[str], bool]:
        """Toggle an interest category on or off for a user.

        Supports multi-category subscriptions.
        Returns: (active_slugs: List[str], is_added: bool)
        """
        pref = await self.get_or_create_preference(user_id)
        current_slugs = [s.strip() for s in (pref.preferred_categories or "").split(",") if s.strip()]

        clean_slug = category_slug.strip().lower()

        if clean_slug == "all":
            pref.preferred_categories = ""
            pref.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return [], False

        if clean_slug in current_slugs:
            current_slugs.remove(clean_slug)
            is_added = False
        else:
            current_slugs.append(clean_slug)
            is_added = True

        pref.preferred_categories = ",".join(current_slugs)
        pref.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        return current_slugs, is_added

    async def update_user_preferred_categories(self, user_id: int, category_slugs: List[str]) -> List[str]:
        """Overwrite user subscribed category slugs with a validated list."""
        pref = await self.get_or_create_preference(user_id)
        cleaned_slugs = [s.strip().lower() for s in category_slugs if s.strip()]
        pref.preferred_categories = ",".join(cleaned_slugs)
        pref.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        return cleaned_slugs

    async def get_user_preferred_categories(self, user_id: int) -> List[str]:
        """Get list of active preferred category slugs for a user."""
        pref = await self.get_or_create_preference(user_id)
        if not pref.preferred_categories:
            return []
        return [s.strip() for s in pref.preferred_categories.split(",") if s.strip()]

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

    async def record_lesson_completion(self, user_id: int, topic: str, level: str = "beginner") -> UserLearningProgress:
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
        stmt = select(UserWatchlist).where(UserWatchlist.user_id == user_id).order_by(UserWatchlist.keyword.asc())
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

    async def has_notification_been_sent(self, user_id: int, article_id: Optional[int], notification_type: str) -> bool:
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
        sources_count = (
            await self.session.execute(select(func.count(Source.id)).where(Source.is_active.is_(True)))
        ).scalar_one() or 0
        categories_count = (await self.session.execute(select(func.count(Category.id)))).scalar_one() or 0
        total_delivered = (await self.session.execute(select(func.count(NotificationLog.id)))).scalar_one() or 0
        users_count = (await self.session.execute(select(func.count(User.id)))).scalar_one() or 0
        opportunities_count = (
            await self.session.execute(select(func.count(Opportunity.id)).where(Opportunity.status == "open"))
        ).scalar_one() or 0
        universities_count = (await self.session.execute(select(func.count(UniversityProfile.id)))).scalar_one() or 0
        resources_count = (await self.session.execute(select(func.count(AcademicResource.id)))).scalar_one() or 0

        stats = {
            "total_articles": articles_count,
            "active_sources": sources_count,
            "stem_categories": categories_count,
            "total_notifications_sent": total_delivered,
            "total_users": users_count,
            "verified_opportunities": opportunities_count,
            "universities_count": universities_count,
            "academic_resources_count": resources_count,
        }

        if user_id is not None:
            user_saved = (
                await self.session.execute(select(func.count(SavedArticle.id)).where(SavedArticle.user_id == user_id))
            ).scalar_one() or 0
            user_watchlist_count = (
                await self.session.execute(select(func.count(UserWatchlist.id)).where(UserWatchlist.user_id == user_id))
            ).scalar_one() or 0
            user_notifications = (
                await self.session.execute(
                    select(func.count(NotificationLog.id)).where(NotificationLog.user_id == user_id)
                )
            ).scalar_one() or 0
            user_quizzes = (
                await self.session.execute(
                    select(func.sum(UserLearningProgress.quizzes_taken)).where(UserLearningProgress.user_id == user_id)
                )
            ).scalar_one() or 0

            stats["user_saved_articles"] = user_saved
            stats["user_watchlist_keywords"] = user_watchlist_count
            stats["user_notifications_received"] = user_notifications
            stats["user_quizzes_taken"] = user_quizzes

        return stats

    # ------------------ Public User Management & Access Control ------------------

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> Tuple[User, bool]:
        """Fetch existing user or auto-register public user on first interaction."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # Update last activity and profile if changed
            user.last_active_at = datetime.now(timezone.utc)
            if username and user.username != username:
                user.username = username
            if first_name and user.first_name != first_name:
                user.first_name = first_name
            if last_name and user.last_name != last_name:
                user.last_name = last_name
            await self.session.commit()
            return user, False

        # Pre-assign admin role if telegram_id is configured in settings
        is_admin = bool(settings.allowed_user_ids and telegram_id in settings.allowed_user_ids)

        new_user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_admin=is_admin,
            is_active=True,
            is_banned=False,
        )
        self.session.add(new_user)
        await self.session.commit()
        return new_user, True

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Fetch user by Telegram ID."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def is_user_admin(self, telegram_id: int) -> bool:
        """Check if a user has administrative privileges."""
        if settings.allowed_user_ids and telegram_id in settings.allowed_user_ids:
            return True
        user = await self.get_user_by_telegram_id(telegram_id)
        return bool(user and user.is_admin)

    async def set_user_ban_status(self, telegram_id: int, is_banned: bool) -> bool:
        """Update user banned/blocked status."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if not user:
            return False
        user.is_banned = is_banned
        user.is_active = not is_banned
        await self.session.commit()
        return True

    async def save_user_feedback(self, telegram_id: int, message: str, category: str = "general") -> UserFeedback:
        """Store user feedback or issue report."""
        fb = UserFeedback(user_id=telegram_id, category=category, message=message.strip())
        self.session.add(fb)
        await self.session.commit()
        return fb

    async def export_user_data(self, telegram_id: int) -> dict:
        """Export all user-associated data for GDPR compliance / transparency."""
        user = await self.get_user_by_telegram_id(telegram_id)
        pref = await self.get_or_create_preference(telegram_id)
        saved = await self.get_saved_articles(telegram_id, limit=100)
        watchlist = await self.get_user_watchlist(telegram_id)
        learning = await self.get_user_learning_history(telegram_id)

        return {
            "telegram_id": telegram_id,
            "profile": {
                "username": user.username if user else None,
                "first_name": user.first_name if user else None,
                "is_admin": user.is_admin if user else False,
                "created_at": user.created_at.isoformat() if user else None,
            },
            "preferences": {
                "preferred_categories": pref.preferred_categories,
                "digest_time": pref.digest_time,
                "notifications_enabled": pref.notifications_enabled,
                "quiet_hours": f"{pref.quiet_hours_start} - {pref.quiet_hours_end}",
                "high_impact_alerts": pref.high_impact_alerts_enabled,
                "weekly_report": pref.weekly_report_enabled,
            },
            "saved_articles_count": len(saved),
            "watchlist_keywords": [w.keyword for w in watchlist],
            "learning_records_count": len(learning),
        }

    async def delete_user_data(self, telegram_id: int) -> dict:
        """Permanently delete all user data across preferences, bookmarks, watchlists, and learning progress."""
        await self.session.execute(delete(SavedArticle).where(SavedArticle.user_id == telegram_id))
        await self.session.execute(delete(UserPreference).where(UserPreference.user_id == telegram_id))
        await self.session.execute(delete(UserWatchlist).where(UserWatchlist.user_id == telegram_id))
        await self.session.execute(delete(UserLearningProgress).where(UserLearningProgress.user_id == telegram_id))
        await self.session.execute(delete(UserFeedback).where(UserFeedback.user_id == telegram_id))
        await self.session.execute(delete(NotificationLog).where(NotificationLog.user_id == telegram_id))
        await self.session.commit()
        return {"status": "deleted", "telegram_id": telegram_id}

    # ------------------ Student Hub & Opportunities ------------------

    async def save_opportunity(
        self,
        title: str,
        slug: str,
        opportunity_type: str,
        provider_name: str,
        official_url: str,
        country: str,
        study_level: str,
        stem_fields: str = "All STEM",
        funding_type: str = "fully_funded",
        eligibility_criteria: str = "",
        provider_type: str = "university",
        application_url: Optional[str] = None,
        eligible_nationalities: str = "All",
        benefits: Optional[str] = None,
        required_documents: Optional[str] = None,
        application_opens_at: Optional[datetime] = None,
        application_deadline: Optional[datetime] = None,
        is_rolling: bool = False,
        verification_tier: str = "officially_verified",
        status: str = "open",
        source_attribution: str = "",
        commit: bool = True,
    ) -> Tuple[Opportunity, bool]:
        """Save a new academic opportunity with duplicate detection by slug."""
        stmt = select(Opportunity).where(Opportunity.slug == slug)
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            return existing, False

        opp = Opportunity(
            title=title.strip(),
            slug=slug.strip(),
            opportunity_type=opportunity_type.strip(),
            provider_name=provider_name.strip(),
            provider_type=provider_type.strip(),
            official_url=official_url.strip(),
            application_url=application_url.strip() if application_url else None,
            country=country.strip(),
            eligible_nationalities=eligible_nationalities.strip(),
            study_level=study_level.strip(),
            stem_fields=stem_fields.strip(),
            funding_type=funding_type.strip(),
            benefits=benefits.strip() if benefits else None,
            eligibility_criteria=eligibility_criteria.strip(),
            required_documents=required_documents.strip() if required_documents else None,
            application_opens_at=application_opens_at,
            application_deadline=application_deadline,
            is_rolling=is_rolling,
            verification_tier=verification_tier.strip(),
            status=status.strip(),
            source_attribution=source_attribution.strip() or provider_name.strip(),
        )
        self.session.add(opp)
        if commit:
            await self.session.commit()
            await self.session.refresh(opp)
        return opp, True

    async def get_opportunity_by_id(self, opportunity_id: int) -> Optional[Opportunity]:
        """Fetch an opportunity by primary key."""
        stmt = select(Opportunity).where(Opportunity.id == opportunity_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_opportunity_by_slug(self, slug: str) -> Optional[Opportunity]:
        """Fetch an opportunity by unique slug."""
        stmt = select(Opportunity).where(Opportunity.slug == slug)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_opportunities(
        self,
        opportunity_type: Optional[str] = None,
        study_level: Optional[str] = None,
        funding_type: Optional[str] = None,
        country: Optional[str] = None,
        stem_field: Optional[str] = None,
        status: Optional[str] = "open",
        verification_tier: Optional[str] = None,
        active_only: bool = True,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Opportunity]:
        """Query opportunities with multi-faceted filtering."""
        stmt = select(Opportunity)

        if opportunity_type and opportunity_type != "all":
            stmt = stmt.where(Opportunity.opportunity_type == opportunity_type)
        if study_level and study_level != "all":
            stmt = stmt.where(or_(Opportunity.study_level == study_level, Opportunity.study_level == "all_levels"))
        if funding_type and funding_type != "all":
            stmt = stmt.where(Opportunity.funding_type == funding_type)
        if country and country != "all":
            stmt = stmt.where(Opportunity.country.ilike(f"%{country}%"))
        if stem_field and stem_field != "all":
            stmt = stmt.where(
                or_(
                    Opportunity.stem_fields.ilike(f"%{stem_field}%"),
                    Opportunity.stem_fields == "All STEM",
                )
            )
        if status and status != "all":
            stmt = stmt.where(Opportunity.status == status)
        if verification_tier:
            stmt = stmt.where(Opportunity.verification_tier == verification_tier)

        if active_only:
            current_time = datetime.now(timezone.utc)
            stmt = stmt.where(Opportunity.status != "expired")
            stmt = stmt.where(
                or_(
                    Opportunity.application_deadline >= current_time,
                    Opportunity.is_rolling.is_(True),
                    Opportunity.application_deadline.is_(None),
                )
            )

        stmt = stmt.order_by(
            Opportunity.application_deadline.asc().nulls_last(),
            Opportunity.published_at.desc(),
        )
        stmt = stmt.limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def count_opportunities(
        self,
        opportunity_type: Optional[str] = None,
        study_level: Optional[str] = None,
        funding_type: Optional[str] = None,
        country: Optional[str] = None,
        stem_field: Optional[str] = None,
        status: Optional[str] = "open",
        verification_tier: Optional[str] = None,
        active_only: bool = True,
    ) -> int:
        """Count matching opportunities for pagination."""
        stmt = select(func.count(Opportunity.id))

        if opportunity_type and opportunity_type != "all":
            stmt = stmt.where(Opportunity.opportunity_type == opportunity_type)
        if study_level and study_level != "all":
            stmt = stmt.where(or_(Opportunity.study_level == study_level, Opportunity.study_level == "all_levels"))
        if funding_type and funding_type != "all":
            stmt = stmt.where(Opportunity.funding_type == funding_type)
        if country and country != "all":
            stmt = stmt.where(Opportunity.country.ilike(f"%{country}%"))
        if stem_field and stem_field != "all":
            stmt = stmt.where(
                or_(
                    Opportunity.stem_fields.ilike(f"%{stem_field}%"),
                    Opportunity.stem_fields == "All STEM",
                )
            )
        if status and status != "all":
            stmt = stmt.where(Opportunity.status == status)
        if verification_tier:
            stmt = stmt.where(Opportunity.verification_tier == verification_tier)

        if active_only:
            current_time = datetime.now(timezone.utc)
            stmt = stmt.where(Opportunity.status != "expired")
            stmt = stmt.where(
                or_(
                    Opportunity.application_deadline >= current_time,
                    Opportunity.is_rolling.is_(True),
                    Opportunity.application_deadline.is_(None),
                )
            )

        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def expire_lapsed_opportunities(self, now: Optional[datetime] = None) -> int:
        """Mark opportunities whose application deadline has passed as expired."""
        check_time = now or datetime.now(timezone.utc)
        stmt = (
            select(Opportunity)
            .where(Opportunity.status == "open")
            .where(Opportunity.is_rolling.is_(False))
            .where(Opportunity.application_deadline.is_not(None))
            .where(Opportunity.application_deadline < check_time)
        )
        res = await self.session.execute(stmt)
        lapsed = list(res.scalars().all())
        for opp in lapsed:
            opp.status = "expired"
        if lapsed:
            await self.session.commit()
        return len(lapsed)

    # ------------------ University Profiles ------------------

    async def save_university_profile(
        self,
        name: str,
        slug: str,
        country: str,
        official_portal_url: str,
        admissions_portal_url: str,
        city: Optional[str] = None,
        admission_requirements: Optional[str] = None,
        application_procedures: Optional[str] = None,
        tuition_and_funding: Optional[str] = None,
        international_guidelines_url: Optional[str] = None,
        academic_regulations_url: Optional[str] = None,
        research_opportunities_url: Optional[str] = None,
        commit: bool = True,
    ) -> Tuple[UniversityProfile, bool]:
        """Save university profile with duplicate detection by slug."""
        stmt = select(UniversityProfile).where(UniversityProfile.slug == slug)
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            return existing, False

        profile = UniversityProfile(
            name=name.strip(),
            slug=slug.strip(),
            country=country.strip(),
            city=city.strip() if city else None,
            official_portal_url=official_portal_url.strip(),
            admissions_portal_url=admissions_portal_url.strip(),
            admission_requirements=admission_requirements.strip() if admission_requirements else None,
            application_procedures=application_procedures.strip() if application_procedures else None,
            tuition_and_funding=tuition_and_funding.strip() if tuition_and_funding else None,
            international_guidelines_url=international_guidelines_url.strip() if international_guidelines_url else None,
            academic_regulations_url=academic_regulations_url.strip() if academic_regulations_url else None,
            research_opportunities_url=research_opportunities_url.strip() if research_opportunities_url else None,
        )
        self.session.add(profile)
        if commit:
            await self.session.commit()
            await self.session.refresh(profile)
        return profile, True

    async def get_university_profiles(
        self,
        country: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[UniversityProfile]:
        """Fetch verified university profiles with optional country filter."""
        stmt = select(UniversityProfile)
        if country and country != "all":
            stmt = stmt.where(UniversityProfile.country.ilike(f"%{country}%"))
        stmt = stmt.order_by(UniversityProfile.name.asc()).limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_university_by_slug(self, slug: str) -> Optional[UniversityProfile]:
        """Fetch university profile by slug."""
        stmt = select(UniversityProfile).where(UniversityProfile.slug == slug)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def count_university_profiles(self, country: Optional[str] = None) -> int:
        """Count university profiles for pagination."""
        stmt = select(func.count(UniversityProfile.id))
        if country and country != "all":
            stmt = stmt.where(UniversityProfile.country.ilike(f"%{country}%"))
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    # ------------------ Academic Resources ------------------

    async def save_academic_resource(
        self,
        title: str,
        slug: str,
        resource_type: str,
        stem_discipline: str,
        provider_institution: str,
        official_access_url: str,
        license_type: str = "Open Access",
        is_copyright_verified: bool = True,
        description: Optional[str] = None,
        commit: bool = True,
    ) -> Tuple[AcademicResource, bool]:
        """Save an open educational resource record."""
        stmt = select(AcademicResource).where(AcademicResource.slug == slug)
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            return existing, False

        resource = AcademicResource(
            title=title.strip(),
            slug=slug.strip(),
            resource_type=resource_type.strip(),
            stem_discipline=stem_discipline.strip(),
            provider_institution=provider_institution.strip(),
            official_access_url=official_access_url.strip(),
            license_type=license_type.strip(),
            is_copyright_verified=is_copyright_verified,
            description=description.strip() if description else None,
        )
        self.session.add(resource)
        if commit:
            await self.session.commit()
            await self.session.refresh(resource)
        return resource, True

    async def get_academic_resources(
        self,
        resource_type: Optional[str] = None,
        stem_discipline: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[AcademicResource]:
        """Fetch academic resources filtered by type or discipline."""
        stmt = select(AcademicResource).where(AcademicResource.is_copyright_verified.is_(True))
        if resource_type and resource_type != "all":
            stmt = stmt.where(AcademicResource.resource_type == resource_type)
        if stem_discipline and stem_discipline != "all":
            stmt = stmt.where(AcademicResource.stem_discipline.ilike(f"%{stem_discipline}%"))
        stmt = stmt.order_by(AcademicResource.title.asc()).limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_academic_resource_by_slug(self, slug: str) -> Optional[AcademicResource]:
        """Fetch an academic resource by slug."""
        stmt = select(AcademicResource).where(AcademicResource.slug == slug)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def count_academic_resources(
        self,
        resource_type: Optional[str] = None,
        stem_discipline: Optional[str] = None,
    ) -> int:
        """Count academic resources for pagination."""
        stmt = select(func.count(AcademicResource.id)).where(AcademicResource.is_copyright_verified.is_(True))
        if resource_type and resource_type != "all":
            stmt = stmt.where(AcademicResource.resource_type == resource_type)
        if stem_discipline and stem_discipline != "all":
            stmt = stmt.where(AcademicResource.stem_discipline.ilike(f"%{stem_discipline}%"))
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    # ------------------ Reports & Trust Moderation ------------------

    async def submit_opportunity_report(
        self,
        user_id: int,
        report_type: str,
        details: str,
        opportunity_id: Optional[int] = None,
    ) -> OpportunityReport:
        """Submit a community issue report or public submission for admin moderation."""
        report = OpportunityReport(
            user_id=user_id,
            opportunity_id=opportunity_id,
            report_type=report_type.strip(),
            details=details.strip(),
            status="pending_review",
        )
        self.session.add(report)
        if opportunity_id:
            opp_stmt = select(Opportunity).where(Opportunity.id == opportunity_id)
            opp_res = await self.session.execute(opp_stmt)
            opp = opp_res.scalar_one_or_none()
            if opp:
                opp.report_count += 1
        await self.session.commit()
        await self.session.refresh(report)
        return report

    async def get_opportunity_reports(
        self,
        status: str = "pending_review",
        limit: int = 20,
        offset: int = 0,
    ) -> List[OpportunityReport]:
        """Fetch community reports for moderation audit."""
        stmt = select(OpportunityReport)
        if status != "all":
            stmt = stmt.where(OpportunityReport.status == status)
        stmt = stmt.order_by(OpportunityReport.created_at.desc()).limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def count_opportunity_reports(self, status: str = "pending_review") -> int:
        """Count community reports by status."""
        stmt = select(func.count(OpportunityReport.id))
        if status != "all":
            stmt = stmt.where(OpportunityReport.status == status)
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def get_pending_opportunities(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Opportunity]:
        """Fetch submitted opportunities awaiting administrative moderation and verification."""
        stmt = (
            select(Opportunity)
            .where(Opportunity.status == "pending_approval")
            .order_by(Opportunity.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def count_pending_opportunities(self) -> int:
        """Count submitted opportunities awaiting review."""
        stmt = select(func.count(Opportunity.id)).where(Opportunity.status == "pending_approval")
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def approve_opportunity(
        self,
        opportunity_id: int,
        admin_user_id: int,
        verification_tier: str = "officially_verified",
        notes: Optional[str] = None,
    ) -> Optional[Opportunity]:
        """Approve an unverified opportunity, assign verification tier, and publish."""
        stmt = select(Opportunity).where(Opportunity.id == opportunity_id)
        res = await self.session.execute(stmt)
        opp = res.scalar_one_or_none()
        if not opp:
            return None

        opp.status = "open"
        opp.verification_tier = verification_tier
        opp.last_verified_at = datetime.now(timezone.utc)

        # Resolve any pending submission reports for this opportunity
        rep_stmt = (
            select(OpportunityReport)
            .where(OpportunityReport.opportunity_id == opportunity_id)
            .where(OpportunityReport.report_type == "submission")
            .where(OpportunityReport.status == "pending_review")
        )
        rep_res = await self.session.execute(rep_stmt)
        for rep in rep_res.scalars().all():
            rep.status = "verified_resolved"
            rep.reviewed_by_admin_id = admin_user_id

        await self.session.commit()
        await self.session.refresh(opp)
        return opp

    async def reject_opportunity(
        self,
        opportunity_id: int,
        admin_user_id: int,
        reason: Optional[str] = None,
    ) -> Optional[Opportunity]:
        """Reject an opportunity submission and archive."""
        stmt = select(Opportunity).where(Opportunity.id == opportunity_id)
        res = await self.session.execute(stmt)
        opp = res.scalar_one_or_none()
        if not opp:
            return None

        opp.status = "rejected"

        rep_stmt = (
            select(OpportunityReport)
            .where(OpportunityReport.opportunity_id == opportunity_id)
            .where(OpportunityReport.report_type == "submission")
            .where(OpportunityReport.status == "pending_review")
        )
        rep_res = await self.session.execute(rep_stmt)
        for rep in rep_res.scalars().all():
            rep.status = "dismissed"
            rep.reviewed_by_admin_id = admin_user_id

        await self.session.commit()
        await self.session.refresh(opp)
        return opp

    async def resolve_opportunity_report(
        self,
        report_id: int,
        admin_user_id: int,
        resolution: str = "verified_resolved",
        action_taken: Optional[str] = None,
    ) -> Optional[OpportunityReport]:
        """Resolve a community issue report with optional action on the opportunity."""
        stmt = select(OpportunityReport).where(OpportunityReport.id == report_id)
        res = await self.session.execute(stmt)
        report = res.scalar_one_or_none()
        if not report:
            return None

        report.status = resolution
        report.reviewed_by_admin_id = admin_user_id

        # If action is to mark opportunity expired
        if action_taken == "expire_opportunity" and report.opportunity_id:
            opp_stmt = select(Opportunity).where(Opportunity.id == report.opportunity_id)
            opp_res = await self.session.execute(opp_stmt)
            opp = opp_res.scalar_one_or_none()
            if opp:
                opp.status = "expired"

        await self.session.commit()
        await self.session.refresh(report)
        return report

    # ------------------ Unified Search Across Domains ------------------

    async def search_opportunities(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        opportunity_type: Optional[str] = None,
        active_only: bool = True,
    ) -> List[Opportunity]:
        """Search opportunities by keyword across title, provider, criteria, and stem fields."""
        pattern = f"%{query.strip()}%"
        stmt = select(Opportunity).where(
            or_(
                Opportunity.title.ilike(pattern),
                Opportunity.provider_name.ilike(pattern),
                Opportunity.stem_fields.ilike(pattern),
                Opportunity.eligibility_criteria.ilike(pattern),
                Opportunity.country.ilike(pattern),
            )
        )
        if opportunity_type and opportunity_type != "all":
            stmt = stmt.where(Opportunity.opportunity_type == opportunity_type)
        if active_only:
            current_time = datetime.now(timezone.utc)
            stmt = stmt.where(Opportunity.status != "expired")
            stmt = stmt.where(
                or_(
                    Opportunity.application_deadline >= current_time,
                    Opportunity.is_rolling.is_(True),
                    Opportunity.application_deadline.is_(None),
                )
            )
        stmt = stmt.order_by(Opportunity.published_at.desc()).offset(offset).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def search_university_profiles(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        country: Optional[str] = None,
    ) -> List[UniversityProfile]:
        """Search university profiles by keyword in name, country, city, or requirements."""
        pattern = f"%{query.strip()}%"
        stmt = select(UniversityProfile).where(
            or_(
                UniversityProfile.name.ilike(pattern),
                UniversityProfile.country.ilike(pattern),
                UniversityProfile.city.ilike(pattern),
                UniversityProfile.admission_requirements.ilike(pattern),
            )
        )
        if country and country != "all":
            stmt = stmt.where(UniversityProfile.country.ilike(f"%{country}%"))
        stmt = stmt.order_by(UniversityProfile.name.asc()).offset(offset).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def search_academic_resources(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        resource_type: Optional[str] = None,
        discipline: Optional[str] = None,
    ) -> List[AcademicResource]:
        """Search legal academic resources by keyword in title, discipline, provider, or description."""
        pattern = f"%{query.strip()}%"
        stmt = select(AcademicResource).where(
            AcademicResource.is_copyright_verified.is_(True),
            or_(
                AcademicResource.title.ilike(pattern),
                AcademicResource.stem_discipline.ilike(pattern),
                AcademicResource.provider_institution.ilike(pattern),
                AcademicResource.description.ilike(pattern),
            ),
        )
        if resource_type and resource_type != "all":
            stmt = stmt.where(AcademicResource.resource_type == resource_type)
        if discipline and discipline != "all":
            stmt = stmt.where(AcademicResource.stem_discipline.ilike(f"%{discipline}%"))
        stmt = stmt.order_by(AcademicResource.title.asc()).offset(offset).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # ------------------ Consented Search History ------------------

    async def save_search_query_log(
        self,
        query: str,
        user_id: Optional[int] = None,
        category: Optional[str] = None,
        results_count: int = 0,
    ) -> SearchQueryLog:
        """Record user search query for telemetry and quick retrieval if permitted."""
        log = SearchQueryLog(
            user_id=user_id,
            query=query.strip(),
            category=category.strip() if category else None,
            results_count=results_count,
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def get_user_search_history(self, user_id: int, limit: int = 10) -> List[SearchQueryLog]:
        """Fetch recent consented search queries for a user."""
        stmt = (
            select(SearchQueryLog)
            .where(SearchQueryLog.user_id == user_id)
            .order_by(SearchQueryLog.created_at.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def clear_user_search_history(self, user_id: int) -> int:
        """Clear all search query logs for a user upon request."""
        stmt = delete(SearchQueryLog).where(SearchQueryLog.user_id == user_id)
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount or 0
