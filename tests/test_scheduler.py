"""Tests for the background IntelligenceScheduler."""

import asyncio

import pytest

from app.scheduler.jobs import IntelligenceScheduler


@pytest.mark.asyncio
async def test_scheduler_lifecycle():
    sched = IntelligenceScheduler(collection_interval_minutes=15)
    assert sched.scheduler.running is False

    sched.start()
    assert sched.scheduler.running is True

    # Starting twice should be idempotent
    sched.start()
    assert sched.scheduler.running is True

    sched.shutdown()
    await asyncio.sleep(0.05)
    assert sched.scheduler.running is False
