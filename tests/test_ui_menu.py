"""Comprehensive tests for the unified 8-Hub Main Menu, navigation controls, and onboarding."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import CallbackQuery, Chat, Message, Update, User

from app.bot.filters.auth import _USER_REQUEST_TIMESTAMPS
from app.bot.handlers.base import (
    discover_command,
    main_menu_callback_router,
    menu_command,
    myspace_command,
    start_command,
    stem_command,
)
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
    get_discover_hub_keyboard,
    get_legacy_main_menu_keyboard,
    get_main_menu_keyboard,
    get_myspace_keyboard,
    get_onboarding_goals_keyboard,
    get_onboarding_interests_keyboard,
    get_onboarding_welcome_keyboard,
    get_research_hub_keyboard,
    get_stem_tech_hub_keyboard,
    is_duplicate_callback,
    safe_edit_or_reply,
)
from app.config import settings


@pytest.fixture(autouse=True)
def reset_rate_limits_and_callbacks():
    """Clear debounce and rate limit caches before and after each test."""
    _RECENT_CALLBACKS.clear()
    _USER_REQUEST_TIMESTAMPS.clear()
    yield
    _RECENT_CALLBACKS.clear()
    _USER_REQUEST_TIMESTAMPS.clear()


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


def test_main_menu_keyboard_has_8_hubs():
    """Verify that get_main_menu_keyboard contains the flagship 8-Hub interactive sections."""
    keyboard = get_main_menu_keyboard()
    assert len(keyboard.inline_keyboard) == 4  # 4 rows of 2 buttons each = 8 buttons

    all_callbacks = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    expected_callbacks = [
        "menu:discover",
        "menu:stem_tech",
        "menu:research",
        "menu:student_hub",
        "menu:learn",
        "menu:projects",
        "menu:search",
        "menu:myspace",
    ]
    assert all_callbacks == expected_callbacks


def test_legacy_main_menu_keyboard_has_16_callbacks():
    """Verify that get_legacy_main_menu_keyboard maintains 100% backward compatibility."""
    keyboard = get_legacy_main_menu_keyboard()
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


def test_hub_keyboards_structure():
    """Verify keyboard structures for Discover, STEM Tech, Research, and My Space."""
    disc_kb = get_discover_hub_keyboard()
    disc_callbacks = [btn.callback_data for row in disc_kb.inline_keyboard for btn in row]
    assert "menu:briefing" in disc_callbacks
    assert "menu:trending" in disc_callbacks
    assert "menu:radar" in disc_callbacks
    assert "menu:velocity" in disc_callbacks
    assert "menu:home" in disc_callbacks

    stem_kb = get_stem_tech_hub_keyboard()
    stem_callbacks = [btn.callback_data for row in stem_kb.inline_keyboard for btn in row]
    assert "cat:ai" in stem_callbacks
    assert "cat:computer-science" in stem_callbacks
    assert "cat:cybersecurity" in stem_callbacks
    assert "cat:robotics" in stem_callbacks
    assert "cat:all" in stem_callbacks

    res_kb = get_research_hub_keyboard()
    res_callbacks = [btn.callback_data for row in res_kb.inline_keyboard for btn in row]
    assert "menu:arxiv_papers" in res_callbacks
    assert "menu:radar" in res_callbacks
    assert "menu:ai_explain" in res_callbacks

    space_kb = get_myspace_keyboard()
    space_callbacks = [btn.callback_data for row in space_kb.inline_keyboard for btn in row]
    assert "menu:saved" in space_callbacks
    assert "menu:interests" in space_callbacks
    assert "menu:watchlist" in space_callbacks
    assert "menu:progress" in space_callbacks
    assert "menu:privacy" in space_callbacks


def test_onboarding_keyboards():
    """Verify onboarding welcome, interests, and goals keyboards."""
    wel_kb = get_onboarding_welcome_keyboard()
    wel_callbacks = [btn.callback_data for row in wel_kb.inline_keyboard for btn in row]
    assert "onboard:interests" in wel_callbacks
    assert "onboard:skip" in wel_callbacks

    int_kb = get_onboarding_interests_keyboard(selected_slugs=["ai"])
    int_callbacks = [btn.callback_data for row in int_kb.inline_keyboard for btn in row]
    assert "onboard:toggle:ai" in int_callbacks
    assert "onboard:goals" in int_callbacks
    assert "onboard:skip" in int_callbacks

    # Verify active selection marker is added on selected slug
    ai_btn = next(btn for row in int_kb.inline_keyboard for btn in row if btn.callback_data == "onboard:toggle:ai")
    assert "• " in ai_btn.text

    goals_kb = get_onboarding_goals_keyboard()
    goals_callbacks = [btn.callback_data for row in goals_kb.inline_keyboard for btn in row]
    assert "onboard:track:student" in goals_callbacks
    assert "onboard:track:researcher" in goals_callbacks
    assert "onboard:track:engineer" in goals_callbacks
    assert "onboard:track:learner" in goals_callbacks


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
    assert len(p_start) == 2
    assert p_start[0].text == "1 / 5"
    assert p_start[1].callback_data == "nav:all:1"

    # 3. Pagination row in middle
    p_mid = nav_pagination_row(offset=2, total=5, prefix="nav:all")
    assert len(p_mid) == 3
    assert p_mid[0].callback_data == "nav:all:1"
    assert p_mid[1].text == "3 / 5"
    assert p_mid[2].callback_data == "nav:all:3"

    # 4. Standalone and compound nav keyboards
    back_home_kb = get_back_home_keyboard(back_target="menu:home")
    assert len(back_home_kb.inline_keyboard) == 1

    compound_kb = build_nav_keyboard([], back_target="menu:home", home_target="menu:home")
    assert len(compound_kb.inline_keyboard) == 1


def test_menu_formatters():
    """Verify text presentation formatters."""
    main_text = format_main_menu("Ada", {"total_articles": 42, "active_sources": 8, "user_saved_articles": 3})
    assert "STEM RADAR" in main_text
    assert "Ada" in main_text
    assert "Indexed records: 42" in main_text
    assert "Active sources: 8" in main_text
    assert "Saved items: 3" in main_text

    ai_text = format_ai_hub_intro()
    assert "AI Analysis Tools" in ai_text

    learn_text = format_learn_hub_intro()
    assert "Learn STEM" in learn_text

    search_text = format_search_intro()
    assert "/search <query>" in search_text

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
    """Verify /start displays the 8-hub dashboard."""
    with patch.object(settings, "allowed_user_ids", [112233]):
        await start_command(mock_menu_update, MagicMock())

    mock_menu_update.effective_message.reply_text.assert_called_once()
    reply_call = mock_menu_update.effective_message.reply_text.call_args
    text = reply_call[0][0]
    markup = reply_call[1]["reply_markup"]

    assert "STEM RADAR" in text
    assert "Alan" in text
    assert len(markup.inline_keyboard) == 4


@pytest.mark.asyncio
async def test_start_command_with_onboarding(mock_menu_update):
    """Verify /start onboard triggers the personalized onboarding card."""
    mock_context = MagicMock()
    mock_context.args = ["onboard"]

    with patch.object(settings, "allowed_user_ids", [112233]):
        await start_command(mock_menu_update, mock_context)

    mock_menu_update.effective_message.reply_text.assert_called_once()
    reply_call = mock_menu_update.effective_message.reply_text.call_args
    text = reply_call[0][0]
    markup = reply_call[1]["reply_markup"]

    assert "30 seconds" in text
    callbacks = [btn.callback_data for row in markup.inline_keyboard for btn in row]
    assert "onboard:interests" in callbacks
    assert "onboard:skip" in callbacks


@pytest.mark.asyncio
async def test_menu_command_renders_dashboard(mock_menu_update):
    """Verify /menu explicitly renders the 8-hub main menu dashboard."""
    mock_menu_update.callback_query = None
    with patch.object(settings, "allowed_user_ids", [112233]):
        await menu_command(mock_menu_update, MagicMock())

    mock_menu_update.effective_message.reply_text.assert_called_once()
    call_args = mock_menu_update.effective_message.reply_text.call_args
    text = call_args[0][0]
    markup = call_args[1]["reply_markup"]

    assert "STEM RADAR" in text
    assert "Alan" in text
    assert len(markup.inline_keyboard) == 4


@pytest.mark.asyncio
async def test_discover_command(mock_menu_update):
    """Verify /discover renders the Discover Hub intro and keyboard."""
    mock_menu_update.callback_query = None
    with patch.object(settings, "allowed_user_ids", [112233]):
        await discover_command(mock_menu_update, MagicMock())

    mock_menu_update.effective_message.reply_text.assert_called_once()
    call_args = mock_menu_update.effective_message.reply_text.call_args
    text = call_args[0][0]
    assert "*Discover*" in text


@pytest.mark.asyncio
async def test_stem_command(mock_menu_update):
    """Verify /stem renders the STEM & Technology Hub."""
    mock_menu_update.callback_query = None
    with patch.object(settings, "allowed_user_ids", [112233]):
        await stem_command(mock_menu_update, MagicMock())

    mock_menu_update.effective_message.reply_text.assert_called_once()
    call_args = mock_menu_update.effective_message.reply_text.call_args
    text = call_args[0][0]
    assert "*STEM & Technology*" in text


@pytest.mark.asyncio
async def test_myspace_command(mock_menu_update):
    """Verify /myspace renders the personal control center."""
    mock_menu_update.callback_query = None
    with patch.object(settings, "allowed_user_ids", [112233]):
        await myspace_command(mock_menu_update, MagicMock())

    mock_menu_update.effective_message.reply_text.assert_called_once()
    call_args = mock_menu_update.effective_message.reply_text.call_args
    text = call_args[0][0]
    assert "*My Space*" in text
    assert "Alan" in text


@pytest.mark.asyncio
async def test_main_menu_callback_routes_discover_and_research_and_myspace(mock_menu_update):
    """Verify menu:discover, menu:research, and menu:myspace route to their respective hub views."""
    # Discover Hub
    _RECENT_CALLBACKS.clear()
    mock_menu_update.callback_query.data = "menu:discover"
    with patch.object(settings, "allowed_user_ids", [112233]):
        await main_menu_callback_router(mock_menu_update, MagicMock())
    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    text = mock_menu_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "*Discover*" in text

    # STEM Tech Hub
    _RECENT_CALLBACKS.clear()
    mock_menu_update.callback_query.data = "menu:stem_tech"
    mock_menu_update.callback_query.message.edit_text.reset_mock()
    with patch.object(settings, "allowed_user_ids", [112233]):
        await main_menu_callback_router(mock_menu_update, MagicMock())
    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    text = mock_menu_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "*STEM & Technology*" in text

    # Research Hub
    _RECENT_CALLBACKS.clear()
    mock_menu_update.callback_query.data = "menu:research"
    mock_menu_update.callback_query.message.edit_text.reset_mock()
    with patch.object(settings, "allowed_user_ids", [112233]):
        await main_menu_callback_router(mock_menu_update, MagicMock())
    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    text = mock_menu_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "*Research & Innovation*" in text

    # My Space Hub
    _RECENT_CALLBACKS.clear()
    mock_menu_update.callback_query.data = "menu:myspace"
    mock_menu_update.callback_query.message.edit_text.reset_mock()
    with patch.object(settings, "allowed_user_ids", [112233]):
        await main_menu_callback_router(mock_menu_update, MagicMock())
    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    text = mock_menu_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "My Space" in text


@pytest.mark.asyncio
async def test_onboarding_callbacks_routing(mock_menu_update):
    """Verify onboarding interactive callbacks."""
    # 1. onboard:interests
    _RECENT_CALLBACKS.clear()
    mock_menu_update.callback_query.data = "onboard:interests"
    with patch.object(settings, "allowed_user_ids", [112233]):
        await main_menu_callback_router(mock_menu_update, MagicMock())
    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    text = mock_menu_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "Step 1 of 2" in text

    # 2. onboard:goals
    _RECENT_CALLBACKS.clear()
    mock_menu_update.callback_query.data = "onboard:goals"
    mock_menu_update.callback_query.message.edit_text.reset_mock()
    with patch.object(settings, "allowed_user_ids", [112233]):
        await main_menu_callback_router(mock_menu_update, MagicMock())
    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    text = mock_menu_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "Step 2 of 2" in text

    # 3. onboard:skip
    _RECENT_CALLBACKS.clear()
    mock_menu_update.callback_query.data = "onboard:skip"
    mock_menu_update.callback_query.message.edit_text.reset_mock()
    mock_context = MagicMock()
    mock_context.user_data = {}
    with patch.object(settings, "allowed_user_ids", [112233]):
        await main_menu_callback_router(mock_menu_update, mock_context)
    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    text = mock_menu_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "STEM RADAR" in text
    assert "Alan" in text
    assert mock_context.user_data.get("onboarded") is True


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
    assert "STEM RADAR" in text
    assert "Alan" in text


@pytest.mark.asyncio
async def test_main_menu_callback_routes_ai_hub(mock_menu_update):
    """Verify clicking menu:ai opens the AI Analysis Tools view."""
    mock_menu_update.callback_query.data = "menu:ai"
    _RECENT_CALLBACKS.clear()

    with patch.object(settings, "allowed_user_ids", [112233]):
        await main_menu_callback_router(mock_menu_update, MagicMock())

    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    text = mock_menu_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "AI Analysis Tools" in text


@pytest.mark.asyncio
async def test_main_menu_callback_routes_learn_hub(mock_menu_update):
    """Verify clicking menu:learn opens Learn STEM."""
    mock_menu_update.callback_query.data = "menu:learn"
    _RECENT_CALLBACKS.clear()

    with patch.object(settings, "allowed_user_ids", [112233]):
        await main_menu_callback_router(mock_menu_update, MagicMock())

    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    text = mock_menu_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "Learn STEM" in text


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
    assert "/search <query>" in text


@pytest.mark.asyncio
async def test_main_menu_callback_routes_interests(mock_menu_update):
    """Verify clicking menu:interests displays domain subscriptions."""
    mock_menu_update.callback_query.data = "menu:interests"
    _RECENT_CALLBACKS.clear()

    with patch.object(settings, "allowed_user_ids", [112233]):
        await main_menu_callback_router(mock_menu_update, MagicMock())

    mock_menu_update.callback_query.message.edit_text.assert_called_once()
    text = mock_menu_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "Domain Subscriptions" in text


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


@pytest.mark.asyncio
async def test_main_menu_callback_routes_universities_and_courses(mock_menu_update):
    """Verify menu:universities and menu:courses route to their respective handlers."""
    _RECENT_CALLBACKS.clear()
    mock_menu_update.callback_query.data = "menu:universities"

    with patch("app.bot.handlers.base.universities_command", AsyncMock()) as mock_uni_cmd:
        with patch.object(settings, "allowed_user_ids", [112233]):
            await main_menu_callback_router(mock_menu_update, MagicMock())
        mock_uni_cmd.assert_called_once()

    _RECENT_CALLBACKS.clear()
    mock_menu_update.callback_query.data = "menu:courses"

    with patch("app.bot.handlers.base.courses_command", AsyncMock()) as mock_crs_cmd:
        with patch.object(settings, "allowed_user_ids", [112233]):
            await main_menu_callback_router(mock_menu_update, MagicMock())
        mock_crs_cmd.assert_called_once()


@pytest.mark.asyncio
async def test_main_menu_callback_routes_deadlines_and_submit_opportunity(mock_menu_update):
    """Verify menu:deadlines and menu:submit_opportunity route to their handlers."""
    _RECENT_CALLBACKS.clear()
    mock_menu_update.callback_query.data = "menu:deadlines"

    with patch("app.bot.handlers.base.deadlines_command", AsyncMock()) as mock_deadlines_cmd:
        with patch.object(settings, "allowed_user_ids", [112233]):
            await main_menu_callback_router(mock_menu_update, MagicMock())
        mock_deadlines_cmd.assert_called_once()

    _RECENT_CALLBACKS.clear()
    mock_menu_update.callback_query.data = "menu:submit_opportunity"

    with patch("app.bot.handlers.base.submit_opportunity_command", AsyncMock()) as mock_submit_cmd:
        with patch.object(settings, "allowed_user_ids", [112233]):
            await main_menu_callback_router(mock_menu_update, MagicMock())
        mock_submit_cmd.assert_called_once()


def test_all_flagship_hub_keyboards_guarantee_home_navigation():
    """Verify that every major sub-menu keyboard has zero dead-ends and includes home navigation."""
    from app.bot.ui.menu import (
        get_discover_hub_keyboard,
        get_learn_hub_keyboard,
        get_myspace_keyboard,
        get_projects_hub_keyboard,
        get_research_hub_keyboard,
        get_stem_tech_hub_keyboard,
    )

    keyboards = [
        ("Discover", get_discover_hub_keyboard()),
        ("STEM Tech", get_stem_tech_hub_keyboard()),
        ("Research", get_research_hub_keyboard()),
        ("Learn", get_learn_hub_keyboard()),
        ("Projects", get_projects_hub_keyboard()),
        ("My Space", get_myspace_keyboard()),
    ]

    for name, kb in keyboards:
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "menu:home" in callbacks, f"Keyboard '{name}' lacks menu:home navigation!"


def test_empty_state_formatter_accessibility():
    """Verify empty states produce readable, accessible messages with clear next steps."""
    card = format_empty_state(
        title="No Results Found",
        message="No research papers matched your search filter.",
        action_hint="Try broader keywords or browse /research.",
    )
    assert "No Results Found" in card
    assert "No research papers matched your search filter." in card
    assert "Next step:" in card
    assert "Try broader keywords or browse /research." in card
