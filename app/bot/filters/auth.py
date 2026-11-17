"""Telegram user authorization, rate limiting, and role-based access control filters."""

import logging
import time
from functools import wraps
from typing import Callable, Dict, List, Tuple

from telegram import Update
from telegram.ext import ContextTypes

from app.config import settings
from app.database.database import get_session_factory
from app.database.repository import Repository

logger = logging.getLogger(__name__)

# Sliding-window rate limiter cache: {user_id: [timestamp, ...]}
_USER_REQUEST_TIMESTAMPS: Dict[int, List[float]] = {}


def check_rate_limit(user_id: int, max_requests: int = 30, window_seconds: int = 60) -> Tuple[bool, int]:
    """Sliding-window per-user rate limiter. Returns (is_allowed, retry_after_seconds)."""
    now = time.time()
    timestamps = _USER_REQUEST_TIMESTAMPS.setdefault(user_id, [])

    # Evict timestamps older than window
    cutoff = now - window_seconds
    valid_timestamps = [t for t in timestamps if t > cutoff]
    _USER_REQUEST_TIMESTAMPS[user_id] = valid_timestamps

    if len(valid_timestamps) >= max_requests:
        oldest_in_window = valid_timestamps[0]
        retry_after = max(1, int(oldest_in_window + window_seconds - now))
        return False, retry_after

    valid_timestamps.append(now)
    return True, 0


def authorized_only(func: Callable):
    """Decorator ensuring user is registered, active, rate-bounded, and authorized."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        user_id = user.id

        # 1. Check strict whitelist if configured
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

        # 2. Rate limit check (30 requests / 60 seconds)
        is_allowed, retry_after = check_rate_limit(user_id, max_requests=30, window_seconds=60)
        if not is_allowed:
            msg = (
                "⏳ *Rate Limit Exceeded*\n\n"
                f"You are sending requests too quickly. Please wait `{retry_after}` seconds before trying again."
            )
            if update.effective_message:
                await update.effective_message.reply_text(msg, parse_mode="Markdown")
            return

        # 3. Auto-registration and Ban Check in Database
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                repo = Repository(session)
                db_user, created = await repo.get_or_create_user(
                    telegram_id=user_id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                )
                if created and hasattr(context, "user_data") and isinstance(context.user_data, dict):
                    context.user_data["is_new_registration"] = True

                if db_user and db_user.is_banned:
                    logger.warning("Banned user %d attempted access", user_id)
                    banned_msg = (
                        "⛔ *Account Suspended*\n\n"
                        "Your access to STEM RADAR has been disabled for violating platform usage policies."
                    )
                    if update.effective_message:
                        await update.effective_message.reply_text(banned_msg, parse_mode="Markdown")
                    return
        except Exception as exc:
            logger.debug("User registration tracking fallback: %s", exc)

        return await func(update, context, *args, **kwargs)

    return wrapper


def admin_only(func: Callable):
    """Decorator restricting command execution strictly to platform administrators."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        user_id = user.id
        is_admin = False

        if settings.allowed_user_ids and user_id in settings.allowed_user_ids:
            is_admin = True
        else:
            try:
                session_factory = get_session_factory()
                async with session_factory() as session:
                    repo = Repository(session)
                    is_admin = await repo.is_user_admin(user_id)
            except Exception as exc:
                logger.error("Admin check failed: %s", exc)

        if not is_admin:
            logger.warning(
                "Unauthorized admin command attempt by user %d (%s)",
                user_id,
                user.username or user.first_name,
            )
            msg = (
                "⛔ *Admin Access Required*\n\n"
                "This command is restricted to platform administrators.\n"
                "Contact the platform administrator if you require elevated access."
            )
            if update.effective_message:
                await update.effective_message.reply_text(msg, parse_mode="Markdown")
            return

        return await func(update, context, *args, **kwargs)

    return wrapper
