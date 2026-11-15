"""Telegram bot application setup, lifecycle management, and handler registration."""

import logging

from telegram.ext import Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler
from telegram.request import HTTPXRequest

from app.bot.handlers.base import error_handler, help_command, start_command
from app.bot.handlers.content import digest_command, ideas_command, trending_command
from app.bot.handlers.news import (
    ai_command,
    callback_router,
    collect_command,
    engineering_command,
    github_command,
    news_command,
    programming_command,
    research_command,
    robotics_command,
    saved_command,
    science_command,
    search_command,
    sources_command,
)
from app.bot.handlers.settings import settings_callback_router, settings_command
from app.config import settings
from app.scheduler.jobs import scheduler

logger = logging.getLogger(__name__)


async def on_startup(application: Application) -> None:
    """Lifecycle hook executed after bot initialization."""
    logger.info("Starting background intelligence scheduler alongside bot...")
    scheduler.start()


async def on_shutdown(application: Application) -> None:
    """Lifecycle hook executed during bot termination."""
    logger.info("Stopping background intelligence scheduler...")
    scheduler.shutdown()


def create_bot_app() -> Application:
    """Build and configure the python-telegram-bot Application instance."""
    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured in .env!")

    request = HTTPXRequest(
        connect_timeout=settings.telegram_connect_timeout,
        read_timeout=settings.telegram_read_timeout,
        write_timeout=settings.telegram_read_timeout,
        pool_timeout=settings.telegram_connect_timeout,
        proxy=settings.telegram_proxy_url,
    )

    app = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .request(request)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .build()
    )

    # Core base commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))

    # News & domain commands
    app.add_handler(CommandHandler("news", news_command))
    app.add_handler(CommandHandler("ai", ai_command))
    app.add_handler(CommandHandler("robotics", robotics_command))
    app.add_handler(CommandHandler("science", science_command))
    app.add_handler(CommandHandler("engineering", engineering_command))
    app.add_handler(CommandHandler("programming", programming_command))
    app.add_handler(CommandHandler("research", research_command))
    app.add_handler(CommandHandler("github", github_command))

    # Intelligence & Content Opportunities
    app.add_handler(CommandHandler("trending", trending_command))
    app.add_handler(CommandHandler("ideas", ideas_command))
    app.add_handler(CommandHandler("digest", digest_command))

    # Operations & user tools
    app.add_handler(CommandHandler("sources", sources_command))
    app.add_handler(CommandHandler("collect", collect_command))
    app.add_handler(CommandHandler("refresh", collect_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("saved", saved_command))
    app.add_handler(CommandHandler("settings", settings_command))

    # Interactive inline callbacks
    app.add_handler(CallbackQueryHandler(settings_callback_router, pattern="^(toggle_notif|pref_cat:.*)$"))
    app.add_handler(CallbackQueryHandler(callback_router))

    # Global error handler
    app.add_error_handler(error_handler)

    return app
