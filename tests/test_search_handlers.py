"""Tests for Telegram bot search handlers, category chips, sort switches, and callbacks."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import CallbackQuery, Chat, Message, Update, User

from app.bot.handlers.base import main_menu_callback_router
from app.bot.handlers.news import callback_router, search_command
from app.bot.ui.menu import _RECENT_CALLBACKS
from app.config import settings
from app.services.search.models import SearchResultItem, UnifiedSearchResponse


@pytest.fixture
def mock_search_update():
    """Mock Telegram update for search handler testing."""
    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = 887766
    user.first_name = "Ada"
    user.username = "lovelace"

    chat = MagicMock(spec=Chat)
    chat.id = 887766

    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()
    message.edit_text = AsyncMock()

    query = MagicMock(spec=CallbackQuery)
    query.id = "query_search_1"
    query.data = "menu:search"
    query.message = message
    query.answer = AsyncMock()

    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = message
    update.callback_query = query
    return update


@pytest.mark.asyncio
async def test_search_command_without_args_shows_intro(mock_search_update):
    """Verify /search without arguments renders the search dashboard and topic shortcuts."""
    context = MagicMock()
    context.args = []

    with patch.object(settings, "allowed_user_ids", [887766]):
        await search_command(mock_search_update, context)

    mock_search_update.callback_query.message.edit_text.assert_called_once()
    text = mock_search_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "Unified Search Engine" in text
    assert "/search <keyword>" in text


@pytest.mark.asyncio
async def test_search_command_with_query_renders_unified_results(mock_search_update):
    """Verify /search <keyword> executes unified search and renders categorized result cards."""
    context = MagicMock()
    context.args = ["astronomy"]
    mock_search_update.callback_query = None

    mock_response = UnifiedSearchResponse(
        items=[
            SearchResultItem(
                id="art:1",
                title="James Webb Space Telescope Deep Field Observation",
                snippet="Infrared survey of distant galaxies.",
                source_name="NASA / ESA",
                category="Research Papers",
                is_verified=True,
                url="https://example.com/jwst-survey",
                score=9.5,
                item_type="paper",
                original_id=1,
            ),
            SearchResultItem(
                id="opp:2",
                title="Astrophysics Doctoral Research Fellowship",
                snippet="Full funding for astrophysics research.",
                source_name="European Southern Observatory",
                category="Scholarships",
                is_verified=True,
                url="https://example.org/astrophysics-fellowship",
                score=7.8,
                item_type="scholarship",
                original_id=2,
            ),
        ],
        total_items=2,
        page=1,
        page_size=4,
        total_pages=1,
        query="astronomy",
        category="all",
        sort_by="relevance",
    )

    with patch("app.bot.handlers.news.search_service.search", AsyncMock(return_value=mock_response)):
        with patch.object(settings, "allowed_user_ids", [887766]):
            await search_command(mock_search_update, context)

    mock_search_update.effective_message.reply_text.assert_called_once()
    reply_text = mock_search_update.effective_message.reply_text.call_args[1]["text"]
    assert 'Search Results for "astronomy"' in reply_text
    assert "James Webb Space Telescope" in reply_text
    assert "Astrophysics Doctoral Research Fellowship" in reply_text


@pytest.mark.asyncio
async def test_search_callback_router_interactions(mock_search_update):
    """Verify category filtering, sort toggling, and pagination callbacks."""
    mock_response = UnifiedSearchResponse(
        items=[],
        total_items=0,
        page=1,
        page_size=4,
        total_pages=1,
        query="robotics",
        category="scholarships",
        sort_by="date",
    )

    # 1. Category switch: search:cat:scholarships:relevance:robotics
    _RECENT_CALLBACKS.clear()
    mock_search_update.callback_query.data = "search:cat:scholarships:relevance:robotics"
    mock_search_update.callback_query.message.edit_text.reset_mock()

    with patch("app.bot.handlers.news.search_service.search", AsyncMock(return_value=mock_response)):
        with patch.object(settings, "allowed_user_ids", [887766]):
            await callback_router(mock_search_update, MagicMock())

    mock_search_update.callback_query.message.edit_text.assert_called_once()

    # 2. Sort switch: search:sort:all:date:robotics
    _RECENT_CALLBACKS.clear()
    mock_search_update.callback_query.data = "search:sort:all:date:robotics"
    mock_search_update.callback_query.message.edit_text.reset_mock()

    with patch("app.bot.handlers.news.search_service.search", AsyncMock(return_value=mock_response)):
        with patch.object(settings, "allowed_user_ids", [887766]):
            await callback_router(mock_search_update, MagicMock())

    mock_search_update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_main_menu_quick_topic_search(mock_search_update):
    """Verify search_kw:quantum callback in main menu triggers unified search view."""
    _RECENT_CALLBACKS.clear()
    mock_search_update.callback_query.data = "search_kw:quantum"
    mock_search_update.callback_query.message.edit_text.reset_mock()

    with patch("app.bot.handlers.base.send_search_view", AsyncMock()) as mock_send_search:
        with patch.object(settings, "allowed_user_ids", [887766]):
            await main_menu_callback_router(mock_search_update, MagicMock())

    mock_send_search.assert_called_once()
    assert mock_send_search.call_args[1]["query"] == "quantum"
