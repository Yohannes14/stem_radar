"""News, category, search, and collection Telegram handlers."""

import logging
import re
from typing import List, Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.filters.auth import admin_only, authorized_only
from app.bot.keyboards.inline import (
    get_article_keyboard,
    get_category_keyboard,
    get_concept_mode_keyboard,
    get_explanation_keyboard,
    get_paper_analysis_keyboard,
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
    format_sources_list,
    format_stem_content,
)
from app.bot.ui.menu import get_research_hub_keyboard, get_search_shortcuts_keyboard, safe_edit_or_reply
from app.services.ai import ai_service
from app.services.news_service import NewsService
from app.services.search import search_service
from app.services.search.ai_assistant import search_ai_assistant

logger = logging.getLogger(__name__)
news_service = NewsService()


async def send_article_view(
    update: Update,
    category_slug: Optional[str] = None,
    category_slugs: Optional[List[str]] = None,
    source_slug: Optional[str] = None,
    source_type: Optional[str] = None,
    query: Optional[str] = None,
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
        category_slugs=category_slugs,
        source_slug=source_slug,
        source_type=source_type,
        query=query,
    )

    if not articles:
        empty_title = (
            "No research papers found in this category yet."
            if source_type == "arxiv"
            else "No articles found in this category yet."
        )
        msg = (
            f"📭 *{empty_title}*\n\n"
            "Run `/collect` to fetch the latest scientific preprints and technical feeds right now!"
        )
        empty_markup = get_research_hub_keyboard() if source_type == "arxiv" else get_category_keyboard()
        await safe_edit_or_reply(
            update,
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=empty_markup,
        )
        return

    safe_offset = max(0, min(offset, len(articles) - 1))
    current_article = articles[safe_offset]

    # Check if article is bookmarked
    saved_articles = await news_service.get_saved_articles(user_id=user_id, limit=50)
    saved_ids = {a.id for a in saved_articles}
    is_saved = current_article.id in saved_ids
    is_paper = bool(
        current_article.source
        and (current_article.source.source_type == "arxiv" or "arxiv" in current_article.source.slug.lower())
    )

    nav_slug = category_slug
    if source_type == "arxiv":
        nav_slug = f"arxiv_{category_slug}" if category_slug and category_slug != "all" else "arxiv"
    elif not nav_slug and category_slugs:
        if "ethiopia-tech" in category_slugs or "ethiopia-affairs" in category_slugs:
            nav_slug = "ethiopia"
        elif "global-politics" in category_slugs or "tech-policy" in category_slugs:
            nav_slug = "politics"

    text = format_article_view(current_article, index=safe_offset, total=len(articles))
    reply_markup = get_article_keyboard(
        article_id=current_article.id,
        url=current_article.url,
        offset=safe_offset,
        total=len(articles),
        category_slug=nav_slug,
        is_saved=is_saved,
        title=current_article.title,
        is_paper=is_paper,
    )

    if is_edit:
        await safe_edit_or_reply(
            update,
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    elif update.effective_message:
        await update.effective_message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup, disable_web_page_preview=True
        )


SEARCH_PAGE_SIZE = 4


async def send_search_view(
    update: Update,
    query: str,
    page: int = 1,
    category: str = "all",
    sort_by: str = "relevance",
    source: str = "all",
    is_edit: bool = False,
) -> None:
    """Display paginated multi-domain search results for a keyword query."""
    clean_query = query.strip()
    if not clean_query:
        return

    user = update.effective_user
    user_id = user.id if user else None
    safe_page = max(1, page if page > 0 else 1)

    response = await search_service.search(
        query=clean_query,
        category=category,
        sort_by=sort_by,
        page=safe_page,
        page_size=SEARCH_PAGE_SIZE,
        user_id=user_id,
        source=source,
        news_service=news_service,
    )

    text = search_service.format_search_results_page(response)
    reply_markup = search_service.get_search_results_keyboard(
        query=clean_query,
        page=response.page,
        total_pages=response.total_pages,
        category=response.category,
        sort_by=response.sort_by,
        source=response.source,
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
    """Fetch latest arXiv research papers, with optional subcategory or topic search."""
    if context.args:
        raw_arg = " ".join(context.args).strip()
        cat_map = {
            "ai": "ai",
            "ml": "ai",
            "machine-learning": "ai",
            "robotics": "robotics",
            "cs": "computer-science",
            "computer-science": "computer-science",
            "systems": "computer-science",
            "physics": "physics",
        }
        if raw_arg.lower() in cat_map:
            await send_article_view(update, source_type="arxiv", category_slug=cat_map[raw_arg.lower()], offset=0)
            return
        await send_article_view(update, source_type="arxiv", query=raw_arg, offset=0)
        return

    await send_article_view(update, source_type="arxiv", offset=0)


@authorized_only
async def github_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch trending repositories on GitHub."""
    await send_article_view(update, source_type="github", offset=0)


@authorized_only
async def ethiopia_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch latest Ethiopia technology, startup, and current affairs developments."""
    await send_article_view(update, category_slugs=["ethiopia-tech", "ethiopia-affairs"], offset=0)


@authorized_only
async def politics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch worldwide politics, geopolitics, and tech policy developments."""
    await send_article_view(update, category_slugs=["global-politics", "tech-policy"], offset=0)


@authorized_only
async def sources_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display all configured intelligence sources and their active status."""
    sources = await news_service.get_sources_list()
    msg = format_sources_list(sources)
    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


@admin_only
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
    """Unified search across STEM news, research papers, scholarships, and academic resources."""
    if not context.args:
        text = (
            "🔍 *STEM RADAR — Unified Search Engine*\n\n"
            "Search across verified STEM news, arXiv research papers, global scholarships, "
            "accredited university admissions, and open educational courses.\n\n"
            "*Usage:* `/search <keyword>`\n\n"
            "*Examples:*\n"
            "• `/search quantum` — Quantum computing breakthroughs & papers\n"
            "• `/search robotics` — Robotics engineering & lab research\n"
            "• `/search scholarship` — Open funding awards & deadlines\n"
            "• `/search algorithms` — Free courses & academic materials\n\n"
            "Or tap a quick search topic below:"
        )
        markup = get_search_shortcuts_keyboard()
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return

    query = " ".join(context.args)
    await send_search_view(
        update, query=query, page=1, category="all", sort_by="relevance", source="all", is_edit=False
    )


@authorized_only
async def websearch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute live external web discovery across academic and web providers."""
    if not context.args:
        text = (
            "📡 *STEM RADAR — Live Web Discovery*\n\n"
            "Search across live external academic and web providers (Semantic Scholar, Brave, Google Search).\n\n"
            "*Usage:* `/websearch <topic or query>`\n\n"
            "*Examples:*\n"
            "• `/websearch reinforcement learning robotics`\n"
            "• `/websearch erasmus mundus scholarships 2026`\n"
            "• `/websearch neuromorphic computing breakthroughs`\n"
        )
        markup = get_back_home_keyboard(back_target="menu:search", home_target="menu:home")
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return

    query = " ".join(context.args)
    await send_search_view(
        update, query=query, page=1, category="all", sort_by="relevance", source="external", is_edit=False
    )


@authorized_only
async def search_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Synthesize grounded AI search overview across multiple sources with direct citations."""
    if not context.args:
        text = (
            "🧠 *STEM RADAR — AI Search Assistant*\n\n"
            "Synthesize multi-source research summaries, key findings, and discovery recommendations "
            "with verified source citations.\n\n"
            "*Usage:* `/search_ai <topic or query>`\n\n"
            "*Examples:*\n"
            "• `/search_ai solid state battery breakthroughs`\n"
            "• `/search_ai humanoid robotics manipulation benchmarks`\n"
            "• `/search_ai fully funded masters scholarships germany`\n"
        )
        markup = get_back_home_keyboard(back_target="menu:search", home_target="menu:home")
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return

    query = " ".join(context.args)
    summary = await search_service.ai_summarize_query(
        query=query,
        category="all",
        source="all",
        limit=5,
        news_service=news_service,
    )
    text = search_ai_assistant.format_search_ai_summary(summary)
    markup = search_ai_assistant.get_search_ai_summary_keyboard(summary, category="all", source="all")

    await safe_edit_or_reply(
        update,
        text,
        reply_markup=markup,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


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
    markup = get_concept_mode_keyboard(concept_name, current_mode=mode)

    if status_msg:
        await status_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
    elif update.effective_message:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)


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
        await safe_edit_or_reply(
            update,
            "Select a STEM domain to explore:",
            reply_markup=get_category_keyboard(),
        )
        return

    if data.startswith("cat:"):
        cat_slug = data.split(":", 1)[1]
        if cat_slug in ("ethiopia", "ethiopia-tech", "ethiopia-affairs"):
            await send_article_view(
                update, category_slugs=["ethiopia-tech", "ethiopia-affairs"], offset=0, is_edit=True
            )
            return
        if cat_slug in ("politics", "global-politics", "tech-policy"):
            await send_article_view(update, category_slugs=["global-politics", "tech-policy"], offset=0, is_edit=True)
            return
        await send_article_view(update, category_slug=cat_slug, offset=0, is_edit=True)
        return

    if data.startswith("arxiv_cat:"):
        subcat = data.split(":", 1)[1]
        if subcat in ("cs", "systems"):
            subcat = "computer-science"
        category = subcat if subcat != "all" else None
        await send_article_view(update, source_type="arxiv", category_slug=category, offset=0, is_edit=True)
        return

    if data.startswith("nav:"):
        parts = data.split(":")
        cat_slug = parts[1] if len(parts) > 1 else "all"
        offset = int(parts[2]) if len(parts) > 2 else 0
        if cat_slug == "arxiv":
            await send_article_view(update, source_type="arxiv", offset=offset, is_edit=True)
            return
        if cat_slug.startswith("arxiv_"):
            subcat = cat_slug.split("_", 1)[1]
            if subcat in ("cs", "systems"):
                subcat = "computer-science"
            await send_article_view(update, source_type="arxiv", category_slug=subcat, offset=offset, is_edit=True)
            return
        if cat_slug in ("ethiopia", "ethiopia-tech", "ethiopia-affairs"):
            await send_article_view(
                update, category_slugs=["ethiopia-tech", "ethiopia-affairs"], offset=offset, is_edit=True
            )
            return
        if cat_slug in ("politics", "global-politics", "tech-policy"):
            await send_article_view(
                update, category_slugs=["global-politics", "tech-policy"], offset=offset, is_edit=True
            )
            return
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
                msg_text = query.message.text or ""
                if "Scientific Research Paper Analysis" in msg_text:
                    new_markup = get_paper_analysis_keyboard(article.id, is_saved=is_now_saved)
                else:
                    is_paper = bool(
                        article.source
                        and (article.source.source_type == "arxiv" or "arxiv" in article.source.slug.lower())
                    )
                    nav_slug = "arxiv" if is_paper else (article.categories[0].slug if article.categories else None)
                    new_markup = get_article_keyboard(
                        article_id=article.id,
                        url=article.url,
                        offset=0,
                        total=1,
                        category_slug=nav_slug,
                        is_saved=is_now_saved,
                        title=article.title,
                        is_paper=is_paper,
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

    if data.startswith("ai_paper:"):
        article_id = int(data.split(":", 1)[1])
        article = await news_service.get_article_by_id(article_id)
        if article:
            user = update.effective_user
            user_id = user.id if user else 0
            saved = await news_service.get_saved_articles(user_id=user_id, limit=50)
            is_saved = article.id in {a.id for a in saved}
            analysis = await ai_service.analyze_research_paper(article)
            text = format_paper_analysis(analysis)
            markup = get_paper_analysis_keyboard(article.id, is_saved=is_saved)
            await safe_edit_or_reply(
                update,
                text,
                reply_markup=markup,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
        return

    if data.startswith("c_mode:"):
        parts = data.split(":")
        concept_name = parts[1]
        mode = parts[2]
        explanation = await ai_service.explain_concept(concept_name, mode=mode)
        text = format_concept_explanation(explanation)
        markup = get_concept_mode_keyboard(concept_name, current_mode=mode)
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
            is_paper = bool(
                article.source and (article.source.source_type == "arxiv" or "arxiv" in article.source.slug.lower())
            )
            nav_slug = "arxiv" if is_paper else (article.categories[0].slug if article.categories else None)
            text = format_article_view(article, index=0, total=1)
            markup = get_article_keyboard(
                article_id=article.id,
                url=article.url,
                offset=0,
                total=1,
                category_slug=nav_slug,
                is_saved=is_saved,
                title=article.title,
                is_paper=is_paper,
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
        await send_search_view(update, query=query_kw, page=page + 1, category="all", is_edit=True)
        return

    if data.startswith("search:src:"):
        parts = data.split(":", 5)
        src = parts[2] if len(parts) > 2 and parts[2] in ("all", "internal", "external") else "all"
        cat = parts[3] if len(parts) > 3 else "all"
        sort_by = parts[4] if len(parts) > 4 else "relevance"
        query_kw = parts[5] if len(parts) > 5 else ""
        await send_search_view(update, query=query_kw, page=1, category=cat, sort_by=sort_by, source=src, is_edit=True)
        return

    if data.startswith("search:page:"):
        parts = data.split(":", 6)
        page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
        cat = parts[3] if len(parts) > 3 else "all"
        sort_by = parts[4] if len(parts) > 4 else "relevance"
        if len(parts) > 6 or (len(parts) > 5 and parts[5] in ("all", "internal", "external")):
            src = parts[5] if parts[5] in ("all", "internal", "external") else "all"
            query_kw = parts[6] if len(parts) > 6 else ""
        else:
            src = "all"
            query_kw = parts[5] if len(parts) > 5 else ""
        await send_search_view(
            update, query=query_kw, page=page, category=cat, sort_by=sort_by, source=src, is_edit=True
        )
        return

    if data.startswith("search:cat:"):
        parts = data.split(":", 5)
        cat = parts[2] if len(parts) > 2 else "all"
        sort_by = parts[3] if len(parts) > 3 else "relevance"
        if len(parts) > 5:
            src = parts[4] if parts[4] in ("all", "internal", "external") else "all"
            query_kw = parts[5]
        else:
            src = "all"
            query_kw = parts[4] if len(parts) > 4 else ""
        await send_search_view(update, query=query_kw, page=1, category=cat, sort_by=sort_by, source=src, is_edit=True)
        return

    if data.startswith("search:sort:"):
        parts = data.split(":", 5)
        cat = parts[2] if len(parts) > 2 else "all"
        sort_by = parts[3] if len(parts) > 3 else "relevance"
        if len(parts) > 5:
            src = parts[4] if parts[4] in ("all", "internal", "external") else "all"
            query_kw = parts[5]
        else:
            src = "all"
            query_kw = parts[4] if len(parts) > 4 else ""
        await send_search_view(update, query=query_kw, page=1, category=cat, sort_by=sort_by, source=src, is_edit=True)
        return

    if data.startswith("search:ai_sum:"):
        parts = data.split(":", 4)
        cat = parts[2] if len(parts) > 2 else "all"
        src = parts[3] if len(parts) > 3 else "all"
        query_kw = parts[4] if len(parts) > 4 else ""

        summary = await search_service.ai_summarize_query(
            query=query_kw,
            category=cat,
            source=src,
            limit=5,
            news_service=news_service,
        )
        text = search_ai_assistant.format_search_ai_summary(summary)
        markup = search_ai_assistant.get_search_ai_summary_keyboard(summary, category=cat, source=src)
        await safe_edit_or_reply(
            update,
            text,
            reply_markup=markup,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        return

    if data.startswith("search:rel_q:"):
        question = data[len("search:rel_q:") :].strip()
        await send_search_view(
            update, query=question, page=1, category="all", sort_by="relevance", source="all", is_edit=True
        )
        return

    if data.startswith("search:back:"):
        parts = data.split(":", 4)
        cat = parts[2] if len(parts) > 2 else "all"
        src = parts[3] if len(parts) > 3 else "all"
        query_kw = parts[4] if len(parts) > 4 else ""
        await send_search_view(
            update, query=query_kw, page=1, category=cat, sort_by="relevance", source=src, is_edit=True
        )
        return

    if data == "search:noop":
        await query.answer()
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


@authorized_only
async def quick_ai_summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle direct deep-link commands like /ai_sum_42."""
    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text.strip()
    match = re.search(r"/ai_sum_(\d+)", text)
    if not match:
        return

    article_id = int(match.group(1))
    article = await news_service.get_article_by_id(article_id)
    if not article:
        await message.reply_text(
            "⚠️ *Article Not Found*\n\nThis article could not be retrieved from intelligence archives.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    is_paper = article.source and (article.source.source_type == "arxiv" or "arxiv" in article.source.slug.lower())
    if is_paper:
        analysis = await ai_service.analyze_research_paper(article)
        out_text = format_paper_analysis(analysis)
    else:
        summary = await ai_service.summarize_news(article, mode="intermediate")
        out_text = format_news_summary(summary)

    await message.reply_text(out_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
