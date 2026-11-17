"""Unified 12-section interactive Main Menu, sub-menus, and layout formatters for STEM RADAR."""

import logging
import re
import time
from typing import Dict, List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode

from app.bot.keyboards.navigation import nav_back_home_row

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
    """Generate the flagship interactive main menu dashboard."""
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
            InlineKeyboardButton("🤖 AI & LLMs", callback_data="ed_learn:Artificial Intelligence"),
            InlineKeyboardButton("🦾 Robotics", callback_data="ed_learn:Robotics"),
        ],
        [
            InlineKeyboardButton("⚛️ Quantum Computing", callback_data="ed_learn:Quantum Computing"),
            InlineKeyboardButton("🛡️ Cybersecurity", callback_data="ed_learn:Cybersecurity"),
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
            InlineKeyboardButton("🤖 AI & LLMs", callback_data="prj_topic:Artificial Intelligence"),
            InlineKeyboardButton("🦾 Robotics", callback_data="prj_topic:Robotics"),
        ],
        [
            InlineKeyboardButton("🛡️ CyberSec", callback_data="prj_topic:Cybersecurity"),
            InlineKeyboardButton("⚡ Embedded Systems", callback_data="prj_topic:Embedded Systems"),
        ],
        [
            InlineKeyboardButton("💻 Software Systems", callback_data="prj_topic:Software Architecture"),
            InlineKeyboardButton("⚛️ Quantum Computing", callback_data="prj_topic:Quantum Computing"),
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
        "• *Interactive Lessons:* Concept overview, architecture, code, and key takeaways.\n"
        "• *Topic Roadmaps:* 4-phase structured engineering curricula.\n"
        "• *Comprehension Quizzes:* Test your technical knowledge with instant scoring.\n"
        "• *Concept Comparisons:* Contrast architectural paradigms (e.g., Transformers vs RNNs).\n\n"
        "Choose a flagship domain below to begin learning:"
    )


def format_search_intro() -> str:
    """Format search instruction screen with keyword hints."""
    return (
        "🔍 *Search STEM RADAR Intelligence*\n\n"
        "You can search indexed articles, arXiv papers, and open-source projects by keyword.\n\n"
        "👉 *To search instantly, type:*\n"
        "`/search <keyword>`\n\n"
        "_Example:_ `/search humanoid robotics`\n"
        "_Example:_ `/search quantum computing`\n\n"
        "Or tap one of the popular topic shortcuts below:"
    )


def format_empty_state(title: str, message: str, action_hint: str = "Run `/collect` to fetch updates.") -> str:
    """Format a consistent empty state card with guidance."""
    return f"📭 *{title}*\n\n{message}\n\n💡 *Next Step:* {action_hint}"
