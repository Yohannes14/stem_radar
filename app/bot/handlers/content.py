"""Handlers for AI intelligence, content opportunities, and trending digests."""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.filters.auth import authorized_only
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
        msg = "📭 No articles found. Run `/collect` first to ingest fresh intelligence."
        if update.effective_message:
            await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        return

    article = articles[0]
    opportunity = content_service.generate_opportunity(article)

    slides_text = "\n".join([f"• {s}" for s in opportunity.carousel_slides])
    vocab_text = ", ".join([f"`{v}`" for v in opportunity.vocabulary])

    msg = (
        f"💡 *STEM Content Opportunity Finder*\n\n"
        f"📌 *Topic:* {opportunity.article_title}\n"
        f"📊 *Level:* `{opportunity.difficulty_level}`\n\n"
        f"1️⃣ *NEWS DISCOVERY*\n{opportunity.news_discovery}\n\n"
        f"2️⃣ *TECHNICAL EXPLANATION*\n{opportunity.technical_explanation}\n\n"
        f"3️⃣ *EDUCATIONAL VALUE*\n{opportunity.educational_value}\n\n"
        f"4️⃣ *TECHNICAL VOCABULARY*\n{vocab_text}\n\n"
        f"5️⃣ *CAROUSEL OUTLINE (5 Slides)*\n{slides_text}\n\n"
        f"6️⃣ *SHORT VIDEO SCRIPT*\n```text\n{opportunity.video_script}\n```\n\n"
        f"7️⃣ *LINKEDIN POST TEMPLATE*\n```markdown\n{opportunity.linkedin_post}\n```\n\n"
        f"🔗 [Original Source]({opportunity.url})"
    )

    if update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


@authorized_only
async def trending_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display high-impact trending technology intelligence scored by the ranking engine."""
    articles = await news_service.get_recent_news(limit=15, offset=0)
    if not articles:
        msg = "📭 No articles found. Run `/collect` to fetch updates."
        if update.effective_message:
            await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        return

    # Score articles with the ranking engine
    scored_articles = []
    for a in articles:
        cats = [(c.slug, 1.0) for c in a.categories]
        score = ranker.calculate_score(
            title=a.title,
            description=a.description,
            published_at=a.published_at,
            categories=cats,
        )
        scored_articles.append((score, a))

    scored_articles.sort(key=lambda x: x[0], reverse=True)
    top_items = scored_articles[:5]

    lines = ["🔥 *Trending STEM Intelligence (High-Impact Signals):*\n"]
    for i, (score, a) in enumerate(top_items, 1):
        source = a.source.name if a.source else "Tech"
        lines.append(f"{i}. [{a.title}]({a.url})\n   Impact Score: `{score}/100` | _{source}_\n")

    if update.effective_message:
        await update.effective_message.reply_text(
            "\n".join(lines), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )


@authorized_only
async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a daily technology intelligence brief."""
    articles = await news_service.get_recent_news(limit=5, offset=0)
    if not articles:
        msg = "📭 No intelligence available for digest. Run `/collect` first."
        if update.effective_message:
            await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        return

    lines = ["📡 *STEM RADAR Daily Intelligence Digest*\n"]
    for i, a in enumerate(articles, 1):
        cat = a.categories[0].name if a.categories else "STEM"
        lines.append(f"{i}. *[{cat}]* [{a.title}]({a.url})")

    lines.append("\nUse `/ideas` to generate educational content opportunities from today's top story.")

    if update.effective_message:
        await update.effective_message.reply_text(
            "\n".join(lines), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )
