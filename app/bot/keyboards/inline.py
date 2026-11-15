"""Inline keyboards for interactive Telegram navigation."""

from typing import List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_article_keyboard(
    article_id: int,
    url: str,
    offset: int,
    total: int,
    category_slug: Optional[str] = None,
    is_saved: bool = False,
) -> InlineKeyboardMarkup:
    """Generate keyboard for an article with action buttons and pagination."""
    cat_tag = category_slug or "all"
    bookmark_label = "Saved ✅" if is_saved else "Bookmark ⭐"

    # Row 1: External Link & Bookmark Toggle
    row1 = [
        InlineKeyboardButton("Read Original 🔗", url=url),
        InlineKeyboardButton(bookmark_label, callback_data=f"save:{article_id}"),
    ]

    # Row 2: Navigation controls
    row2: List[InlineKeyboardButton] = []
    if offset > 0:
        row2.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"nav:{cat_tag}:{offset - 1}"))
    row2.append(InlineKeyboardButton(f"{offset + 1}/{total}", callback_data="noop"))
    if offset + 1 < total:
        row2.append(InlineKeyboardButton("Next ➡️", callback_data=f"nav:{cat_tag}:{offset + 1}"))

    # Row 3: AI Intelligence actions
    row3 = [
        InlineKeyboardButton("AI Analysis 🧠", callback_data=f"ai_sum:{article_id}"),
        InlineKeyboardButton("Content Kit 🎨", callback_data=f"ai_cnt:{article_id}"),
    ]

    # Row 4: Quick Category Picker & Refresh
    row4 = [
        InlineKeyboardButton("Categories 🗂️", callback_data="show_cats"),
        InlineKeyboardButton("Refresh 🔄", callback_data=f"nav:{cat_tag}:{offset}"),
    ]

    return InlineKeyboardMarkup([row1, row2, row3, row4])


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

