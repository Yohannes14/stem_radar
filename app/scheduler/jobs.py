"""Background scheduler managing automated intelligence collection and daily digests."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.services.news_service import NewsService

logger = logging.getLogger(__name__)


class IntelligenceScheduler:
    """Automated job runner executing scheduled news collection and digest alerts."""

    def __init__(self, collection_interval_minutes: int = 30) -> None:
        self.interval_minutes = collection_interval_minutes
        self.scheduler = AsyncIOScheduler()
        self.news_service = NewsService()

    def start(self) -> None:
        """Register periodic jobs and start the asynchronous scheduler."""
        if self.scheduler.running:
            logger.warning("Scheduler is already active.")
            return

        # 1. Periodic Multi-Source Collection Job
        self.scheduler.add_job(
            self._scheduled_collection_job,
            trigger=IntervalTrigger(minutes=self.interval_minutes),
            id="periodic_intelligence_collection",
            name="Periodic Multi-Source Collection",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info(
            "IntelligenceScheduler started. Auto-collection scheduled every %d minutes.",
            self.interval_minutes,
        )

    def shutdown(self) -> None:
        """Gracefully stop background scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("IntelligenceScheduler shut down gracefully.")

    async def _scheduled_collection_job(self) -> None:
        """Background worker executing ingestion pass."""
        logger.info("[Scheduler] Starting scheduled intelligence collection...")
        try:
            results = await self.news_service.collect_from_all_sources()
            total = sum(results.values())
            logger.info("[Scheduler] Scheduled collection complete. Saved %d new items.", total)
        except Exception as exc:
            logger.error("[Scheduler] Error during scheduled collection: %s", exc, exc_info=True)


scheduler = IntelligenceScheduler()
