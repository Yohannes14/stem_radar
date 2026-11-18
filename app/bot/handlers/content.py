"""Handlers for AI intelligence, content opportunities, and trending digests."""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.filters.auth import authorized_only
from app.bot.ui.design_system import sanitize_markdown
from app.bot.ui.formatters import chunk_message, format_trending_feed
from app.processors.ranking import ranker
from app.services.content_service import content_service
from app.services.news_service import NewsService

logger = logging.getLogger(__name__)
news_service = NewsService()


@authorized_only
async def ideas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate structured STEM educational content opportunities from recent intelligence."""
    articles = await news_service.get_recent_news(limit=1, offset=0)
    if not articles:
        msg = "No articles are available yet. Run `/collect` to fetch recent updates."
        if update.effective_message:
            await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        return

    article = articles[0]
    opportunity = content_service.generate_opportunity(article)

    slides_text = "\n".join(f"- {sanitize_markdown(s)}" for s in opportunity.carousel_slides)
    vocab_text = ", ".join(sanitize_markdown(v) for v in opportunity.vocabulary)

    msg = (
        f"*STEM Content Opportunity*\n\n"
        f"Topic: {sanitize_markdown(opportunity.article_title)}\n"
        f"Level: {sanitize_markdown(opportunity.difficulty_level)}\n\n"
        f"*News Discovery*\n{sanitize_markdown(opportunity.news_discovery)}\n\n"
        f"*Technical Explanation*\n{sanitize_markdown(opportunity.technical_explanation)}\n\n"
        f"*Educational Value*\n{sanitize_markdown(opportunity.educational_value)}\n\n"
        f"*Technical Vocabulary*\n{vocab_text}\n\n"
        f"*Carousel Outline (5 Slides)*\n{slides_text}\n\n"
        f"*Short Video Script*\n```text\n{opportunity.video_script}\n```\n\n"
        f"*Post Template*\n```markdown\n{opportunity.linkedin_post}\n```\n\n"
        f"[Original source]({opportunity.url})"
    )

    if update.effective_message:
        for chunk in chunk_message(msg, max_length=4000):
            await update.effective_message.reply_text(
                chunk, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
            )


@authorized_only
async def trending_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display high-impact trending technology intelligence scored by the ranking engine."""
    articles = await news_service.get_recent_news(limit=15, offset=0)
    if not articles:
        msg = "No articles are available yet. Run `/collect` to fetch recent updates."
        if update.effective_message:
            await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        return

    scored_articles = []
    for a in articles:
        cats = [(c.slug, 1.0) for c in a.categories]
        score = ranker.calculate_score(
            title=a.title,
            description=a.description,
            published_at=a.published_at,
            categories=cats,
        )
        scored_articles.append((a, score))

    scored_articles.sort(key=lambda x: x[1], reverse=True)
    text = format_trending_feed(scored_articles[:5])

    if update.effective_message:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


@authorized_only
async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a daily technology intelligence brief."""
    articles = await news_service.get_recent_news(limit=5, offset=0)
    if not articles:
        msg = "No articles are available yet. Run `/collect` to fetch recent updates."
        if update.effective_message:
            await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        return

    lines = ["*Daily Technology Digest*\n"]
    for i, a in enumerate(articles, 1):
        source = sanitize_markdown(a.source.name if a.source else "Source")
        cats = ", ".join(sanitize_markdown(c.name) for c in a.categories) if a.categories else "Technology"
        lines.append(f"{i}. [{sanitize_markdown(a.title)}]({a.url})\n   {cats} · {source}\n")

    lines.append("Run `/ideas` to turn recent developments into educational content.")

    if update.effective_message:
        await update.effective_message.reply_text(
            "\n".join(lines), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )
