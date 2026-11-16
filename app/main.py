"""Main entry point for the STEM RADAR platform."""

import argparse
import asyncio
import logging
import sys

from app.bot.bot import create_bot_app
from app.config import setup_logging
from app.database.database import init_db
from app.services.news_service import NewsService

logger = logging.getLogger("stem_radar")


async def run_collector_once() -> None:
    """Run a single intelligence collection pass across all active sources."""
    await init_db()
    service = NewsService()
    logger.info("Starting one-shot intelligence collection pass...")
    results = await service.collect_from_all_sources()
    total = sum(results.values())
    logger.info("Collection complete. Total new articles saved: %d", total)
    for slug, count in results.items():
        logger.info("  • %s: +%d", slug, count)


def main() -> None:
    """Application CLI entry point."""
    parser = argparse.ArgumentParser(description="STEM RADAR - Technology Intelligence Platform")
    parser.add_argument(
        "--collect",
        action="store_true",
        help="Run a one-time news collection pass and exit without starting the Telegram bot.",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize the SQLite database and seed default categories & sources.",
    )
    args = parser.parse_args()

    setup_logging()

    if args.init_db:
        logger.info("Initializing database...")
        asyncio.run(init_db())
        logger.info("Database successfully initialized.")
        return

    if args.collect:
        asyncio.run(run_collector_once())
        return

    # Default action: run the Telegram Bot
    logger.info("Starting STEM RADAR Telegram Bot...")
    try:
        # Initialize database before starting bot
        asyncio.run(init_db())

        app = create_bot_app()
        logger.info("Bot application initialized. Commencing polling...")
        app.run_polling(drop_pending_updates=True, bootstrap_retries=5)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C). Shutting down gracefully.")
    except Exception as exc:
        err_name = exc.__class__.__name__
        if "TimedOut" in err_name or "NetworkError" in err_name:
            logger.error(
                "\n=======================================================\n"
                "⚠️  TELEGRAM CONNECTION TIMEOUT\n"
                "=======================================================\n"
                "Your computer could not connect to api.telegram.org.\n"
                "This happens when:\n"
                "  1. Telegram is blocked/throttled by your local ISP or region.\n"
                "  2. A VPN or proxy is needed to access Telegram.\n\n"
                "SOLUTIONS:\n"
                "  • Turn on a VPN (e.g., Cloudflare WARP 1.1.1.1, ProtonVPN).\n"
                "  • Or set a proxy in your .env file:\n"
                "      TELEGRAM_PROXY_URL=http://127.0.0.1:7890\n"
                "      (or socks5://127.0.0.1:1080)\n"
                "=======================================================\n"
            )
        else:
            logger.critical("Fatal error starting STEM RADAR: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
