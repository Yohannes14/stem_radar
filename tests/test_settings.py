"""Tests for the user settings command and preferences toggling."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat, Message, Update, User

from app.bot.handlers.base import main_menu_callback_router
from app.bot.handlers.settings import settings_callback_router, settings_command
from app.bot.ui.menu import format_myspace_intro, get_myspace_keyboard
from app.database.repository import Repository


@pytest.fixture
def mock_settings_update():
    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = 556677
    user.first_name = "Jordan"

    chat = MagicMock(spec=Chat)
    chat.id = 556677

    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()

    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = message
    update.callback_query = None
    return update


@pytest.mark.asyncio
async def test_settings_command_renders_panel(mock_settings_update, test_session_factory):
    # Call settings command
    await settings_command(mock_settings_update, MagicMock())

    mock_settings_update.effective_message.reply_text.assert_called_once()
    reply_text = mock_settings_update.effective_message.reply_text.call_args[0][0]
    assert "User Settings" in reply_text
    assert "556677" in reply_text
    assert "Quiet Hours" in reply_text


@pytest.mark.asyncio
async def test_settings_toggle_quiet_hours(mock_settings_update, monkeypatch, test_session_factory):
    monkeypatch.setattr("app.bot.handlers.settings.get_session_factory", lambda: test_session_factory)

    update = MagicMock(spec=Update)
    query = MagicMock()
    query.data = "toggle_quiet"
    query.answer = AsyncMock()
    query.message = MagicMock()
    query.message.edit_reply_markup = AsyncMock()
    update.callback_query = query
    update.effective_user = mock_settings_update.effective_user

    # Default quiet hours: start="22:00", end="07:00" -> currently on
    # Toggling should turn quiet hours OFF (00:00 - 00:00)
    await settings_callback_router(update, MagicMock())
    query.answer.assert_called_once()
    assert "disabled" in query.answer.call_args[0][0].lower()
    query.message.edit_reply_markup.assert_called_once()

    async with test_session_factory() as session:
        repo = Repository(session)
        pref = await repo.get_or_create_preference(556677)
        assert pref.quiet_hours_start == "00:00"
        assert pref.quiet_hours_end == "00:00"

    # Toggle again -> turns quiet hours ON (22:00 - 07:00)
    query.answer.reset_mock()
    query.message.edit_reply_markup.reset_mock()
    await settings_callback_router(update, MagicMock())
    query.answer.assert_called_once()
    assert "enabled" in query.answer.call_args[0][0].lower()

    async with test_session_factory() as session:
        repo = Repository(session)
        pref = await repo.get_or_create_preference(556677)
        assert pref.quiet_hours_start == "22:00"
        assert pref.quiet_hours_end == "07:00"


def test_myspace_keyboard_and_intro():
    """Verify My Space keyboard buttons and telemetry introduction."""
    kb = get_myspace_keyboard()
    callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "menu:saved" in callbacks
    assert "menu:interests" in callbacks
    assert "menu:watchlist" in callbacks
    assert "menu:progress" in callbacks
    assert "menu:settings" in callbacks
    assert "menu:feedback" in callbacks
    assert "menu:export" in callbacks
    assert "menu:privacy" in callbacks
    assert "menu:help" in callbacks
    assert "menu:home" in callbacks

    stats = {
        "user_saved_articles": 7,
        "user_watchlist_keywords": 3,
        "user_quizzes_taken": 5,
        "user_notifications_received": 12,
    }
    intro = format_myspace_intro(user_name="Jordan", stats=stats)
    assert "Jordan" in intro
    assert "`7` articles & papers bookmarked" in intro
    assert "`3` tracked technology keywords" in intro
    assert "`5` quizzes completed" in intro
    assert "`12` briefings & notifications received" in intro


@pytest.mark.asyncio
async def test_main_menu_callback_routes_myspace_feedback_and_export(monkeypatch, test_session_factory):
    """Verify that main_menu_callback_router handles menu:feedback and menu:export."""
    monkeypatch.setattr("app.bot.handlers.base.get_session_factory", lambda: test_session_factory)
    monkeypatch.setattr("app.bot.handlers.user_management.get_session_factory", lambda: test_session_factory)

    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = 556677
    user.first_name = "Jordan"
    update.effective_user = user

    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()
    update.effective_message = message

    query = MagicMock()
    query.answer = AsyncMock()
    query.message = message
    update.callback_query = query

    # Route menu:feedback
    query.data = "menu:feedback"
    await main_menu_callback_router(update, MagicMock())
    message.reply_text.assert_called()
    fb_text = message.reply_text.call_args[0][0]
    assert "Feedback" in fb_text

    # Route menu:export
    message.reply_text.reset_mock()
    query.data = "menu:export"
    await main_menu_callback_router(update, MagicMock())
    message.reply_text.assert_called()
    exp_text = message.reply_text.call_args[0][0]
    assert "Exported Personal Data" in exp_text
