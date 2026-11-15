"""User settings and personalization Telegram handler."""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.filters.auth import authorized_only
from app.database.database import get_session_factory
from app.database.repository import Repository

logger = logging.getLogger(__name__)


def get_settings_keyboard(notifications_enabled: bool) -> InlineKeyboardMarkup:
    """Build inline keyboard for managing user preferences."""
    notif_btn = "🔔 Notifications: ON" if notifications_enabled else "🔕 Notifications: OFF"
    buttons = [
        [InlineKeyboardButton(notif_btn, callback_data="toggle_notif")],
        [
            InlineKeyboardButton("🌐 Preferred: All STEM", callback_data="pref_cat:all"),
            InlineKeyboardButton("🤖 AI Only", callback_data="pref_cat:ai"),
        ],
        [
            InlineKeyboardButton("🦾 Robotics Only", callback_data="pref_cat:robotics"),
            InlineKeyboardButton("💻 Software Only", callback_data="pref_cat:cs"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


@authorized_only
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display user preferences and settings panel."""
    user = update.effective_user
    if not user:
        return

    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = Repository(session)
        pref = await repo.get_or_create_preference(user.id)

    status_str = "Enabled 🟢" if pref.notifications_enabled else "Disabled 🔴"
    cats_str = pref.preferred_categories or "All Categories"

    text = (
        f"⚙️ *STEM RADAR User Settings*\n\n"
        f"👤 *User ID:* `{user.id}`\n"
        f"🔔 *Daily Digest & Alerts:* {status_str}\n"
        f"⏰ *Digest Time:* `{pref.digest_time}` UTC\n"
        f"🗂️ *Active Filter:* `{cats_str}`\n\n"
        "Tap the buttons below to toggle your preferences:"
    )

    if update.effective_message:
        await update.effective_message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_settings_keyboard(pref.notifications_enabled),
        )


async def settings_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle settings inline keyboard interactions."""
    query = update.callback_query
    if not query or not query.data:
        return

    user = update.effective_user
    if not user:
        return

    data = query.data
    session_factory = get_session_factory()

    if data == "toggle_notif":
        async with session_factory() as session:
            repo = Repository(session)
            pref = await repo.get_or_create_preference(user.id)
            pref.notifications_enabled = not pref.notifications_enabled
            await session.commit()
            new_state = pref.notifications_enabled

        status_text = "Notifications turned ON 🔔" if new_state else "Notifications turned OFF 🔕"
        await query.answer(status_text)

        if query.message:
            await query.message.edit_reply_markup(reply_markup=get_settings_keyboard(new_state))
        return

    if data.startswith("pref_cat:"):
        cat = data.split(":", 1)[1]
        async with session_factory() as session:
            repo = Repository(session)
            pref = await repo.get_or_create_preference(user.id)
            pref.preferred_categories = cat
            await session.commit()

        await query.answer(f"Preferred category set to: {cat}")
        return
