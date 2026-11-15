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
