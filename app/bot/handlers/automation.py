"""Automation, watchlist, briefing, and platform telemetry Telegram handlers."""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.filters.auth import authorized_only
from app.bot.handlers.settings import settings_command
from app.bot.keyboards.inline import (
    get_briefing_keyboard,
    get_tech_radar_keyboard,
    get_watchlist_keyboard,
)
from app.bot.ui.formatters import (
    format_platform_stats,
    format_tech_radar,
    format_trend_velocity,
    format_trending_feed,
    format_watchlist,
)
from app.database.database import get_session_factory
from app.database.repository import Repository
from app.services.automation_service import automation_service

logger = logging.getLogger(__name__)


@authorized_only
async def briefing_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and display personalized executive daily STEM briefing."""
    user = update.effective_user
    if not user:
        return

    user_name = user.first_name or "Engineer"
    text, _ = await automation_service.generate_daily_briefing(user_id=user.id, user_name=user_name)

    if update.effective_message:
        await update.effective_message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_briefing_keyboard(),
            disable_web_page_preview=True,
        )


@authorized_only
async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manage keyword and technology watchlists (list, add, remove, clear)."""
    user = update.effective_user
    if not user:
        return

    session_factory = get_session_factory()
    args = context.args or []

    # 1. No arguments: Display active watchlist
    if not args:
        async with session_factory() as session:
            repo = Repository(session)
            watchlist = await repo.get_user_watchlist(user.id)

        msg = format_watchlist(watchlist)
        markup = get_watchlist_keyboard(watchlist) if watchlist else None
        if update.effective_message:
            await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        return

    action = args[0].lower()

    # 2. Add keyword: /watchlist add <keyword>
    if action == "add":
        if len(args) < 2:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ *Usage:* `/watchlist add <keyword>`\n\n_Example:_ `/watchlist add humanoid`",
                    parse_mode=ParseMode.MARKDOWN,
                )
            return

        keyword = " ".join(args[1:]).strip()
        async with session_factory() as session:
            repo = Repository(session)
            item, created = await repo.add_watchlist_keyword(user.id, keyword)

        if created:
            reply_text = f"✅ Added *#{item.keyword}* to your STEM watchlist!\nWe will alert you when matches appear."
        else:
            reply_text = f"ℹ️ *#{item.keyword}* is already in your watchlist ({item.match_count} matches so far)."

        if update.effective_message:
            await update.effective_message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN)
        return

    # 3. Remove keyword: /watchlist remove <keyword>
    if action in ("remove", "rm", "delete"):
        if len(args) < 2:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ *Usage:* `/watchlist remove <keyword>`", parse_mode=ParseMode.MARKDOWN
                )
            return

        keyword = " ".join(args[1:]).strip()
        async with session_factory() as session:
            repo = Repository(session)
            removed = await repo.remove_watchlist_keyword(user.id, keyword)

        if removed:
            reply_text = f"🗑️ Removed *#{keyword.lower()}* from your watchlist."
        else:
            reply_text = f"⚠️ Keyword *#{keyword.lower()}* was not found in your watchlist."

        if update.effective_message:
            await update.effective_message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN)
        return

    # 4. Clear all: /watchlist clear
    if action in ("clear", "reset"):
        async with session_factory() as session:
            repo = Repository(session)
            count = await repo.clear_user_watchlist(user.id)

        reply_text = f"🗑️ Cleared all {count} keywords from your watchlist."
        if update.effective_message:
            await update.effective_message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN)
        return

    # Invalid subcommand
    if update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Unknown watchlist option. Use `/watchlist`, `/watchlist add <keyword>`, or `/watchlist clear`.",
            parse_mode=ParseMode.MARKDOWN,
        )


@authorized_only
async def trends_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display high-impact STEM developments ranked by composite intelligence score."""
    scored = await automation_service.get_trending_developments(limit=7)
    text = format_trending_feed(scored)

    if update.effective_message:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


@authorized_only
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display system-wide telemetry and personalized intelligence statistics."""
    user = update.effective_user
    user_id = user.id if user else None

    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = Repository(session)
        stats = await repo.get_platform_stats(user_id=user_id)

    text = format_platform_stats(stats)
    if update.effective_message:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@authorized_only
async def radar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display interactive STEM Technology Radar classified into 4 adoption horizons."""
    raw_args = context.args or []
    horizon = (
        raw_args[0].lower()
        if raw_args and raw_args[0].lower() in ("all", "adopt", "trial", "assess", "hold")
        else "all"
    )

    scored = await automation_service.get_trending_developments(limit=5)
    velocities = await automation_service.calculate_domain_velocity()

    text = format_tech_radar(horizon=horizon, scored_articles=scored, domain_velocities=velocities)
    markup = get_tech_radar_keyboard(current_horizon=horizon)

    if update.effective_message:
        await update.effective_message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup,
            disable_web_page_preview=True,
        )


@authorized_only
async def velocity_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display evidence-based trend velocity and momentum indicators across STEM domains."""
    velocities = await automation_service.calculate_domain_velocity()
    text = format_trend_velocity(velocities)

    if update.effective_message:
        await update.effective_message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )


@authorized_only
async def automation_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route callback queries from watchlist and briefing interactive buttons."""
    query = update.callback_query
    if not query or not query.data:
        return

    user = update.effective_user
    if not user:
        return

    data = query.data
    session_factory = get_session_factory()

    if data.startswith("wl_rm:"):
        kw = data.split(":", 1)[1]
        async with session_factory() as session:
            repo = Repository(session)
            await repo.remove_watchlist_keyword(user.id, kw)
            watchlist = await repo.get_user_watchlist(user.id)

        await query.answer(f"Removed #{kw}")
        msg = format_watchlist(watchlist)
        markup = get_watchlist_keyboard(watchlist) if watchlist else None
        if query.message:
            await query.message.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        return

    if data == "wl_clear":
        async with session_factory() as session:
            repo = Repository(session)
            await repo.clear_user_watchlist(user.id)

        await query.answer("Watchlist cleared!")
        msg = format_watchlist([])
        if query.message:
            await query.message.edit_text(msg, parse_mode=ParseMode.MARKDOWN)
        return

    if data == "refresh_briefing":
        await query.answer("Refreshing briefing...")
        user_name = user.first_name or "Engineer"
        text, _ = await automation_service.generate_daily_briefing(user_id=user.id, user_name=user_name)
        if query.message:
            await query.message.edit_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_briefing_keyboard(),
                disable_web_page_preview=True,
            )
        return

    if data == "nav_trends":
        await query.answer()
        scored = await automation_service.get_trending_developments(limit=7)
        text = format_trending_feed(scored)
        if query.message:
            await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return

    if data == "open_settings":
        await query.answer()
        await settings_command(update, context)
        return

    if data.startswith("radar_h:"):
        horizon = data.split(":", 1)[1]
        if horizon == "refresh":
            horizon = "all"
            await query.answer("Refreshing technology radar...")
        else:
            await query.answer(f"Horizon: {horizon.upper()}")

        scored = await automation_service.get_trending_developments(limit=5)
        velocities = await automation_service.calculate_domain_velocity()
        text = format_tech_radar(horizon=horizon, scored_articles=scored, domain_velocities=velocities)
        markup = get_tech_radar_keyboard(current_horizon=horizon)
        if query.message:
            await query.message.edit_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
        return
