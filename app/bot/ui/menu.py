"""Unified 12-section interactive Main Menu, sub-menus, and layout formatters for STEM RADAR."""

import logging
import re
import time
from typing import Dict, List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode

from app.bot.keyboards.navigation import nav_back_home_row
from app.core.taxonomy import taxonomy

logger = logging.getLogger(__name__)

# Debounce tracking for rapid callback clicks
_RECENT_CALLBACKS: Dict[str, float] = {}
DEBOUNCE_WINDOW_SECONDS = 0.6


def is_duplicate_callback(user_id: int, callback_data: str) -> bool:
    """Check if a callback is a rapid duplicate submission within the debounce window."""
    now = time.time()
    key = f"{user_id}:{callback_data}"
    last_time = _RECENT_CALLBACKS.get(key, 0.0)

    # Periodic cleanup
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
                return  # Safe idempotent update
            if "can't parse entities" in err_str and parse_mode is not None:
                # Markdown entity syntax error: retry immediately as plain text
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
                # Fallback to plain text delivery
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
    """Generate the flagship 8-Hub interactive main menu dashboard."""
    buttons = [
        [
            InlineKeyboardButton("🧭 Discover", callback_data="menu:discover"),
            InlineKeyboardButton("🔬 STEM & Tech", callback_data="menu:stem_tech"),
        ],
        [
            InlineKeyboardButton("📄 Research", callback_data="menu:research"),
            InlineKeyboardButton("🎓 Student Hub", callback_data="menu:student_hub"),
        ],
        [
            InlineKeyboardButton("🧠 Learn STEM", callback_data="menu:learn"),
            InlineKeyboardButton("💡 Projects & Labs", callback_data="menu:projects"),
        ],
        [
            InlineKeyboardButton("🔍 Search & Web", callback_data="menu:search"),
            InlineKeyboardButton("👤 My Space", callback_data="menu:myspace"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def get_legacy_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Legacy 16-button menu keyboard retained for backward-compatibility tests."""
    buttons = [
        [
            InlineKeyboardButton("📰 Latest News", callback_data="menu:news"),
            InlineKeyboardButton("📈 Trending Tech", callback_data="menu:trending"),
        ],
        [
            InlineKeyboardButton("🎓 Student Hub", callback_data="menu:student_hub"),
            InlineKeyboardButton("🎁 Scholarships", callback_data="menu:scholarships"),
        ],
        [
            InlineKeyboardButton("🇪🇹 Ethiopia Radar", callback_data="menu:ethiopia"),
            InlineKeyboardButton("🌍 World & Politics", callback_data="menu:politics"),
        ],
        [
            InlineKeyboardButton("🧠 AI Intelligence", callback_data="menu:ai"),
            InlineKeyboardButton("📄 Research Papers", callback_data="menu:research"),
        ],
        [
            InlineKeyboardButton("🎓 Learn STEM", callback_data="menu:learn"),
            InlineKeyboardButton("💡 Project Ideas", callback_data="menu:projects"),
        ],
        [
            InlineKeyboardButton("🎯 Tech Radar", callback_data="menu:radar"),
            InlineKeyboardButton("🔍 Search Articles", callback_data="menu:search"),
        ],
        [
            InlineKeyboardButton("⭐ Saved Items", callback_data="menu:saved"),
            InlineKeyboardButton("🏷️ My Interests", callback_data="menu:interests"),
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="menu:settings"),
            InlineKeyboardButton("❓ Help & Guide", callback_data="menu:help"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def get_discover_hub_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu keyboard for the Discover Hub (Briefing, Trends, Radar, Velocity)."""
    buttons = [
        [
            InlineKeyboardButton("🌅 Executive Briefing", callback_data="menu:briefing"),
            InlineKeyboardButton("🔥 Trending Breakthroughs", callback_data="menu:trending"),
        ],
        [
            InlineKeyboardButton("🎯 Technology Radar", callback_data="menu:radar"),
            InlineKeyboardButton("⚡ Domain Velocity", callback_data="menu:velocity"),
        ],
        nav_back_home_row(back_target="menu:home", home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(buttons)


def get_stem_tech_hub_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu keyboard for exploring the 12 primary STEM disciplines and regional tags."""
    buttons = [
        [
            InlineKeyboardButton("🤖 AI & Data", callback_data="cat:ai"),
            InlineKeyboardButton("💻 Computer Science", callback_data="cat:computer-science"),
        ],
        [
            InlineKeyboardButton("⚙️ Software Systems", callback_data="cat:software-engineering"),
            InlineKeyboardButton("🛡️ Cybersecurity", callback_data="cat:cybersecurity"),
        ],
        [
            InlineKeyboardButton("🦾 Robotics", callback_data="cat:robotics"),
            InlineKeyboardButton("⚡ Electronics & IoT", callback_data="cat:electronics"),
        ],
        [
            InlineKeyboardButton("🏗️ Applied Engineering", callback_data="cat:mechanical-engineering"),
            InlineKeyboardButton("🔬 Natural Sciences", callback_data="cat:physics"),
        ],
        [
            InlineKeyboardButton("🚀 Space Tech", callback_data="cat:space-technology"),
            InlineKeyboardButton("🌱 Energy & Climate", callback_data="cat:renewable-energy"),
        ],
        [
            InlineKeyboardButton("🧬 Biotechnology", callback_data="cat:biotechnology"),
            InlineKeyboardButton("✨ Frontier Tech", callback_data="cat:emerging-tech"),
        ],
        [
            InlineKeyboardButton("🇪🇹 Ethiopia Tech", callback_data="cat:ethiopia-tech"),
            InlineKeyboardButton("🌍 Global & Policy", callback_data="cat:global-politics"),
        ],
        [
            InlineKeyboardButton("🌐 All Recent News", callback_data="cat:all"),
        ],
        nav_back_home_row(back_target="menu:home", home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(buttons)


def get_research_hub_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu keyboard for Research & Innovation (arXiv, Radar, Paper Explainer, Impact)."""
    buttons = [
        [
            InlineKeyboardButton("📄 All arXiv Literature", callback_data="menu:arxiv_papers"),
            InlineKeyboardButton("🎯 Technology Radar", callback_data="menu:radar"),
        ],
        [
            InlineKeyboardButton("🤖 AI & ML (cs.AI)", callback_data="arxiv_cat:ai"),
            InlineKeyboardButton("🦾 Robotics (cs.RO)", callback_data="arxiv_cat:robotics"),
        ],
        [
            InlineKeyboardButton("💻 Systems & SE (cs.SE)", callback_data="arxiv_cat:computer-science"),
            InlineKeyboardButton("💡 Explain Paper/Concept", callback_data="menu:ai_explain"),
        ],
        [
            InlineKeyboardButton("📊 Tech Impact Assessment", callback_data="menu:ai_impact"),
            InlineKeyboardButton("🎨 STEM Content Package", callback_data="menu:ai_content"),
        ],
        nav_back_home_row(back_target="menu:home", home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(buttons)


def get_myspace_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu keyboard for My Space (Bookmarks, Topics, Watchlists, Settings)."""
    buttons = [
        [
            InlineKeyboardButton("⭐ Saved Bookmarks", callback_data="menu:saved"),
            InlineKeyboardButton("🏷️ Subscribed Domains", callback_data="menu:interests"),
        ],
        [
            InlineKeyboardButton("👁️ Technology Watchlist", callback_data="menu:watchlist"),
            InlineKeyboardButton("🏆 Learning Progress", callback_data="menu:progress"),
        ],
        [
            InlineKeyboardButton("⚙️ Settings & Alerts", callback_data="menu:settings"),
            InlineKeyboardButton("💬 Send Feedback", callback_data="menu:feedback"),
        ],
        [
            InlineKeyboardButton("📦 Export My Data", callback_data="menu:export"),
            InlineKeyboardButton("🔒 Privacy & Rights", callback_data="menu:privacy"),
        ],
        [
            InlineKeyboardButton("❓ Help & Commands", callback_data="menu:help"),
        ],
        nav_back_home_row(back_target="menu:home", home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(buttons)


def get_onboarding_welcome_keyboard() -> InlineKeyboardMarkup:
    """Entry keyboard for first-time user onboarding."""
    buttons = [
        [
            InlineKeyboardButton("🎯 Personalize My Feed (30s)", callback_data="onboard:interests"),
        ],
        [
            InlineKeyboardButton("🚀 Skip & Open Main Menu", callback_data="onboard:skip"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def get_onboarding_interests_keyboard(selected_slugs: Optional[List[str]] = None) -> InlineKeyboardMarkup:
    """Interactive topic selection keyboard for onboarding."""
    selected = set(selected_slugs or [])
    domains = taxonomy.get_interests_options()

    rows: List[List[InlineKeyboardButton]] = []
    current_row: List[InlineKeyboardButton] = []

    for name, slug, emoji in domains:
        mark = "✅ " if slug in selected else ""
        short_name = name.split("&")[0].strip()[:18]
        btn_text = f"{mark}{emoji} {short_name}"
        current_row.append(InlineKeyboardButton(btn_text, callback_data=f"onboard:toggle:{slug}"))
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    rows.append(
        [
            InlineKeyboardButton("Continue to Goals ➡️", callback_data="onboard:goals"),
            InlineKeyboardButton("Skip ➡️", callback_data="onboard:skip"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def get_onboarding_goals_keyboard() -> InlineKeyboardMarkup:
    """Goal/role selection keyboard for onboarding."""
    buttons = [
        [
            InlineKeyboardButton("🎓 Student (Scholarships & Academics)", callback_data="onboard:track:student"),
        ],
        [
            InlineKeyboardButton("🔬 Academic Researcher / Scientist", callback_data="onboard:track:researcher"),
        ],
        [
            InlineKeyboardButton("💻 Software & Systems Engineer", callback_data="onboard:track:engineer"),
        ],
        [
            InlineKeyboardButton("📚 Curious Technical Learner", callback_data="onboard:track:learner"),
        ],
        [
            InlineKeyboardButton("🚀 Complete Onboarding", callback_data="onboard:skip"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def get_ai_hub_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu keyboard for AI Intelligence features."""
    buttons = [
        [
            InlineKeyboardButton("📝 Summarize Latest", callback_data="menu:ai_summarize"),
            InlineKeyboardButton("💡 Explain Concept", callback_data="menu:ai_explain"),
        ],
        [
            InlineKeyboardButton("📊 Technology Impact", callback_data="menu:ai_impact"),
            InlineKeyboardButton("🎨 STEM Content Kit", callback_data="menu:ai_content"),
        ],
        nav_back_home_row(back_target="menu:home", home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(buttons)


def get_learn_hub_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu keyboard for the STEM Learning Academy."""
    buttons = [
        [
            InlineKeyboardButton("🐣 Beginner Path", callback_data="learn_lvl:beginner"),
            InlineKeyboardButton("🧑‍💻 Intermediate", callback_data="learn_lvl:intermediate"),
            InlineKeyboardButton("🔬 Advanced Track", callback_data="learn_lvl:advanced"),
        ],
        [
            InlineKeyboardButton("🤖 AI & LLMs", callback_data="ed_learn:Artificial Intelligence"),
            InlineKeyboardButton("🦾 Robotics", callback_data="ed_learn:Robotics"),
        ],
        [
            InlineKeyboardButton("⚛️ Quantum Computing", callback_data="ed_learn:Quantum Computing"),
            InlineKeyboardButton("🛡️ Cybersecurity", callback_data="ed_learn:Cybersecurity"),
        ],
        [
            InlineKeyboardButton("⚡ Embedded Systems", callback_data="ed_learn:Embedded Systems"),
            InlineKeyboardButton("💻 Software Systems", callback_data="ed_learn:Software Architecture"),
        ],
        [
            InlineKeyboardButton("📝 Interactive Quiz", callback_data="menu:learn_quiz"),
            InlineKeyboardButton("⚖️ Compare Concepts", callback_data="menu:learn_compare"),
        ],
        [
            InlineKeyboardButton("🗺️ Curated Roadmaps", callback_data="menu:roadmaps"),
            InlineKeyboardButton("🏆 Learning Progress", callback_data="menu:progress"),
        ],
        nav_back_home_row(back_target="menu:home", home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(buttons)


def get_projects_hub_keyboard() -> InlineKeyboardMarkup:
    """Sub-menu keyboard for generating practical engineering portfolio projects."""
    buttons = [
        [
            InlineKeyboardButton("🐣 Beginner Labs", callback_data="prj_diff:beginner"),
            InlineKeyboardButton("🧑‍💻 Intermediate Labs", callback_data="prj_diff:intermediate"),
            InlineKeyboardButton("🔬 Advanced Labs", callback_data="prj_diff:advanced"),
        ],
        [
            InlineKeyboardButton("🤖 AI & LLMs", callback_data="prj_topic:Artificial Intelligence"),
            InlineKeyboardButton("🦾 Robotics", callback_data="prj_topic:Robotics"),
        ],
        [
            InlineKeyboardButton("🛡️ Cybersecurity", callback_data="prj_topic:Cybersecurity"),
            InlineKeyboardButton("⚡ Embedded Systems", callback_data="prj_topic:Embedded Systems"),
        ],
        [
            InlineKeyboardButton("💻 Software Systems", callback_data="prj_topic:Software Architecture"),
            InlineKeyboardButton("⚛️ Quantum Computing", callback_data="prj_topic:Quantum Computing"),
        ],
        [
            InlineKeyboardButton("🎲 Random Lab Idea", callback_data="prj_rand"),
            InlineKeyboardButton("💼 Portfolio Strategy", callback_data="menu:portfolio_tips"),
        ],
        nav_back_home_row(back_target="menu:home", home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(buttons)


def get_search_shortcuts_keyboard() -> InlineKeyboardMarkup:
    """Quick search shortcuts and navigation."""
    buttons = [
        [
            InlineKeyboardButton("🤖 #AI", callback_data="search_kw:ai"),
            InlineKeyboardButton("🦾 #Robotics", callback_data="search_kw:robotics"),
            InlineKeyboardButton("⚛️ #Quantum", callback_data="search_kw:quantum"),
        ],
        [
            InlineKeyboardButton("🧬 #Biotech", callback_data="search_kw:biotech"),
            InlineKeyboardButton("🛡️ #Security", callback_data="search_kw:cybersecurity"),
            InlineKeyboardButton("🚀 #Space", callback_data="search_kw:space"),
        ],
        nav_back_home_row(back_target="menu:home", home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(buttons)


def get_interests_keyboard(active_slugs: Optional[List[str]] = None) -> InlineKeyboardMarkup:
    """Interactive multi-category selector keyboard with active checkmarks."""
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
        ("🇪🇹 Ethiopia Tech", "ethiopia-tech"),
        ("🇪🇹 Ethiopian Affairs", "ethiopia-affairs"),
        ("🌍 Global Politics", "global-politics"),
        ("⚖️ Tech Policy", "tech-policy"),
    ]

    rows: List[List[InlineKeyboardButton]] = []
    current_row: List[InlineKeyboardButton] = []

    for name, slug in categories:
        mark = "✅ " if slug in selected else ""
        btn_text = f"{mark}{name}"
        current_row.append(InlineKeyboardButton(btn_text, callback_data=f"pref_cat:{slug}"))
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    rows.append([InlineKeyboardButton("🌐 Reset to All Domains", callback_data="pref_cat:all")])
    rows.append(nav_back_home_row(back_target="menu:home", home_target="menu:home"))
    return InlineKeyboardMarkup(rows)


# ------------------ Presentation & Markdown Formatters ------------------


def format_main_menu(user_name: str = "Researcher", stats: Optional[Dict[str, int]] = None) -> str:
    """Format the flagship welcome & dashboard text."""
    total_articles = stats.get("total_articles", 0) if stats else 0
    active_sources = stats.get("active_sources", 0) if stats else 0
    user_saved = stats.get("user_saved_articles", 0) if stats else 0
    verified_opps = stats.get("verified_opportunities", 0) if stats else 0
    safe_user_name = re.sub(r"[*_`]", "", user_name or "Researcher").strip() or "Researcher"

    lines = [
        f"📡 *Welcome to STEM RADAR, {safe_user_name}!* 🚀\n",
        "Your AI-powered intelligence platform collecting, analyzing, and organizing "
        "the latest developments in Science, Technology, Engineering, and Mathematics.\n",
        "📊 *Live Platform Telemetry:*",
        f"• *Monitored Sources:* `{active_sources or 13}` verified feeds & APIs",
        f"• *Indexed Articles:* `{total_articles}` research records",
        "• *Intelligence Domains:* `23 Specialized Topics & Regions`",
    ]

    if verified_opps > 0:
        lines.append(f"• *Student Hub:* `{verified_opps}` verified scholarships & awards")

    if user_saved > 0:
        lines.append(f"• *Your Bookmarks:* `{user_saved}` articles saved")

    lines.append("\n*Tap a section below to explore:*")
    return "\n".join(lines)


def format_ai_hub_intro() -> str:
    """Format introduction for the AI Intelligence suite."""
    return (
        "🧠 *STEM RADAR — AI Intelligence Hub*\n\n"
        "Leverage specialized AI models to extract insights from technical publications:\n\n"
        "• *Executive Summaries:* 3-bullet core takeaways and impact analysis.\n"
        "• *Concept Explanations:* Multi-tier breakdowns for any engineering or scientific concept.\n"
        "• *Technology Impact:* Economic, industry, and academic horizon assessment.\n"
        "• *STEM Content Kit:* Formatted posts, carousels, and glossaries for educators & researchers.\n\n"
        "Select an AI tool below or pass `/explain <concept>` at any time:"
    )


def format_learn_hub_intro() -> str:
    """Format introduction for the STEM Learning Academy."""
    return (
        "🎓 *STEM Learning Academy*\n\n"
        "Master complex technical disciplines through guided, step-by-step AI lessons:\n\n"
        "• *Structured Paths:* Beginner, Intermediate, and Advanced engineering curricula.\n"
        "• *Interactive Lessons:* Concept overview, architecture, code, and key takeaways.\n"
        "• *Topic Roadmaps:* 4-phase structured engineering learning roadmaps.\n"
        "• *Comprehension Quizzes:* Test your technical knowledge with instant scoring.\n"
        "• *Concept Comparisons:* Contrast architectural paradigms (e.g., Transformers vs RNNs).\n\n"
        "Choose a difficulty path or discipline below to begin learning:"
    )


def format_projects_hub_intro() -> str:
    """Format introduction for the STEM Projects & Labs Hub."""
    return (
        "💡 *STEM Portfolio Project Generator — Engineering Labs*\n\n"
        "Build practical, production-grade engineering systems that prove your technical depth:\n\n"
        "• *Portfolio-Ready Specs:* Real problem statements, architecture, and tech stacks.\n"
        "• *Step-by-Step Milestones:* Incremental implementation phases with verifiable goals.\n"
        "• *Testing & Benchmarking:* Concrete verification steps and performance metrics.\n"
        "• *Pitfall Prevention:* Avoid common architectural, memory, and hardware traps.\n"
        "• *Recruiter Impact:* Targeted portfolio talking points for engineering interviews.\n\n"
        "Choose a track or discipline below, or run `/project <topic>` for any custom lab:"
    )


def format_search_intro() -> str:
    """Format search instruction screen with keyword hints and multi-modal discovery options."""
    return (
        "🔍 *Search STEM RADAR Intelligence & Web Discovery*\n\n"
        "Search indexed technical intelligence, live scientific repositories, or synthesize AI briefings:\n\n"
        "• `/search <keyword>` — Instant multi-domain database search (Articles, arXiv, Scholarships)\n"
        "• `/websearch <query>` — Live web & academic discovery via Semantic Scholar, Google & Brave\n"
        "• `/search_ai <topic>` — Grounded multi-source AI synthesis with citations & takeaways\n\n"
        "_Example:_ `/search humanoid robotics`\n"
        "_Example:_ `/search_ai quantum key distribution`\n\n"
        "Or tap one of the popular topic shortcuts below:"
    )


def format_discover_hub_intro() -> str:
    """Format introduction for the Discover Hub."""
    return (
        "🧭 *STEM RADAR — Daily Discovery & Pulse*\n\n"
        "Your real-time lens into high-impact breakthroughs, technology momentum, and strategic intelligence:\n\n"
        "• *Executive Briefing:* Personalized 3-minute morning intelligence brief.\n"
        "• *Trending Breakthroughs:* High-impact stories ranked by composite scoring.\n"
        "• *Technology Radar:* Emerging technology mapped across 4 horizons (Adopt, Trial, Assess, Hold).\n"
        "• *Domain Velocity:* Publishing momentum across 12 foundational STEM disciplines.\n\n"
        "Select a discovery channel below:"
    )


def format_stem_tech_hub_intro() -> str:
    """Format introduction for the STEM & Technology Disciplines Hub."""
    return (
        "🔬 *STEM & Technology Disciplines*\n\n"
        "Explore peer-reviewed research, engineering breakthroughs, and technical reporting "
        "across 12 foundational STEM disciplines.\n\n"
        "Select a discipline below to view curated intelligence:"
    )


def format_research_hub_intro() -> str:
    """Format introduction for the Research & Innovation Hub."""
    return (
        "🔬 *Research & Innovation Hub*\n\n"
        "Explore peer-reviewed scientific breakthroughs, preprint arXiv literature, and AI paper breakdowns:\n\n"
        "• *arXiv Literature:* Pre-print scientific research in AI, Robotics, Systems & Natural Sciences.\n"
        "• *Paper Deep Dives:* 6-dimension empirical breakdowns (Problem, Method, Findings, Limits, Questions).\n"
        "• *Technology Radar:* Emerging technology maturity and horizon tracking.\n"
        "• *Concept Explanations:* Multi-tier breakdowns for complex mathematical and algorithmic principles.\n"
        "• *Technology Impact:* Economic, industry, and academic horizon assessment.\n\n"
        "⚠️ *Academic Integrity Policy:*\n"
        "_AI-generated summaries are analytical study aids and do not substitute for reading "
        "original publications._\n\n"
        "Select a research channel below or use `/research <topic>` or `/explain <concept>` anytime:"
    )


def format_myspace_intro(user_name: str = "Researcher", stats: Optional[Dict[str, int]] = None) -> str:
    """Format introduction for the My Space personal control center."""
    safe_name = re.sub(r"[*_`]", "", user_name or "Researcher").strip() or "Researcher"
    user_saved = stats.get("user_saved_articles", 0) if stats else 0
    user_watchlists = stats.get("user_watchlist_keywords", 0) if stats else 0
    user_quizzes = stats.get("user_quizzes_taken", 0) if stats else 0
    user_notifs = stats.get("user_notifications_received", 0) if stats else 0

    lines = [
        f"👤 *My Space — Personal Hub, {safe_name}*\n",
        "Your personal control center to manage saved research, topic subscriptions, "
        "active keyword watchlists, and privacy settings.\n",
        "📊 *Your Personal Status:*",
        f"• *Saved Items:* `{user_saved}` articles & papers bookmarked",
        f"• *Active Watchlists:* `{user_watchlists}` tracked technology keywords",
        f"• *Learning Lab Mastery:* `{user_quizzes}` quizzes completed",
        f"• *Intelligence Delivered:* `{user_notifs}` briefings & notifications received",
        "• *Telemetry & Tracking:* Active",
        "\nSelect a personal management section below:",
    ]
    return "\n".join(lines)


def format_onboarding_welcome(user_name: str = "Researcher") -> str:
    """Format welcoming message for first-time onboarding."""
    safe_name = re.sub(r"[*_`]", "", user_name or "Researcher").strip() or "Researcher"
    return (
        f"👋 *Welcome to STEM RADAR, {safe_name}!* 🚀\n\n"
        "Your AI-powered intelligence platform collecting, analyzing, and organizing "
        "the latest developments in Science, Technology, Engineering, and Mathematics.\n\n"
        "Take **30 seconds** to personalize your feed so you only see what matters most to you!"
    )


def format_onboarding_interests() -> str:
    """Format message for onboarding topic selection."""
    return (
        "🎯 *Step 1 of 2: What STEM domains interest you most?*\n\n"
        "Tap to toggle the disciplines you'd like prioritized in your daily briefings, "
        "recommendations, and alerts.\n\n"
        "You can choose multiple topics:"
    )


def format_onboarding_goals() -> str:
    """Format message for onboarding goal/track selection."""
    return (
        "🎯 *Step 2 of 2: What best describes your primary goal?*\n\n"
        "This helps us tailor opportunity suggestions, educational roadmaps, and difficulty levels:\n\n"
        "• *Student:* Focus on verified scholarships, university admissions & free courses.\n"
        "• *Researcher:* Focus on arXiv literature, paper breakdowns & scientific breakthroughs.\n"
        "• *Engineer:* Focus on production architectures, robotics & developer tools.\n"
        "• *Self-Learner:* Focus on interactive lessons, quizzes & roadmaps."
    )


def format_empty_state(title: str, message: str, action_hint: str = "Run `/collect` to fetch updates.") -> str:
    """Format a consistent empty state card with guidance."""
    return f"📭 *{title}*\n\n{message}\n\n💡 *Next Step:* {action_hint}"
