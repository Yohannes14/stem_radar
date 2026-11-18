"""Unified 8-Hub Main Menu dashboard, sub-menus, onboarding flows, and debounce controls."""

import logging
import re
import time
from typing import Dict, List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode

from app.bot.keyboards.navigation import nav_back_home_row
from app.bot.ui.design_system import format_empty_state as _ds_empty_state
from app.core.taxonomy import taxonomy

logger = logging.getLogger(__name__)

# In-memory callback deduplication cache: {f"{user_id}:{callback_data}": timestamp}
_RECENT_CALLBACKS: Dict[str, float] = {}
DEBOUNCE_WINDOW_SECONDS = 1.0


def is_duplicate_callback(user_id: int, callback_data: str) -> bool:
    """Check if a callback is a rapid duplicate submission within the debounce window."""
    now = time.time()
    key = f"{user_id}:{callback_data}"
    last_time = _RECENT_CALLBACKS.get(key, 0.0)

    if len(_RECENT_CALLBACKS) > 1000:
        expired = [k for k, t in _RECENT_CALLBACKS.items() if now - t > 10.0]
        for k in expired:
            _RECENT_CALLBACKS.pop(k, None)

    if now - last_time < DEBOUNCE_WINDOW_SECONDS:
        return True

    _RECENT_CALLBACKS[key] = now
    return False


async def safe_edit_or_reply(
    update: Update,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = ParseMode.MARKDOWN,
    disable_web_page_preview: bool = True,
) -> None:
    """Safely edit existing message text or fallback to sending a new message without crashing."""
    query = update.callback_query
    if query and query.message:
        try:
            await query.message.edit_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
            return
        except Exception as exc:
            err_str = str(exc).lower()
            if "message is not modified" in err_str or "query is too old" in err_str:
                return
            if "can't parse entities" in err_str and parse_mode is not None:
                try:
                    await query.message.edit_text(
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=None,
                        disable_web_page_preview=disable_web_page_preview,
                    )
                    return
                except Exception:
                    pass
            logger.debug("safe_edit_or_reply edit_text fallback: %s", exc)

    if update.effective_message:
        try:
            await update.effective_message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
        except Exception as exc:
            err_str = str(exc).lower()
            if "message is not modified" in err_str:
                return
            if "can't parse entities" in err_str and parse_mode is not None:
                try:
                    await update.effective_message.reply_text(
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=None,
                        disable_web_page_preview=disable_web_page_preview,
                    )
                    return
                except Exception as inner_exc:
                    logger.error("safe_edit_or_reply plain text reply failed: %s", inner_exc)
            logger.error("safe_edit_or_reply reply_text failed: %s", exc)


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Generate the 8-Hub interactive main menu dashboard."""
    buttons = [
        [
            InlineKeyboardButton("Discover", callback_data="menu:discover"),
            InlineKeyboardButton("STEM & Tech", callback_data="menu:stem_tech"),
        ],
        [
            InlineKeyboardButton("Research", callback_data="menu:research"),
            InlineKeyboardButton("Student Hub", callback_data="menu:student_hub"),
        ],
        [
            InlineKeyboardButton("Learn", callback_data="menu:learn"),
            InlineKeyboardButton("Projects", callback_data="menu:projects"),
        ],
        [
            InlineKeyboardButton("Search", callback_data="menu:search"),
            InlineKeyboardButton("My Space", callback_data="menu:myspace"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def get_legacy_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Legacy 16-button menu keyboard retained for backward-compatibility tests."""
    buttons = [
        [
            InlineKeyboardButton("Latest News", callback_data="menu:news"),
            InlineKeyboardButton("Trending", callback_data="menu:trending"),
        ],
        [
            InlineKeyboardButton("Student Hub", callback_data="menu:student_hub"),
            InlineKeyboardButton("Scholarships", callback_data="menu:scholarships"),
        ],
        [
            InlineKeyboardButton("Ethiopia Tech", callback_data="menu:ethiopia"),
            InlineKeyboardButton("Global & Policy", callback_data="menu:politics"),
        ],
        [
            InlineKeyboardButton("AI Tools", callback_data="menu:ai"),
            InlineKeyboardButton("Research Papers", callback_data="menu:research"),
        ],
        [
            InlineKeyboardButton("Learn STEM", callback_data="menu:learn"),
            InlineKeyboardButton("Projects", callback_data="menu:projects"),
        ],
        [
            InlineKeyboardButton("Tech Radar", callback_data="menu:radar"),
            InlineKeyboardButton("Search", callback_data="menu:search"),
        ],
        [
            InlineKeyboardButton("Saved Items", callback_data="menu:saved"),
            InlineKeyboardButton("Subscriptions", callback_data="menu:interests"),
        ],
        [
            InlineKeyboardButton("Settings", callback_data="menu:settings"),
            InlineKeyboardButton("Help", callback_data="menu:help"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def get_discover_hub_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu keyboard for the Discover Hub."""
    buttons = [
        [
            InlineKeyboardButton("Daily Briefing", callback_data="menu:briefing"),
            InlineKeyboardButton("Trending", callback_data="menu:trending"),
        ],
        [
            InlineKeyboardButton("Technology Radar", callback_data="menu:radar"),
            InlineKeyboardButton("Domain Velocity", callback_data="menu:velocity"),
        ],
        nav_back_home_row(back_target="menu:home", home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(buttons)


def get_stem_tech_hub_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu keyboard for exploring the 12 primary STEM disciplines and regional domains."""
    buttons = [
        [
            InlineKeyboardButton("AI & Data", callback_data="cat:ai"),
            InlineKeyboardButton("Computer Science", callback_data="cat:computer-science"),
        ],
        [
            InlineKeyboardButton("Software Engineering", callback_data="cat:software-engineering"),
            InlineKeyboardButton("Cybersecurity", callback_data="cat:cybersecurity"),
        ],
        [
            InlineKeyboardButton("Robotics", callback_data="cat:robotics"),
            InlineKeyboardButton("Electronics & IoT", callback_data="cat:electronics"),
        ],
        [
            InlineKeyboardButton("Engineering", callback_data="cat:mechanical-engineering"),
            InlineKeyboardButton("Natural Sciences", callback_data="cat:physics"),
        ],
        [
            InlineKeyboardButton("Space & Aerospace", callback_data="cat:space-technology"),
            InlineKeyboardButton("Energy & Climate", callback_data="cat:renewable-energy"),
        ],
        [
            InlineKeyboardButton("Biotechnology", callback_data="cat:biotechnology"),
            InlineKeyboardButton("Emerging Tech", callback_data="cat:emerging-tech"),
        ],
        [
            InlineKeyboardButton("Ethiopia Tech", callback_data="cat:ethiopia-tech"),
            InlineKeyboardButton("Global & Policy", callback_data="cat:global-politics"),
        ],
        [
            InlineKeyboardButton("All Recent News", callback_data="cat:all"),
        ],
        nav_back_home_row(back_target="menu:home", home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(buttons)


def get_research_hub_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu keyboard for Research & Innovation."""
    buttons = [
        [
            InlineKeyboardButton("All arXiv Papers", callback_data="menu:arxiv_papers"),
            InlineKeyboardButton("Technology Radar", callback_data="menu:radar"),
        ],
        [
            InlineKeyboardButton("AI & ML (cs.AI)", callback_data="arxiv_cat:ai"),
            InlineKeyboardButton("Robotics (cs.RO)", callback_data="arxiv_cat:robotics"),
        ],
        [
            InlineKeyboardButton("Systems (cs.SE)", callback_data="arxiv_cat:computer-science"),
            InlineKeyboardButton("Explain Concept", callback_data="menu:ai_explain"),
        ],
        [
            InlineKeyboardButton("Impact Assessment", callback_data="menu:ai_impact"),
            InlineKeyboardButton("Content Package", callback_data="menu:ai_content"),
        ],
        nav_back_home_row(back_target="menu:home", home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(buttons)


def get_myspace_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu keyboard for My Space."""
    buttons = [
        [
            InlineKeyboardButton("Saved Items", callback_data="menu:saved"),
            InlineKeyboardButton("Subscriptions", callback_data="menu:interests"),
        ],
        [
            InlineKeyboardButton("Watchlist", callback_data="menu:watchlist"),
            InlineKeyboardButton("Learning Progress", callback_data="menu:progress"),
        ],
        [
            InlineKeyboardButton("Settings", callback_data="menu:settings"),
            InlineKeyboardButton("Feedback", callback_data="menu:feedback"),
        ],
        [
            InlineKeyboardButton("Export Data", callback_data="menu:export"),
            InlineKeyboardButton("Privacy", callback_data="menu:privacy"),
        ],
        [
            InlineKeyboardButton("Help & Commands", callback_data="menu:help"),
        ],
        nav_back_home_row(back_target="menu:home", home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(buttons)


def get_onboarding_welcome_keyboard() -> InlineKeyboardMarkup:
    """Entry keyboard for first-time user onboarding."""
    buttons = [
        [
            InlineKeyboardButton("Personalize Feed", callback_data="onboard:interests"),
        ],
        [
            InlineKeyboardButton("Skip to Home", callback_data="onboard:skip"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def get_onboarding_interests_keyboard(selected_slugs: Optional[List[str]] = None) -> InlineKeyboardMarkup:
    """Interactive topic selection keyboard for onboarding."""
    selected = set(selected_slugs or [])
    domains = taxonomy.get_interests_options()

    rows: List[List[InlineKeyboardButton]] = []
    current_row: List[InlineKeyboardButton] = []

    for name, slug, _emoji in domains:
        mark = "• " if slug in selected else ""
        short_name = name.split("&")[0].strip()[:20]
        btn_text = f"{mark}{short_name}"
        current_row.append(InlineKeyboardButton(btn_text, callback_data=f"onboard:toggle:{slug}"))
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    rows.append(
        [
            InlineKeyboardButton("Continue", callback_data="onboard:goals"),
            InlineKeyboardButton("Skip", callback_data="onboard:skip"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def get_onboarding_goals_keyboard() -> InlineKeyboardMarkup:
    """Goal/role selection keyboard for onboarding."""
    buttons = [
        [
            InlineKeyboardButton("Student (Scholarships & Courses)", callback_data="onboard:track:student"),
        ],
        [
            InlineKeyboardButton("Researcher (Papers & Science)", callback_data="onboard:track:researcher"),
        ],
        [
            InlineKeyboardButton("Engineer (Systems & Dev Tools)", callback_data="onboard:track:engineer"),
        ],
        [
            InlineKeyboardButton("Self-Learner (Lessons & Quizzes)", callback_data="onboard:track:learner"),
        ],
        [
            InlineKeyboardButton("Finish Setup", callback_data="onboard:skip"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def get_ai_hub_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu keyboard for AI tools."""
    buttons = [
        [
            InlineKeyboardButton("Summarize Latest", callback_data="menu:ai_summarize"),
            InlineKeyboardButton("Explain Concept", callback_data="menu:ai_explain"),
        ],
        [
            InlineKeyboardButton("Impact Assessment", callback_data="menu:ai_impact"),
            InlineKeyboardButton("Content Package", callback_data="menu:ai_content"),
        ],
        nav_back_home_row(back_target="menu:home", home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(buttons)


def get_learn_hub_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu keyboard for Learn STEM."""
    buttons = [
        [
            InlineKeyboardButton("Beginner", callback_data="learn_lvl:beginner"),
            InlineKeyboardButton("Intermediate", callback_data="learn_lvl:intermediate"),
            InlineKeyboardButton("Advanced", callback_data="learn_lvl:advanced"),
        ],
        [
            InlineKeyboardButton("AI & LLMs", callback_data="ed_learn:Artificial Intelligence"),
            InlineKeyboardButton("Robotics", callback_data="ed_learn:Robotics"),
        ],
        [
            InlineKeyboardButton("Quantum Computing", callback_data="ed_learn:Quantum Computing"),
            InlineKeyboardButton("Cybersecurity", callback_data="ed_learn:Cybersecurity"),
        ],
        [
            InlineKeyboardButton("Embedded Systems", callback_data="ed_learn:Embedded Systems"),
            InlineKeyboardButton("Software Architecture", callback_data="ed_learn:Software Architecture"),
        ],
        [
            InlineKeyboardButton("Quiz", callback_data="menu:learn_quiz"),
            InlineKeyboardButton("Compare Concepts", callback_data="menu:learn_compare"),
        ],
        [
            InlineKeyboardButton("Roadmaps", callback_data="menu:roadmaps"),
            InlineKeyboardButton("Progress", callback_data="menu:progress"),
        ],
        nav_back_home_row(back_target="menu:home", home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(buttons)


def get_projects_hub_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu keyboard for engineering project recommendations."""
    buttons = [
        [
            InlineKeyboardButton("Beginner", callback_data="prj_diff:beginner"),
            InlineKeyboardButton("Intermediate", callback_data="prj_diff:intermediate"),
            InlineKeyboardButton("Advanced", callback_data="prj_diff:advanced"),
        ],
        [
            InlineKeyboardButton("AI & LLMs", callback_data="prj_topic:Artificial Intelligence"),
            InlineKeyboardButton("Robotics", callback_data="prj_topic:Robotics"),
        ],
        [
            InlineKeyboardButton("Cybersecurity", callback_data="prj_topic:Cybersecurity"),
            InlineKeyboardButton("Embedded Systems", callback_data="prj_topic:Embedded Systems"),
        ],
        [
            InlineKeyboardButton("Software Architecture", callback_data="prj_topic:Software Architecture"),
            InlineKeyboardButton("Quantum Computing", callback_data="prj_topic:Quantum Computing"),
        ],
        [
            InlineKeyboardButton("Random Project", callback_data="prj_rand"),
            InlineKeyboardButton("Portfolio Guide", callback_data="menu:portfolio_tips"),
        ],
        nav_back_home_row(back_target="menu:home", home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(buttons)


def get_search_shortcuts_keyboard() -> InlineKeyboardMarkup:
    """Quick search shortcuts and navigation."""
    buttons = [
        [
            InlineKeyboardButton("AI", callback_data="search_kw:ai"),
            InlineKeyboardButton("Robotics", callback_data="search_kw:robotics"),
            InlineKeyboardButton("Quantum", callback_data="search_kw:quantum"),
        ],
        [
            InlineKeyboardButton("Biotech", callback_data="search_kw:biotech"),
            InlineKeyboardButton("Cybersecurity", callback_data="search_kw:cybersecurity"),
            InlineKeyboardButton("Space", callback_data="search_kw:space"),
        ],
        nav_back_home_row(back_target="menu:home", home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(buttons)


def get_interests_keyboard(active_slugs: Optional[List[str]] = None) -> InlineKeyboardMarkup:
    """Interactive multi-category selector keyboard with active indicators."""
    selected = set(active_slugs or [])
    categories = [
        ("AI & LLMs", "ai"),
        ("Machine Learning", "machine-learning"),
        ("Robotics", "robotics"),
        ("Computer Science", "computer-science"),
        ("Cybersecurity", "cybersecurity"),
        ("Electronics", "electronics"),
        ("Physics", "physics"),
        ("Space Tech", "space-technology"),
        ("Clean Energy", "renewable-energy"),
        ("Ethiopia Tech", "ethiopia-tech"),
        ("Ethiopian Affairs", "ethiopia-affairs"),
        ("Global Politics", "global-politics"),
        ("Tech Policy", "tech-policy"),
    ]

    rows: List[List[InlineKeyboardButton]] = []
    current_row: List[InlineKeyboardButton] = []

    for name, slug in categories:
        mark = "• " if slug in selected else ""
        btn_text = f"{mark}{name}"
        current_row.append(InlineKeyboardButton(btn_text, callback_data=f"pref_cat:{slug}"))
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    rows.append([InlineKeyboardButton("Reset to All Domains", callback_data="pref_cat:all")])
    rows.append(nav_back_home_row(back_target="menu:home", home_target="menu:home"))
    return InlineKeyboardMarkup(rows)


# ------------------ Presentation & Markdown Formatters ------------------


def format_main_menu(user_name: str = "Researcher", stats: Optional[Dict[str, int]] = None) -> str:
    """Format the main menu dashboard text."""
    total_articles = stats.get("total_articles", 0) if stats else 0
    active_sources = stats.get("active_sources", 0) if stats else 0
    user_saved = stats.get("user_saved_articles", 0) if stats else 0
    verified_opps = stats.get("verified_opportunities", 0) if stats else 0
    safe_user_name = re.sub(r"[*_`]", "", user_name or "Researcher").strip() or "Researcher"

    lines = [
        f"*STEM RADAR* — {safe_user_name}\n",
        "Technology, scientific research, academic opportunities, and STEM learning.\n",
        f"Active sources: {active_sources or 13}",
        f"Indexed records: {total_articles}",
        "Coverage: 12 STEM disciplines, 4 regional and policy domains",
    ]

    if verified_opps > 0:
        lines.append(f"Verified opportunities: {verified_opps}")

    if user_saved > 0:
        lines.append(f"Saved items: {user_saved}")

    lines.append("\nSelect a section:")
    return "\n".join(lines)


def format_ai_hub_intro() -> str:
    """Format introduction for AI tools."""
    return (
        "*AI Analysis Tools*\n\n"
        "- Summarize Latest: Key points and context from recent articles.\n"
        "- Explain Concept: Beginner, intermediate, or advanced breakdowns.\n"
        "- Impact Assessment: Technical, industry, and ethical considerations.\n"
        "- Content Package: Outlines, scripts, and vocabulary from a topic.\n\n"
        "Select a tool below, or run `/explain <concept>` directly."
    )


def format_learn_hub_intro() -> str:
    """Format introduction for Learn STEM."""
    return (
        "*Learn STEM*\n\n"
        "Structured lessons, engineering roadmaps, quizzes, and concept comparisons "
        "across core science and engineering fields.\n\n"
        "Choose a difficulty level or topic below, or run `/learn <topic>`."
    )


def format_projects_hub_intro() -> str:
    """Format introduction for the STEM Projects Hub."""
    return (
        "*STEM Projects*\n\n"
        "Practical engineering project specifications with architecture notes, "
        "implementation milestones, verification tests, and common pitfalls.\n\n"
        "Select a level or discipline below, or run `/project <topic>`."
    )


def format_search_intro() -> str:
    """Format search instruction screen."""
    return (
        "*Search*\n\n"
        "Search indexed records, live web sources, or generate a cited synthesis:\n\n"
        "- `/search <query>` — Search indexed articles, papers, and scholarships\n"
        "- `/websearch <query>` — Live web and academic search\n"
        "- `/search_ai <topic>` — Cited multi-source summary\n\n"
        "Examples:\n"
        "`/search humanoid robotics`\n"
        "`/search_ai quantum key distribution`\n\n"
        "Or select a topic below:"
    )


def format_discover_hub_intro() -> str:
    """Format introduction for the Discover Hub."""
    return (
        "*Discover*\n\n"
        "- Daily Briefing: Curated summary based on your subscriptions.\n"
        "- Trending: High-signal developments ranked by recency and impact.\n"
        "- Technology Radar: Technologies grouped by adoption stage (Adopt, Trial, Assess, Hold).\n"
        "- Domain Velocity: Recent publishing momentum across STEM fields.\n\n"
        "Select a view:"
    )


def format_stem_tech_hub_intro() -> str:
    """Format introduction for the STEM & Technology Hub."""
    return (
        "*STEM & Technology*\n\n"
        "Browse recent articles and technical reports across 12 STEM disciplines "
        "and regional policy feeds.\n\n"
        "Select a category:"
    )


def format_research_hub_intro() -> str:
    """Format introduction for the Research & Innovation Hub."""
    return (
        "*Research & Innovation*\n\n"
        "Browse recent arXiv preprints, structured paper summaries, and concept explanations.\n\n"
        "_Note: AI-assisted paper summaries are study aids and do not replace reading "
        "the original publication._\n\n"
        "Select a section below, or run `/research <topic>` or `/explain <concept>`."
    )


def format_myspace_intro(user_name: str = "Researcher", stats: Optional[Dict[str, int]] = None) -> str:
    """Format introduction for My Space."""
    safe_name = re.sub(r"[*_`]", "", user_name or "Researcher").strip() or "Researcher"
    user_saved = stats.get("user_saved_articles", 0) if stats else 0
    user_watchlists = stats.get("user_watchlist_keywords", 0) if stats else 0
    user_quizzes = stats.get("user_quizzes_taken", 0) if stats else 0
    user_notifs = stats.get("user_notifications_received", 0) if stats else 0

    lines = [
        f"*My Space* — {safe_name}\n",
        "Manage saved items, topic subscriptions, keyword watchlists, notifications, and data controls.\n",
        f"Saved items: {user_saved}",
        f"Watchlist keywords: {user_watchlists}",
        f"Quizzes completed: {user_quizzes}",
        f"Notifications delivered: {user_notifs}",
        "\nSelect an option:",
    ]
    return "\n".join(lines)


def format_onboarding_welcome(user_name: str = "Researcher") -> str:
    """Format welcoming message for first-time onboarding."""
    safe_name = re.sub(r"[*_`]", "", user_name or "Researcher").strip() or "Researcher"
    return (
        f"*Welcome to STEM RADAR do, {safe_name}*\n\n"
        "STEM RADAR tracks developments across science, engineering, research papers, "
        "and verified academic opportunities.\n\n"
        "Take *30 seconds* to select your topics so briefings and feeds focus on your interests."
    )


def format_onboarding_interests() -> str:
    """Format message for onboarding topic selection."""
    return (
        "*Step 1 of 2 — Select your STEM topics*\n\n"
        "Choose one or more disciplines to prioritize in your briefings and alerts. "
        "You can change these later in Settings."
    )


def format_onboarding_goals() -> str:
    """Format message for onboarding goal/track selection."""
    return (
        "*Step 2 of 2 — Primary focus*\n\n"
        "Choose what best matches how you plan to use STEM RADAR:\n\n"
        "- Student: Scholarships, university admissions, and free courses.\n"
        "- Researcher: arXiv preprints and structured paper summaries.\n"
        "- Engineer: Systems engineering, robotics, and developer tooling.\n"
        "- Self-Learner: Guided lessons, roadmaps, and quizzes."
    )


def format_empty_state(title: str, message: str, action_hint: str = "Run `/collect` to fetch updates.") -> str:
    """Format a consistent empty state card with guidance."""
    return _ds_empty_state(title=title, message=message, action_hint=action_hint)
