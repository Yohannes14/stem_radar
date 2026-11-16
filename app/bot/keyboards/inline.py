"""Inline keyboards for interactive Telegram navigation."""

from typing import List, Optional
from urllib.parse import quote

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_article_keyboard(
    article_id: int,
    url: str,
    offset: int,
    total: int,
    category_slug: Optional[str] = None,
    is_saved: bool = False,
    title: str = "",
) -> InlineKeyboardMarkup:
    """Generate redesigned keyboard for an article with 5 action buttons and pagination.

    Actions:
    1. Read Original (external URL)
    2. Explain with AI (interactive breakdown callback)
    3. Save / Bookmark (toggle callback)
    4. Share (native Telegram share sheet)
    5. Related Articles (category/topic discovery callback)
    """
    cat_tag = category_slug or "all"
    bookmark_label = "Saved ✅" if is_saved else "Bookmark ⭐"
    share_text = f"STEM Breakthrough: {title}" if title else "STEM Intelligence Article"
    share_url = f"https://t.me/share/url?url={quote(url)}&text={quote(share_text)}"

    # Row 1: Read Original & AI Explainer
    row1 = [
        InlineKeyboardButton("Read Original 🔗", url=url),
        InlineKeyboardButton("Explain with AI 🧠", callback_data=f"ai_exp:{article_id}"),
    ]

    # Row 2: Bookmark, Share, Related
    row2 = [
        InlineKeyboardButton(bookmark_label, callback_data=f"save:{article_id}"),
        InlineKeyboardButton("Share 📤", url=share_url),
        InlineKeyboardButton("Related 🔍", callback_data=f"rel:{article_id}"),
    ]

    # Row 3: Pagination controls
    row3: List[InlineKeyboardButton] = []
    if offset > 0:
        row3.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"nav:{cat_tag}:{offset - 1}"))
    row3.append(InlineKeyboardButton(f"{offset + 1}/{total}", callback_data="noop"))
    if offset + 1 < total:
        row3.append(InlineKeyboardButton("Next ➡️", callback_data=f"nav:{cat_tag}:{offset + 1}"))

    # Row 4: Navigation controls
    row4 = [
        InlineKeyboardButton("🗂️ Categories", callback_data="show_cats"),
        InlineKeyboardButton("🔄 Refresh", callback_data=f"nav:{cat_tag}:{offset}"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="menu:home"),
    ]

    return InlineKeyboardMarkup([row1, row2, row3, row4])


def get_explanation_keyboard(article_id: int, current_mode: str = "intermediate") -> InlineKeyboardMarkup:
    """Difficulty mode selector attached to AI concept explanation."""
    b_mark = "• " if current_mode == "beginner" else ""
    i_mark = "• " if current_mode == "intermediate" else ""
    a_mark = "• " if current_mode == "advanced" else ""

    buttons = [
        [
            InlineKeyboardButton(f"{b_mark}🐣 Beginner", callback_data=f"exp_mode:{article_id}:beginner"),
            InlineKeyboardButton(f"{i_mark}🧑‍💻 Intermediate", callback_data=f"exp_mode:{article_id}:intermediate"),
            InlineKeyboardButton(f"{a_mark}🔬 Advanced", callback_data=f"exp_mode:{article_id}:advanced"),
        ],
        [
            InlineKeyboardButton("⬅️ Back to Article", callback_data=f"back_art:{article_id}"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="menu:home"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def get_search_pagination_keyboard(query: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Pagination keyboard for search results."""
    rows: List[List[InlineKeyboardButton]] = []
    pag_row: List[InlineKeyboardButton] = []

    clean_query = query.strip()[:30]
    if page > 0:
        pag_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"s_nav:{clean_query}:{page - 1}"))
    pag_row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    if page + 1 < total_pages:
        pag_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"s_nav:{clean_query}:{page + 1}"))

    rows.append(pag_row)
    rows.append(
        [
            InlineKeyboardButton("🔍 New Search", callback_data="menu:search"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="menu:home"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def get_category_keyboard() -> InlineKeyboardMarkup:
    """Generate keyboard with quick STEM category buttons."""
    buttons = [
        [
            InlineKeyboardButton("🤖 AI", callback_data="cat:ai"),
            InlineKeyboardButton("🦾 Robotics", callback_data="cat:robotics"),
            InlineKeyboardButton("💻 Dev / CS", callback_data="cat:computer-science"),
        ],
        [
            InlineKeyboardButton("🔬 Science", callback_data="cat:physics"),
            InlineKeyboardButton("⚡ Electronics", callback_data="cat:electronics"),
            InlineKeyboardButton("🛡️ CyberSec", callback_data="cat:cybersecurity"),
        ],
        [
            InlineKeyboardButton("🚀 Space Tech", callback_data="cat:space-technology"),
            InlineKeyboardButton("🌱 Clean Energy", callback_data="cat:renewable-energy"),
            InlineKeyboardButton("💡 Emerging", callback_data="cat:emerging-tech"),
        ],
        [
            InlineKeyboardButton("🌐 All Latest News", callback_data="cat:all"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="menu:home"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


# ------------------ Phase 4: STEM Education Keyboards ------------------


def get_lesson_keyboard(topic: str, level: str) -> InlineKeyboardMarkup:
    """Action buttons attached to an educational lesson."""
    next_level = "intermediate" if level == "beginner" else ("advanced" if level == "intermediate" else "beginner")
    buttons = [
        [
            InlineKeyboardButton("📝 Take Topic Quiz", callback_data=f"ed_quiz:{topic}"),
            InlineKeyboardButton(f"⚙️ Level: {next_level.capitalize()}", callback_data=f"ed_lvl:{topic}:{next_level}"),
        ],
        [
            InlineKeyboardButton("🗺️ Full Roadmap", callback_data=f"ed_map:{topic}"),
            InlineKeyboardButton("🚀 Project Idea", callback_data=f"ed_prj:{topic}"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def get_quiz_keyboard(topic: str, q_index: int, total_q: int) -> InlineKeyboardMarkup:
    """Interactive ABCD multiple choice buttons for quiz question."""
    buttons = [
        [
            InlineKeyboardButton("A", callback_data=f"qz_ans:{topic}:{q_index}:0"),
            InlineKeyboardButton("B", callback_data=f"qz_ans:{topic}:{q_index}:1"),
            InlineKeyboardButton("C", callback_data=f"qz_ans:{topic}:{q_index}:2"),
            InlineKeyboardButton("D", callback_data=f"qz_ans:{topic}:{q_index}:3"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def get_education_topics_keyboard() -> InlineKeyboardMarkup:
    """Quick selection of flagship STEM learning domains."""
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
            InlineKeyboardButton("⚡ Embedded Systems", callback_data="ed_learn:Embedded Systems"),
            InlineKeyboardButton("💻 Software Systems", callback_data="ed_learn:Software Architecture"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


# ------------------ Phase 5: Personalization & Automation Keyboards ------------------


def get_settings_panel_keyboard(
    notifications_enabled: bool,
    high_impact_enabled: bool = True,
    weekly_reports_enabled: bool = True,
) -> InlineKeyboardMarkup:
    """Build interactive preference management panel with toggle controls."""
    notif_btn = "🔔 Notifications: ON" if notifications_enabled else "🔕 Notifications: OFF"
    impact_btn = "⚡ High-Impact Alerts: ON" if high_impact_enabled else "⚡ High-Impact Alerts: OFF"
    weekly_btn = "🌐 Weekly Report: ON" if weekly_reports_enabled else "🌐 Weekly Report: OFF"

    buttons = [
        [InlineKeyboardButton(notif_btn, callback_data="toggle_notif")],
        [InlineKeyboardButton(impact_btn, callback_data="toggle_impact")],
        [InlineKeyboardButton(weekly_btn, callback_data="toggle_weekly")],
        [
            InlineKeyboardButton("🤖 AI", callback_data="pref_cat:ai"),
            InlineKeyboardButton("🦾 Robotics", callback_data="pref_cat:robotics"),
            InlineKeyboardButton("💻 CS / Dev", callback_data="pref_cat:computer-science"),
        ],
        [
            InlineKeyboardButton("🛡️ CyberSec", callback_data="pref_cat:cybersecurity"),
            InlineKeyboardButton("⚛️ Physics", callback_data="pref_cat:physics"),
            InlineKeyboardButton("🌐 All STEM", callback_data="pref_cat:all"),
        ],
        [
            InlineKeyboardButton("🏠 Main Menu", callback_data="menu:home"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def get_watchlist_keyboard(keywords: list) -> InlineKeyboardMarkup:
    """Interactive removal controls for active watchlist keywords."""
    buttons: List[List[InlineKeyboardButton]] = []
    # Up to 4 individual remove buttons
    row: List[InlineKeyboardButton] = []
    for item in keywords[:4]:
        kw = item.keyword if hasattr(item, "keyword") else str(item)
        row.append(InlineKeyboardButton(f"❌ #{kw}", callback_data=f"wl_rm:{kw}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    if keywords:
        buttons.append([InlineKeyboardButton("🗑️ Clear All Watchlist", callback_data="wl_clear")])
    buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="menu:home")])

    return InlineKeyboardMarkup(buttons)


def get_briefing_keyboard() -> InlineKeyboardMarkup:
    """Interactive controls attached to the daily executive briefing."""
    buttons = [
        [
            InlineKeyboardButton("📈 View Trending SOTA", callback_data="nav_trends"),
            InlineKeyboardButton("🔄 Refresh Briefing", callback_data="refresh_briefing"),
        ],
        [
            InlineKeyboardButton("⚙️ Notification Settings", callback_data="open_settings"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="menu:home"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)
