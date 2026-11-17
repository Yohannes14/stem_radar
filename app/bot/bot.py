"""Telegram bot application setup, lifecycle management, and handler registration."""

import logging

from telegram import BotCommand
from telegram.ext import Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler
from telegram.request import HTTPXRequest

from app.bot.handlers.automation import (
    automation_callback_router,
    briefing_command,
    radar_command,
    stats_command,
    trends_command,
    velocity_command,
    watchlist_command,
)
from app.bot.handlers.base import (
    error_handler,
    help_command,
    main_menu_callback_router,
    start_command,
)
from app.bot.handlers.content import digest_command, ideas_command, trending_command
from app.bot.handlers.education import (
    compare_command,
    education_callback_router,
    learn_command,
    progress_command,
    project_command,
    quiz_command,
    roadmap_command,
    vocabulary_command,
)
from app.bot.handlers.news import (
    ai_command,
    callback_router,
    collect_command,
    engineering_command,
    ethiopia_command,
    explain_command,
    github_command,
    impact_command,
    news_command,
    politics_command,
    programming_command,
    research_command,
    robotics_command,
    saved_command,
    science_command,
    search_command,
    sources_command,
)
from app.bot.handlers.settings import (
    interests_command,
    settings_callback_router,
    settings_command,
)
from app.bot.handlers.student_hub import (
    courses_command,
    deadlines_command,
    scholarships_command,
    student_hub_callback_router,
    student_hub_command,
    universities_command,
)
from app.bot.handlers.user_management import (
    ban_command,
    delete_account_command,
    export_command,
    feedback_command,
    privacy_command,
    unban_command,
)
from app.config import settings
from app.scheduler.jobs import scheduler

logger = logging.getLogger(__name__)


async def on_startup(application: Application) -> None:
    """Lifecycle hook executed after bot initialization."""
    logger.info("Starting background intelligence scheduler alongside bot...")
    scheduler.start(bot=application.bot)

    # Register commands with Telegram Bot API so they appear in the [ / ] Menu button
    try:
        commands = [
            BotCommand("start", "🏠 Main Menu Dashboard"),
            BotCommand("news", "📰 Latest Technology News"),
            BotCommand("scholarships", "🎁 Verified STEM Scholarships"),
            BotCommand("universities", "🏛️ University Admissions & Guides"),
            BotCommand("courses", "📚 Free STEM Courses & Materials"),
            BotCommand("deadlines", "⏰ Upcoming Application Deadlines"),
            BotCommand("studenthub", "🎓 Student Hub & Academic Resources"),
            BotCommand("ethiopia", "🇪🇹 Ethiopia Tech & News"),
            BotCommand("politics", "🌍 World Politics & Affairs"),
            BotCommand("trending", "📈 High-Impact Breakthroughs"),
            BotCommand("radar", "🎯 Technology Radar"),
            BotCommand("ai", "🤖 Artificial Intelligence"),
            BotCommand("research", "📄 Research Papers"),
            BotCommand("search", "🔍 Unified STEM Search"),
            BotCommand("saved", "⭐ Bookmarked Items"),
            BotCommand("interests", "🏷️ Customize Topics"),
            BotCommand("briefing", "🌅 Executive Daily Briefing"),
            BotCommand("learn", "🎓 STEM Learning Academy"),
            BotCommand("help", "❓ Command Catalog"),
        ]
        await application.bot.set_my_commands(commands)
        logger.info("Registered Telegram bot menu commands successfully.")
    except Exception as exc:
        logger.warning("Could not set bot menu commands: %s", exc)


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
    app.add_handler(CommandHandler("ethiopia", ethiopia_command))
    app.add_handler(CommandHandler("politics", politics_command))
    app.add_handler(CommandHandler("ai", ai_command))
    app.add_handler(CommandHandler("robotics", robotics_command))
    app.add_handler(CommandHandler("science", science_command))
    app.add_handler(CommandHandler("engineering", engineering_command))
    app.add_handler(CommandHandler("programming", programming_command))
    app.add_handler(CommandHandler("research", research_command))
    app.add_handler(CommandHandler("github", github_command))

    # Intelligence & Content Opportunities
    app.add_handler(CommandHandler("trending", trending_command))
    app.add_handler(CommandHandler("explain", explain_command))
    app.add_handler(CommandHandler("impact", impact_command))
    app.add_handler(CommandHandler("ideas", ideas_command))
    app.add_handler(CommandHandler("digest", digest_command))

    # Operations & user tools
    app.add_handler(CommandHandler("sources", sources_command))
    app.add_handler(CommandHandler("collect", collect_command))
    app.add_handler(CommandHandler("refresh", collect_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("saved", saved_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("interests", interests_command))

    # Phase 4: Interactive STEM Education & Learning Assistant
    app.add_handler(CommandHandler("learn", learn_command))
    app.add_handler(CommandHandler("roadmap", roadmap_command))
    app.add_handler(CommandHandler("quiz", quiz_command))
    app.add_handler(CommandHandler("compare", compare_command))
    app.add_handler(CommandHandler("project", project_command))
    app.add_handler(CommandHandler("vocabulary", vocabulary_command))
    app.add_handler(CommandHandler("progress", progress_command))

    # Phase 5: Personalization & Automation Commands
    app.add_handler(CommandHandler("briefing", briefing_command))
    app.add_handler(CommandHandler("watchlist", watchlist_command))
    app.add_handler(CommandHandler("trends", trends_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("radar", radar_command))
    app.add_handler(CommandHandler("velocity", velocity_command))

    # Phase 7: Public User Management, Privacy & Admin Moderation
    app.add_handler(CommandHandler("feedback", feedback_command))
    app.add_handler(CommandHandler("privacy", privacy_command))
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CommandHandler("delete_account", delete_account_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))

    # Stage 11 & 12: Student Hub, Scholarship, University & Course Commands
    app.add_handler(CommandHandler("scholarships", scholarships_command))
    app.add_handler(CommandHandler("universities", universities_command))
    app.add_handler(CommandHandler("courses", courses_command))
    app.add_handler(CommandHandler("deadlines", deadlines_command))
    app.add_handler(CommandHandler("studenthub", student_hub_command))

    # Interactive inline callbacks
    app.add_handler(CallbackQueryHandler(student_hub_callback_router, pattern="^hub:.*$"))
    app.add_handler(
        CallbackQueryHandler(
            main_menu_callback_router,
            pattern="^(menu:.*|nav:home|search_kw:.*|radar_h:.*|prj_topic:.*)$",
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            settings_callback_router,
            pattern="^(toggle_notif|toggle_impact|toggle_weekly|pref_cat:.*)$",
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            automation_callback_router,
            pattern="^(wl_rm:.*|wl_clear|refresh_briefing|nav_trends|open_settings|radar_h:.*)$",
        )
    )
    app.add_handler(CallbackQueryHandler(education_callback_router, pattern="^(qz_|ed_)"))
    app.add_handler(CallbackQueryHandler(callback_router))

    # Global error handler
    app.add_error_handler(error_handler)

    return app


if __name__ == "__main__":
    from app.main import main

    main()
