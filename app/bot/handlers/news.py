"""News, category, search, and collection Telegram handlers."""

import logging
from typing import Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.filters.auth import authorized_only
from app.bot.keyboards.inline import get_article_keyboard, get_category_keyboard
from app.bot.ui.formatters import format_article_view, format_search_results, format_sources_list
from app.services.news_service import NewsService

logger = logging.getLogger(__name__)
news_service = NewsService()


async def send_article_view(
    update: Update,
    category_slug: Optional[str] = None,
    source_slug: Optional[str] = None,
    offset: int = 0,
    is_edit: bool = False,
) -> None:
    """Helper to fetch and display an article at a given offset."""
    user = update.effective_user
    user_id = user.id if user else 0

    articles = await news_service.get_recent_news(
        limit=10,
        offset=0,
        category_slug=category_slug if category_slug != "all" else None,
        source_slug=source_slug,
    )

    if not articles:
        msg = (
            "📭 *No articles found in this category yet.*\n\n"
            "Run `/collect` to fetch the latest technology feeds and papers right now!"
        )
        if is_edit and update.callback_query and update.callback_query.message:
            await update.callback_query.message.edit_text(
                msg, parse_mode=ParseMode.MARKDOWN, reply_markup=get_category_keyboard()
            )
        elif update.effective_message:
            await update.effective_message.reply_text(
                msg, parse_mode=ParseMode.MARKDOWN, reply_markup=get_category_keyboard()
            )
        return

    safe_offset = max(0, min(offset, len(articles) - 1))
    current_article = articles[safe_offset]

    # Check if article is bookmarked
    saved_articles = await news_service.get_saved_articles(user_id=user_id, limit=50)
    saved_ids = {a.id for a in saved_articles}
    is_saved = current_article.id in saved_ids

    text = format_article_view(current_article, index=safe_offset, total=len(articles))
    reply_markup = get_article_keyboard(
        article_id=current_article.id,
        url=current_article.url,
        offset=safe_offset,
        total=len(articles),
        category_slug=category_slug,
        is_saved=is_saved,
    )

    if is_edit and update.callback_query and update.callback_query.message:
        try:
            await update.callback_query.message.edit_text(
                text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
            )
        except Exception:
            pass
    elif update.effective_message:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


# ------------------ Command Handlers ------------------


@authorized_only
async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch latest technology news across all categories."""
    await send_article_view(update, category_slug="all", offset=0)


@authorized_only
async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch Artificial Intelligence and Machine Learning intelligence."""
    await send_article_view(update, category_slug="ai", offset=0)


@authorized_only
async def robotics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch Robotics updates."""
    await send_article_view(update, category_slug="robotics", offset=0)


@authorized_only
async def science_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch Physics and Scientific updates."""
    await send_article_view(update, category_slug="physics", offset=0)


@authorized_only
async def engineering_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch Electronics & Engineering updates."""
    await send_article_view(update, category_slug="electronics", offset=0)


@authorized_only
async def programming_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch Computer Science & Software Engineering updates."""
    await send_article_view(update, category_slug="software-engineering", offset=0)


@authorized_only
async def research_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch latest arXiv research papers."""
    await send_article_view(update, source_slug="arxiv-ai", offset=0)


@authorized_only
async def github_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch trending repositories on GitHub."""
    await send_article_view(update, source_slug="github-trending", offset=0)


@authorized_only
async def sources_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display all configured intelligence sources and their active status."""
    sources = await news_service.get_sources_list()
    msg = format_sources_list(sources)
    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


@authorized_only
async def collect_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trigger manual collection from all active sources."""
    status_msg = None
    if update.effective_message:
        status_msg = await update.effective_message.reply_text(
            "⏳ *Collecting intelligence from all sources...*\nThis might take a few moments.",
            parse_mode=ParseMode.MARKDOWN,
        )

    results = await news_service.collect_from_all_sources()
    total_saved = sum(results.values())

    summary_lines = [f"✅ *Intelligence Collection Complete!*\n\nSaved *{total_saved}* new articles:\n"]
    for slug, count in results.items():
        summary_lines.append(f"• `{slug}`: +{count} new")

    summary_lines.append("\nView latest intelligence with `/news` or `/ai`.")
    final_text = "\n".join(summary_lines)

    if status_msg:
        await status_msg.edit_text(final_text, parse_mode=ParseMode.MARKDOWN)
    elif update.effective_message:
        await update.effective_message.reply_text(final_text, parse_mode=ParseMode.MARKDOWN)


@authorized_only
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search articles by keyword."""
    if not context.args:
        if update.effective_message:
            await update.effective_message.reply_text(
                "🔍 *Usage:* `/search <keyword>`\nExample: `/search humanoid` or `/search quantum`",
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    query = " ".join(context.args)
    results = await news_service.search_news(query=query, limit=5)
    msg = format_search_results(query, results)

    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


@authorized_only
async def saved_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display user's saved/bookmarked articles."""
    user = update.effective_user
    user_id = user.id if user else 0

    saved = await news_service.get_saved_articles(user_id=user_id, limit=10)
    if not saved:
        msg = "⭐ *You haven't bookmarked any articles yet.*\nTap *Bookmark ⭐* under any article to save it!"
        if update.effective_message:
            await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        return

    lines = ["⭐ *Your Bookmarked Articles:*\n"]
    for i, a in enumerate(saved, 1):
        lines.append(f"{i}. [{a.title}]({a.url})\nSource: _{a.source.name}_\n")

    if update.effective_message:
        await update.effective_message.reply_text(
            "\n".join(lines), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )


# ------------------ Callback Query Handler ------------------


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route callback queries from inline keyboard buttons."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    data = query.data

    if data == "noop":
        return

    if data == "show_cats":
        if query.message:
            await query.message.edit_text(
                "Select a STEM domain to explore:",
                reply_markup=get_category_keyboard(),
            )
        return

    if data.startswith("cat:"):
        cat_slug = data.split(":", 1)[1]
        await send_article_view(update, category_slug=cat_slug, offset=0, is_edit=True)
        return

    if data.startswith("nav:"):
        parts = data.split(":")
        cat_slug = parts[1] if len(parts) > 1 else "all"
        offset = int(parts[2]) if len(parts) > 2 else 0
        await send_article_view(update, category_slug=cat_slug, offset=offset, is_edit=True)
        return

    if data.startswith("save:"):
        article_id = int(data.split(":", 1)[1])
        user = update.effective_user
        if user:
            is_now_saved = await news_service.toggle_save_article(user.id, article_id)
            status_text = "Article added to bookmarks ⭐" if is_now_saved else "Article removed from bookmarks 🗑️"
            await query.answer(status_text)
        return
