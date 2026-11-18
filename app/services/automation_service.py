"""Automation, scheduling, and personalization service for STEM RADAR.

Provides scheduled daily STEM briefings, weekly intelligence digests,
personalized notification delivery, keyword watchlists, and quiet hours enforcement.
"""

import asyncio
import logging
import re
from datetime import datetime, time, timezone
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from telegram.constants import ParseMode
from telegram.error import RetryAfter, TelegramError

from app.bot.ui.formatters import (
    format_daily_briefing,
    format_high_impact_alert,
    format_watchlist_alert,
    format_weekly_report,
)
from app.database.database import get_session_factory
from app.database.models import Article, UserPreference, UserWatchlist
from app.database.repository import Repository
from app.processors.ranking import ArticleRanker

logger = logging.getLogger(__name__)


def parse_time_str(time_str: str) -> Optional[time]:
    """Parse 'HH:MM' string into datetime.time object."""
    try:
        parts = time_str.strip().split(":")
        if len(parts) == 2:
            return time(hour=int(parts[0]), minute=int(parts[1]))
    except Exception:
        pass
    return None


def is_in_quiet_hours(pref: UserPreference, current_time: Optional[datetime] = None) -> bool:
    """Determine whether current UTC time falls within user's configured quiet hours.

    Supports both normal ranges (e.g. 01:00 to 06:00) and overnight ranges (e.g. 22:00 to 07:00).
    """
    start_t = parse_time_str(pref.quiet_hours_start)
    end_t = parse_time_str(pref.quiet_hours_end)

    if not start_t or not end_t or start_t == end_t:
        return False

    now_t = (current_time or datetime.now(timezone.utc)).time()

    if start_t < end_t:
        # Same-day interval (e.g. 01:00 to 06:00)
        return start_t <= now_t < end_t
    else:
        # Overnight interval crossing midnight (e.g. 22:00 to 07:00)
        return now_t >= start_t or now_t < end_t


class AutomationService:
    """Core intelligence automation service managing briefings, alerts, and watchlists."""

    def __init__(self, ranker: Optional[ArticleRanker] = None) -> None:
        self.ranker = ranker or ArticleRanker()

    async def get_trending_developments(
        self,
        limit: int = 10,
        user_id: Optional[int] = None,
        session: Optional[AsyncSession] = None,
    ) -> List[Tuple[Article, float]]:
        """Rank recent articles by composite technological impact score, optionally boosted by user interests."""
        user_interests = None
        if session:
            repo = Repository(session)
            if user_id:
                user_interests = await repo.get_user_preferred_categories(user_id)
            articles = await repo.get_recent_articles(limit=limit * 3)
        else:
            session_factory = get_session_factory()
            async with session_factory() as s:
                repo = Repository(s)
                if user_id:
                    user_interests = await repo.get_user_preferred_categories(user_id)
                articles = await repo.get_recent_articles(limit=limit * 3)

        scored: List[Tuple[Article, float]] = []
        for art in articles:
            categories = [(c.slug, 1.0) for c in art.categories] if art.categories else None
            score = self.ranker.calculate_score(
                title=art.title,
                description=art.description,
                published_at=art.published_at or art.collected_at,
                categories=categories,
                user_interests=user_interests,
            )
            scored.append((art, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    async def calculate_domain_velocity(
        self,
        session: Optional[AsyncSession] = None,
        limit: int = 100,
    ) -> dict:
        """Compute evidence-based trend velocity indicators across STEM domains."""
        close_session = False
        if session is None:
            session_factory = get_session_factory()
            session = await session_factory().__aenter__()
            close_session = True

        try:
            repo = Repository(session)
            categories = await repo.get_categories()
            articles = await repo.get_recent_articles(limit=limit)

            domain_data: dict = {}
            for cat in categories:
                domain_data[cat.slug] = {
                    "slug": cat.slug,
                    "name": cat.name,
                    "articles": [],
                    "papers": 0,
                }

            for art in articles:
                if not art.categories:
                    continue
                is_paper = bool(art.source and art.source.source_type == "arxiv")
                score = self.ranker.calculate_score(
                    title=art.title,
                    description=art.description,
                    published_at=art.published_at or art.collected_at,
                    categories=[(c.slug, 1.0) for c in art.categories],
                )
                for c in art.categories:
                    if c.slug in domain_data:
                        domain_data[c.slug]["articles"].append((art, score))
                        if is_paper:
                            domain_data[c.slug]["papers"] += 1

            results: dict = {}
            for slug, d in domain_data.items():
                scored_list = d["articles"]
                count = len(scored_list)
                if count > 0:
                    avg_score = sum(s for _, s in scored_list) / count
                    top_art, _ = max(scored_list, key=lambda x: x[1])
                    top_headline = top_art.title
                else:
                    avg_score = 0.0
                    top_headline = "No recent articles indexed"

                # Calculate evidence-based momentum
                if count >= 4 and avg_score >= 60.0:
                    momentum = "Surging"
                elif count >= 2 or avg_score >= 50.0:
                    momentum = "Rising"
                else:
                    momentum = "Stable"

                results[slug] = {
                    "slug": slug,
                    "name": d["name"],
                    "count": count,
                    "paper_count": d["papers"],
                    "avg_score": round(avg_score, 1),
                    "momentum": momentum,
                    "top_headline": top_headline,
                }

            return results
        finally:
            if close_session and session:
                await session.close()

    async def generate_daily_briefing(
        self, user_id: int, user_name: str = "", limit: int = 5, session: Optional[AsyncSession] = None
    ) -> Tuple[str, List[Article]]:
        """Generate personalized executive daily briefing based on user preferences."""
        close_session = False
        if session is None:
            session_factory = get_session_factory()
            session = await session_factory().__aenter__()
            close_session = True

        try:
            repo = Repository(session)
            pref = await repo.get_or_create_preference(user_id)

            user_interests = [
                s.strip() for s in (pref.preferred_categories or "").split(",") if s.strip() and s.strip() != "all"
            ]

            articles = await repo.get_recent_articles(
                limit=25,
                category_slugs=user_interests if user_interests else None,
            )

            # If user has specific categories but fewer articles returned, supplement with general articles
            if len(articles) < limit and user_interests:
                more_articles = await repo.get_recent_articles(limit=15)
                existing_ids = {a.id for a in articles}
                articles.extend([a for a in more_articles if a.id not in existing_ids])

            # Score and rank to select the top breakthroughs with user interest match boost
            scored = []
            for a in articles:
                categories = [(c.slug, 1.0) for c in a.categories] if a.categories else None
                score = self.ranker.calculate_score(
                    title=a.title,
                    description=a.description,
                    published_at=a.published_at or a.collected_at,
                    categories=categories,
                    user_interests=user_interests,
                )
                scored.append((a, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            top_articles = [item[0] for item in scored[:limit]]

            cat_filter_display = ", ".join([f"#{s}" for s in user_interests]) if user_interests else ""
            text = format_daily_briefing(
                top_articles,
                user_name=user_name,
                category_filter=cat_filter_display,
            )
            return text, top_articles
        finally:
            if close_session and session:
                await session.__aexit__(None, None, None)

    async def generate_weekly_report(
        self, user_id: int, session: Optional[AsyncSession] = None
    ) -> Tuple[str, List[Article]]:
        """Generate comprehensive weekly intelligence report with domain breakdowns."""
        close_session = False
        if session is None:
            session_factory = get_session_factory()
            session = await session_factory().__aenter__()
            close_session = True

        try:
            repo = Repository(session)
            articles = await repo.get_recent_articles(limit=30)

            # Compute category breakdown
            breakdown: dict = {}
            scored = []
            for a in articles:
                if a.categories:
                    for cat in a.categories:
                        breakdown[cat.name] = breakdown.get(cat.name, 0) + 1
                score = self.ranker.calculate_score(
                    title=a.title,
                    description=a.description,
                    published_at=a.published_at or a.collected_at,
                )
                scored.append((a, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            top_breakthroughs = [item[0] for item in scored[:5]]

            text = format_weekly_report(
                articles=top_breakthroughs,
                total_collected=len(articles),
                domain_breakdown=breakdown,
            )
            return text, top_breakthroughs
        finally:
            if close_session and session:
                await session.__aexit__(None, None, None)

    def match_watchlist_keywords(self, text: str, watchlist: List[UserWatchlist]) -> List[UserWatchlist]:
        """Identify which user watchlist keywords match the given article text."""
        matched: List[UserWatchlist] = []
        lower_text = text.lower()
        for item in watchlist:
            kw = item.keyword.strip().lower()
            if not kw:
                continue
            # Regex match with word boundary when single token or substring when multi-word
            pattern = rf"\b{re.escape(kw)}\b" if " " not in kw else re.escape(kw)
            if re.search(pattern, lower_text):
                matched.append(item)
        return matched

    async def evaluate_article_for_alerts(
        self, article: Article, user_id: int, pref: UserPreference, watchlist: List[UserWatchlist]
    ) -> List[dict]:
        """Evaluate a single article against user preferences and watchlist.

        Returns candidate alerts list with type, article, score or matched keyword.
        """
        alerts: List[dict] = []
        corpus = f"{article.title} {article.description or ''}"

        # 1. Watchlist keywords check
        matches = self.match_watchlist_keywords(corpus, watchlist)
        for m in matches:
            alerts.append(
                {
                    "type": "watchlist_alert",
                    "keyword": m.keyword,
                    "watchlist_id": m.id,
                    "article": article,
                }
            )

        # 2. High-impact development check
        if pref.high_impact_alerts_enabled:
            score = self.ranker.calculate_score(
                title=article.title,
                description=article.description,
                published_at=article.published_at or article.collected_at,
            )
            # Threshold for high-impact alert notification
            if score >= 75.0:
                alerts.append(
                    {
                        "type": "high_impact_alert",
                        "score": score,
                        "article": article,
                    }
                )

        return alerts

    async def dispatch_user_alerts(
        self,
        bot,
        user_id: int,
        alerts: List[dict],
        repo: Repository,
    ) -> int:
        """Deliver alerts to a user, checking duplicate prevention, quiet hours, and rate limits."""
        if not alerts:
            return 0

        pref = await repo.get_or_create_preference(user_id)
        if not pref.notifications_enabled:
            logger.debug("Notifications disabled for user %d. Skipping alerts.", user_id)
            return 0

        if is_in_quiet_hours(pref):
            logger.info(
                "User %d is in quiet hours (%s - %s). Suppressing alerts.",
                user_id,
                pref.quiet_hours_start,
                pref.quiet_hours_end,
            )
            return 0

        delivered_count = 0
        for alert in alerts:
            art = alert["article"]
            alert_type = alert["type"]

            # Duplicate notification prevention
            already_sent = await repo.has_notification_been_sent(
                user_id=user_id,
                article_id=art.id,
                notification_type=alert_type,
            )
            if already_sent:
                continue

            # Format message according to alert type
            if alert_type == "watchlist_alert":
                msg_text = format_watchlist_alert(art, alert["keyword"])
            else:
                msg_text = format_high_impact_alert(art, alert["score"])

            # Send via Telegram bot if provided
            sent_successfully = True
            if bot is not None:
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=msg_text,
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=False,
                    )
                    # Respect Telegram messaging limit
                    await asyncio.sleep(0.05)
                except RetryAfter as exc:
                    logger.warning("Telegram flood limit reached. Backing off %s s", exc.retry_after)
                    await asyncio.sleep(float(exc.retry_after))
                    try:
                        await bot.send_message(
                            chat_id=user_id,
                            text=msg_text,
                            parse_mode=ParseMode.MARKDOWN,
                        )
                    except Exception as inner_exc:
                        logger.error("Failed alert send after retry to %d: %s", user_id, inner_exc)
                        sent_successfully = False
                except TelegramError as exc:
                    logger.error("Telegram error delivering alert to %d: %s", user_id, exc)
                    sent_successfully = False

            status_str = "delivered" if sent_successfully else "failed"
            await repo.log_notification(
                user_id=user_id,
                article_id=art.id,
                notification_type=alert_type,
                status=status_str,
            )

            if sent_successfully:
                delivered_count += 1
                if alert_type == "watchlist_alert" and "watchlist_id" in alert:
                    await repo.increment_watchlist_matches(alert["watchlist_id"])

        return delivered_count

    async def check_and_dispatch_realtime_alerts(self, bot=None) -> int:
        """Periodic batch worker: evaluates recent articles against active user watchlists & preferences."""
        session_factory = get_session_factory()
        total_delivered = 0

        async with session_factory() as session:
            repo = Repository(session)
            active_prefs = await repo.get_all_active_preferences()
            if not active_prefs:
                return 0

            # Pull recently collected articles (last 20)
            recent_articles = await repo.get_recent_articles(limit=20)
            if not recent_articles:
                return 0

            for pref in active_prefs:
                watchlist = await repo.get_user_watchlist(pref.user_id)
                user_alerts: List[dict] = []
                for art in recent_articles:
                    evaluated = await self.evaluate_article_for_alerts(
                        article=art,
                        user_id=pref.user_id,
                        pref=pref,
                        watchlist=watchlist,
                    )
                    user_alerts.extend(evaluated)

                if user_alerts:
                    delivered = await self.dispatch_user_alerts(
                        bot=bot,
                        user_id=pref.user_id,
                        alerts=user_alerts,
                        repo=repo,
                    )
                    total_delivered += delivered

        return total_delivered

    async def check_and_dispatch_daily_briefings(self, bot=None, current_hour_str: Optional[str] = None) -> int:
        """Hourly worker: checks users whose digest_time matches current hour and sends daily briefing."""
        target_hour = current_hour_str or datetime.now(timezone.utc).strftime("%H:00")
        session_factory = get_session_factory()
        delivered_count = 0

        async with session_factory() as session:
            repo = Repository(session)
            active_prefs = await repo.get_all_active_preferences()

            for pref in active_prefs:
                # Check if digest time hour matches
                pref_hour = pref.digest_time.split(":")[0] + ":00" if ":" in pref.digest_time else pref.digest_time
                if pref_hour != target_hour:
                    continue

                if is_in_quiet_hours(pref):
                    continue

                # Check duplicate prevention for today's briefing
                already_sent = await repo.has_notification_been_sent(
                    user_id=pref.user_id,
                    article_id=None,
                    notification_type="daily_briefing",
                )
                if already_sent:
                    continue

                briefing_text, _ = await self.generate_daily_briefing(user_id=pref.user_id, session=session)

                sent = True
                if bot is not None:
                    try:
                        await bot.send_message(
                            chat_id=pref.user_id,
                            text=briefing_text,
                            parse_mode=ParseMode.MARKDOWN,
                        )
                        await asyncio.sleep(0.05)
                    except Exception as exc:
                        logger.error("Failed sending daily briefing to %d: %s", pref.user_id, exc)
                        sent = False

                status = "delivered" if sent else "failed"
                await repo.log_notification(
                    user_id=pref.user_id,
                    article_id=None,
                    notification_type="daily_briefing",
                    status=status,
                )
                if sent:
                    delivered_count += 1

        return delivered_count

    async def check_and_dispatch_weekly_reports(self, bot=None) -> int:
        """Weekly worker: sends weekly intelligence reports to subscribers."""
        session_factory = get_session_factory()
        delivered_count = 0

        async with session_factory() as session:
            repo = Repository(session)
            active_prefs = await repo.get_all_active_preferences()

            for pref in active_prefs:
                if not pref.weekly_report_enabled or is_in_quiet_hours(pref):
                    continue

                already_sent = await repo.has_notification_been_sent(
                    user_id=pref.user_id,
                    article_id=None,
                    notification_type="weekly_report",
                )
                if already_sent:
                    continue

                report_text, _ = await self.generate_weekly_report(user_id=pref.user_id, session=session)

                sent = True
                if bot is not None:
                    try:
                        await bot.send_message(
                            chat_id=pref.user_id,
                            text=report_text,
                            parse_mode=ParseMode.MARKDOWN,
                        )
                        await asyncio.sleep(0.05)
                    except Exception as exc:
                        logger.error("Failed sending weekly report to %d: %s", pref.user_id, exc)
                        sent = False

                status = "delivered" if sent else "failed"
                await repo.log_notification(
                    user_id=pref.user_id,
                    article_id=None,
                    notification_type="weekly_report",
                    status=status,
                )
                if sent:
                    delivered_count += 1

        return delivered_count


automation_service = AutomationService()
