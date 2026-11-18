"""Centralized UI design system for STEM RADAR Telegram presentation.

Provides consistent editorial typography, metadata blocks, plain-text status
conventions, Markdown sanitization, empty/error states, and AI disclosure notices.
"""

import html
import re
from datetime import datetime
from typing import Iterable, Optional, Sequence, Tuple, Union

AI_EDITORIAL_STYLE_INSTRUCTION = (
    "Write in a clear, factual, editorial tone. Do not use emojis, exclamation marks, "
    "hype language, or conversational filler (such as 'Great question' or 'Let's dive in'). "
    "Preserve accurate technical terminology and distinguish sourced facts from interpretation."
)


def sanitize_markdown(text: Optional[str]) -> str:
    """Strip uncontrolled Markdown control characters that could break Telegram rendering."""
    if not text:
        return ""
    cleaned = html.unescape(str(text))
    cleaned = cleaned.replace("*", "").replace("_", " ").replace("`", "")
    return re.sub(r"\s+", " ", cleaned).strip()


def format_date(dt: Optional[datetime], fallback: str = "Recent") -> str:
    """Format a datetime into a clean editorial date (e.g. '18 Nov 2026')."""
    if not dt:
        return fallback
    return dt.strftime("%d %b %Y").lstrip("0")


def format_datetime(dt: Optional[datetime], fallback: str = "Never") -> str:
    """Format a datetime with UTC timestamp (e.g. '18 Nov, 14:30 UTC')."""
    if not dt:
        return fallback
    return dt.strftime("%d %b, %H:%M UTC").lstrip("0")


def format_header(title: str, subtitle: Optional[str] = None) -> str:
    """Render a primary editorial heading with an optional supporting line."""
    clean_title = sanitize_markdown(title)
    if subtitle:
        return f"*{clean_title}*\n{subtitle.strip()}"
    return f"*{clean_title}*"


def format_meta(pairs: Sequence[Tuple[str, Optional[str]]]) -> str:
    """Render concise 'Label: Value' metadata lines, omitting empty values."""
    lines = []
    for label, value in pairs:
        if value is None:
            continue
        text_val = str(value).strip()
        if not text_val:
            continue
        lines.append(f"{label}: {text_val}")
    return "\n".join(lines)


def format_section(heading: str, content: Union[str, Iterable[str], None]) -> str:
    """Render a section heading followed by body text or hyphen bullets.

    Returns an empty string if content is empty so callers can join cleanly.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        body = content.strip()
        if not body:
            return ""
        return f"*{heading}*\n{body}"

    items = [sanitize_markdown(item) for item in content if item and str(item).strip()]
    if not items:
        return ""
    bullets = "\n".join(f"- {item}" for item in items)
    return f"*{heading}*\n{bullets}"


def format_status(label: str, detail: Optional[str] = None) -> str:
    """Format a plain-text status string without relying on emoji colors."""
    clean = label.strip()
    if detail:
        return f"{clean} ({detail.strip()})"
    return clean


def format_ai_notice(kind: str = "general") -> str:
    """Return a consistent, understated AI disclosure footer."""
    if kind == "paper":
        return (
            "_AI-assisted summary. This breakdown is an analytical aid and does not substitute "
            "for reading the original research paper._"
        )
    if kind == "opportunity":
        return (
            "_Verify final eligibility, funding, and deadlines directly on the official provider portal. "
            "STEM RADAR does not guarantee selection or funding._"
        )
    return "_AI-assisted summary. Verify key details against the original source._"


def format_empty_state(
    title: str,
    message: str,
    action_hint: Optional[str] = None,
) -> str:
    """Format a consistent, calm empty state card with optional next step."""
    parts = [f"*{sanitize_markdown(title)}*", message.strip()]
    if action_hint:
        parts.append(f"Next step: {action_hint.strip()}")
    return "\n\n".join(parts)


def format_error_state(
    message: Optional[str] = None,
    action_hint: Optional[str] = None,
) -> str:
    """Format a calm, human-readable error recovery message."""
    body = message.strip() if message else "Something went wrong while loading this content. Please try again."
    if action_hint:
        return f"{body}\n\n{action_hint.strip()}"
    return body

