"""Tests for Telegram bot handlers and authorization security."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Chat, Message, Update, User

from app.bot.filters.auth import authorized_only
from app.bot.handlers.base import help_command, start_command
from app.bot.handlers.news import (
    callback_router,
    ethiopia_command,
    explain_command,
    github_command,
    impact_command,
    news_command,
    politics_command,
    research_command,
    sources_command,
)
from app.config import settings


@pytest.fixture
def mock_update():
    """Create a mock Telegram Update."""
    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = 112233
    user.first_name = "Alex"
    user.username = "alexperry"

    chat = MagicMock(spec=Chat)
    chat.id = 112233

    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()

    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = message
    update.callback_query = None
    return update


@pytest.mark.asyncio
async def test_auth_decorator_blocks_unauthorized_user(mock_update):
    mock_func = AsyncMock()
    decorated = authorized_only(mock_func)

    # Whitelist does NOT contain user 112233
    with patch.object(settings, "allowed_user_ids", [999999]):
        await decorated(mock_update, MagicMock())

    # Target function should NOT have been called
    mock_func.assert_not_called()
    # Bot should reply with access restricted warning showing user ID
    mock_update.effective_message.reply_text.assert_called_once()
    reply_text = mock_update.effective_message.reply_text.call_args[0][0]
    assert "Access Restricted" in reply_text
    assert "112233" in reply_text


@pytest.mark.asyncio
async def test_auth_decorator_allows_authorized_user(mock_update):
    mock_func = AsyncMock()
    decorated = authorized_only(mock_func)

    # Whitelist contains user 112233
    with patch.object(settings, "allowed_user_ids", [112233]):
        await decorated(mock_update, MagicMock())

    # Target function should have been executed
    mock_func.assert_called_once()


@pytest.mark.asyncio
async def test_start_command_renders_welcome(mock_update):
    with patch.object(settings, "allowed_user_ids", [112233]):
        await start_command(mock_update, MagicMock())

    mock_update.effective_message.reply_text.assert_called_once()
    reply_text = mock_update.effective_message.reply_text.call_args[0][0]
    assert "STEM RADAR" in reply_text


@pytest.mark.asyncio
async def test_help_command_renders_catalog(mock_update):
    with patch.object(settings, "allowed_user_ids", [112233]):
        await help_command(mock_update, MagicMock())

    mock_update.effective_message.reply_text.assert_called_once()
    reply_text = mock_update.effective_message.reply_text.call_args[0][0]
    assert "Command Reference" in reply_text


@pytest.mark.asyncio
async def test_sources_command_renders_health(mock_update):
    with patch.object(settings, "allowed_user_ids", [112233]):
        await sources_command(mock_update, MagicMock())

    mock_update.effective_message.reply_text.assert_called_once()
    reply_text = mock_update.effective_message.reply_text.call_args[0][0]
    assert "Configured Sources" in reply_text
    assert "Status:" in reply_text


@pytest.mark.asyncio
async def test_news_command_renders_view(mock_update):
    with patch.object(settings, "allowed_user_ids", [112233]):
        await news_command(mock_update, MagicMock())

    mock_update.effective_message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_research_command_renders_view(mock_update):
    with patch.object(settings, "allowed_user_ids", [112233]):
        await research_command(mock_update, MagicMock())

    mock_update.effective_message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_github_command_renders_view(mock_update):
    with patch.object(settings, "allowed_user_ids", [112233]):
        await github_command(mock_update, MagicMock())

    mock_update.effective_message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_callback_router_authorization(mock_update):
    mock_update.callback_query = MagicMock()
    mock_update.callback_query.data = "cat:ai"
    mock_update.callback_query.answer = AsyncMock()

    # Unauthorized user
    with patch.object(settings, "allowed_user_ids", [999999]):
        await callback_router(mock_update, MagicMock())

    # User message blocked
    mock_update.effective_message.reply_text.assert_called_once()
    reply_text = mock_update.effective_message.reply_text.call_args[0][0]
    assert "Access Restricted" in reply_text


@pytest.mark.asyncio
async def test_explain_command_usage_prompt(mock_update):
    context = MagicMock()
    context.args = []
    with patch.object(settings, "allowed_user_ids", [112233]):
        await explain_command(mock_update, context)

    mock_update.effective_message.reply_text.assert_called_once()
    reply_text = mock_update.effective_message.reply_text.call_args[0][0]
    assert "Usage:" in reply_text
    assert "/explain" in reply_text


@pytest.mark.asyncio
async def test_explain_command_with_concept(mock_update):
    context = MagicMock()
    context.args = ["beginner", "Direct", "Drive", "Actuators"]
    mock_update.effective_message.reply_text = AsyncMock()

    with patch.object(settings, "allowed_user_ids", [112233]):
        await explain_command(mock_update, context)

    assert mock_update.effective_message.reply_text.call_count >= 1


@pytest.mark.asyncio
async def test_impact_command_renders_assessment(mock_update):
    context = MagicMock()
    mock_update.effective_message.reply_text = AsyncMock()

    with patch.object(settings, "allowed_user_ids", [112233]):
        await impact_command(mock_update, context)

    assert mock_update.effective_message.reply_text.call_count >= 1


@pytest.mark.asyncio
async def test_ethiopia_and_politics_commands(mock_update):
    """Verify /ethiopia and /politics commands call send_article_view with correct category slugs."""
    from app.database.models import Article, Category, Source

    sample_art = Article(
        id=101,
        title="Ethiopia Launches National AI Initiative",
        url="https://example.com/eaii-initiative",
        url_hash="hash_et_ai",
        description="EAII announces research initiatives in Addis Ababa.",
        source=Source(id=1, name="Shega", slug="shega", url="https://shega.co"),
        categories=[Category(id=1, name="Ethiopia Tech & Innovation", slug="ethiopia-tech")],
    )

    with patch("app.bot.handlers.news.news_service.get_recent_news", AsyncMock(return_value=[sample_art])):
        with patch.object(settings, "allowed_user_ids", [112233]):
            await ethiopia_command(mock_update, MagicMock())

    mock_update.effective_message.reply_text.assert_called_once()
    reply_text = mock_update.effective_message.reply_text.call_args[0][0]
    assert "Ethiopia Launches National AI Initiative" in reply_text

    mock_update.effective_message.reply_text.reset_mock()
    sample_art.title = "Global Treaty on Autonomous Systems"
    sample_art.categories = [Category(id=2, name="Global Politics & Geopolitics", slug="global-politics")]

    with patch("app.bot.handlers.news.news_service.get_recent_news", AsyncMock(return_value=[sample_art])):
        with patch.object(settings, "allowed_user_ids", [112233]):
            await politics_command(mock_update, MagicMock())

    mock_update.effective_message.reply_text.assert_called_once()
    reply_text2 = mock_update.effective_message.reply_text.call_args[0][0]
    assert "Global Treaty on Autonomous Systems" in reply_text2
