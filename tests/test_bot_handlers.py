"""Tests for Telegram bot handlers and authorization security."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Chat, Message, Update, User

from app.bot.filters.auth import authorized_only
from app.bot.handlers.base import help_command, start_command
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
    assert "Welcome to STEM RADAR" in reply_text


@pytest.mark.asyncio
async def test_help_command_renders_catalog(mock_update):
    with patch.object(settings, "allowed_user_ids", [112233]):
        await help_command(mock_update, MagicMock())

    mock_update.effective_message.reply_text.assert_called_once()
    reply_text = mock_update.effective_message.reply_text.call_args[0][0]
    assert "Command Catalog" in reply_text
