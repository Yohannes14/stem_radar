"""Unit and regression tests for the STEM RADAR editorial UI design system."""

import re
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Update

from app.bot.handlers.base import error_handler
from app.bot.keyboards.inline import (
    get_article_keyboard,
    get_explanation_keyboard,
    get_settings_panel_keyboard,
)
from app.bot.keyboards.student_hub import get_student_hub_keyboard
from app.bot.ui.design_system import (
    AI_EDITORIAL_STYLE_INSTRUCTION,
    format_ai_notice,
    format_date,
    format_datetime,
    format_empty_state,
    format_error_state,
    format_header,
    format_meta,
    format_section,
    format_status,
    sanitize_markdown,
)
from app.bot.ui.formatters import format_article_view, format_related_articles
from app.bot.ui.menu import format_main_menu, get_main_menu_keyboard
from app.services.student_hub_service import StudentHubService

# Broad Unicode emoji pattern matching pictographs, symbols, flags, and keycaps.
EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FAFF"
    r"\U00002600-\U000027BF"
    r"\U0001F1E6-\U0001F1FF"
    r"\uFE0F]"
)


def _flatten_keyboard_labels(markup) -> list[str]:
    return [btn.text for row in markup.inline_keyboard for btn in row]


# ---------------------------------------------------------------------------
# Design system helpers
# ---------------------------------------------------------------------------


def test_sanitize_markdown_strips_control_chars_and_unescapes_html():
    raw = "  *Breaking* _AI_ `Model` &amp; New\n\tResults  "
    assert sanitize_markdown(raw) == "Breaking AI Model & New Results"
    assert sanitize_markdown(None) == ""
    assert sanitize_markdown("") == ""


def test_format_date_and_datetime():
    dt = datetime(2026, 3, 5, 9, 7, tzinfo=timezone.utc)
    assert format_date(dt) == "5 Mar 2026"
    assert format_date(None, fallback="Unknown") == "Unknown"
    assert format_datetime(dt) == "5 Mar, 09:07 UTC"
    assert format_datetime(None) == "Never"


def test_format_header_with_and_without_subtitle():
    assert format_header("AI_Research *Weekly*") == "*AI Research Weekly*"
    assert format_header("Technology Radar", "Curated engineering briefs") == (
        "*Technology Radar*\nCurated engineering briefs"
    )


def test_format_meta_omits_empty_values():
    rendered = format_meta(
        [
            ("Source", "MIT Tech Review"),
            ("Published", ""),
            ("Author", None),
            ("Category", "Artificial Intelligence"),
        ]
    )
    assert rendered == "Source: MIT Tech Review\nCategory: Artificial Intelligence"


def test_format_section_string_and_list_and_empty():
    assert format_section("Overview", "Concise summary.") == "*Overview*\nConcise summary."
    assert format_section("Key Points", ["First *point*", "", "Second_point"]) == (
        "*Key Points*\n- First point\n- Second point"
    )
    assert format_section("Empty", "") == ""
    assert format_section("Empty List", ["", "   "]) == ""
    assert format_section("None", None) == ""


def test_format_status_variants():
    assert format_status("Open") == "Open"
    assert format_status("Degraded", "2 errors") == "Degraded (2 errors)"


def test_format_ai_notice_variants():
    assert "original source" in format_ai_notice("general")
    assert "original research paper" in format_ai_notice("paper")
    assert "official provider portal" in format_ai_notice("opportunity")
    assert "do not use emojis" in AI_EDITORIAL_STYLE_INSTRUCTION.lower()


def test_format_empty_and_error_states():
    empty = format_empty_state("Saved Items", "No saved items yet.", "Select Save on an article.")
    assert "*Saved Items*" in empty
    assert "Next step: Select Save on an article." in empty

    err = format_error_state()
    assert "Something went wrong" in err
    err_hint = format_error_state("Could not load feed.", "Return to Home.")
    assert err_hint == "Could not load feed.\n\nReturn to Home."


# ---------------------------------------------------------------------------
# Bug-fix & UX regression tests
# ---------------------------------------------------------------------------


def test_explanation_keyboard_default_mode_marks_intermediate():
    """Regression: previously defaulted to 'interm      ediate' typo."""
    kb = get_explanation_keyboard(article_id=42)
    labels = _flatten_keyboard_labels(kb)
    assert "• Intermediate" in labels
    assert "Beginner" in labels
    assert "Advanced" in labels


def test_format_related_articles_has_balanced_italics():
    """Regression: previously left an unclosed italic underscore."""
    parent = SimpleNamespace(title="Attention Is All You Need")
    rel = [
        SimpleNamespace(
            title="FlashAttention-3",
            url="https://example.com/fa3",
            source=SimpleNamespace(name="arXiv"),
            description="Fast exact attention.",
        )
    ]
    text = format_related_articles(parent, rel)
    assert text.count("_") % 2 == 0
    assert "_Attention Is All You Need_" in text


def test_format_article_view_omits_generic_boilerplate():
    """Regression: never fabricate generic 'Why it matters' filler when no analysis exists."""
    article = SimpleNamespace(
        title="Sparse Autoencoders for Mechanistic Interpretability",
        url="https://example.com/sae",
        description="A concise single-sentence abstract.",
        content=None,
        ai_summary=None,
        ai_analysis=None,
        published_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
        collected_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
        source=SimpleNamespace(name="arXiv"),
        categories=[SimpleNamespace(name="Artificial Intelligence")],
    )
    rendered = format_article_view(article)
    assert "Why it matters" not in rendered
    assert "This development highlights" not in rendered
    assert not EMOJI_RE.search(rendered)


@pytest.mark.asyncio
async def test_error_handler_sends_calm_recovery_message():
    """Regression: error_handler should reply with a calm recovery prompt instead of failing silently."""
    update = MagicMock(spec=Update)
    update.callback_query = None
    update.effective_message = MagicMock()
    update.effective_message.reply_text = AsyncMock()
    context = MagicMock()
    context.error = RuntimeError("database timeout")

    await error_handler(update, context)

    update.effective_message.reply_text.assert_awaited_once()
    call_args, call_kwargs = update.effective_message.reply_text.call_args
    msg_text = call_args[0] if call_args else call_kwargs.get("text", "")
    assert "Something went wrong" in msg_text
    assert not EMOJI_RE.search(msg_text)
    markup = call_kwargs.get("reply_markup")
    assert markup is not None
    assert "Home" in _flatten_keyboard_labels(markup)


# ---------------------------------------------------------------------------
# Zero decorative emoji presentation checks
# ---------------------------------------------------------------------------


def test_core_views_and_keyboards_have_zero_decorative_emojis():
    main_text = format_main_menu(user_name="Alex")
    assert not EMOJI_RE.search(main_text)

    scholarship = SimpleNamespace(
        id=1,
        title="DAAD Research Grants",
        provider_name="DAAD",
        country="Germany",
        study_level="phd",
        funding_type="fully_funded",
        stem_fields="Computer Science, Physics",
        eligible_nationalities="All international applicants",
        eligibility_criteria="International applicants with a Master's degree.",
        benefits="Monthly stipend, travel allowance, and health insurance.",
        required_documents="Transcripts, CV, research proposal.",
        application_opens_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        application_deadline=datetime(2026, 12, 15, tzinfo=timezone.utc),
        is_rolling=False,
        status="open",
        verification_tier="officially_verified",
        last_verified_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        official_url="https://daad.de/example",
        application_url="https://daad.de/apply",
        source_attribution="DAAD Official Portal",
    )
    card = StudentHubService().format_scholarship_card(scholarship)
    assert not EMOJI_RE.search(card)

    pref = SimpleNamespace(
        notifications_enabled=True,
        daily_digest_enabled=True,
        weekly_radar_enabled=True,
        quiet_hours_enabled=False,
        difficulty_level="intermediate",
        preferred_categories="ai,robotics",
    )
    keyboards = [
        get_main_menu_keyboard(),
        get_article_keyboard(
            article_id=1,
            url="https://example.com",
            offset=0,
            total=5,
            is_saved=False,
            is_paper=True,
        ),
        get_student_hub_keyboard(),
        get_settings_panel_keyboard(pref),
    ]
    for kb in keyboards:
        for label in _flatten_keyboard_labels(kb):
            assert not EMOJI_RE.search(label), f"Unexpected emoji in button label: {label!r}"
