"""Tests for the background IntelligenceScheduler."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.scheduler.jobs import IntelligenceScheduler


@pytest.mark.asyncio
async def test_scheduler_lifecycle():
    sched = IntelligenceScheduler(collection_interval_minutes=15)
    assert sched.scheduler.running is False

    sched.start()
    assert sched.scheduler.running is True

    # Check that jobs were added
    job_ids = [job.id for job in sched.scheduler.get_jobs()]
    assert "periodic_intelligence_collection" in job_ids
    assert "periodic_watchlist_and_impact_alerts" in job_ids
    assert "hourly_daily_briefing_check" in job_ids
    assert "weekly_intelligence_report" in job_ids

    # Starting twice should be idempotent
    sched.start()
    assert sched.scheduler.running is True

    sched.shutdown()
    await asyncio.sleep(0.05)
    assert sched.scheduler.running is False


@pytest.mark.asyncio
async def test_scheduler_set_bot():
    sched = IntelligenceScheduler()
    mock_bot = MagicMock()
    sched.set_bot(mock_bot)
    assert sched.bot is mock_bot


@pytest.mark.asyncio
async def test_scheduler_job_failure_recovery():
    """Verify that an exception in collection or alerts does not crash the scheduler."""
    mock_service = MagicMock()
    mock_service.check_and_dispatch_realtime_alerts = AsyncMock(side_effect=RuntimeError("Simulated alerts error"))
    mock_service.check_and_dispatch_daily_briefings = AsyncMock(side_effect=RuntimeError("Simulated briefing error"))
    mock_service.check_and_dispatch_weekly_reports = AsyncMock(side_effect=RuntimeError("Simulated weekly error"))

    sched = IntelligenceScheduler(service=mock_service)
    sched.news_service.collect_from_all_sources = AsyncMock(side_effect=RuntimeError("Network down"))

    # Each job worker must execute and recover gracefully without raising
    await sched._scheduled_collection_job()
    await sched._scheduled_alerts_job()
    await sched._scheduled_daily_briefing_job()
    await sched._scheduled_weekly_report_job()
