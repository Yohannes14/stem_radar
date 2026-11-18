"""Tests for Telegram bot search handlers, category chips, sort switches, and callbacks."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import CallbackQuery, Chat, Message, Update, User

from app.bot.handlers.base import main_menu_callback_router
from app.bot.handlers.news import (
    callback_router,
    quick_ai_summary_command,
    search_ai_command,
    search_command,
    websearch_command,
)
from app.bot.ui.menu import _RECENT_CALLBACKS
from app.config import settings
from app.services.search.models import (
    SearchAISummary,
    SearchResultItem,
    SourceCitation,
    UnifiedSearchResponse,
)


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
    assert "*Search*" in text
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
    assert 'Search Results — "astronomy"' in reply_text
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


@pytest.mark.asyncio
async def test_websearch_command_without_args_shows_intro(mock_search_update):
    """Verify /websearch without arguments renders the live web discovery intro."""
    context = MagicMock()
    context.args = []

    with patch.object(settings, "allowed_user_ids", [887766]):
        await websearch_command(mock_search_update, context)

    mock_search_update.callback_query.message.edit_text.assert_called_once()
    call_kwargs = mock_search_update.callback_query.message.edit_text.call_args[1]
    text = call_kwargs["text"]
    assert "Live Web Search" in text
    assert "/websearch <query>" in text
    assert call_kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_websearch_command_with_query_triggers_external_search(mock_search_update):
    """Verify /websearch <query> invokes send_search_view with source='external'."""
    context = MagicMock()
    context.args = ["robotics", "breakthrough"]
    mock_search_update.callback_query = None

    with patch("app.bot.handlers.news.send_search_view", AsyncMock()) as mock_send_search:
        with patch.object(settings, "allowed_user_ids", [887766]):
            await websearch_command(mock_search_update, context)

    mock_send_search.assert_called_once()
    assert mock_send_search.call_args[1]["query"] == "robotics breakthrough"
    assert mock_send_search.call_args[1]["source"] == "external"


@pytest.mark.asyncio
async def test_search_source_switch_callback(mock_search_update):
    """Verify search:src:external:all:relevance:quantum callback switches scope and refreshes view."""
    _RECENT_CALLBACKS.clear()
    mock_search_update.callback_query.data = "search:src:external:all:relevance:quantum"
    mock_search_update.callback_query.message.edit_text.reset_mock()

    mock_response = UnifiedSearchResponse(
        items=[],
        total_items=0,
        page=1,
        page_size=4,
        total_pages=1,
        query="quantum",
        category="all",
        sort_by="relevance",
        source="external",
    )

    with patch("app.bot.handlers.news.search_service.search", AsyncMock(return_value=mock_response)):
        with patch.object(settings, "allowed_user_ids", [887766]):
            await callback_router(mock_search_update, MagicMock())

    mock_search_update.callback_query.message.edit_text.assert_called_once()
    args = mock_search_update.callback_query.message.edit_text.call_args[1]
    assert "SCOPE: EXTERNAL" in args["text"] or "Search Results" in args["text"]


@pytest.mark.asyncio
async def test_search_ai_command_without_args_shows_intro(mock_search_update):
    """Verify /search_ai without arguments renders the AI Search Assistant intro."""
    context = MagicMock()
    context.args = []

    with patch.object(settings, "allowed_user_ids", [887766]):
        await search_ai_command(mock_search_update, context)

    mock_search_update.callback_query.message.edit_text.assert_called_once()
    call_kwargs = mock_search_update.callback_query.message.edit_text.call_args[1]
    text = call_kwargs["text"]
    assert "Cited Search Summary" in text
    assert "/search_ai <topic>" in text
    assert call_kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_search_ai_command_with_query_renders_summary(mock_search_update):
    """Verify /search_ai <query> calls ai_summarize_query and displays structured synthesis."""
    context = MagicMock()
    context.args = ["metamaterials", "cloaking"]
    mock_search_update.callback_query = None

    mock_summary = SearchAISummary(
        query="metamaterials cloaking",
        executive_summary=(
            "Electromagnetic cloaking via coordinate transformations demonstrates broadband phase control."
        ),
        sourced_facts=["Negative refractive index achieved in microwave spectrum [1]."],
        analytical_implications=["Practical optical wavelengths require sub-nanometer nanofabrication."],
        source_citations=[
            SourceCitation(
                index=1,
                title="Transformation Optics Metamaterials",
                url="https://example.com/optics-paper",
                source_name="Optics Express",
                is_verified=True,
            )
        ],
        related_questions=["Can transformation optics work in acoustic regimes?"],
        research_recommendations=["Fabricate multi-layer dielectric stacks."],
        disclaimer="AI synthesis derived strictly from cited search results.",
    )

    with patch("app.bot.handlers.news.search_service.ai_summarize_query", AsyncMock(return_value=mock_summary)):
        with patch.object(settings, "allowed_user_ids", [887766]):
            await search_ai_command(mock_search_update, context)

    mock_search_update.effective_message.reply_text.assert_called_once()
    text = mock_search_update.effective_message.reply_text.call_args[1]["text"]
    assert 'Search Summary — "metamaterials cloaking"' in text
    assert "Negative refractive index achieved" in text
    assert "Optics Express" in text


@pytest.mark.asyncio
async def test_search_ai_sum_callback(mock_search_update):
    """Verify search:ai_sum callback invokes AI search synthesis and updates view."""
    _RECENT_CALLBACKS.clear()
    mock_search_update.callback_query.data = "search:ai_sum:all:all:superconductivity"
    mock_search_update.callback_query.message.edit_text.reset_mock()

    mock_summary = SearchAISummary(
        query="superconductivity",
        executive_summary="High-Tc cuprate phase diagrams show persistent pseudogap behavior.",
        sourced_facts=["Cuprate crystals exhibit non-Fermi liquid transport [1]."],
        analytical_implications=["Unconventional pairing mechanisms demand non-BCS models."],
        source_citations=[
            SourceCitation(
                index=1,
                title="Cuprate Superconductors",
                url="https://example.com/cuprates",
                source_name="Physical Review B",
                is_verified=True,
            )
        ],
        related_questions=["What is the mechanism of the pseudogap?"],
        research_recommendations=["Measure angle-resolved photoemission spectroscopy."],
        disclaimer="AI synthesis derived strictly from cited search results.",
    )

    with patch("app.bot.handlers.news.search_service.ai_summarize_query", AsyncMock(return_value=mock_summary)):
        with patch.object(settings, "allowed_user_ids", [887766]):
            await callback_router(mock_search_update, MagicMock())

    mock_search_update.callback_query.message.edit_text.assert_called_once()
    text = mock_search_update.callback_query.message.edit_text.call_args[1]["text"]
    assert 'Search Summary — "superconductivity"' in text
    assert "Cuprate Superconductors" in text


@pytest.mark.asyncio
async def test_search_rel_q_and_back_callbacks(mock_search_update):
    """Verify search:rel_q and search:back callbacks trigger send_search_view."""
    # 1. search:rel_q:quantum algorithms
    _RECENT_CALLBACKS.clear()
    mock_search_update.callback_query.data = "search:rel_q:quantum algorithms"
    with patch("app.bot.handlers.news.send_search_view", AsyncMock()) as mock_send_search:
        with patch.object(settings, "allowed_user_ids", [887766]):
            await callback_router(mock_search_update, MagicMock())

    mock_send_search.assert_called_once()
    assert mock_send_search.call_args[1]["query"] == "quantum algorithms"

    # 2. search:back:all:all:quantum
    _RECENT_CALLBACKS.clear()
    mock_search_update.callback_query.data = "search:back:all:all:quantum"
    with patch("app.bot.handlers.news.send_search_view", AsyncMock()) as mock_send_search:
        with patch.object(settings, "allowed_user_ids", [887766]):
            await callback_router(mock_search_update, MagicMock())

    mock_send_search.assert_called_once()
    assert mock_send_search.call_args[1]["query"] == "quantum"


@pytest.mark.asyncio
async def test_quick_ai_summary_command(mock_search_update):
    """Verify /ai_sum_<id> generates an executive AI summary for an indexed article."""
    from app.database.models import Article, Category, Source

    sample_article = Article(
        id=42,
        title="Sparse Neural Network Kernel for Low-Power Microcontrollers",
        url="https://technologyreview.com/sparse-kernel",
        url_hash="hash_sparse_123",
        description="Researchers demonstrated a memory-efficient sparse kernel enabling real-time neural execution.",
        content="Extended content describing matrix multiplication optimizations on ARM Cortex-M silicon.",
        source_id=1,
    )
    sample_article.source = Source(
        id=1, name="MIT Technology Review", slug="mit-tech-review", url="https://technologyreview.com"
    )
    sample_article.categories = [Category(id=1, name="Artificial Intelligence", slug="ai")]

    mock_search_update.effective_message.text = "/ai_sum_42"
    mock_search_update.effective_message.reply_text.reset_mock()

    with patch("app.bot.handlers.news.news_service.get_article_by_id", AsyncMock(return_value=sample_article)):
        with patch.object(settings, "allowed_user_ids", [887766]):
            await quick_ai_summary_command(mock_search_update, MagicMock())

    mock_search_update.effective_message.reply_text.assert_called_once()
    text = mock_search_update.effective_message.reply_text.call_args[0][0]
    assert "AI Technical Summary" in text or "Sparse Neural Network" in text
