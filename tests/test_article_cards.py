"""Tests for redesigned article cards, inline actions suite, and search pagination."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import CallbackQuery, Chat, Message, Update, User

from app.bot.handlers.news import callback_router, search_command
from app.bot.keyboards.inline import (
    get_article_keyboard,
    get_explanation_keyboard,
    get_search_pagination_keyboard,
)
from app.bot.ui.formatters import (
    estimate_reading_time,
    format_article_view,
    format_related_articles,
    format_search_results_page,
)
from app.config import settings
from app.database.models import Article, Category, Source


@pytest.fixture
def sample_article():
    """Create a sample Article mock model for card testing."""
    source = Source(id=1, name="MIT Technology Review", slug="mit-tech-review", url="https://technologyreview.com")
    cat1 = Category(id=1, name="Artificial Intelligence", slug="ai")
    cat2 = Category(id=2, name="Robotics", slug="robotics")

    article = Article(
        id=42,
        title="Sparse Neural Network Kernel for Low-Power Microcontrollers",
        url="https://technologyreview.com/sparse-kernel",
        url_hash="hash123",
        description="Researchers demonstrated a memory-efficient sparse kernel enabling real-time neural execution.",
        content="Extended content describing matrix multiplication optimizations on ARM Cortex-M silicon.",
        source_id=1,
    )
    article.source = source
    article.categories = [cat1, cat2]
    return article


@pytest.fixture
def mock_news_update():
    """Mock Telegram update for news callbacks."""
    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = 112233
    user.first_name = "Grace"
    user.username = "ghopper"

    chat = MagicMock(spec=Chat)
    chat.id = 112233

    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()
    message.edit_text = AsyncMock()
    message.edit_reply_markup = AsyncMock()

    query = MagicMock(spec=CallbackQuery)
    query.id = "query_news_1"
    query.data = "ai_exp:42"
    query.message = message
    query.answer = AsyncMock()

    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = message
    update.callback_query = query
    return update


def test_reading_time_estimator():
    """Verify reading time calculation based on word count."""
    assert estimate_reading_time("") == "~1 min read"
    short_text = "This is a brief text snippet."
    assert estimate_reading_time(short_text) == "~1 min read"

    long_text = "word " * 450
    assert estimate_reading_time(long_text) == "~2 min read"


def test_format_article_view_card_structure(sample_article):
    """Verify that format_article_view includes all required fields from Section 5."""
    card = format_article_view(sample_article, index=0, total=1)

    # 1. Category & Source header
    assert "Artificial Intelligence" in card
    assert "MIT Technology Review" in card

    # 2. Date & Reading time
    assert "⏱️" in card
    assert "min read" in card

    # 3. Title
    assert "Sparse Neural Network Kernel" in card

    # 4. Summary & Why it matters
    assert "📝 *Summary:*" in card
    assert "💡 *Why It Matters:*" in card

    # 5. Hashtags
    assert "#ArtificialIntelligence" in card

    # 6. Read original link
    assert "https://technologyreview.com/sparse-kernel" in card


def test_get_article_keyboard_action_suite(sample_article):
    """Verify that get_article_keyboard includes all 5 actions plus pagination and navigation."""
    keyboard = get_article_keyboard(
        article_id=sample_article.id,
        url=sample_article.url,
        offset=1,
        total=5,
        category_slug="ai",
        is_saved=False,
        title=sample_article.title,
    )

    # Row 1: Read Original + Explain with AI
    row1 = keyboard.inline_keyboard[0]
    assert len(row1) == 2
    assert row1[0].text == "Read Original 🔗"
    assert row1[0].url == sample_article.url
    assert row1[1].text == "Explain with AI 🧠"
    assert row1[1].callback_data == f"ai_exp:{sample_article.id}"

    # Row 2: Bookmark + Share + Related
    row2 = keyboard.inline_keyboard[1]
    assert len(row2) == 3
    assert row2[0].text == "Bookmark ⭐"
    assert row2[0].callback_data == f"save:{sample_article.id}"
    assert row2[1].text == "Share 📤"
    assert "https://t.me/share/url" in row2[1].url
    assert row2[2].text == "Related 🔍"
    assert row2[2].callback_data == f"rel:{sample_article.id}"

    # Row 3: Pagination
    row3 = keyboard.inline_keyboard[2]
    assert len(row3) == 3
    assert row3[0].callback_data == "nav:ai:0"  # Prev
    assert row3[1].text == "2/5"  # Counter
    assert row3[2].callback_data == "nav:ai:2"  # Next

    # Row 4: Navigation
    row4 = keyboard.inline_keyboard[3]
    assert len(row4) == 3
    assert row4[0].callback_data == "show_cats"
    assert row4[1].callback_data == "nav:ai:1"
    assert row4[2].callback_data == "menu:home"


def test_explanation_and_search_keyboards():
    """Verify AI explanation mode selector and search pagination keyboards."""
    exp_kb = get_explanation_keyboard(article_id=42, current_mode="beginner")
    assert len(exp_kb.inline_keyboard) == 2
    mode_btns = exp_kb.inline_keyboard[0]
    assert "Beginner" in mode_btns[0].text
    assert mode_btns[0].callback_data == "exp_mode:42:beginner"
    assert "Intermediate" in mode_btns[1].text
    assert "Advanced" in mode_btns[2].text

    search_kb = get_search_pagination_keyboard(query="robotics", page=0, total_pages=3)
    assert len(search_kb.inline_keyboard) == 2
    pag_row = search_kb.inline_keyboard[0]
    assert pag_row[0].text == "1/3"
    assert pag_row[1].callback_data == "s_nav:robotics:1"


def test_format_related_and_search_pages(sample_article):
    """Verify related articles formatter and search page formatters."""
    related_text = format_related_articles(sample_article, [sample_article])
    assert "Articles & Papers Related to:" in related_text
    assert sample_article.title in related_text

    search_text = format_search_results_page(
        query="sparse",
        articles=[sample_article],
        page=0,
        total_pages=2,
        total_count=10,
    )
    assert 'Search Results for "sparse"' in search_text
    assert "Page `1` of `2`" in search_text
    assert "`10` total matches" in search_text


@pytest.mark.asyncio
async def test_callback_router_handles_ai_explain(mock_news_update, sample_article):
    """Verify callback ai_exp:<id> generates and renders concept explanation."""
    mock_news_update.callback_query.data = f"ai_exp:{sample_article.id}"

    with patch("app.bot.handlers.news.news_service.get_article_by_id", AsyncMock(return_value=sample_article)):
        with patch.object(settings, "allowed_user_ids", [112233]):
            await callback_router(mock_news_update, MagicMock())

    mock_news_update.callback_query.answer.assert_called_once()
    mock_news_update.callback_query.message.edit_text.assert_called_once()
    edit_call = mock_news_update.callback_query.message.edit_text.call_args[1]
    assert "AI Concept Breakdown" in edit_call["text"]


@pytest.mark.asyncio
async def test_callback_router_handles_related_articles(mock_news_update, sample_article):
    """Verify callback rel:<id> fetches and displays related articles."""
    mock_news_update.callback_query.data = f"rel:{sample_article.id}"

    with patch("app.bot.handlers.news.news_service.get_article_by_id", AsyncMock(return_value=sample_article)):
        with patch(
            "app.bot.handlers.news.news_service.get_related_articles",
            AsyncMock(return_value=[sample_article]),
        ):
            with patch.object(settings, "allowed_user_ids", [112233]):
                await callback_router(mock_news_update, MagicMock())

    mock_news_update.callback_query.message.edit_text.assert_called_once()
    edit_call = mock_news_update.callback_query.message.edit_text.call_args[1]
    assert "Articles & Papers Related to:" in edit_call["text"]


@pytest.mark.asyncio
async def test_search_command_with_query_renders_paginated_results(mock_news_update, sample_article):
    """Verify /search <query> displays paginated results."""
    mock_news_update.callback_query = None
    context = MagicMock()
    context.args = ["kernel"]

    with patch("app.bot.handlers.news.news_service.count_news", AsyncMock(return_value=12)):
        with patch("app.bot.handlers.news.news_service.get_recent_news", AsyncMock(return_value=[sample_article])):
            with patch.object(settings, "allowed_user_ids", [112233]):
                await search_command(mock_news_update, context)

    mock_news_update.effective_message.reply_text.assert_called_once()
    reply_call = mock_news_update.effective_message.reply_text.call_args[1]
    assert 'Search Results for "kernel"' in reply_call["text"]
    assert "Page `1` of `3`" in reply_call["text"]
