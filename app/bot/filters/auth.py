"""Telegram user authorization filter and decorator."""

import logging
from functools import wraps
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from app.config import settings

logger = logging.getLogger(__name__)


def authorized_only(func: Callable):
    """Decorator restricting command execution to authorized Telegram users."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        user_id = user.id
        if not settings.is_user_allowed(user_id):
            logger.warning(
                "Unauthorized access attempt by user: %s (ID: %d)",
                user.username or user.first_name,
                user_id,
            )
            msg = (
                "⛔ *Access Restricted*\n\n"
                "This STEM RADAR instance is private.\n\n"
                f"Your Telegram User ID: `{user_id}`\n\n"
                "To authorize your account, add this ID to your `.env` file:\n"
                f"`ALLOWED_TELEGRAM_USER_IDS={user_id}`\n"
                "and restart the bot."
            )
            if update.effective_message:
                await update.effective_message.reply_text(msg, parse_mode="Markdown")
            return

        return await func(update, context, *args, **kwargs)

    return wrapper
