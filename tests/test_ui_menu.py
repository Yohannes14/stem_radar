"""Comprehensive tests for the unified 12-section Main Menu, navigation controls, and debouncing."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import CallbackQuery, Chat, Message, Update, User

from app.bot.handlers.base import main_menu_callback_router, start_command
from app.bot.keyboards.navigation import (
    build_nav_keyboard,
    get_back_home_keyboard,
    nav_back_home_row,
    nav_pagination_row,
)
from app.bot.ui.menu import (
    _RECENT_CALLBACKS,
    format_ai_hub_intro,
    format_empty_state,
    format_learn_hub_intro,
    format_main_menu,
    format_search_intro,
    get_main_menu_keyboard,
    is_duplicate_callback,
    safe_edit_or_reply,
)
from app.config import settings


@pytest.fixture
def mock_menu_update():
    """Mock Telegram Update with callback query for menu testing."""
    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = 112233
    user.first_name = "Alan"
    user.username = "alanturing"

    chat = MagicMock(spec=Chat)
    chat.id = 112233

    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()
    message.edit_text = AsyncMock()

    query = MagicMock(spec=CallbackQuery)
    query.id = "query_123"
    query.data = "menu:home"
    query.message = message
    query.answer = AsyncMock()

    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = message
    update.callback_query = query
    return update


def test_main_menu_keyboard_has_12_sections():
    """Verify that get_main_menu_keyboard contains the flagship interactive sections."""
    keyboard = get_main_menu_keyboard()
    assert len(keyboard.inline_keyboard) == 8  # 8 rows of 2 buttons each = 16 buttons

    all_callbacks = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    expected_callbacks = [
        "menu:news",
        "menu:trending",
        "menu:student_hub",
        "menu:scholarships",
        "menu:ethiopia",
        "menu:politics",
        "menu:ai",
        "menu:research",
        "menu:learn",
        "menu:projects",
        "menu:radar",
        "menu:search",
        "menu:saved",
        "menu:interests",
        "menu:settings",
        "menu:help",
    ]
    assert all_callbacks == expected_callbacks


def test_navigation_helpers():
    """Verify navigation rows, back/home rows, and pagination."""
    # 1. Back and home row
    row = nav_back_home_row(back_target="menu:news", home_target="menu:home", refresh_target="refresh:1")
    assert len(row) == 3
    assert row[0].callback_data == "menu:news"
    assert row[1].callback_data == "refresh:1"
    assert row[2].callback_data == "menu:home"

    # 2. Pagination row at start
    p_start = nav_pagination_row(offset=0, total=5, prefix="nav:all")
    assert len(p_start) == 2  # counter + next
    assert p_start[0].text == "1/5"
    assert p_start[1].callback_data == "nav:all:1"

    # 3. Pagination row in middle
    p_mid = nav_pagination_row(offset=2, total=5, prefix="nav:all")
    assert len(p_mid) == 3  # prev + counter + next
    assert p_mid[0].callback_data == "nav:all:1"
    assert p_mid[1].text == "3/5"
    assert p_mid[2].callback_data == "nav:all:3"

    # 4. Standalone and compound nav keyboards
    back_home_kb = get_back_home_keyboard(back_target="menu:home")
    assert len(back_home_kb.inline_keyboard) == 1

    compound_kb = build_nav_keyboard([], back_target="menu:home", home_target="menu:home")
    assert len(compound_kb.inline_keyboard) == 1


def test_menu_formatters():
    """Verify text presentation formatters."""
    main_text = format_main_menu("Ada", {"total_articles": 42, "active_sources": 8, "user_saved_articles": 3})
    assert "Welcome to STEM RADAR, Ada!" in main_text
    assert "`42` research records" in main_text
    assert "`8` verified feeds" in main_text
    assert "`3` articles saved" in main_text

    ai_text = format_ai_hub_intro()
    assert "AI Intelligence Hub" in ai_text

    learn_text = format_learn_hub_intro()
    assert "STEM Learning Academy" in learn_text

    search_text = format_search_intro()
    assert "/search <keyword>" in search_text

    empty_text = format_empty_state("No Articles", "Check back soon.")
    assert "No Articles" in empty_text


def test_debounce_mechanism():
    """Verify callback click debouncing prevents rapid duplicate submissions."""
    _RECENT_CALLBACKS.clear()
    uid = 999111
    data = "menu:ai"

    # First click: allowed
    assert is_duplicate_callback(uid, data) is False

    # Immediate second click: debounced
    assert is_duplicate_callback(uid, data) is True

    # After expiry: allowed again
    with patch("time.time", return_value=time.time() + 2.0):
        assert is_duplicate_callback(uid, data) is False


@pytest.mark.asyncio
async def test_safe_edit_or_reply_handles_message_not_modified(mock_menu_update):
    """Verify that 'message is not modified' Telegram errors are handled idempotently without throwing."""
    mock_menu_update.callback_query.message.edit_text.side_effect = Exception(
        "BadRequest: Message is not modified: specified new message content and reply markup are exactly the same"
    )
    # Should not raise exception
    await safe_edit_or_reply(mock_menu_update, "Same text")
    mock_menu_update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_safe_edit_or_reply_handles_cant_parse_entities_fallback(mock_menu_update):
    """Verify that 'can't parse entities' errors immediately fall back to parse_mode=None."""
    mock_menu_update.callback_query.message.edit_text.side_effect = [
        Exception("Can't parse entities: can't find end of the entity starting at byte offset 37"),
        None,
    ]
    await safe_edit_or_reply(mock_menu_update, "Text with unmatched *bold")
    assert mock_menu_update.callback_query.message.edit_text.call_count == 2
    second_call_kwargs = mock_menu_update.callback_query.message.edit_text.call_args_list[1][1]
    assert second_call_kwargs["parse_mode"] is None


@pytest.mark.asyncio
async def test_start_command_renders_main_menu(mock_menu_update):
    """Verify /start displays the 12-section dashboard."""
    with patch.object(settings, "allowed_user_ids", [112233]):
        await start_command(mock_menu_update, MagicMock())

    mock_menu_update.effective_message.reply_text.assert_called_once()
    reply_call = mock_menu_update.effective_message.reply_text.call_args
    text = reply_call[0][0]
    markup = reply_call[1]["reply_markup"]

    assert "Welcome to STEM RADAR, Alan!" in text
    assert len(markup.inline_keyboard) == 8


@pytest.mark.asyncio
async def test_main_menu_callback_routes_home(mock_menu_update):
    """Verify clicking menu:home edits message to the main dashboard."""
    mock_menu_update.callback_query.data = "menu:home"
    _RECENT_CALLBACKS.clear()

    with patch.object(settings, "allowed_user_ids", [112233]):
        await main_menu_callback_router(mock_menu_update, MagicMock())

    mock_menu_update.callback_query.answer.assert_called_once()
    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    text = mock_menu_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "Welcome to STEM RADAR, Alan!" in text


@pytest.mark.asyncio
async def test_main_menu_callback_routes_ai_hub(mock_menu_update):
    """Verify clicking menu:ai opens the AI Intelligence Hub."""
    mock_menu_update.callback_query.data = "menu:ai"
    _RECENT_CALLBACKS.clear()

    with patch.object(settings, "allowed_user_ids", [112233]):
        await main_menu_callback_router(mock_menu_update, MagicMock())

    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    text = mock_menu_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "AI Intelligence Hub" in text


@pytest.mark.asyncio
async def test_main_menu_callback_routes_learn_hub(mock_menu_update):
    """Verify clicking menu:learn opens the STEM Learning Academy."""
    mock_menu_update.callback_query.data = "menu:learn"
    _RECENT_CALLBACKS.clear()

    with patch.object(settings, "allowed_user_ids", [112233]):
        await main_menu_callback_router(mock_menu_update, MagicMock())

    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    text = mock_menu_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "STEM Learning Academy" in text


@pytest.mark.asyncio
async def test_main_menu_callback_routes_radar(mock_menu_update):
    """Verify clicking menu:radar renders Technology Radar."""
    mock_menu_update.callback_query.data = "menu:radar"
    _RECENT_CALLBACKS.clear()

    with patch.object(settings, "allowed_user_ids", [112233]):
        await main_menu_callback_router(mock_menu_update, MagicMock())

    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    text = mock_menu_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "STEM Technology Radar" in text


@pytest.mark.asyncio
async def test_main_menu_callback_routes_search(mock_menu_update):
    """Verify clicking menu:search opens the search hub."""
    mock_menu_update.callback_query.data = "menu:search"
    _RECENT_CALLBACKS.clear()

    with patch.object(settings, "allowed_user_ids", [112233]):
        await main_menu_callback_router(mock_menu_update, MagicMock())

    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    text = mock_menu_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "/search <keyword>" in text


@pytest.mark.asyncio
async def test_main_menu_callback_routes_interests(mock_menu_update):
    """Verify clicking menu:interests displays domain subscriptions."""
    mock_menu_update.callback_query.data = "menu:interests"
    _RECENT_CALLBACKS.clear()

    with patch.object(settings, "allowed_user_ids", [112233]):
        await main_menu_callback_router(mock_menu_update, MagicMock())

    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    text = mock_menu_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "My STEM Domain Subscriptions" in text


@pytest.mark.asyncio
async def test_main_menu_callback_routes_ethiopia_and_politics(mock_menu_update):
    """Verify clicking menu:ethiopia and menu:politics calls send_article_view with correct category slugs."""
    from app.database.models import Article, Category, Source

    sample_art = Article(
        id=99,
        title="Telebirr and Safaricom Expand Interoperability",
        url="https://example.com/ethiopia-telebirr",
        url_hash="hash_et",
        description="Mobile money integration in Ethiopia.",
        source=Source(id=1, name="Shega", slug="shega", url="https://shega.co"),
        categories=[Category(id=1, name="Ethiopia Tech & Innovation", slug="ethiopia-tech")],
    )

    _RECENT_CALLBACKS.clear()
    mock_menu_update.callback_query.data = "menu:ethiopia"

    with patch("app.bot.handlers.news.news_service.get_recent_news", AsyncMock(return_value=[sample_art])):
        with patch.object(settings, "allowed_user_ids", [112233]):
            await main_menu_callback_router(mock_menu_update, MagicMock())

    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    call_args = mock_menu_update.callback_query.message.edit_text.call_args
    text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    assert "Telebirr and Safaricom" in text

    _RECENT_CALLBACKS.clear()
    mock_menu_update.callback_query.data = "menu:politics"
    mock_menu_update.callback_query.message.edit_text.reset_mock()

    sample_art.title = "Global Summit on AI Safety Treaties"
    sample_art.categories = [Category(id=2, name="Global Politics & Geopolitics", slug="global-politics")]

    with patch("app.bot.handlers.news.news_service.get_recent_news", AsyncMock(return_value=[sample_art])):
        with patch.object(settings, "allowed_user_ids", [112233]):
            await main_menu_callback_router(mock_menu_update, MagicMock())

    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    call_args2 = mock_menu_update.callback_query.message.edit_text.call_args
    text2 = call_args2[0][0] if call_args2[0] else call_args2[1].get("text", "")
    assert "Global Summit on AI Safety Treaties" in text2
