"""Unit and integration tests for Stage 6: Technology Trend Analysis, Radar, and Learning Hub."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Chat, Message, Update, User
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.handlers.automation import (
    automation_callback_router,
    radar_command,
    velocity_command,
)
from app.bot.handlers.base import main_menu_callback_router
from app.bot.keyboards.inline import (
    get_projects_hub_keyboard,
    get_tech_radar_keyboard,
)
from app.bot.ui.formatters import (
    format_project_recommendation,
    format_tech_radar,
    format_trend_velocity,
)
from app.database.models import Source
from app.database.repository import Repository
from app.services.ai import ai_service
from app.services.automation_service import automation_service


@pytest.fixture
def mock_bot_user():
    user = MagicMock(spec=User)
    user.id = 778899
    user.first_name = "Alan"
    return user


@pytest.fixture
def mock_radar_update(mock_bot_user):
    update = MagicMock(spec=Update)
    chat = MagicMock(spec=Chat)
    chat.id = mock_bot_user.id

    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()
    message.edit_text = AsyncMock()

    update.effective_user = mock_bot_user
    update.effective_chat = chat
    update.effective_message = message
    update.callback_query = None
    return update


@pytest.fixture
def mock_radar_context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    return context


# ------------------ 1. Keyboard Structure & Highlighting Tests ------------------


def test_get_tech_radar_keyboard_highlighting():
    """Verify Tech Radar keyboard renders 4 horizons, refresh, and highlights active horizon."""
    # Default: "all"
    kb_all = get_tech_radar_keyboard("all")
    all_btn_text = kb_all.inline_keyboard[2][0].text
    assert "• " in all_btn_text
    assert "Full Radar" in all_btn_text

    # Adopt selected
    kb_adopt = get_tech_radar_keyboard("adopt")
    adopt_btn = kb_adopt.inline_keyboard[0][0]
    assert "• " in adopt_btn.text
    assert "Adopt" in adopt_btn.text
    assert adopt_btn.callback_data == "radar_h:adopt"

    # Trial selected
    kb_trial = get_tech_radar_keyboard("trial")
    trial_btn = kb_trial.inline_keyboard[0][1]
    assert "• " in trial_btn.text
    assert "Trial" in trial_btn.text
    assert trial_btn.callback_data == "radar_h:trial"

    # Assess selected
    kb_assess = get_tech_radar_keyboard("assess")
    assess_btn = kb_assess.inline_keyboard[1][0]
    assert "• " in assess_btn.text
    assert "Assess" in assess_btn.text
    assert assess_btn.callback_data == "radar_h:assess"

    # Hold selected
    kb_hold = get_tech_radar_keyboard("hold")
    hold_btn = kb_hold.inline_keyboard[1][1]
    assert "• " in hold_btn.text
    assert "Hold" in hold_btn.text
    assert hold_btn.callback_data == "radar_h:hold"

    # Main menu button present in last row
    assert kb_all.inline_keyboard[3][0].callback_data == "menu:home"


def test_get_projects_hub_keyboard():
    """Verify projects hub keyboard provides domain buttons and home navigation."""
    kb = get_projects_hub_keyboard()
    flattened_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]

    assert "prj_topic:Artificial Intelligence" in flattened_data
    assert "prj_topic:Robotics" in flattened_data
    assert "prj_topic:Cybersecurity" in flattened_data
    assert "prj_topic:Embedded Systems" in flattened_data
    assert "prj_topic:Software Architecture" in flattened_data
    assert "prj_topic:Quantum Computing" in flattened_data
    assert "menu:home" in flattened_data


# ------------------ 2. Tech Radar & Trend Velocity Formatters ------------------


def test_format_tech_radar_horizons():
    """Verify format_tech_radar outputs specific content for each horizon."""
    # Full Radar
    text_all = format_tech_radar("all")
    assert "STEM Technology Radar" in text_all
    assert "ADOPT:" in text_all
    assert "TRIAL:" in text_all
    assert "ASSESS:" in text_all
    assert "HOLD:" in text_all

    # Adopt
    text_adopt = format_tech_radar("adopt")
    assert "ADOPT Horizon" in text_adopt
    assert "LLM Orchestration & Vector RAG" in text_adopt
    assert "PyTorch 2.x" in text_adopt
    assert "FlashAttention-2" in text_adopt

    # Trial
    text_trial = format_tech_radar("trial")
    assert "TRIAL Horizon" in text_trial
    assert "Vision-Language-Action (VLA)" in text_trial
    assert "Locomotion" in text_trial

    # Assess
    text_assess = format_tech_radar("assess")
    assert "ASSESS Horizon" in text_assess
    assert "Quantum Error Mitigation" in text_assess
    assert "Brain-Computer Interfaces" in text_assess

    # Hold
    text_hold = format_tech_radar("hold")
    assert "HOLD Horizon" in text_hold
    assert "Monolithic RNNs" in text_hold
    assert "Proprietary Closed Formats" in text_hold


def test_format_tech_radar_with_velocities_and_articles():
    """Verify format_tech_radar embeds dynamic domain signals when supplied."""
    velocities = {
        "ai": {
            "name": "Artificial Intelligence",
            "momentum": "🔥 Surging",
            "count": 12,
            "paper_count": 5,
        },
        "robotics": {
            "name": "Robotics",
            "momentum": "📈 Rising",
            "count": 4,
            "paper_count": 2,
        },
    }
    text = format_tech_radar("all", domain_velocities=velocities)
    assert "Empirical Domain Velocity Signals:" in text
    assert "Artificial Intelligence*: 🔥 Surging (`12` articles, `5` papers)" in text
    assert "Robotics*: 📈 Rising (`4` articles, `2` papers)" in text


def test_format_trend_velocity():
    """Verify format_trend_velocity accurately formats domain velocity indicators."""
    velocities = {
        "ai": {
            "name": "Artificial Intelligence",
            "momentum": "🔥 Surging",
            "count": 10,
            "paper_count": 4,
            "avg_score": 75.5,
            "top_headline": "DeepSeek-V3 Open Model Benchmark",
        }
    }
    formatted = format_trend_velocity(velocities)
    assert "STEM Domain Trend Velocity & Momentum Analysis" in formatted
    assert "Artificial Intelligence" in formatted
    assert "Momentum: *🔥 Surging*" in formatted
    assert "Indexed Articles: `10` (Research Papers: `4`)" in formatted
    assert "Avg Intelligence Score: `75.5/100`" in formatted
    assert "Top Signal: _DeepSeek-V3 Open Model Benchmark_" in formatted


# ------------------ 3. Velocity Calculation Engine ------------------


@pytest.mark.asyncio
async def test_calculate_domain_velocity_with_database(test_session_factory):
    """Test calculate_domain_velocity accurately aggregates articles, arXiv papers, and momentum."""
    async with test_session_factory() as session:
        repo = Repository(session)
        cats = await repo.get_categories()
        ai_cat = next(c for c in cats if c.slug == "ai")

        # Create arXiv source and standard source with unique slugs
        arxiv_source = Source(
            name="arXiv cs.AI Unique",
            slug="arxiv-unique-ai",
            url="https://arxiv.org/unique",
            source_type="arxiv",
            is_active=True,
        )
        tech_source = Source(
            name="TechCrunch Unique",
            slug="tc-unique-news",
            url="https://techcrunch.com/unique",
            source_type="rss",
            is_active=True,
        )
        session.add(arxiv_source)
        session.add(tech_source)
        await session.commit()

        # Add 4 articles for AI (2 papers, 2 news)
        for i in range(4):
            src = arxiv_source if i < 2 else tech_source
            await repo.save_article(
                title=f"AI Deep Learning Model Breakthrough {i}",
                url=f"https://example.com/ai-{i}",
                source_id=src.id,
                description="Transformer attention and state-of-the-art benchmark results.",
                category_ids=[ai_cat.id],
            )

        velocities = await automation_service.calculate_domain_velocity(session=session)

        assert "ai" in velocities
        ai_data = velocities["ai"]
        assert ai_data["count"] == 4
        assert ai_data["paper_count"] == 2
        assert ai_data["avg_score"] > 0
        assert ai_data["momentum"] in ("🔥 Surging", "📈 Rising")


# ------------------ 4. Project Idea Generator & Fields ------------------


@pytest.mark.asyncio
async def test_project_recommendation_domain_aware_fields():
    """Verify recommend_project generates required skills, materials, and cost estimates."""
    # Robotics
    rob_proj = await ai_service.recommend_project("robotics")
    assert rob_proj.required_skills
    assert any("ROS" in s or "Kinematics" in s or "Python" in s for s in rob_proj.required_skills)
    assert rob_proj.components_and_materials
    assert "Gazebo" in rob_proj.components_and_materials[1] or "ESP32" in str(rob_proj.components_and_materials)
    assert "simulation" in rob_proj.estimated_cost or "$0" in rob_proj.estimated_cost

    # Quantum
    q_proj = await ai_service.recommend_project("quantum computing")
    assert any("Quantum" in s or "Linear Algebra" in s for s in q_proj.required_skills)
    assert any("Qiskit" in m or "IBM" in m for m in q_proj.components_and_materials)

    # General Formatting
    formatted = format_project_recommendation(rob_proj)
    assert "Portfolio Project:" in formatted
    assert "Required Skills:" in formatted
    assert "Components & Materials:" in formatted
    assert "Estimated Budget & Assumptions:" in formatted
    assert "System Architecture:" in formatted
    assert "Recommended Tech Stack:" in formatted


# ------------------ 5. Commands and Interactive Callbacks ------------------


@pytest.mark.asyncio
async def test_radar_command_execution(mock_radar_update, mock_radar_context):
    """Test /radar command replies with radar text and interactive keyboard."""
    with patch.object(automation_service, "calculate_domain_velocity", new_callable=AsyncMock) as mock_vel:
        mock_vel.return_value = {"ai": {"name": "AI", "momentum": "🔥 Surging", "count": 5, "paper_count": 2}}
        await radar_command(mock_radar_update, mock_radar_context)

    mock_radar_update.effective_message.reply_text.assert_called_once()
    call_args = mock_radar_update.effective_message.reply_text.call_args
    assert "STEM Technology Radar" in call_args[0][0]
    assert call_args[1]["parse_mode"] == ParseMode.MARKDOWN
    assert call_args[1]["reply_markup"] is not None


@pytest.mark.asyncio
async def test_velocity_command_execution(mock_radar_update, mock_radar_context):
    """Test /velocity command replies with trend momentum analysis."""
    with patch.object(automation_service, "calculate_domain_velocity", new_callable=AsyncMock) as mock_vel:
        mock_vel.return_value = {
            "robotics": {
                "name": "Robotics",
                "momentum": "📈 Rising",
                "count": 3,
                "paper_count": 1,
                "avg_score": 62.0,
                "top_headline": "Humanoid Actuator",
            }
        }
        await velocity_command(mock_radar_update, mock_radar_context)

    mock_radar_update.effective_message.reply_text.assert_called_once()
    text = mock_radar_update.effective_message.reply_text.call_args[0][0]
    assert "Trend Velocity & Momentum Analysis" in text
    assert "Robotics" in text


@pytest.mark.asyncio
async def test_automation_callback_router_radar_horizon(mock_radar_update, mock_radar_context):
    """Test switching radar horizon in-place via automation_callback_router."""
    query = MagicMock()
    query.data = "radar_h:trial"
    query.answer = AsyncMock()
    query.message = MagicMock()
    query.message.edit_text = AsyncMock()
    mock_radar_update.callback_query = query

    with patch.object(automation_service, "calculate_domain_velocity", new_callable=AsyncMock) as mock_vel:
        mock_vel.return_value = {}
        await automation_callback_router(mock_radar_update, mock_radar_context)

    query.answer.assert_called_once()
    query.message.edit_text.assert_called_once()
    call_args = query.message.edit_text.call_args
    call_text = call_args[0][0] if call_args[0] else call_args[1].get("text", "")
    assert "TRIAL Horizon" in call_text


@pytest.mark.asyncio
async def test_main_menu_callback_router_projects_and_topics(mock_radar_update, mock_radar_context):
    """Test menu:projects displays projects hub and prj_topic generates project idea."""
    query = MagicMock()
    query.data = "menu:projects"
    query.answer = AsyncMock()
    query.message = MagicMock()
    query.message.edit_text = AsyncMock()
    mock_radar_update.callback_query = query

    # 1. Tap menu:projects
    await main_menu_callback_router(mock_radar_update, mock_radar_context)
    query.message.edit_text.assert_called_once()
    text = query.message.edit_text.call_args[1]["text"]
    assert "Portfolio Project Generator" in text

    # 2. Tap prj_topic:Robotics
    query.data = "prj_topic:Robotics"
    query.message.edit_text.reset_mock()
    await main_menu_callback_router(mock_radar_update, mock_radar_context)
    query.message.edit_text.assert_called_once()
    text2 = query.message.edit_text.call_args[1]["text"]
    assert "Portfolio Project:" in text2
    assert "robotics" in text2.lower()


@pytest.mark.asyncio
async def test_main_menu_callback_router_learn_quiz_and_compare(mock_radar_update, mock_radar_context):
    """Test menu:learn_quiz and menu:learn_compare from the Learning Academy menu."""
    query = MagicMock()
    query.data = "menu:learn_quiz"
    query.answer = AsyncMock()
    query.message = MagicMock()
    query.message.edit_text = AsyncMock()
    mock_radar_update.callback_query = query

    # 1. Quiz callback
    await main_menu_callback_router(mock_radar_update, mock_radar_context)
    query.message.edit_text.assert_called_once()
    text = query.message.edit_text.call_args[1]["text"]
    assert "Interactive STEM Quiz" in text or "Quiz" in text

    # 2. Compare callback
    query.data = "menu:learn_compare"
    query.message.edit_text.reset_mock()
    await main_menu_callback_router(mock_radar_update, mock_radar_context)
    query.message.edit_text.assert_called_once()
    text2 = query.message.edit_text.call_args[1]["text"]
    assert "Architectural Concept Comparison" in text2
