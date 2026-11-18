"""Base bot commands: /start, /help, error handlers, and the unified 12-section Main Menu router."""

import logging
import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.filters.auth import authorized_only
from app.bot.handlers.automation import (
    briefing_command,
    velocity_command,
    watchlist_command,
)
from app.bot.handlers.news import send_article_view, send_search_view
from app.bot.handlers.settings import settings_command
from app.bot.handlers.student_hub import (
    courses_command,
    deadlines_command,
    scholarships_command,
    student_hub_command,
    submit_opportunity_command,
    universities_command,
)
from app.bot.handlers.user_management import export_command, feedback_command, privacy_command
from app.bot.keyboards.inline import (
    get_project_card_keyboard,
    get_projects_hub_keyboard,
    get_quiz_keyboard,
    get_tech_radar_keyboard,
)
from app.bot.keyboards.navigation import get_back_home_keyboard
from app.bot.ui.design_system import format_error_state, sanitize_markdown
from app.bot.ui.formatters import (
    chunk_message,
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
    format_discover_hub_intro,
    format_learn_hub_intro,
    format_main_menu,
    format_myspace_intro,
    format_onboarding_goals,
    format_onboarding_interests,
    format_onboarding_welcome,
    format_projects_hub_intro,
    format_research_hub_intro,
    format_search_intro,
    format_stem_tech_hub_intro,
    get_ai_hub_keyboard,
    get_discover_hub_keyboard,
    get_interests_keyboard,
    get_learn_hub_keyboard,
    get_main_menu_keyboard,
    get_myspace_keyboard,
    get_onboarding_goals_keyboard,
    get_onboarding_interests_keyboard,
    get_onboarding_welcome_keyboard,
    get_research_hub_keyboard,
    get_search_shortcuts_keyboard,
    get_stem_tech_hub_keyboard,
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
    """Send welcome message and render either the onboarding flow or flagship 8-hub dashboard."""
    user = update.effective_user
    name = user.first_name if user else "Researcher"
    user_id = user.id if user else 0

    # Check for onboarding request or first-time user status
    args = getattr(context, "args", None)
    explicit_onboard = bool(
        args and isinstance(args, (list, tuple)) and len(args) > 0 and str(args[0]).lower() in ("onboard", "welcome")
    )

    show_onboarding = explicit_onboard
    stats = None

    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            repo = Repository(session)
            stats = await repo.get_platform_stats(user_id=user_id if user_id else None)
            if not explicit_onboard and user_id:
                # Check session new-registration flag set by auth layer
                is_new_registration = bool(
                    hasattr(context, "user_data")
                    and isinstance(context.user_data, dict)
                    and context.user_data.get("is_new_registration", False)
                )
                if is_new_registration:
                    show_onboarding = True
    except Exception as exc:
        logger.debug("Telemetry/preference check on /start fallback: %s", exc)

    if show_onboarding:
        welcome_text = format_onboarding_welcome(user_name=name)
        keyboard = get_onboarding_welcome_keyboard()
    else:
        welcome_text = format_main_menu(user_name=name, stats=stats)
        keyboard = get_main_menu_keyboard()

    if update.effective_message:
        await update.effective_message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )


@authorized_only
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explicitly render the flagship 8-hub interactive main menu dashboard."""
    user = update.effective_user
    name = user.first_name if user else "Researcher"
    user_id = user.id if user else 0

    stats = None
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            repo = Repository(session)
            stats = await repo.get_platform_stats(user_id=user_id if user_id else None)
    except Exception as exc:
        logger.debug("Telemetry stats unavailable on /menu: %s", exc)

    welcome_text = format_main_menu(user_name=name, stats=stats)
    markup = get_main_menu_keyboard()

    query = update.callback_query
    if query and query.message:
        await safe_edit_or_reply(update, welcome_text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
    elif update.effective_message:
        await update.effective_message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup,
            disable_web_page_preview=True,
        )


@authorized_only
async def discover_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open the Discover Hub (Briefing, Trends, Radar, Velocity)."""
    text = format_discover_hub_intro()
    markup = get_discover_hub_keyboard()
    query = update.callback_query
    if query and query.message:
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
    elif update.effective_message:
        await update.effective_message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup,
            disable_web_page_preview=True,
        )


@authorized_only
async def stem_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explore the 12 foundational STEM disciplines and regional tags."""
    text = format_stem_tech_hub_intro()
    markup = get_stem_tech_hub_keyboard()
    query = update.callback_query
    if query and query.message:
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
    elif update.effective_message:
        await update.effective_message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup,
            disable_web_page_preview=True,
        )


@authorized_only
async def myspace_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open the My Space personal control center (Bookmarks, Topics, Settings)."""
    user = update.effective_user
    name = user.first_name if user else "Researcher"
    user_id = user.id if user else 0

    stats = None
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            repo = Repository(session)
            stats = await repo.get_platform_stats(user_id=user_id if user_id else None)
    except Exception as exc:
        logger.debug("Telemetry stats unavailable on /myspace: %s", exc)

    text = format_myspace_intro(user_name=name, stats=stats)
    markup = get_myspace_keyboard()
    query = update.callback_query
    if query and query.message:
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
    elif update.effective_message:
        await update.effective_message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup,
            disable_web_page_preview=True,
        )


@authorized_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display command reference with Home navigation."""
    help_text = (
        "*STEM RADAR — Command Reference*\n\n"
        "*Main Sections*\n"
        "- `/menu` — Open main menu\n"
        "- `/discover` — Daily briefing, trending, radar, and velocity\n"
        "- `/stem` — Browse 12 STEM disciplines\n"
        "- `/research` — arXiv papers and paper summaries\n"
        "- `/student` — Scholarships, universities, and courses\n"
        "- `/learn` — Lessons, roadmaps, and quizzes\n"
        "- `/search` — Search database and live web\n"
        "- `/myspace` — Saved items, watchlist, and settings\n\n"
        "*News & Research*\n"
        "- `/news`, `/ai`, `/robotics`, `/science`, `/engineering`, `/programming`, `/github`\n"
        "- `/ethiopia`, `/politics` — Regional and policy coverage\n"
        "- `/trending`, `/briefing`, `/radar`, `/velocity`, `/sources`, `/collect`\n\n"
        "*Student Hub*\n"
        "- `/scholarships` — Verified STEM scholarships\n"
        "- `/deadlines` — Upcoming application deadlines\n"
        "- `/universities` — University admission profiles\n"
        "- `/courses` — Free courses and study materials\n"
        "- `/submit_opportunity` — Submit an opportunity for review\n\n"
        "*Search & Analysis*\n"
        "- `/search <query>` — Search indexed records\n"
        "- `/websearch <query>` — Search live web and academic sources\n"
        "- `/search_ai <topic>` — Cited multi-source summary\n"
        "- `/explain <concept>` — Beginner, intermediate, or advanced explanation\n"
        "- `/impact`, `/ideas`, `/digest`\n\n"
        "*Learning & Projects*\n"
        "- `/learn <topic>`, `/roadmap <topic>`, `/quiz <topic>`\n"
        "- `/compare <A> vs <B>`, `/project <topic>`, `/vocabulary <topic>`, `/progress`\n\n"
        "*Personal & Privacy*\n"
        "- `/saved`, `/interests`, `/watchlist`, `/settings`, `/stats`\n"
        "- `/feedback <text>`, `/privacy`, `/export`, `/delete_account`"
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
        await query.answer("Please wait a moment.", show_alert=False)
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

    # Onboarding Navigation & Interaction
    if data == "onboard:interests":
        active_slugs = []
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                repo = Repository(session)
                pref = await repo.get_or_create_preference(user_id)
                active_slugs = [s.strip() for s in (pref.preferred_categories or "").split(",") if s.strip()]
        except Exception as exc:
            logger.debug("Could not fetch user preferences for onboarding: %s", exc)
        await safe_edit_or_reply(
            update,
            format_onboarding_interests(),
            reply_markup=get_onboarding_interests_keyboard(active_slugs),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data.startswith("onboard:toggle:"):
        slug = data.split(":", 2)[2]
        active_slugs = []
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                repo = Repository(session)
                active_slugs, _ = await repo.toggle_user_interest_category(user_id, slug)
        except Exception as exc:
            logger.debug("Could not toggle interest category: %s", exc)
        await safe_edit_or_reply(
            update,
            format_onboarding_interests(),
            reply_markup=get_onboarding_interests_keyboard(active_slugs),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "onboard:goals":
        await safe_edit_or_reply(
            update,
            format_onboarding_goals(),
            reply_markup=get_onboarding_goals_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data.startswith("onboard:track:"):
        track = data.split(":", 2)[2]
        if hasattr(context, "user_data") and isinstance(context.user_data, dict):
            context.user_data["onboarded"] = True
            context.user_data["track"] = track
            context.user_data.pop("is_new_registration", None)
        await query.answer(f"Focus set to {track.title()}.", show_alert=False)
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

    if data == "onboard:skip":
        if hasattr(context, "user_data") and isinstance(context.user_data, dict):
            context.user_data["onboarded"] = True
            context.user_data.pop("is_new_registration", None)
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

    # Flagship 8-Hub Section Handlers
    if data == "menu:discover":
        await safe_edit_or_reply(
            update,
            format_discover_hub_intro(),
            reply_markup=get_discover_hub_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "menu:stem_tech":
        await safe_edit_or_reply(
            update,
            format_stem_tech_hub_intro(),
            reply_markup=get_stem_tech_hub_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "menu:research":
        await safe_edit_or_reply(
            update,
            format_research_hub_intro(),
            reply_markup=get_research_hub_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "menu:arxiv_papers":
        await send_article_view(update, source_type="arxiv", offset=0, is_edit=True)
        return

    if data.startswith("arxiv_cat:"):
        subcat = data.split(":", 1)[1]
        if subcat in ("cs", "systems"):
            subcat = "computer-science"
        category = subcat if subcat != "all" else None
        await send_article_view(update, source_type="arxiv", category_slug=category, offset=0, is_edit=True)
        return

    if data == "menu:myspace":
        stats = None
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                repo = Repository(session)
                stats = await repo.get_platform_stats(user_id=user_id)
        except Exception:
            pass
        await safe_edit_or_reply(
            update,
            format_myspace_intro(user_name=user.first_name if user else "Researcher", stats=stats),
            reply_markup=get_myspace_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "menu:briefing":
        await briefing_command(update, context)
        return

    if data == "menu:velocity":
        await velocity_command(update, context)
        return

    if data == "menu:watchlist":
        await watchlist_command(update, context)
        return

    if data == "menu:privacy":
        await privacy_command(update, context)
        return

    if data == "menu:feedback":
        await feedback_command(update, context)
        return

    if data == "menu:export":
        await export_command(update, context)
        return

    # 2. Latest News
    if data == "menu:news":
        await send_article_view(update, category_slug="all", offset=0, is_edit=True)
        return

    # Student Hub & Academic Resources
    if data == "menu:student_hub":
        await student_hub_command(update, context)
        return

    if data == "menu:scholarships":
        await scholarships_command(update, context)
        return

    if data in ("menu:universities", "menu:admissions"):
        await universities_command(update, context)
        return

    if data in ("menu:courses", "menu:study_materials", "menu:academic_resources"):
        await courses_command(update, context)
        return

    if data in ("menu:deadlines", "menu:scholarship_deadlines"):
        await deadlines_command(update, context)
        return

    if data in ("menu:submit_opportunity", "menu:submit"):
        await submit_opportunity_command(update, context)
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
            text = "*Trending*\n\nNo ranked articles are available yet. Run `/collect` to fetch recent articles."
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
        await safe_edit_or_reply(
            update,
            format_projects_hub_intro(),
            reply_markup=get_projects_hub_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Project Idea Topic Generation
    if data.startswith("prj_topic:"):
        topic = data.split(":", 1)[1]
        proj = await ai_service.recommend_project(topic, difficulty="intermediate")
        text = format_project_recommendation(proj)
        chunks = chunk_message(text, max_length=4000)
        action_keyboard = get_project_card_keyboard(topic, difficulty="intermediate")
        await safe_edit_or_reply(
            update,
            chunks[0],
            reply_markup=action_keyboard,
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Project Generation with Difficulty Switcher
    if data.startswith("prj_gen:"):
        parts = data.split(":")
        topic = parts[1]
        diff = parts[2] if len(parts) > 2 else "intermediate"
        proj = await ai_service.recommend_project(topic, difficulty=diff)
        text = format_project_recommendation(proj)
        chunks = chunk_message(text, max_length=4000)
        action_keyboard = get_project_card_keyboard(topic, difficulty=diff)
        await safe_edit_or_reply(
            update,
            chunks[0],
            reply_markup=action_keyboard,
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Project Level Selector View
    if data.startswith("prj_diff:"):
        level = data.split(":", 1)[1]
        if level == "beginner":
            intro = (
                "*Beginner Projects*\n\n"
                "Foundational engineering projects with clear architecture and no paid hardware required.\n\n"
                "Select a project below, or run `/project beginner <topic>`:"
            )
            buttons = [
                [
                    InlineKeyboardButton(
                        "Image Classifier (FastAPI)", callback_data="prj_gen:Vision Classifier:beginner"
                    ),
                    InlineKeyboardButton("2-DOF Arm Simulator", callback_data="prj_gen:2-DOF Robotic Arm:beginner"),
                ],
                [
                    InlineKeyboardButton("ESP32 Telemetry Hub", callback_data="prj_gen:ESP32 Telemetry Hub:beginner"),
                    InlineKeyboardButton(
                        "Async Key-Value Cache", callback_data="prj_gen:In-Memory Key-Value Store:beginner"
                    ),
                ],
                [
                    InlineKeyboardButton("Back", callback_data="menu:projects"),
                    InlineKeyboardButton("Home", callback_data="menu:home"),
                ],
            ]
        elif level == "advanced":
            intro = (
                "*Advanced Projects*\n\n"
                "Systems focusing on distributed consensus, simulation, real-time control, "
                "and high-concurrency engineering.\n\n"
                "Select a project below, or run `/project advanced <topic>`:"
            )
            buttons = [
                [
                    InlineKeyboardButton(
                        "Quantum Error Mitigation",
                        callback_data="prj_gen:Quantum Circuit Error Mitigation:advanced",
                    ),
                    InlineKeyboardButton(
                        "Quadruped MPC Controller", callback_data="prj_gen:Quadruped MPC Controller:advanced"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "Distributed Raft Consensus", callback_data="prj_gen:Raft Distributed Consensus:advanced"
                    ),
                    InlineKeyboardButton("ZK Proof Verifier", callback_data="prj_gen:ZK Proof Verifier:advanced"),
                ],
                [
                    InlineKeyboardButton("Back", callback_data="menu:projects"),
                    InlineKeyboardButton("Home", callback_data="menu:home"),
                ],
            ]
        else:
            intro = (
                "*Intermediate Projects*\n\n"
                "Practical architectures, asynchronous pipelines, and real-world system integrations.\n\n"
                "Select a project below, or run `/project intermediate <topic>`:"
            )
            buttons = [
                [
                    InlineKeyboardButton("Hybrid RAG Engine", callback_data="prj_gen:Hybrid RAG Engine:intermediate"),
                    InlineKeyboardButton(
                        "ROS 2 Navigation Robot", callback_data="prj_gen:ROS 2 Nav Robot:intermediate"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "Network Intrusion Detector", callback_data="prj_gen:Intrusion Detection System:intermediate"
                    ),
                    InlineKeyboardButton(
                        "CAN Bus Telemetry Logger", callback_data="prj_gen:CAN Bus Logger:intermediate"
                    ),
                ],
                [
                    InlineKeyboardButton("Back", callback_data="menu:projects"),
                    InlineKeyboardButton("Home", callback_data="menu:home"),
                ],
            ]
        await safe_edit_or_reply(
            update,
            intro,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Random Project Generator
    if data == "prj_rand":
        random_topics = [
            "Autonomous Quadruped Robot",
            "Zero-Knowledge Rollup Engine",
            "Edge AI Embedded Computer Vision",
            "Satellite Ground Station SDR",
            "Bioinformatics Genomic Sequence Aligner",
            "High-Frequency Distributed Order Book",
            "Brain-Computer Interface Signal Processor",
            "Autonomous Drone Obstacle Avoidance",
        ]
        topic = random.choice(random_topics)
        proj = await ai_service.recommend_project(topic, difficulty="intermediate")
        text = format_project_recommendation(proj)
        chunks = chunk_message(text, max_length=4000)
        action_keyboard = get_project_card_keyboard(topic, difficulty="intermediate")
        await safe_edit_or_reply(
            update,
            chunks[0],
            reply_markup=action_keyboard,
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Portfolio Strategy Guide
    if data == "menu:portfolio_tips":
        text = (
            "*Engineering Portfolio Guide*\n\n"
            "How to turn technical projects into strong engineering credentials:\n\n"
            "1. *Depth over tutorial clones*\n"
            "Build systems with explicit architectural trade-offs, benchmarks, and clear failure handling.\n\n"
            "2. *Observable systems*\n"
            "Include architecture diagrams, automated tests, structured logging, "
            "and measured metrics (latency, throughput, memory).\n\n"
            "3. *Reproducible setup*\n"
            "Provide clear setup instructions, pinned dependencies, and automated CI checks.\n\n"
            "4. *Documented trade-offs*\n"
            "Explain why you chose specific tools, what failure modes exist, "
            "and what you would change at higher scale."
        )
        action_keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Browse Projects", callback_data="menu:projects"),
                    InlineKeyboardButton("Home", callback_data="menu:home"),
                ]
            ]
        )
        await safe_edit_or_reply(
            update,
            text,
            reply_markup=action_keyboard,
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Learn Hub Level Tracks
    if data.startswith("learn_lvl:"):
        level = data.split(":", 1)[1]
        if level == "beginner":
            intro = (
                "*Beginner Learning Path*\n\n"
                "Foundational lessons with clear mental models and minimal prerequisites.\n\n"
                "Select a topic:"
            )
            buttons = [
                [
                    InlineKeyboardButton("AI Foundations", callback_data="ed_learn:Artificial Intelligence"),
                    InlineKeyboardButton("Intro to Robotics", callback_data="ed_learn:Robotics"),
                ],
                [
                    InlineKeyboardButton("Computer Systems 101", callback_data="ed_learn:Computer Systems"),
                    InlineKeyboardButton("Circuits & Electronics", callback_data="ed_learn:Embedded Systems"),
                ],
                [
                    InlineKeyboardButton("Back", callback_data="menu:learn"),
                    InlineKeyboardButton("Home", callback_data="menu:home"),
                ],
            ]
        elif level == "advanced":
            intro = (
                "*Advanced Learning Path*\n\n"
                "Research-level topics covering control theory, hardware synthesis, and distributed algorithms.\n\n"
                "Select a topic:"
            )
            buttons = [
                [
                    InlineKeyboardButton("Diffusion & State Space", callback_data="ed_learn:Artificial Intelligence"),
                    InlineKeyboardButton("Non-Linear Control & MPC", callback_data="ed_learn:Robotics"),
                ],
                [
                    InlineKeyboardButton("Quantum Circuit Synthesis", callback_data="ed_learn:Quantum Computing"),
                    InlineKeyboardButton("Distributed Systems", callback_data="ed_learn:Software Architecture"),
                ],
                [
                    InlineKeyboardButton("Back", callback_data="menu:learn"),
                    InlineKeyboardButton("Home", callback_data="menu:home"),
                ],
            ]
        else:
            intro = (
                "*Intermediate Learning Path*\n\n"
                "Deepen architectural, mathematical, and algorithmic understanding with practical examples.\n\n"
                "Select a topic:"
            )
            buttons = [
                [
                    InlineKeyboardButton("Transformer Architectures", callback_data="ed_learn:Artificial Intelligence"),
                    InlineKeyboardButton("Kinematics & ROS 2", callback_data="ed_learn:Robotics"),
                ],
                [
                    InlineKeyboardButton("Distributed Systems", callback_data="ed_learn:Software Architecture"),
                    InlineKeyboardButton("Cryptography & Security", callback_data="ed_learn:Cybersecurity"),
                ],
                [
                    InlineKeyboardButton("Back", callback_data="menu:learn"),
                    InlineKeyboardButton("Home", callback_data="menu:home"),
                ],
            ]
        await safe_edit_or_reply(
            update,
            intro,
            reply_markup=InlineKeyboardMarkup(buttons),
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
                "*Saved Items*\n\n"
                "You have not saved any articles or papers yet.\n\n"
                "Select Save on any article card to keep it here."
            )
        else:
            lines = ["*Saved Items*\n"]
            for idx, art in enumerate(saved, 1):
                source_name = sanitize_markdown(art.source.name if art.source else "Source")
                clean_title = sanitize_markdown(art.title)
                lines.append(f"{idx}. [{clean_title}]({art.url})\n   Source: {source_name}\n")
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

        safe_subs = (pref.preferred_categories or "All domains").replace("_", "-")
        text = (
            "*Domain Subscriptions*\n\n"
            "Select the disciplines to prioritize in your briefings and feeds.\n\n"
            f"Active: {safe_subs}"
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
            text = "No articles are available to summarize yet. Run `/collect` to fetch recent updates."
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
            "*Concept Explainer*\n\n"
            "Use `/explain <concept>` to get a structured explanation.\n\n"
            "Examples:\n"
            "- `/explain Transformer Architecture`\n"
            "- `/explain Quantum Entanglement`\n"
            "- `/explain Zero Knowledge Proofs`\n"
            "- `/explain Kalman Filters`"
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
            text = "No articles are available to assess yet. Run `/collect` to fetch recent updates."
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
            text = "No articles are available yet. Run `/collect` to fetch recent updates."
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
            "*Learning Roadmaps*\n\n"
            "Generate a 4-phase study roadmap with `/roadmap <topic>`.\n\n"
            "Examples:\n"
            "- `/roadmap Robotics`\n"
            "- `/roadmap Artificial Intelligence`\n"
            "- `/roadmap Quantum Computing`\n"
            "- `/roadmap Cybersecurity`"
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
            "*Concept Comparison*\n\n"
            "Compare two technologies, frameworks, or protocols side by side using `/compare`.\n\n"
            "Examples:\n"
            "- `/compare PyTorch vs JAX`\n"
            "- `/compare REST vs gRPC`\n"
            "- `/compare Monolith vs Microservices`\n"
            "- `/compare Transformer vs Mamba`\n"
            "- `/compare Kafka vs RabbitMQ`"
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
                "*Learning Progress*\n\n"
                "You have not completed any lessons or quizzes yet.\n\n"
                "Use `/learn` or `/quiz` to start tracking progress."
            )
        else:
            lines = ["*Learning Progress*\n"]
            for item in history:
                pct = int((item.quiz_score_total / item.quiz_score_max * 100)) if item.quiz_score_max > 0 else 0
                lines.append(
                    f"- *{sanitize_markdown(item.topic.title())}* ({item.level.capitalize()})\n"
                    f"  Lessons: {item.lessons_completed} | Quizzes: {item.quizzes_taken} ({pct}%)\n"
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
    """Log exceptions and present a calm recovery message to the user."""
    logger.error("Exception while handling Telegram update: %s", context.error, exc_info=context.error)
    if isinstance(update, Update):
        try:
            err_text = format_error_state(
                message="Something went wrong while loading this content. Please try again.",
                action_hint="You can return to the main menu below.",
            )
            await safe_edit_or_reply(
                update,
                err_text,
                reply_markup=get_back_home_keyboard(back_target="", home_target="menu:home"),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            logger.debug("Unable to send fallback error message to user.")
