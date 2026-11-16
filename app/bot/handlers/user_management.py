"""User management, privacy compliance, data export/deletion, feedback, and admin moderation."""

import json
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.filters.auth import admin_only, authorized_only
from app.bot.keyboards.navigation import get_back_home_keyboard
from app.database.database import get_session_factory
from app.database.repository import Repository

logger = logging.getLogger(__name__)


# ------------------ 1. Feedback Command (/feedback) ------------------


@authorized_only
async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Submit user feedback, feature suggestions, or issue reports."""
    user = update.effective_user
    if not user:
        return

    args = context.args or []
    if not args:
        msg = (
            "💬 *STEM RADAR Feedback & Issue Reporting*\n\n"
            "We value your suggestions and bug reports!\n\n"
            "*Usage:* `/feedback <your message>`\n\n"
            "*Examples:*\n"
            "• `/feedback Please add more quantum computing feeds`\n"
            "• `/feedback The quiz question on robotics had a typo`\n"
            "• `/feedback Love the daily briefing feature!`"
        )
        if update.effective_message:
            await update.effective_message.reply_text(
                msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_back_home_keyboard(),
            )
        return

    feedback_text = " ".join(args).strip()
    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = Repository(session)
        await repo.save_user_feedback(telegram_id=user.id, message=feedback_text)

    reply = (
        "✅ *Thank You for Your Feedback!*\n\n"
        "Your message has been securely submitted to the engineering team. "
        "We continuously review feedback to improve platform intelligence."
    )
    if update.effective_message:
        await update.effective_message.reply_text(
            reply,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_home_keyboard(),
        )


# ------------------ 2. Privacy Policy Command (/privacy) ------------------


@authorized_only
async def privacy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display platform privacy policy, data collection scope, and user rights."""
    privacy_policy = (
        "🛡️ *STEM RADAR Privacy Policy & Data Protection*\n\n"
        "*1. Data Collection Scope:*\n"
        "• Telegram User ID, Username, and First Name (used solely for message delivery & personalization).\n"
        "• Selected STEM domain preferences and notification quiet hours.\n"
        "• Bookmarked articles and watchlist keywords you explicitly save.\n"
        "• Interactive quiz progress and completed lesson records.\n\n"
        "*2. What We Never Do:*\n"
        "• We *never* sell, share, or monetize your personal data.\n"
        "• We *never* track your activity outside this bot interaction.\n"
        "• We *never* expose your saved items or preferences to other users.\n\n"
        "*3. Your Rights & Controls:*\n"
        "• `/export` — Export a complete machine-readable copy of your stored data.\n"
        "• `/delete_account` — Permanently purge your stored preferences, bookmarks, and learning history.\n"
        "• `/settings` — Toggle or update notifications and subscriptions at any time.\n\n"
        "_STEM RADAR adheres to standard privacy-by-design and GDPR transparency principles._"
    )
    if update.effective_message:
        await update.effective_message.reply_text(
            privacy_policy,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_home_keyboard(),
        )


# ------------------ 3. Data Export Command (/export) ------------------


@authorized_only
async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Export all stored user data in structured JSON format for transparency."""
    user = update.effective_user
    if not user:
        return

    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = Repository(session)
        data = await repo.export_user_data(user.id)

    formatted_json = json.dumps(data, indent=2)
    response_text = (
        f"📦 *Your Exported Personal Data Profile*\n\n"
        f"```json\n{formatted_json}\n```\n\n"
        "To permanently delete this data, use `/delete_account`."
    )
    if update.effective_message:
        await update.effective_message.reply_text(
            response_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_home_keyboard(),
        )


# ------------------ 4. Delete Account Command (/delete_account) ------------------


@authorized_only
async def delete_account_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Permanently delete all user-stored preferences, bookmarks, and learning records."""
    user = update.effective_user
    if not user:
        return

    args = context.args or []
    if not args or args[0].lower() != "confirm":
        msg = (
            "⚠️ *Confirm Permanent Data Deletion*\n\n"
            "This action will permanently delete:\n"
            "• All your bookmarked and saved articles\n"
            "• All your keyword alerts and watchlists\n"
            "• All your domain subscriptions and quiet hour settings\n"
            "• All your educational quiz history and progress\n\n"
            "To confirm deletion, type:\n"
            "`/delete_account confirm`"
        )
        if update.effective_message:
            await update.effective_message.reply_text(
                msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_back_home_keyboard(),
            )
        return

    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = Repository(session)
        await repo.delete_user_data(user.id)

    confirm_msg = (
        "🗑️ *All User Data Successfully Deleted*\n\n"
        "Your preferences, saved articles, watchlists, and learning progress have been completely wiped.\n\n"
        "You can restart fresh at any time with `/start`."
    )
    if update.effective_message:
        await update.effective_message.reply_text(
            confirm_msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_home_keyboard(),
        )


# ------------------ 5. Admin Moderation Commands (/ban, /unban) ------------------


@admin_only
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command: block/ban a user from using the platform."""
    args = context.args or []
    if not args or not args[0].isdigit():
        if update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ *Usage:* `/ban <telegram_user_id>`\nExample: `/ban 123456789`",
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    target_id = int(args[0])
    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = Repository(session)
        await repo.get_or_create_user(target_id)
        await repo.set_user_ban_status(target_id, is_banned=True)

    msg = f"⛔ *User {target_id} has been banned.* Their requests will be rejected."
    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


@admin_only
async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command: restore access for a previously banned user."""
    args = context.args or []
    if not args or not args[0].isdigit():
        if update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ *Usage:* `/unban <telegram_user_id>`\nExample: `/unban 123456789`",
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    target_id = int(args[0])
    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = Repository(session)
        success = await repo.set_user_ban_status(target_id, is_banned=False)

    if success:
        msg = f"✅ *User {target_id} has been unbanned.* Access restored."
    else:
        msg = f"⚠️ *User {target_id} was not found.*"

    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
