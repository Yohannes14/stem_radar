"""Tests for research paper intelligence, peer-review deep dives, and multi-tier STEM explanations."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import CallbackQuery, Chat, Message, Update, User

from app.bot.handlers.news import callback_router, explain_command, research_command
from app.bot.keyboards.inline import (
    get_article_keyboard,
    get_concept_mode_keyboard,
    get_paper_analysis_keyboard,
)
from app.bot.ui.formatters import format_concept_explanation, format_paper_analysis
from app.bot.ui.menu import format_research_hub_intro, get_research_hub_keyboard
from app.config import settings
from app.database.models import Article, Category, Source
from app.services.ai import ai_service


@pytest.fixture
def sample_arxiv_paper():
    """Create a sample arXiv research paper model."""
    source = Source(id=5, name="arXiv AI", slug="arxiv-ai", url="https://export.arxiv.org", source_type="arxiv")
    cat = Category(id=1, name="Artificial Intelligence", slug="ai")

    article = Article(
        id=101,
        title="Sparse Transformer Attention via Dynamic Kernel Pruning",
        url="https://arxiv.org/abs/2611.10101",
        url_hash="arxivhash101",
        description=(
            "We propose a dynamic kernel pruning algorithm for transformer models. "
            "Experiments show that our framework achieves a 4.2x speedup over dense baselines. "
            "However, memory bandwidth challenges remain under variable sequence lengths."
        ),
        source_id=5,
    )
    article.source = source
    article.categories = [cat]
    return article


@pytest.fixture
def mock_explainer_update():
    """Mock Telegram update for concept explanations."""
    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = 334455
    user.first_name = "Richard"
    user.username = "rfeynman"

    chat = MagicMock(spec=Chat)
    chat.id = 334455

    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()
    message.edit_text = AsyncMock()

    query = MagicMock(spec=CallbackQuery)
    query.id = "query_exp_1"
    query.data = "ai_paper:101"
    query.message = message
    query.answer = AsyncMock()

    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = message
    update.callback_query = query
    return update


@pytest.mark.asyncio
async def test_deep_research_paper_analysis(sample_arxiv_paper):
    """Verify research paper analysis extracts all 6 scientific dimensions."""
    analysis = await ai_service.analyze_research_paper(sample_arxiv_paper)

    assert analysis.paper_title == sample_arxiv_paper.title
    assert "transformer" in analysis.research_problem.lower()
    assert "pruning" in analysis.methodology.lower() or "approach" in analysis.methodology.lower()
    assert len(analysis.main_findings) >= 1
    assert len(analysis.limitations) >= 1
    assert len(analysis.practical_applications) >= 1
    assert len(analysis.further_research_questions) >= 1

    formatted = format_paper_analysis(analysis)
    assert "Research Paper Analysis" in formatted
    assert "Research problem" in formatted
    assert "Methodology" in formatted
    assert "Main findings" in formatted
    assert "Limitations" in formatted
    assert "Practical applications" in formatted
    assert "Open questions" in formatted
    assert "AI-assisted summary" in formatted
    assert "does not substitute for reading the original research paper" in formatted


@pytest.mark.asyncio
async def test_multi_tier_concept_explanations():
    """Verify concept explanations tailor depth to beginner, intermediate, and advanced audiences."""
    concept = "Transformer Architecture"

    # 1. Beginner mode: should contain intuitive metaphor / analogy
    beg = await ai_service.explain_concept(concept, mode="beginner")
    assert beg.mode == "beginner"
    assert len(beg.analogy_or_example) > 20
    assert "Attention" in str(beg.key_components)

    # 2. Intermediate mode: architecture and trade-offs
    inter = await ai_service.explain_concept(concept, mode="intermediate")
    assert inter.mode == "intermediate"
    assert "framework" in inter.core_definition.lower() or "technical" in inter.core_definition.lower()

    # 3. Advanced mode: mathematical, algorithmic, asymptotic
    adv = await ai_service.explain_concept(concept, mode="advanced")
    assert adv.mode == "advanced"
    assert "algorithmic" in adv.core_definition.lower() or "paradigm" in adv.core_definition.lower()

    formatted_adv = format_concept_explanation(adv)
    assert "Advanced" in formatted_adv
    assert "Key components:" in formatted_adv


def test_paper_and_concept_keyboards():
    """Verify paper analysis and standalone concept mode switcher keyboards."""
    paper_kb = get_paper_analysis_keyboard(article_id=101, is_saved=False)
    assert len(paper_kb.inline_keyboard) == 3
    assert paper_kb.inline_keyboard[0][0].callback_data == "ai_exp:101"
    assert paper_kb.inline_keyboard[0][1].callback_data == "rel:101"
    assert paper_kb.inline_keyboard[1][0].callback_data == "save:101"
    assert paper_kb.inline_keyboard[1][0].text == "Save"
    assert paper_kb.inline_keyboard[1][1].callback_data == "menu:arxiv_papers"
    assert paper_kb.inline_keyboard[2][0].callback_data == "back_art:101"
    assert paper_kb.inline_keyboard[2][1].callback_data == "menu:home"

    saved_kb = get_paper_analysis_keyboard(article_id=101, is_saved=True)
    assert saved_kb.inline_keyboard[1][0].text == "Saved"

    concept_kb = get_concept_mode_keyboard(concept_name="Quantum Entanglement", current_mode="intermediate")
    assert len(concept_kb.inline_keyboard) == 2
    mode_row = concept_kb.inline_keyboard[0]
    assert "Beginner" in mode_row[0].text
    assert "Intermediate" in mode_row[1].text
    assert "•" in mode_row[1].text
    assert "Advanced" in mode_row[2].text


def test_article_keyboard_identifies_paper_action(sample_arxiv_paper):
    """Verify arXiv papers show 'Analyze Paper' instead of generic 'Explain' and route back to Research Hub."""
    kb = get_article_keyboard(
        article_id=sample_arxiv_paper.id,
        url=sample_arxiv_paper.url,
        offset=0,
        total=1,
        category_slug="ai",
        is_paper=True,
    )
    first_row = kb.inline_keyboard[0]
    assert first_row[1].text == "Analyze Paper"
    assert first_row[1].callback_data == f"ai_paper:{sample_arxiv_paper.id}"

    fourth_row = kb.inline_keyboard[3]
    assert fourth_row[0].text == "Research Hub"
    assert fourth_row[0].callback_data == "menu:research"


@pytest.mark.asyncio
async def test_explain_command_with_switcher(mock_explainer_update):
    """Verify /explain outputs concept explanation with interactive mode switcher."""
    mock_explainer_update.callback_query = None
    context = MagicMock()
    context.args = ["Direct", "Drive", "Actuators"]

    with patch.object(settings, "allowed_user_ids", [334455]):
        await explain_command(mock_explainer_update, context)

    mock_explainer_update.effective_message.reply_text.assert_called_once()
    status_msg = mock_explainer_update.effective_message.reply_text.return_value

    status_msg.edit_text.assert_called_once()
    edit_call = status_msg.edit_text.call_args
    text = edit_call[0][0]
    markup = edit_call[1]["reply_markup"]

    assert "Direct Drive Actuators" in text
    assert "Definition" in text
    assert len(markup.inline_keyboard) == 2


@pytest.mark.asyncio
async def test_callback_router_handles_paper_analysis(mock_explainer_update, sample_arxiv_paper):
    """Verify callback ai_paper:<id> generates and renders deep scientific analysis."""
    mock_explainer_update.callback_query.data = f"ai_paper:{sample_arxiv_paper.id}"

    with patch("app.bot.handlers.news.news_service.get_article_by_id", AsyncMock(return_value=sample_arxiv_paper)):
        with patch.object(settings, "allowed_user_ids", [334455]):
            await callback_router(mock_explainer_update, MagicMock())

    mock_explainer_update.callback_query.message.edit_text.assert_called_once()
    edit_call = mock_explainer_update.callback_query.message.edit_text.call_args[1]
    assert "Research Paper Analysis" in edit_call["text"]


@pytest.mark.asyncio
async def test_callback_router_switches_concept_mode(mock_explainer_update):
    """Verify callback c_mode:<concept>:<mode> switches explanation difficulty level."""
    mock_explainer_update.callback_query.data = "c_mode:Quantum Computing:advanced"

    with patch.object(settings, "allowed_user_ids", [334455]):
        await callback_router(mock_explainer_update, MagicMock())

    mock_explainer_update.callback_query.message.edit_text.assert_called_once()
    edit_call = mock_explainer_update.callback_query.message.edit_text.call_args[1]
    assert "Advanced" in edit_call["text"]


@pytest.mark.asyncio
async def test_paper_analysis_with_code_repository():
    """Verify research paper analysis extracts and formats code/artifact repository links."""
    source = Source(id=5, name="arXiv AI", slug="arxiv-ai", url="https://export.arxiv.org", source_type="arxiv")
    cat = Category(id=1, name="Artificial Intelligence", slug="ai")

    article = Article(
        id=102,
        title="Open-Source Efficient Vision Transformers",
        url="https://arxiv.org/abs/2611.10102",
        url_hash="arxivhash102",
        description=(
            "We introduce an open framework for vision transformers. "
            "Our model runs 2x faster with half the memory footprint. "
            "Code and weights available at https://github.com/stem-radar/vision-transformer."
        ),
        source_id=5,
    )
    article.source = source
    article.categories = [cat]

    analysis = await ai_service.analyze_research_paper(article)
    assert analysis.code_repository_url == "https://github.com/stem-radar/vision-transformer"

    formatted = format_paper_analysis(analysis)
    assert "Code & Replication Repository" in formatted
    assert "https://github.com/stem-radar/vision-transformer" in formatted


def test_research_hub_intro_and_keyboards():
    """Verify Research Hub introduction and sub-discipline keyboard buttons."""
    intro = format_research_hub_intro()
    assert "Research & Innovation" in intro
    assert "do not replace reading the original publication" in intro

    res_kb = get_research_hub_keyboard()
    callbacks = [btn.callback_data for row in res_kb.inline_keyboard for btn in row]
    assert "menu:arxiv_papers" in callbacks
    assert "menu:radar" in callbacks
    assert "arxiv_cat:ai" in callbacks
    assert "arxiv_cat:robotics" in callbacks
    assert "arxiv_cat:computer-science" in callbacks
    assert "menu:ai_explain" in callbacks
    assert "menu:ai_impact" in callbacks
    assert "menu:home" in callbacks


@pytest.mark.asyncio
async def test_research_command_with_subcategories(mock_explainer_update):
    """Verify /research command supports category shortcuts and direct topic searches."""
    mock_explainer_update.callback_query = None
    context = MagicMock()

    with patch.object(settings, "allowed_user_ids", [334455]):
        with patch("app.bot.handlers.news.send_article_view", AsyncMock()) as mock_send:
            # 1. No arguments: all arXiv papers
            context.args = []
            await research_command(mock_explainer_update, context)
            mock_send.assert_called_with(mock_explainer_update, source_type="arxiv", offset=0)

            # 2. Category shortcut: /research ai
            mock_send.reset_mock()
            context.args = ["ai"]
            await research_command(mock_explainer_update, context)
            mock_send.assert_called_with(mock_explainer_update, source_type="arxiv", category_slug="ai", offset=0)

            # 3. Category shortcut: /research robotics
            mock_send.reset_mock()
            context.args = ["robotics"]
            await research_command(mock_explainer_update, context)
            mock_send.assert_called_with(mock_explainer_update, source_type="arxiv", category_slug="robotics", offset=0)

            # 4. Search query: /research dynamic kernel pruning
            mock_send.reset_mock()
            context.args = ["dynamic", "kernel", "pruning"]
            await research_command(mock_explainer_update, context)
            mock_send.assert_called_with(
                mock_explainer_update, source_type="arxiv", query="dynamic kernel pruning", offset=0
            )


@pytest.mark.asyncio
async def test_callback_router_handles_arxiv_category_and_nav(mock_explainer_update):
    """Verify arxiv_cat: and nav:arxiv pagination callbacks route correctly."""
    with patch.object(settings, "allowed_user_ids", [334455]):
        with patch("app.bot.handlers.news.send_article_view", AsyncMock()) as mock_send:
            # arxiv_cat:ai
            mock_explainer_update.callback_query.data = "arxiv_cat:ai"
            await callback_router(mock_explainer_update, MagicMock())
            mock_send.assert_called_with(
                mock_explainer_update, source_type="arxiv", category_slug="ai", offset=0, is_edit=True
            )

            # nav:arxiv:2
            mock_send.reset_mock()
            mock_explainer_update.callback_query.data = "nav:arxiv:2"
            await callback_router(mock_explainer_update, MagicMock())
            mock_send.assert_called_with(mock_explainer_update, source_type="arxiv", offset=2, is_edit=True)

            # nav:arxiv_robotics:1
            mock_send.reset_mock()
            mock_explainer_update.callback_query.data = "nav:arxiv_robotics:1"
            await callback_router(mock_explainer_update, MagicMock())
            mock_send.assert_called_with(
                mock_explainer_update, source_type="arxiv", category_slug="robotics", offset=1, is_edit=True
            )


@pytest.mark.asyncio
async def test_save_callback_preserves_paper_analysis_view(mock_explainer_update, sample_arxiv_paper):
    """Verify toggling bookmark on paper analysis re-renders paper analysis keyboard."""
    mock_explainer_update.callback_query.data = f"save:{sample_arxiv_paper.id}"
    mock_explainer_update.callback_query.message.text = "Research Paper Analysis\n\nTitle..."

    with patch.object(settings, "allowed_user_ids", [334455]):
        with patch("app.bot.handlers.news.news_service.toggle_save_article", AsyncMock(return_value=True)):
            with patch(
                "app.bot.handlers.news.news_service.get_article_by_id", AsyncMock(return_value=sample_arxiv_paper)
            ):
                await callback_router(mock_explainer_update, MagicMock())

    mock_explainer_update.callback_query.message.edit_reply_markup.assert_called_once()
    new_markup = mock_explainer_update.callback_query.message.edit_reply_markup.call_args[1]["reply_markup"]
    assert new_markup.inline_keyboard[0][0].callback_data == f"ai_exp:{sample_arxiv_paper.id}"
    assert new_markup.inline_keyboard[1][0].text == "Saved"
    assert new_markup.inline_keyboard[1][1].callback_data == "menu:arxiv_papers"
