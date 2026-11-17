"""Reusable navigation keyboards, pagination controls, and common UI rows for STEM RADAR."""

from typing import List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def nav_back_home_row(
    back_target: str = "menu:home",
    home_target: str = "menu:home",
    refresh_target: Optional[str] = None,
) -> List[InlineKeyboardButton]:
    """Build a standardized bottom navigation row: [ ⬅️ Back ] [ 🔄 Refresh (optional) ] [ 🏠 Main Menu ]."""
    row: List[InlineKeyboardButton] = []

    if back_target:
        row.append(InlineKeyboardButton("⬅️ Back", callback_data=back_target))

    if refresh_target:
        row.append(InlineKeyboardButton("🔄 Refresh", callback_data=refresh_target))

    if home_target and (home_target != back_target or len(row) == 0):
        row.append(InlineKeyboardButton("🏠 Main Menu", callback_data=home_target))

    return row


def nav_pagination_row(
    offset: int,
    total: int,
    prefix: str,
    show_counter: bool = True,
) -> List[InlineKeyboardButton]:
    """Build a standardized pagination row: [ ⬅️ Prev ] [ 1/10 ] [ Next ➡️ ]."""
    row: List[InlineKeyboardButton] = []

    if offset > 0:
        row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"{prefix}:{offset - 1}"))

    if show_counter:
        current_display = min(offset + 1, total) if total > 0 else 0
        row.append(InlineKeyboardButton(f"{current_display}/{total}", callback_data="noop"))

    if offset + 1 < total:
        row.append(InlineKeyboardButton("Next ➡️", callback_data=f"{prefix}:{offset + 1}"))

    return row


def build_nav_keyboard(
    content_rows: List[List[InlineKeyboardButton]],
    back_target: Optional[str] = "menu:home",
    home_target: Optional[str] = "menu:home",
    refresh_target: Optional[str] = None,
) -> InlineKeyboardMarkup:
    """Combine content button rows with a standardized navigation footer."""
    rows = [list(r) for r in content_rows]
    nav_row = nav_back_home_row(
        back_target=back_target or "",
        home_target=home_target or "",
        refresh_target=refresh_target,
    )
    if nav_row:
        rows.append(nav_row)
    return InlineKeyboardMarkup(rows)


def get_back_home_keyboard(
    back_target: str = "menu:home",
    home_target: str = "menu:home",
    refresh_target: Optional[str] = None,
) -> InlineKeyboardMarkup:
    """Standalone keyboard with only Back / Refresh / Main Menu."""
    row = nav_back_home_row(
        back_target=back_target,
        home_target=home_target,
        refresh_target=refresh_target,
    )
    return InlineKeyboardMarkup([row])
