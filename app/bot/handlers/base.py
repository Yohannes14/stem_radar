"""Base bot commands: /start, /help, error handlers, and the unified 12-section Main Menu router."""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.filters.auth import authorized_only
from app.bot.handlers.news import send_article_view, send_search_view
from app.bot.handlers.settings import settings_command
from app.bot.handlers.student_hub import scholarships_command, student_hub_command
from app.bot.keyboards.inline import (
    get_projects_hub_keyboard,
    get_quiz_keyboard,
    get_tech_radar_keyboard,
)
from app.bot.keyboards.navigation import get_back_home_keyboard
from app.bot.ui.formatters import (
    format_impact_analysis,
    format_news_summary,
    format_project_recommendation,
    format_quiz_question,
    format_stem_content,
    format_tech_radar,
    format_trending_feed,
)
from app.bot.ui.menu import (
    format_ai_hub_intro,
    format_learn_hub_intro,
    format_main_menu,
    format_search_intro,
    get_ai_hub_keyboard,
    get_interests_keyboard,
    get_learn_hub_keyboard,
    get_main_menu_keyboard,
    get_search_shortcuts_keyboard,
    is_duplicate_callback,
    safe_edit_or_reply,
)
from app.database.database import get_session_factory
from app.database.repository import Repository
from app.services.ai import ai_service
from app.services.automation_service import automation_service
from app.services.news_service import NewsService

logger = logging.getLogger(__name__)
news_service = NewsService()


@authorized_only
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message and render the flagship 12-section interactive dashboard."""
    user = update.effective_user
    name = user.first_name if user else "Researcher"

    stats = None
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            repo = Repository(session)
            stats = await repo.get_platform_stats(user_id=user.id if user else None)
    except Exception as exc:
        logger.debug("Telemetry stats unavailable on /start: %s", exc)

    welcome_text = format_main_menu(user_name=name, stats=stats)

    if update.effective_message:
        await update.effective_message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu_keyboard(),
            disable_web_page_preview=True,
        )


@authorized_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display comprehensive command catalog with persistent main menu navigation."""
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
        "• `/ethiopia` — Ethiopia Tech, Innovation & Current Affairs\n"
        "• `/politics` — Worldwide Politics & Geopolitics\n"
        "• `/science` — Physics, Chemistry & Biotechnology\n"
        "• `/engineering` — Electronics & Embedded Systems\n"
        "• `/programming` — Software Engineering & CS\n"
        "• `/research` — Latest arXiv research papers\n"
        "• `/github` — Trending GitHub repositories\n\n"
        "*Search & Personalization:*\n"
        "• `/briefing` — Executive daily STEM intelligence briefing\n"
        "• `/radar` — Interactive STEM Technology Radar (Adopt/Trial/Assess/Hold)\n"
        "• `/watchlist` — Keyword & technology real-time alerts\n"
        "• `/trends` — SOTA breakthrough scoring & impact ranking\n"
        "• `/stats` — Platform telemetry & intelligence metrics\n"
        "• `/search <keyword>` — Search collected articles\n"
        "• `/saved` — View bookmarked articles\n"
        "• `/settings` — Notification preferences & quiet hours\n\n"
        "*STEM Learning Academy:*\n"
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
        "• `/digest` — Daily intelligence summary\n\n"
        "*User & Privacy:*\n"
        "• `/feedback <text>` — Submit suggestions or report issues\n"
        "• `/privacy` — View privacy policy & data rights\n"
        "• `/export` — Export a copy of your stored personal data\n"
        "• `/delete_account` — Permanently purge your stored profile data"
    )

    markup = get_back_home_keyboard(back_target="menu:home", home_target="menu:home")

    query = update.callback_query
    if query and query.message:
        await safe_edit_or_reply(update, help_text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
    elif update.effective_message:
        await update.effective_message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup,
            disable_web_page_preview=True,
        )


@authorized_only
async def main_menu_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Central router handling 12-section main menu clicks, navigation, and sub-views."""
    query = update.callback_query
    if not query or not query.data:
        return

    user = update.effective_user
    user_id = user.id if user else 0
    data = query.data

    # Debounce rapid clicks
    if is_duplicate_callback(user_id, data):
        await query.answer("⏳ Processing, please wait...", show_alert=False)
        return

    await query.answer()

    # 1. Home / Main Menu Dashboard
    if data in ("menu:home", "nav:home"):
        stats = None
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                repo = Repository(session)
                stats = await repo.get_platform_stats(user_id=user_id)
        except Exception:
            pass
        welcome_text = format_main_menu(user_name=user.first_name if user else "Researcher", stats=stats)
        await safe_edit_or_reply(
            update, welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.MARKDOWN
        )
        return

    # 2. Latest News
    if data == "menu:news":
        await send_article_view(update, category_slug="all", offset=0, is_edit=True)
        return

    # Student Hub & Scholarships
    if data == "menu:student_hub":
        await student_hub_command(update, context)
        return

    if data == "menu:scholarships":
        await scholarships_command(update, context)
        return

    # Ethiopia Radar
    if data == "menu:ethiopia":
        await send_article_view(update, category_slugs=["ethiopia-tech", "ethiopia-affairs"], offset=0, is_edit=True)
        return

    # World & Politics
    if data == "menu:politics":
        await send_article_view(update, category_slugs=["global-politics", "tech-policy"], offset=0, is_edit=True)
        return

    # 3. Trending Technology
    if data == "menu:trending":
        scored = await automation_service.get_trending_developments(limit=5)
        if not scored:
            text = (
                "📈 *High-Impact Trending STEM Breakthroughs*\n\n"
                "No ranked articles available yet. Run `/collect` to fetch and analyze fresh developments!"
            )
        else:
            text = format_trending_feed(scored)
        await safe_edit_or_reply(
            update,
            text,
            reply_markup=get_back_home_keyboard(back_target="menu:home", home_target="menu:home"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # 4. AI Intelligence Hub
    if data == "menu:ai":
        await safe_edit_or_reply(
            update,
            format_ai_hub_intro(),
            reply_markup=get_ai_hub_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # 5. Research Papers (arXiv)
    if data == "menu:research":
        await send_article_view(update, source_type="arxiv", offset=0, is_edit=True)
        return

    # 6. Learn STEM Hub
    if data == "menu:learn":
        await safe_edit_or_reply(
            update,
            format_learn_hub_intro(),
            reply_markup=get_learn_hub_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # 7. Project Ideas Hub
    if data == "menu:projects":
        text = (
            "💡 *STEM Portfolio Project Generator*\n\n"
            "Build practical, production-ready engineering systems that prove your technical depth.\n\n"
            "Select an engineering discipline below to generate a tailored project architecture, "
            "tech stack, required skills, and portfolio milestones:\n\n"
            "Or type `/project <topic>` for any custom discipline (e.g. `/project Autonomous Drone`)."
        )
        await safe_edit_or_reply(
            update,
            text,
            reply_markup=get_projects_hub_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Project Idea Topic Generation
    if data.startswith("prj_topic:"):
        topic = data.split(":", 1)[1]
        proj = await ai_service.recommend_project(topic)
        text = format_project_recommendation(proj)
        action_keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🔄 Another Idea", callback_data=f"prj_topic:{topic}"),
                    InlineKeyboardButton("🗂️ Other Domains", callback_data="menu:projects"),
                ],
                [
                    InlineKeyboardButton("🏠 Main Menu", callback_data="menu:home"),
                ],
            ]
        )
        await safe_edit_or_reply(
            update,
            text,
            reply_markup=action_keyboard,
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # 8. Technology Radar
    if data == "menu:radar":
        scored = await automation_service.get_trending_developments(limit=5)
        velocities = await automation_service.calculate_domain_velocity()
        text = format_tech_radar(horizon="all", scored_articles=scored, domain_velocities=velocities)
        await safe_edit_or_reply(
            update,
            text,
            reply_markup=get_tech_radar_keyboard(current_horizon="all"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Technology Radar Horizon Switcher
    if data.startswith("radar_h:"):
        horizon = data.split(":", 1)[1]
        if horizon == "refresh":
            horizon = "all"
        scored = await automation_service.get_trending_developments(limit=5)
        velocities = await automation_service.calculate_domain_velocity()
        text = format_tech_radar(horizon=horizon, scored_articles=scored, domain_velocities=velocities)
        await safe_edit_or_reply(
            update,
            text,
            reply_markup=get_tech_radar_keyboard(current_horizon=horizon),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # 9. Search Articles Hub
    if data == "menu:search":
        await safe_edit_or_reply(
            update,
            format_search_intro(),
            reply_markup=get_search_shortcuts_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # 10. Saved Items / Bookmarks
    if data == "menu:saved":
        session_factory = get_session_factory()
        async with session_factory() as session:
            repo = Repository(session)
            saved = await repo.get_saved_articles(user_id=user_id, limit=10)

        if not saved:
            text = (
                "⭐ *Your Saved Articles & Research*\n\n"
                "You haven't bookmarked any articles yet.\n\n"
                "Tap the *⭐ Bookmark* button on any article card to save it here for later!"
            )
        else:
            lines = ["⭐ *Your Saved Articles & Research Papers:*\n"]
            for idx, art in enumerate(saved, 1):
                source_name = art.source.name if art.source else "Tech"
                lines.append(f"{idx}. [{art.title}]({art.url})\n   Source: _{source_name}_\n")
            text = "\n".join(lines)

        await safe_edit_or_reply(
            update,
            text,
            reply_markup=get_back_home_keyboard(back_target="menu:home", home_target="menu:home"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # 11. My Interests / Subscribed Domains
    if data == "menu:interests":
        session_factory = get_session_factory()
        async with session_factory() as session:
            repo = Repository(session)
            pref = await repo.get_or_create_preference(user_id)
            active_slugs = [s.strip() for s in (pref.preferred_categories or "").split(",") if s.strip()]

        safe_subs = (pref.preferred_categories or "All Domains").replace("_", "-")
        text = (
            "🏷 *My STEM Domain Subscriptions*\n\n"
            "Select the disciplines you want prioritized in your briefings, digests, and recommendations.\n\n"
            f"Active Subscriptions: `{safe_subs}`\n\n"
            "Tap below to toggle active subscriptions:"
        )
        await safe_edit_or_reply(
            update,
            text,
            reply_markup=get_interests_keyboard(active_slugs),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # 12. Settings
    if data == "menu:settings":
        await settings_command(update, context)
        return

    # 13. Help & Guide
    if data == "menu:help":
        await help_command(update, context)
        return

    # --- Sub-views for AI Hub ---
    if data == "menu:ai_summarize":
        articles = await news_service.get_recent_news(limit=1)
        if not articles:
            text = "No articles found to summarize. Run `/collect` first!"
        else:
            summary = await ai_service.summarize_news(articles[0], mode="intermediate")
            text = format_news_summary(summary)
        await safe_edit_or_reply(
            update,
            text,
            reply_markup=get_back_home_keyboard(back_target="menu:ai", home_target="menu:home"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "menu:ai_explain":
        text = (
            "💡 *STEM AI Concept Explainer*\n\n"
            "To break down any scientific, engineering, or mathematical concept:\n\n"
            "Type: `/explain <concept>`\n\n"
            "*Examples:*\n"
            "• `/explain Transformer Architecture`\n"
            "• `/explain Quantum Entanglement`\n"
            "• `/explain Zero Knowledge Proofs`\n"
            "• `/explain Kalman Filters`"
        )
        await safe_edit_or_reply(
            update,
            text,
            reply_markup=get_back_home_keyboard(back_target="menu:ai", home_target="menu:home"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "menu:ai_impact":
        articles = await news_service.get_recent_news(limit=1)
        if not articles:
            text = "No articles found to analyze impact. Run `/collect` first!"
        else:
            impact = await ai_service.analyze_impact(articles[0])
            text = format_impact_analysis(impact)
        await safe_edit_or_reply(
            update,
            text,
            reply_markup=get_back_home_keyboard(back_target="menu:ai", home_target="menu:home"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "menu:ai_content":
        articles = await news_service.get_recent_news(limit=1)
        if not articles:
            text = "No articles found. Run `/collect` first!"
        else:
            pkg = await ai_service.generate_stem_content(articles[0])
            text = format_stem_content(pkg)[:4000]
        await safe_edit_or_reply(
            update,
            text,
            reply_markup=get_back_home_keyboard(back_target="menu:ai", home_target="menu:home"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # --- Sub-views for Learn Hub ---
    if data == "menu:roadmaps":
        text = (
            "🗺️ *STEM Engineering Roadmaps*\n\n"
            "Structured curricula taking you from fundamental theory to production implementations.\n\n"
            "Type `/roadmap <topic>` to generate a 4-phase curriculum:\n\n"
            "• `/roadmap Robotics`\n"
            "• `/roadmap Artificial Intelligence`\n"
            "• `/roadmap Quantum Computing`\n"
            "• `/roadmap Cybersecurity`"
        )
        await safe_edit_or_reply(
            update,
            text,
            reply_markup=get_back_home_keyboard(back_target="menu:learn", home_target="menu:home"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "menu:learn_quiz":
        topic = "Artificial Intelligence"
        quiz = await ai_service.generate_quiz(topic)
        text = format_quiz_question(quiz, question_index=0)
        markup = get_quiz_keyboard(topic, q_index=0, total_q=len(quiz.questions))
        await safe_edit_or_reply(
            update,
            text,
            reply_markup=markup,
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "menu:learn_compare":
        text = (
            "⚖️ *STEM Architectural Concept Comparison*\n\n"
            "Compare two competing frameworks, architectures, or protocols side-by-side.\n\n"
            "Use the `/compare` command with any two technologies:\n\n"
            "• `/compare PyTorch vs JAX`\n"
            "• `/compare REST vs gRPC`\n"
            "• `/compare Monolith vs Microservices`\n"
            "• `/compare Transformer vs Mamba`\n"
            "• `/compare Kafka vs RabbitMQ`"
        )
        await safe_edit_or_reply(
            update,
            text,
            reply_markup=get_back_home_keyboard(back_target="menu:learn", home_target="menu:home"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "menu:progress":
        session_factory = get_session_factory()
        async with session_factory() as session:
            repo = Repository(session)
            history = await repo.get_user_learning_history(user_id=user_id)

        if not history:
            text = (
                "🏆 *Your Learning Progress*\n\n"
                "You haven't completed any lessons or quizzes yet.\n\n"
                "Explore the Academy via `/learn` or `/quiz` to begin tracking your mastery!"
            )
        else:
            lines = ["🏆 *Your STEM Mastery Track:*\n"]
            for item in history:
                pct = int((item.quiz_score_total / item.quiz_score_max * 100)) if item.quiz_score_max > 0 else 0
                lines.append(
                    f"• *{item.topic.title()}* (`{item.level.capitalize()}`)\n"
                    f"  Lessons: `{item.lessons_completed}` | Quizzes: `{item.quizzes_taken}` (Score: `{pct}%`)\n"
                )
            text = "\n".join(lines)

        await safe_edit_or_reply(
            update,
            text,
            reply_markup=get_back_home_keyboard(back_target="menu:learn", home_target="menu:home"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # --- Search Shortcut Callbacks (search_kw:<keyword>) ---
    if data.startswith("search_kw:"):
        keyword = data.split(":", 1)[1]
        await send_search_view(update, query=keyword, page=1, category="all", is_edit=True)
        return


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log exceptions encountered during update handling."""
    logger.error("Exception while handling Telegram update: %s", context.error, exc_info=context.error)
