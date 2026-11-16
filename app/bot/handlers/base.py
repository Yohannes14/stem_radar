"""Base bot commands: /start, /help, and error handlers."""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.filters.auth import authorized_only
from app.bot.keyboards.inline import get_category_keyboard

logger = logging.getLogger(__name__)


@authorized_only
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message and system introduction."""
    user = update.effective_user
    name = user.first_name if user else "Researcher"

    welcome_text = (
        f"📡 *Welcome to STEM RADAR, {name}!* 🚀\n\n"
        "Your AI-powered intelligence platform collecting, analyzing, and organizing "
        "the latest developments in Science, Technology, Engineering, and Mathematics.\n\n"
        "⚡ *Quick Navigation:*\n"
        "• `/news` — Latest technology intelligence\n"
        "• `/ai` — Artificial Intelligence & Machine Learning\n"
        "• `/robotics` — Robotics, Humanoids & Drones\n"
        "• `/research` — Latest arXiv Research Papers\n"
        "• `/github` — Trending Repositories & Open Source\n"
        "• `/sources` — View active intelligence feeds\n"
        "• `/collect` — Trigger instant intelligence collection\n"
        "• `/saved` — View your bookmarked articles\n"
        "• `/help` — Full list of commands\n\n"
        "Select a domain below to start exploring:"
    )

    if update.effective_message:
        await update.effective_message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_category_keyboard(),
        )


@authorized_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display comprehensive command catalog."""
    help_text = (
        "📚 *STEM RADAR Command Catalog*\n\n"
        "*Core Intelligence:*\n"
        "• `/news` — Latest tech articles across all sources\n"
        "• `/trending` — High-impact trending developments\n"
        "• `/sources` — Configured information feeds & status\n"
        "• `/collect` — Force instant multi-source collection\n\n"
        "*Domain Commands:*\n"
        "• `/ai` — Artificial Intelligence & LLMs\n"
        "• `/robotics` — Robotics & Autonomous Systems\n"
        "• `/science` — Physics, Chemistry & Biotechnology\n"
        "• `/engineering` — Electronics & Embedded Systems\n"
        "• `/programming` — Software Engineering & CS\n"
        "• `/research` — Latest arXiv research papers\n"
        "• `/github` — Trending GitHub repositories\n\n"
        "*Search & Personalization (Phase 5):*\n"
        "• `/briefing` — Executive daily STEM intelligence briefing\n"
        "• `/watchlist` — Keyword & technology real-time alerts\n"
        "• `/trends` — SOTA breakthrough scoring & impact ranking\n"
        "• `/stats` — Platform telemetry & intelligence metrics\n"
        "• `/search <keyword>` — Search collected articles\n"
        "• `/saved` — View bookmarked articles\n"
        "• `/settings` — Notification preferences & quiet hours\n\n"
        "*STEM Learning Academy (Phase 4):*\n"
        "• `/learn <topic>` — Interactive multi-tier STEM lesson\n"
        "• `/roadmap <topic>` — 4-phase structured curriculum\n"
        "• `/quiz <topic>` — Interactive comprehension test\n"
        "• `/compare <A> vs <B>` — Architectural concept comparison\n"
        "• `/project <topic>` — Practical engineering portfolio project\n"
        "• `/vocabulary <topic>` — Technical terminology glossary\n"
        "• `/progress` — Track lessons completed and quiz mastery\n\n"
        "*AI Features:*\n"
        "• `/explain <concept>` — Multi-tier concept breakdown\n"
        "• `/impact` — Strategic technology assessment\n"
        "• `/ideas` — Transform news into STEM content opportunities\n"
        "• `/digest` — Daily intelligence summary"
    )

    if update.effective_message:
        await update.effective_message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log exceptions encountered during update handling."""
    logger.error("Exception while handling Telegram update: %s", context.error, exc_info=context.error)
