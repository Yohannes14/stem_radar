"""Background scheduler managing automated intelligence collection, alerts, and briefings."""

import logging
from typing import Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.services.automation_service import AutomationService, automation_service
from app.services.news_service import NewsService

logger = logging.getLogger(__name__)


class IntelligenceScheduler:
    """Automated job runner executing scheduled news collection, alerts, and briefings."""

    def __init__(
        self,
        collection_interval_minutes: int = 30,
        alerts_interval_minutes: int = 15,
        service: Optional[AutomationService] = None,
    ) -> None:
        self.interval_minutes = collection_interval_minutes
        self.alerts_interval_minutes = alerts_interval_minutes
        self.scheduler = AsyncIOScheduler()
        self.news_service = NewsService()
        self.automation_service = service or automation_service
        self.bot: Optional[Any] = None

    def set_bot(self, bot: Any) -> None:
        """Inject or update the Telegram bot instance used for notifications."""
        self.bot = bot

    def start(self, bot: Optional[Any] = None) -> None:
        """Register periodic jobs and start the asynchronous scheduler.

        Idempotent: safe against duplicate invocations and restarts.
        """
        if bot is not None:
            self.bot = bot

        if self.scheduler.running:
            logger.warning("Scheduler is already active. Retaining running instance.")
            return

        # 1. Periodic Multi-Source Collection Job
        self.scheduler.add_job(
            self._scheduled_collection_job,
            trigger=IntervalTrigger(minutes=self.interval_minutes),
            id="periodic_intelligence_collection",
            name="Periodic Multi-Source Collection",
            replace_existing=True,
        )

        # 2. Real-Time Watchlist & High-Impact Alerts Job
        self.scheduler.add_job(
            self._scheduled_alerts_job,
            trigger=IntervalTrigger(minutes=self.alerts_interval_minutes),
            id="periodic_watchlist_and_impact_alerts",
            name="Real-Time Watchlist & High-Impact Alerts",
            replace_existing=True,
        )

        # 3. Daily Executive Briefing Job (runs hourly at minute 0)
        self.scheduler.add_job(
            self._scheduled_daily_briefing_job,
            trigger=CronTrigger(minute=0),
            id="hourly_daily_briefing_check",
            name="Hourly Daily Briefing Dispatcher",
            replace_existing=True,
        )

        # 4. Weekly Intelligence Report Job (runs Mondays at 09:00 UTC)
        self.scheduler.add_job(
            self._scheduled_weekly_report_job,
            trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
            id="weekly_intelligence_report",
            name="Weekly Intelligence Report Dispatcher",
            replace_existing=True,
        )

        # 5. Periodic Opportunity Expiry Sweeper Job (runs every 4 hours)
        self.scheduler.add_job(
            self._scheduled_opportunity_expiry_job,
            trigger=IntervalTrigger(hours=4),
            id="periodic_opportunity_expiry_sweep",
            name="Periodic Opportunity Expiry Sweep",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info(
            "IntelligenceScheduler started. Ingestion: every %d min, Alerts: every %d min.",
            self.interval_minutes,
            self.alerts_interval_minutes,
        )

    def shutdown(self) -> None:
        """Gracefully stop background scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("IntelligenceScheduler shut down gracefully.")

    async def _scheduled_collection_job(self) -> None:
        """Background worker executing ingestion pass followed by alert checks."""
        logger.info("[Scheduler] Starting scheduled intelligence collection...")
        try:
            results = await self.news_service.collect_from_all_sources()
            total = sum(results.values())
            logger.info("[Scheduler] Scheduled collection complete. Ingested %d items.", total)
            if total > 0:
                await self._scheduled_alerts_job()
        except Exception as exc:
            logger.error("[Scheduler] Error during scheduled collection: %s", exc, exc_info=True)

    async def _scheduled_alerts_job(self) -> None:
        """Evaluate recent intelligence against active watchlists and trigger alerts."""
        logger.debug("[Scheduler] Evaluating watchlist and high-impact development alerts...")
        try:
            delivered = await self.automation_service.check_and_dispatch_realtime_alerts(bot=self.bot)
            if delivered > 0:
                logger.info("[Scheduler] Delivered %d personalized alerts.", delivered)
        except Exception as exc:
            logger.error("[Scheduler] Error checking real-time alerts: %s", exc, exc_info=True)

    async def _scheduled_daily_briefing_job(self) -> None:
        """Dispatch daily executive briefings to users configured for current UTC hour."""
        logger.info("[Scheduler] Checking scheduled daily briefings for current hour...")
        try:
            delivered = await self.automation_service.check_and_dispatch_daily_briefings(bot=self.bot)
            if delivered > 0:
                logger.info("[Scheduler] Dispatched %d scheduled daily briefings.", delivered)
        except Exception as exc:
            logger.error("[Scheduler] Error dispatching daily briefings: %s", exc, exc_info=True)

    async def _scheduled_weekly_report_job(self) -> None:
        """Dispatch weekly intelligence reports to subscribers."""
        logger.info("[Scheduler] Checking scheduled weekly intelligence reports...")
        try:
            delivered = await self.automation_service.check_and_dispatch_weekly_reports(bot=self.bot)
            if delivered > 0:
                logger.info("[Scheduler] Dispatched %d weekly intelligence reports.", delivered)
        except Exception as exc:
            logger.error("[Scheduler] Error dispatching weekly reports: %s", exc, exc_info=True)

    async def _scheduled_opportunity_expiry_job(self) -> None:
        """Background worker transitioning lapsed application deadlines to expired status."""
        try:
            from app.services.student_hub_service import student_hub_service

            count = await student_hub_service.expire_lapsed_opportunities()
            if count > 0:
                logger.info("[Scheduler] Automated sweep transitioned %d lapsed opportunities to expired.", count)
        except Exception as exc:
            logger.error("[Scheduler] Error in opportunity expiry sweeper: %s", exc, exc_info=True)


scheduler = IntelligenceScheduler()
