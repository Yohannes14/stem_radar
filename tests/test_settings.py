"""Tests for the user settings command and preferences toggling."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat, Message, Update, User

from app.bot.handlers.settings import settings_command


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
