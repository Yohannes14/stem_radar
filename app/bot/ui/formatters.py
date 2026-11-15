"""Presentation layer formatters generating clean, compliant Telegram markdown messages."""

import html
import re
from typing import List

CATEGORY_EMOJIS = {
    "ai": "🤖",
    "machine-learning": "🧠",
    "robotics": "🦾",
    "computer-science": "💻",
    "software-engineering": "⚙️",
    "cybersecurity": "🛡️",
    "electronics": "⚡",
    "embedded-systems": "📟",
    "iot": "🌐",
    "mechanical-engineering": "🔧",
    "electrical-engineering": "🔌",
    "biotechnology": "🧬",
    "physics": "⚛️",
    "chemistry": "🧪",
    "mathematics": "📐",
    "space-technology": "🚀",
    "renewable-energy": "🌱",
    "stem-education": "🎓",
    "emerging-tech": "🔮",
}


def sanitize_markdown(text: str) -> str:
    """Strip or escape raw markdown characters that could break Telegram rendering."""
    if not text:
        return ""
    cleaned = html.unescape(text)
    # Remove troublesome markdown syntax in uncontrolled text
    cleaned = cleaned.replace("*", "").replace("_", " ").replace("`", "")
    return re.sub(r"\s+", " ", cleaned).strip()


def format_article_view(article, index: int = 0, total: int = 1) -> str:
    """Format an article into a clean mobile-friendly Telegram card."""
    source_name = sanitize_markdown(article.source.name if article.source else "Unknown")
    cat_names = [c.name for c in article.categories] if article.categories else ["Technology"]
    cat_display = ", ".join(cat_names[:2])

    primary_slug = article.categories[0].slug if article.categories else "ai"
    emoji = CATEGORY_EMOJIS.get(primary_slug, "📡")

    pub_date = article.published_at or article.collected_at
    date_str = pub_date.strftime("%b %d, %Y") if pub_date else "Recent"

    safe_title = sanitize_markdown(article.title)

    raw_desc = article.description or "No preview available."
    safe_desc = sanitize_markdown(raw_desc)
    if len(safe_desc) > 380:
        safe_desc = safe_desc[:377].rsplit(" ", 1)[0] + "..."

    return f"{emoji} *{cat_display}* | _{source_name}_\n📅 {date_str}\n\n*{safe_title}*\n\n{safe_desc}\n"


def format_search_results(query: str, articles: list) -> str:
    """Format article search results list."""
    if not articles:
        return f'🔍 No articles found matching *"{sanitize_markdown(query)}"*\n\nTry `/collect` to pull new articles.'

    lines = [f'🔍 *Search Results for "{sanitize_markdown(query)}":*\n']
    for i, a in enumerate(articles, 1):
        clean_title = sanitize_markdown(a.title)
        source = sanitize_markdown(a.source.name if a.source else "Tech")
        lines.append(f"{i}. [{clean_title}]({a.url})\nSource: _{source}_\n")
    return "\n".join(lines)


def format_sources_list(sources: list) -> str:
    """Format configured intelligence sources view."""
    if not sources:
        return "No sources configured yet."

    lines = ["📡 *Configured Intelligence Sources:*\n"]
    for s in sources:
        status = "🟢 Active" if s.is_active else "🔴 Inactive"
        lines.append(f"• *{s.name}* (`{s.source_type}`)\n  Status: {status}\n  URL: `{s.url}`\n")
    lines.append("Use `/collect` to fetch updates immediately.")
    return "\n".join(lines)


def chunk_message(text: str, max_length: int = 4000) -> List[str]:
    """Split long messages into chunks that strictly adhere to Telegram's 4096-char limit."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    lines = text.split("\n")
    current_chunk = []
    current_len = 0

    for line in lines:
        if current_len + len(line) + 1 > max_length:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_len = len(line) + 1
        else:
            current_chunk.append(line)
            current_len += len(line) + 1

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks
