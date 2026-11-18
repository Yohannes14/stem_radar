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
            "*Feedback & Issue Reporting*\n\n"
            "Send suggestions or report issues directly using:\n"
            "`/feedback <your message>`\n\n"
            "Examples:\n"
            "- `/feedback Add more quantum computing feeds`\n"
            "- `/feedback Typo in the robotics quiz question`"
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

    reply = "*Feedback Received*\n\nYour message has been recorded for review."
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
        "*Privacy Policy & Data Protection*\n\n"
        "*Data we store*\n"
        "- Telegram User ID, username, and first name for message delivery and personalization.\n"
        "- Selected STEM domain subscriptions and quiet hour preferences.\n"
        "- Saved articles and watchlist keywords you explicitly add.\n"
        "- Completed lesson counts and quiz history.\n\n"
        "*What we do not do*\n"
        "- We do not sell, share, or monetize your personal data.\n"
        "- We do not track activity outside this bot.\n"
        "- We do not expose your saved items or settings to other users.\n\n"
        "*Your data controls*\n"
        "- `/export` — Export a machine-readable JSON copy of your stored data.\n"
        "- `/delete_account` — Permanently delete your preferences, saved items, and history.\n"
        "- `/settings` — Update notifications and subscriptions at any time."
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
        f"*Exported Personal Data*\n\n"
        f"```json\n{formatted_json}\n```\n\n"
        "To permanently delete this data, run `/delete_account`."
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
            "*Confirm Permanent Data Deletion*\n\n"
            "This action permanently deletes:\n"
            "- Saved articles and papers\n"
            "- Watchlist keywords and alerts\n"
            "- Domain subscriptions and quiet hour settings\n"
            "- Learning and quiz progress\n\n"
            "To confirm deletion, run:\n"
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
        "*User Data Deleted*\n\n"
        "Your preferences, saved items, watchlists, and learning progress have been permanently removed.\n\n"
        "You can start again anytime with `/start`."
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
                "Usage: `/ban <telegram_user_id>`\nExample: `/ban 123456789`",
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    target_id = int(args[0])
    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = Repository(session)
        await repo.get_or_create_user(target_id)
        await repo.set_user_ban_status(target_id, is_banned=True)

    msg = f"*User {target_id} has been banned.* Their requests will be rejected."
    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


@admin_only
async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command: restore access for a previously banned user."""
    args = context.args or []
    if not args or not args[0].isdigit():
        if update.effective_message:
            await update.effective_message.reply_text(
                "Usage: `/unban <telegram_user_id>`\nExample: `/unban 123456789`",
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    target_id = int(args[0])
    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = Repository(session)
        success = await repo.set_user_ban_status(target_id, is_banned=False)

    if success:
        msg = f"*User {target_id} has been unbanned.* Access restored."
    else:
        msg = f"User {target_id} was not found."

    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
