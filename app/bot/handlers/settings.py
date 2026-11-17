"""User settings and personalization Telegram handler."""

import logging

from telegram import InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.filters.auth import authorized_only
from app.bot.keyboards.inline import get_settings_panel_keyboard
from app.bot.ui.menu import get_interests_keyboard, safe_edit_or_reply
from app.database.database import get_session_factory
from app.database.repository import Repository

logger = logging.getLogger(__name__)


def get_settings_keyboard(
    notifications_enabled: bool,
    high_impact_enabled: bool = True,
    weekly_reports_enabled: bool = True,
    quiet_hours_enabled: bool = True,
) -> InlineKeyboardMarkup:
    """Build inline keyboard for managing user preferences."""
    return get_settings_panel_keyboard(
        notifications_enabled=notifications_enabled,
        high_impact_enabled=high_impact_enabled,
        weekly_reports_enabled=weekly_reports_enabled,
        quiet_hours_enabled=quiet_hours_enabled,
    )


@authorized_only
async def interests_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display interactive multi-category domain subscriptions panel."""
    user = update.effective_user
    if not user:
        return

    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = Repository(session)
        active_slugs = await repo.get_user_preferred_categories(user.id)

    active_display = ", ".join([f"#{s}" for s in active_slugs]) if active_slugs else "All STEM Domains"
    safe_display = active_display.replace("_", "-")
    text = (
        "🏷 *My STEM Domain Subscriptions*\n\n"
        "Select the disciplines you want prioritized in your daily briefings, digests, and intelligence feeds.\n\n"
        f"Active Subscriptions: `{safe_display}`\n\n"
        "Tap below to toggle active subscriptions on or off:"
    )

    markup = get_interests_keyboard(active_slugs=active_slugs)
    if update.effective_message:
        try:
            await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        except Exception as exc:
            if "can't parse entities" in str(exc).lower():
                await update.effective_message.reply_text(text, parse_mode=None, reply_markup=markup)
            else:
                raise


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
    impact_str = "Enabled 🟢" if pref.high_impact_alerts_enabled else "Disabled 🔴"
    weekly_str = "Enabled 🟢" if pref.weekly_report_enabled else "Disabled 🔴"
    quiet_hours_on = pref.quiet_hours_start != pref.quiet_hours_end
    quiet_status = (
        f"`{pref.quiet_hours_start}` to `{pref.quiet_hours_end}` UTC (Active 🌙)" if quiet_hours_on else "Disabled ☀️"
    )
    cats_str = pref.preferred_categories or "All Categories"

    text = (
        f"⚙️ *STEM RADAR User Settings*\n\n"
        f"👤 *User ID:* `{user.id}`\n"
        f"🔔 *Daily Digest & Alerts:* {status_str}\n"
        f"⚡ *High-Impact Alerts:* {impact_str}\n"
        f"🌐 *Weekly Intelligence Report:* {weekly_str}\n"
        f"⏰ *Scheduled Digest Time:* `{pref.digest_time}` UTC\n"
        f"🌙 *Quiet Hours:* {quiet_status}\n"
        f"🗂️ *Active Subscribed Domain:* `{cats_str}`\n\n"
        "Tap the buttons below to toggle your notification & domain subscriptions:"
    )

    if update.effective_message:
        await update.effective_message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_settings_keyboard(
                pref.notifications_enabled,
                pref.high_impact_alerts_enabled,
                pref.weekly_report_enabled,
                quiet_hours_on,
            ),
        )


@authorized_only
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
            notif_state = pref.notifications_enabled
            impact_state = pref.high_impact_alerts_enabled
            weekly_state = pref.weekly_report_enabled
            quiet_state = pref.quiet_hours_start != pref.quiet_hours_end

        status_text = "Notifications turned ON 🔔" if notif_state else "Notifications turned OFF 🔕"
        await query.answer(status_text)
        if query.message:
            await query.message.edit_reply_markup(
                reply_markup=get_settings_keyboard(notif_state, impact_state, weekly_state, quiet_state)
            )
        return

    if data == "toggle_impact":
        async with session_factory() as session:
            repo = Repository(session)
            pref = await repo.get_or_create_preference(user.id)
            pref.high_impact_alerts_enabled = not pref.high_impact_alerts_enabled
            await session.commit()
            notif_state = pref.notifications_enabled
            impact_state = pref.high_impact_alerts_enabled
            weekly_state = pref.weekly_report_enabled
            quiet_state = pref.quiet_hours_start != pref.quiet_hours_end

        status_text = "High-impact alerts ON ⚡" if impact_state else "High-impact alerts OFF"
        await query.answer(status_text)
        if query.message:
            await query.message.edit_reply_markup(
                reply_markup=get_settings_keyboard(notif_state, impact_state, weekly_state, quiet_state)
            )
        return

    if data == "toggle_weekly":
        async with session_factory() as session:
            repo = Repository(session)
            pref = await repo.get_or_create_preference(user.id)
            pref.weekly_report_enabled = not pref.weekly_report_enabled
            await session.commit()
            notif_state = pref.notifications_enabled
            impact_state = pref.high_impact_alerts_enabled
            weekly_state = pref.weekly_report_enabled
            quiet_state = pref.quiet_hours_start != pref.quiet_hours_end

        status_text = "Weekly report ON 🌐" if weekly_state else "Weekly report OFF"
        await query.answer(status_text)
        if query.message:
            await query.message.edit_reply_markup(
                reply_markup=get_settings_keyboard(notif_state, impact_state, weekly_state, quiet_state)
            )
        return

    if data == "toggle_quiet":
        async with session_factory() as session:
            repo = Repository(session)
            pref = await repo.get_or_create_preference(user.id)
            is_currently_on = pref.quiet_hours_start != pref.quiet_hours_end
            if is_currently_on:
                pref.quiet_hours_start = "00:00"
                pref.quiet_hours_end = "00:00"
            else:
                pref.quiet_hours_start = "22:00"
                pref.quiet_hours_end = "07:00"
            await session.commit()
            notif_state = pref.notifications_enabled
            impact_state = pref.high_impact_alerts_enabled
            weekly_state = pref.weekly_report_enabled
            quiet_state = pref.quiet_hours_start != pref.quiet_hours_end

        status_text = "Quiet hours enabled (22:00–07:00 UTC) 🌙" if quiet_state else "Quiet hours disabled ☀️"
        await query.answer(status_text)
        if query.message:
            await query.message.edit_reply_markup(
                reply_markup=get_settings_keyboard(notif_state, impact_state, weekly_state, quiet_state)
            )
        return

    if data.startswith("pref_cat:"):
        cat = data.split(":", 1)[1]
        async with session_factory() as session:
            repo = Repository(session)
            active_slugs, is_added = await repo.toggle_user_interest_category(user.id, cat)

        if cat == "all":
            status_text = "Reset subscriptions to All STEM Domains 🌐"
        elif is_added:
            status_text = f"Subscribed to #{cat} ✅"
        else:
            status_text = f"Unsubscribed from #{cat} ❌"

        await query.answer(status_text)

        # Check if the message is the settings panel or the dedicated interests keyboard
        is_settings_panel = False
        if query.message and query.message.reply_markup:
            for row in query.message.reply_markup.inline_keyboard:
                for btn in row:
                    if btn.callback_data == "toggle_notif":
                        is_settings_panel = True
                        break

        if is_settings_panel:
            async with session_factory() as session:
                repo = Repository(session)
                pref = await repo.get_or_create_preference(user.id)
                notif_state = pref.notifications_enabled
                impact_state = pref.high_impact_alerts_enabled
                weekly_state = pref.weekly_report_enabled
                quiet_state = pref.quiet_hours_start != pref.quiet_hours_end

            if query.message:
                await query.message.edit_reply_markup(
                    reply_markup=get_settings_keyboard(notif_state, impact_state, weekly_state, quiet_state)
                )
        else:
            active_display = ", ".join([f"#{s}" for s in active_slugs]) if active_slugs else "All Domains"
            safe_display = active_display.replace("_", "-")
            text = (
                "🏷 *My STEM Domain Subscriptions*\n\n"
                "Select the disciplines you want prioritized in your daily briefings, "
                "digests, and intelligence feeds.\n\n"
                f"Active Subscriptions: `{safe_display}`\n\n"
                "Tap below to toggle active subscriptions on or off:"
            )
            markup = get_interests_keyboard(active_slugs=active_slugs)
            await safe_edit_or_reply(update, text, reply_markup=markup)
        return
