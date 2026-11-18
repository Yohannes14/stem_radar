"""Tests for Phase 5: Personalization, Watchlists, Quiet Hours, and Automation."""

from datetime import datetime, time, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat, Message, Update, User

from app.bot.handlers.automation import (
    automation_callback_router,
    briefing_command,
    stats_command,
    trends_command,
    watchlist_command,
)
from app.bot.handlers.settings import settings_callback_router, settings_command
from app.database.models import Article, UserPreference
from app.database.repository import Repository
from app.services.automation_service import (
    AutomationService,
    is_in_quiet_hours,
    parse_time_str,
)


@pytest.fixture
def mock_bot_user():
    user = MagicMock(spec=User)
    user.id = 998877
    user.first_name = "Ada"
    return user


@pytest.fixture
def mock_automation_update(mock_bot_user):
    update = MagicMock(spec=Update)
    chat = MagicMock(spec=Chat)
    chat.id = mock_bot_user.id

    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()

    update.effective_user = mock_bot_user
    update.effective_chat = chat
    update.effective_message = message
    update.callback_query = None
    return update


def test_parse_time_str():
    assert parse_time_str("22:30") == time(22, 30)
    assert parse_time_str("07:00") == time(7, 0)
    assert parse_time_str("invalid") is None


def test_is_in_quiet_hours_normal_window():
    pref = UserPreference(user_id=1, quiet_hours_start="01:00", quiet_hours_end="06:00")
    # Inside quiet hours
    inside = datetime(2026, 11, 15, 3, 30, tzinfo=timezone.utc)
    assert is_in_quiet_hours(pref, inside) is True

    # Before quiet hours
    before = datetime(2026, 11, 15, 0, 45, tzinfo=timezone.utc)
    assert is_in_quiet_hours(pref, before) is False

    # After quiet hours
    after = datetime(2026, 11, 15, 6, 1, tzinfo=timezone.utc)
    assert is_in_quiet_hours(pref, after) is False


def test_is_in_quiet_hours_overnight_window():
    pref = UserPreference(user_id=1, quiet_hours_start="22:00", quiet_hours_end="07:00")
    # Late night (before midnight)
    late = datetime(2026, 11, 15, 23, 15, tzinfo=timezone.utc)
    assert is_in_quiet_hours(pref, late) is True

    # Early morning (after midnight)
    early = datetime(2026, 11, 15, 4, 0, tzinfo=timezone.utc)
    assert is_in_quiet_hours(pref, early) is True

    # Exactly at boundary
    at_end = datetime(2026, 11, 15, 7, 0, tzinfo=timezone.utc)
    assert is_in_quiet_hours(pref, at_end) is False

    # Midday
    midday = datetime(2026, 11, 15, 14, 0, tzinfo=timezone.utc)
    assert is_in_quiet_hours(pref, midday) is False


def test_is_in_quiet_hours_disabled_or_invalid():
    pref = UserPreference(user_id=1, quiet_hours_start="00:00", quiet_hours_end="00:00")
    now = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
    assert is_in_quiet_hours(pref, now) is False


@pytest.mark.asyncio
async def test_watchlist_repository_crud(test_session_factory):
    async with test_session_factory() as session:
        repo = Repository(session)

        # 1. Add keyword
        item, created = await repo.add_watchlist_keyword(user_id=123, keyword="humanoid")
        assert created is True
        assert item.keyword == "humanoid"

        # 2. Duplicate keyword check
        item_dup, created_dup = await repo.add_watchlist_keyword(user_id=123, keyword="HUMANOID")
        assert created_dup is False
        assert item_dup.id == item.id

        # 3. List keywords
        watchlist = await repo.get_user_watchlist(user_id=123)
        assert len(watchlist) == 1
        assert watchlist[0].keyword == "humanoid"

        # 4. Increment matches
        await repo.increment_watchlist_matches(item.id)
        wl_updated = await repo.get_user_watchlist(user_id=123)
        assert wl_updated[0].match_count == 1

        # 5. Remove keyword
        deleted = await repo.remove_watchlist_keyword(user_id=123, keyword="humanoid")
        assert deleted is True

        deleted_again = await repo.remove_watchlist_keyword(user_id=123, keyword="humanoid")
        assert deleted_again is False

        # 6. Clear keywords
        await repo.add_watchlist_keyword(user_id=123, keyword="quantum")
        await repo.add_watchlist_keyword(user_id=123, keyword="superconductor")
        cleared_count = await repo.clear_user_watchlist(user_id=123)
        assert cleared_count == 2
        assert len(await repo.get_user_watchlist(user_id=123)) == 0


@pytest.mark.asyncio
async def test_duplicate_notification_prevention(test_session_factory):
    async with test_session_factory() as session:
        repo = Repository(session)

        # Seed article
        article, _ = await repo.save_article(
            title="Breakthrough in Quantum Entanglement",
            url="https://example.com/quantum-paper",
            source_id=1,
        )

        user_id = 456
        notif_type = "high_impact_alert"

        # Initially no notification has been logged
        assert await repo.has_notification_been_sent(user_id, article.id, notif_type) is False

        # Log notification
        log_entry = await repo.log_notification(
            user_id=user_id,
            article_id=article.id,
            notification_type=notif_type,
            status="delivered",
        )
        assert log_entry.status == "delivered"

        # Now verification check returns True
        assert await repo.has_notification_been_sent(user_id, article.id, notif_type) is True

        # Secondary logging attempt handles gracefully
        second_log = await repo.log_notification(
            user_id=user_id,
            article_id=article.id,
            notification_type=notif_type,
            status="delivered",
        )
        assert second_log.id == log_entry.id


@pytest.mark.asyncio
async def test_evaluate_article_for_alerts_and_dispatch(test_session_factory):
    svc = AutomationService()
    async with test_session_factory() as session:
        repo = Repository(session)

        # Add user preference and watchlist
        pref = await repo.get_or_create_preference(user_id=789)
        pref.quiet_hours_start = "02:00"
        pref.quiet_hours_end = "04:00"
        wl_item, _ = await repo.add_watchlist_keyword(user_id=789, keyword="superconductor")

        # Create high-impact article matching watchlist
        article = Article(
            id=101,
            title="SOTA Breakthrough: Room Temperature Superconductor Unveiled",
            url="https://example.com/superconductor",
            description="Researchers discovered novel superconducting materials with state of the art benchmarks.",
            source_id=1,
            published_at=datetime.now(timezone.utc),
        )

        alerts = await svc.evaluate_article_for_alerts(
            article=article,
            user_id=789,
            pref=pref,
            watchlist=[wl_item],
        )

        # Should match both watchlist keyword and high-impact score
        alert_types = [a["type"] for a in alerts]
        assert "watchlist_alert" in alert_types
        assert "high_impact_alert" in alert_types

        # Mock Telegram bot
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()

        # Dispatch alerts
        delivered = await svc.dispatch_user_alerts(
            bot=mock_bot,
            user_id=789,
            alerts=alerts,
            repo=repo,
        )
        assert delivered == len(alerts)
        assert mock_bot.send_message.call_count == len(alerts)

        # Second dispatch must be blocked by duplicate prevention
        delivered_again = await svc.dispatch_user_alerts(
            bot=mock_bot,
            user_id=789,
            alerts=alerts,
            repo=repo,
        )
        assert delivered_again == 0


@pytest.mark.asyncio
async def test_briefing_command_renders_briefing(mock_automation_update, monkeypatch, test_session_factory):
    monkeypatch.setattr("app.database.database.get_session_factory", lambda: test_session_factory)
    monkeypatch.setattr("app.services.automation_service.get_session_factory", lambda: test_session_factory)

    async with test_session_factory() as session:
        repo = Repository(session)
        await repo.save_article(
            title="Novel Humanoid Actuator Architecture",
            url="https://example.com/actuator",
            source_id=1,
            description="Engineers created a novel high-torque electric actuator.",
        )

    await briefing_command(mock_automation_update, MagicMock())
    mock_automation_update.effective_message.reply_text.assert_called_once()
    reply = mock_automation_update.effective_message.reply_text.call_args[0][0]
    assert "Daily STEM Briefing" in reply
    assert "Ada" in reply


@pytest.mark.asyncio
async def test_watchlist_command_interactions(mock_automation_update, monkeypatch, test_session_factory):
    monkeypatch.setattr("app.bot.handlers.automation.get_session_factory", lambda: test_session_factory)

    context = MagicMock()

    # 1. /watchlist (empty)
    context.args = []
    await watchlist_command(mock_automation_update, context)
    reply1 = mock_automation_update.effective_message.reply_text.call_args[0][0]
    assert "Watchlist" in reply1
    assert "not tracking any keywords" in reply1

    # 2. /watchlist add humanoid
    context.args = ["add", "humanoid"]
    await watchlist_command(mock_automation_update, context)
    reply2 = mock_automation_update.effective_message.reply_text.call_args[0][0]
    assert "Added" in reply2
    assert "#humanoid" in reply2

    # 3. /watchlist (active)
    context.args = []
    await watchlist_command(mock_automation_update, context)
    reply3 = mock_automation_update.effective_message.reply_text.call_args[0][0]
    assert "Active Watchlist" in reply3
    assert "#humanoid" in reply3

    # 4. /watchlist remove humanoid
    context.args = ["remove", "humanoid"]
    await watchlist_command(mock_automation_update, context)
    reply4 = mock_automation_update.effective_message.reply_text.call_args[0][0]
    assert "Removed" in reply4

    # 5. /watchlist clear
    context.args = ["add", "quantum"]
    await watchlist_command(mock_automation_update, context)
    context.args = ["clear"]
    await watchlist_command(mock_automation_update, context)
    reply5 = mock_automation_update.effective_message.reply_text.call_args[0][0]
    assert "Cleared" in reply5


@pytest.mark.asyncio
async def test_trends_command_renders_feed(mock_automation_update, monkeypatch, test_session_factory):
    monkeypatch.setattr("app.services.automation_service.get_session_factory", lambda: test_session_factory)

    async with test_session_factory() as session:
        repo = Repository(session)
        await repo.save_article(
            title="Breakthrough SOTA Model Unveiled",
            url="https://example.com/sota-ai",
            source_id=1,
            description="Researchers benchmarked a novel architecture with superior reasoning performance.",
        )

    await trends_command(mock_automation_update, MagicMock())
    mock_automation_update.effective_message.reply_text.assert_called_once()
    reply = mock_automation_update.effective_message.reply_text.call_args[0][0]
    assert "Trending STEM Developments" in reply
    assert "Breakthrough SOTA Model Unveiled" in reply


@pytest.mark.asyncio
async def test_stats_command_renders_telemetry(mock_automation_update, monkeypatch, test_session_factory):
    monkeypatch.setattr("app.bot.handlers.automation.get_session_factory", lambda: test_session_factory)

    await stats_command(mock_automation_update, MagicMock())
    mock_automation_update.effective_message.reply_text.assert_called_once()
    reply = mock_automation_update.effective_message.reply_text.call_args[0][0]
    assert "Global Platform Scope" in reply
    assert "Personal Intelligence Activity" in reply


@pytest.mark.asyncio
async def test_settings_panel_and_callbacks(mock_automation_update, monkeypatch, test_session_factory):
    monkeypatch.setattr("app.bot.handlers.settings.get_session_factory", lambda: test_session_factory)

    # 1. Render settings command
    await settings_command(mock_automation_update, MagicMock())
    reply = mock_automation_update.effective_message.reply_text.call_args[0][0]
    assert "Quiet Hours" in reply
    assert "High-Impact Alerts" in reply

    # 2. Callback toggle notifications
    update = MagicMock(spec=Update)
    query = MagicMock()
    query.data = "toggle_notif"
    query.answer = AsyncMock()
    query.message.edit_reply_markup = AsyncMock()
    update.callback_query = query
    update.effective_user = mock_automation_update.effective_user

    await settings_callback_router(update, MagicMock())
    query.answer.assert_called_once()

    # 3. Callback toggle high impact alerts
    query.reset_mock()
    query.data = "toggle_impact"
    await settings_callback_router(update, MagicMock())
    query.answer.assert_called_once()

    # 4. Callback toggle weekly report
    query.reset_mock()
    query.data = "toggle_weekly"
    await settings_callback_router(update, MagicMock())
    query.answer.assert_called_once()

    # 5. Callback set domain filter
    query.reset_mock()
    query.data = "pref_cat:robotics"
    await settings_callback_router(update, MagicMock())
    query.answer.assert_called_once()
    assert "robotics" in query.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_automation_callback_router_watchlist_removal(mock_automation_update, monkeypatch, test_session_factory):
    monkeypatch.setattr("app.bot.handlers.automation.get_session_factory", lambda: test_session_factory)

    async with test_session_factory() as session:
        repo = Repository(session)
        await repo.add_watchlist_keyword(user_id=mock_automation_update.effective_user.id, keyword="fusion")

    update = MagicMock(spec=Update)
    query = MagicMock()
    query.data = "wl_rm:fusion"
    query.answer = AsyncMock()
    query.message.edit_text = AsyncMock()
    update.callback_query = query
    update.effective_user = mock_automation_update.effective_user

    await automation_callback_router(update, MagicMock())
    query.answer.assert_called_once()
    assert "Removed #fusion" in query.answer.call_args[0][0]
