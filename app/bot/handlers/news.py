"""News, category, search, and collection Telegram handlers."""

import logging
from typing import Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.filters.auth import authorized_only
from app.bot.keyboards.inline import (
    get_article_keyboard,
    get_category_keyboard,
    get_explanation_keyboard,
    get_search_pagination_keyboard,
)
from app.bot.keyboards.navigation import get_back_home_keyboard
from app.bot.ui.formatters import (
    chunk_message,
    format_article_view,
    format_concept_explanation,
    format_impact_analysis,
    format_news_summary,
    format_paper_analysis,
    format_related_articles,
    format_search_results_page,
    format_sources_list,
    format_stem_content,
)
from app.bot.ui.menu import safe_edit_or_reply
from app.services.ai import ai_service
from app.services.news_service import NewsService

logger = logging.getLogger(__name__)
news_service = NewsService()


async def send_article_view(
    update: Update,
    category_slug: Optional[str] = None,
    source_slug: Optional[str] = None,
    source_type: Optional[str] = None,
    offset: int = 0,
    is_edit: bool = False,
) -> None:
    """Helper to fetch and display an article at a given offset."""
    user = update.effective_user
    user_id = user.id if user else 0

    articles = await news_service.get_recent_news(
        limit=15,
        offset=0,
        category_slug=category_slug if category_slug != "all" else None,
        source_slug=source_slug,
        source_type=source_type,
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
        title=current_article.title,
    )

    if is_edit and update.callback_query and update.callback_query.message:
        try:
            await update.callback_query.message.edit_text(
                text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup, disable_web_page_preview=True
            )
        except Exception:
            pass
    elif update.effective_message:
        await update.effective_message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup, disable_web_page_preview=True
        )


SEARCH_PAGE_SIZE = 5


async def send_search_view(
    update: Update,
    query: str,
    page: int = 0,
    is_edit: bool = False,
) -> None:
    """Display paginated search results for a keyword query."""
    clean_query = query.strip()
    if not clean_query:
        return

    total_count = await news_service.count_news(query=clean_query)
    total_pages = max(1, (total_count + SEARCH_PAGE_SIZE - 1) // SEARCH_PAGE_SIZE)
    safe_page = max(0, min(page, total_pages - 1))

    articles = await news_service.get_recent_news(
        limit=SEARCH_PAGE_SIZE,
        offset=safe_page * SEARCH_PAGE_SIZE,
        query=clean_query,
    )

    text = format_search_results_page(
        query=clean_query,
        articles=articles,
        page=safe_page,
        total_pages=total_pages,
        total_count=total_count,
    )
    reply_markup = get_search_pagination_keyboard(
        query=clean_query,
        page=safe_page,
        total_pages=total_pages,
    )

    await safe_edit_or_reply(
        update,
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


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
    await send_article_view(update, source_type="arxiv", offset=0)


@authorized_only
async def github_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch trending repositories on GitHub."""
    await send_article_view(update, source_type="github", offset=0)


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
    """Search articles by keyword with interactive pagination."""
    if not context.args:
        if update.effective_message:
            await update.effective_message.reply_text(
                "🔍 *Usage:* `/search <keyword>`\nExample: `/search humanoid` or `/search quantum`",
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    query = " ".join(context.args)
    await send_search_view(update, query=query, page=0, is_edit=False)


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


@authorized_only
async def explain_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explain any technical concept with multi-tier difficulty modes."""
    if not context.args:
        if update.effective_message:
            await update.effective_message.reply_text(
                "💡 *Usage:* `/explain <concept>` or `/explain <beginner|intermediate|advanced> <concept>`\n\n"
                "Examples:\n"
                "• `/explain Quantum Computing`\n"
                "• `/explain beginner Transformer Architecture`\n"
                "• `/explain advanced Direct Drive Actuators`",
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    mode = "intermediate"
    raw_args = list(context.args)
    if raw_args[0].lower() in ("beginner", "intermediate", "advanced"):
        mode = raw_args.pop(0).lower()

    concept_name = " ".join(raw_args)
    status_msg = None
    if update.effective_message:
        status_msg = await update.effective_message.reply_text(
            f"🧠 *Generating {mode}-level technical breakdown for '{concept_name}'...*",
            parse_mode=ParseMode.MARKDOWN,
        )

    explanation = await ai_service.explain_concept(concept_name, mode=mode)
    text = format_concept_explanation(explanation)

    if status_msg:
        await status_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    elif update.effective_message:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@authorized_only
async def impact_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Analyze the strategic and economic impact of latest tech developments."""
    articles = await news_service.get_recent_news(limit=1)
    if not articles:
        if update.effective_message:
            await update.effective_message.reply_text(
                "No articles found to analyze. Run `/collect` first!", parse_mode=ParseMode.MARKDOWN
            )
        return

    target_article = articles[0]
    status_msg = None
    if update.effective_message:
        status_msg = await update.effective_message.reply_text(
            f"📊 *Analyzing technology impact for:*\n_{target_article.title[:80]}..._",
            parse_mode=ParseMode.MARKDOWN,
        )

    impact = await ai_service.analyze_impact(target_article)
    text = format_impact_analysis(impact)

    if status_msg:
        await status_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    elif update.effective_message:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@authorized_only
async def ideas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate STEM educational content kit (LinkedIn, Carousel, Video, Glossary)."""
    articles = await news_service.get_recent_news(limit=1)
    if not articles:
        if update.effective_message:
            await update.effective_message.reply_text(
                "No articles found. Run `/collect` first!", parse_mode=ParseMode.MARKDOWN
            )
        return

    target_article = articles[0]
    status_msg = None
    if update.effective_message:
        status_msg = await update.effective_message.reply_text(
            f"🎨 *Generating STEM content package for:*\n_{target_article.title[:80]}..._",
            parse_mode=ParseMode.MARKDOWN,
        )

    pkg = await ai_service.generate_stem_content(target_article)
    text = format_stem_content(pkg)
    chunks = chunk_message(text, max_length=4000)

    if status_msg:
        await status_msg.edit_text(chunks[0], parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        for extra in chunks[1:]:
            await update.effective_message.reply_text(
                extra, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
            )
    elif update.effective_message:
        for chunk in chunks:
            await update.effective_message.reply_text(
                chunk, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
            )


# ------------------ Callback Query Handler ------------------


@authorized_only
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
            article = await news_service.get_article_by_id(article_id)
            if article and query.message and query.message.reply_markup:
                # Re-render keyboard with toggled saved status
                new_markup = get_article_keyboard(
                    article_id=article.id,
                    url=article.url,
                    offset=0,
                    total=1,
                    category_slug=article.categories[0].slug if article.categories else None,
                    is_saved=is_now_saved,
                    title=article.title,
                )
                try:
                    await query.message.edit_reply_markup(reply_markup=new_markup)
                except Exception:
                    pass
        return

    if data.startswith("ai_exp:"):
        article_id = int(data.split(":", 1)[1])
        article = await news_service.get_article_by_id(article_id)
        if article:
            concept_name = article.categories[0].name if article.categories else article.title[:45]
            explanation = await ai_service.explain_concept(concept_name, mode="intermediate")
            exp_text = f"🧠 *AI Concept Breakdown for:*\n_{article.title[:75]}..._\n\n" + format_concept_explanation(
                explanation
            )
            markup = get_explanation_keyboard(article.id, current_mode="intermediate")
            await safe_edit_or_reply(
                update,
                exp_text,
                reply_markup=markup,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
        return

    if data.startswith("exp_mode:"):
        parts = data.split(":")
        article_id = int(parts[1])
        mode = parts[2]
        article = await news_service.get_article_by_id(article_id)
        if article:
            concept_name = article.categories[0].name if article.categories else article.title[:45]
            explanation = await ai_service.explain_concept(concept_name, mode=mode)
            exp_text = (
                f"🧠 *AI Concept Breakdown ({mode.capitalize()}):*\n_{article.title[:75]}..._\n\n"
                + format_concept_explanation(explanation)
            )
            markup = get_explanation_keyboard(article.id, current_mode=mode)
            await safe_edit_or_reply(
                update,
                exp_text,
                reply_markup=markup,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
        return

    if data.startswith("rel:"):
        article_id = int(data.split(":", 1)[1])
        article = await news_service.get_article_by_id(article_id)
        if article:
            related = await news_service.get_related_articles(article_id, limit=4)
            text = format_related_articles(article, related)
            markup = get_back_home_keyboard(back_target=f"back_art:{article_id}", home_target="menu:home")
            await safe_edit_or_reply(
                update,
                text,
                reply_markup=markup,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
        return

    if data.startswith("back_art:"):
        article_id = int(data.split(":", 1)[1])
        article = await news_service.get_article_by_id(article_id)
        if article:
            user = update.effective_user
            user_id = user.id if user else 0
            saved = await news_service.get_saved_articles(user_id=user_id, limit=50)
            is_saved = article.id in {a.id for a in saved}
            text = format_article_view(article, index=0, total=1)
            markup = get_article_keyboard(
                article_id=article.id,
                url=article.url,
                offset=0,
                total=1,
                category_slug=article.categories[0].slug if article.categories else None,
                is_saved=is_saved,
                title=article.title,
            )
            await safe_edit_or_reply(
                update,
                text,
                reply_markup=markup,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
        return

    if data.startswith("s_nav:"):
        parts = data.split(":")
        query_kw = parts[1]
        page = int(parts[2]) if len(parts) > 2 else 0
        await send_search_view(update, query=query_kw, page=page, is_edit=True)
        return

    if data.startswith("ai_sum:"):
        article_id = int(data.split(":", 1)[1])
        article = await news_service.get_article_by_id(article_id)
        if article and query.message:
            is_paper = article.source and article.source.source_type == "arxiv"
            if is_paper:
                analysis = await ai_service.analyze_research_paper(article)
                text = format_paper_analysis(analysis)
            else:
                summary = await ai_service.summarize_news(article, mode="intermediate")
                text = format_news_summary(summary)
            await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return

    if data.startswith("ai_cnt:"):
        article_id = int(data.split(":", 1)[1])
        article = await news_service.get_article_by_id(article_id)
        if article and query.message:
            pkg = await ai_service.generate_stem_content(article)
            text = format_stem_content(pkg)
            for chunk in chunk_message(text, max_length=4000):
                await query.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return
