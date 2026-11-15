"""Automated tests for Phase 4: STEM Learning Assistant (Roadmaps, Lessons, Quizzes, Progress)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Chat, Message, Update, User

from app.bot.handlers.education import (
    compare_command,
    education_callback_router,
    learn_command,
    progress_command,
    project_command,
    quiz_command,
    roadmap_command,
    vocabulary_command,
)
from app.config import settings
from app.database.repository import Repository
from app.services.ai import ai_service


@pytest.fixture
def mock_update():
    """Create a mock Telegram Update for educational commands."""
    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = 887766
    user.first_name = "Taylor"

    chat = MagicMock(spec=Chat)
    chat.id = 887766

    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()

    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = message
    update.callback_query = None
    return update


# ------------------ AI Service Education Capabilities Tests ------------------


@pytest.mark.asyncio
async def test_ai_service_generates_roadmap():
    roadmap = await ai_service.generate_roadmap("Quantum Computing")
    assert roadmap.topic == "Quantum Computing"
    assert len(roadmap.stages) == 4
    assert roadmap.estimated_duration_weeks >= 4
    assert len(roadmap.prerequisites) >= 1
    assert "Foundations" in roadmap.stages[0].title


@pytest.mark.asyncio
async def test_ai_service_generates_interactive_lesson():
    # 1. Beginner
    beg_lesson = await ai_service.generate_lesson("Transformer Architecture", level="beginner")
    assert beg_lesson.level == "beginner"
    assert len(beg_lesson.key_takeaways) >= 2
    assert beg_lesson.practical_exercise is not None

    # 2. Advanced
    adv_lesson = await ai_service.generate_lesson("Transformer Architecture", level="advanced")
    assert adv_lesson.level == "advanced"
    assert "Foundations" in adv_lesson.core_lesson or "###" in adv_lesson.core_lesson


@pytest.mark.asyncio
async def test_ai_service_generates_quiz():
    quiz = await ai_service.generate_quiz("Robotics Kinematics", difficulty="intermediate")
    assert quiz.topic == "Robotics Kinematics"
    assert len(quiz.questions) == 3
    for q in quiz.questions:
        assert len(q.options) == 4
        assert 0 <= q.correct_option_index <= 3
        assert len(q.explanation) > 10


@pytest.mark.asyncio
async def test_ai_service_compares_concepts():
    comp = await ai_service.compare_concepts("PyTorch", "JAX")
    assert comp.concept_a == "PyTorch"
    assert comp.concept_b == "JAX"
    assert len(comp.key_differences) >= 2
    assert len(comp.when_to_use_a) >= 1
    assert len(comp.when_to_use_b) >= 1
    assert comp.summary_verdict is not None


@pytest.mark.asyncio
async def test_ai_service_recommends_project():
    proj = await ai_service.recommend_project("Autonomous Drones", difficulty="intermediate")
    assert proj.topic == "Autonomous Drones"
    assert len(proj.tech_stack) >= 3
    assert len(proj.step_by_step_milestones) >= 3
    assert proj.portfolio_impact is not None


@pytest.mark.asyncio
async def test_ai_service_generates_vocabulary():
    glossary = await ai_service.generate_vocabulary("Cybersecurity")
    assert glossary.topic == "Cybersecurity"
    assert len(glossary.terms) >= 4
    for term in glossary.terms:
        assert len(term.term) > 0
        assert len(term.definition) > 10


# ------------------ Database Progress Tracking Tests ------------------


@pytest.mark.asyncio
async def test_repository_learning_progress_tracking(test_session_factory):
    async with test_session_factory() as session:
        repo = Repository(session)
        user_id = 12345

        # 1. Record lesson
        p1 = await repo.record_lesson_completion(user_id, topic="Robotics", level="beginner")
        assert p1.lessons_completed == 1
        assert p1.level == "beginner"

        # 2. Record another lesson on same topic
        p2 = await repo.record_lesson_completion(user_id, topic="Robotics", level="intermediate")
        assert p2.lessons_completed == 2
        assert p2.level == "intermediate"

        # 3. Record quiz completion
        p3 = await repo.record_quiz_completion(user_id, topic="Robotics", score=3, max_score=3)
        assert p3.quizzes_taken == 1
        assert p3.quiz_score_total == 3
        assert p3.quiz_score_max == 3

        # 4. Fetch history
        history = await repo.get_user_learning_history(user_id)
        assert len(history) == 1
        assert history[0].topic == "robotics"


# ------------------ Telegram Command Handler Tests ------------------


@pytest.mark.asyncio
async def test_learn_command_shows_domain_menu_when_no_args(mock_update):
    context = MagicMock()
    context.args = []
    with patch.object(settings, "allowed_user_ids", [887766]):
        await learn_command(mock_update, context)

    mock_update.effective_message.reply_text.assert_called_once()
    reply_text = mock_update.effective_message.reply_text.call_args[0][0]
    assert "Learning Academy" in reply_text


@pytest.mark.asyncio
async def test_learn_command_renders_lesson_and_tracks_progress(mock_update, test_session_factory):
    context = MagicMock()
    context.args = ["beginner", "Machine", "Learning"]

    with (
        patch.object(settings, "allowed_user_ids", [887766]),
        patch("app.bot.handlers.education.get_session_factory", return_value=test_session_factory),
    ):
        await learn_command(mock_update, context)

    assert mock_update.effective_message.reply_text.call_count >= 1

    # Verify progress was recorded in test DB
    async with test_session_factory() as session:
        repo = Repository(session)
        history = await repo.get_user_learning_history(887766)
        assert len(history) == 1
        assert history[0].lessons_completed == 1


@pytest.mark.asyncio
async def test_roadmap_command_renders_curriculum(mock_update):
    context = MagicMock()
    context.args = ["Deep", "Learning"]

    with patch.object(settings, "allowed_user_ids", [887766]):
        await roadmap_command(mock_update, context)

    assert mock_update.effective_message.reply_text.call_count >= 1


@pytest.mark.asyncio
async def test_quiz_command_renders_question_card(mock_update):
    context = MagicMock()
    context.args = ["AI"]

    with patch.object(settings, "allowed_user_ids", [887766]):
        await quiz_command(mock_update, context)

    assert mock_update.effective_message.reply_text.call_count >= 1


@pytest.mark.asyncio
async def test_compare_command_renders_matrix(mock_update):
    context = MagicMock()
    context.args = ["REST", "vs", "gRPC"]

    with patch.object(settings, "allowed_user_ids", [887766]):
        await compare_command(mock_update, context)

    assert mock_update.effective_message.reply_text.call_count >= 1


@pytest.mark.asyncio
async def test_project_command_renders_recommendation(mock_update):
    context = MagicMock()
    context.args = ["intermediate", "Robotics"]

    with patch.object(settings, "allowed_user_ids", [887766]):
        await project_command(mock_update, context)

    assert mock_update.effective_message.reply_text.call_count >= 1


@pytest.mark.asyncio
async def test_vocabulary_command_renders_glossary(mock_update):
    context = MagicMock()
    context.args = ["Quantum", "Computing"]

    with patch.object(settings, "allowed_user_ids", [887766]):
        await vocabulary_command(mock_update, context)

    assert mock_update.effective_message.reply_text.call_count >= 1


@pytest.mark.asyncio
async def test_progress_command_renders_history(mock_update, test_session_factory):
    context = MagicMock()
    # Seed progress
    async with test_session_factory() as session:
        repo = Repository(session)
        await repo.record_lesson_completion(887766, "Robotics", "intermediate")
        await repo.record_quiz_completion(887766, "Robotics", score=3, max_score=3)

    with (
        patch.object(settings, "allowed_user_ids", [887766]),
        patch("app.bot.handlers.education.get_session_factory", return_value=test_session_factory),
    ):
        await progress_command(mock_update, context)

    mock_update.effective_message.reply_text.assert_called_once()
    reply_text = mock_update.effective_message.reply_text.call_args[0][0]
    assert "ROBOTICS" in reply_text
    assert "100%" in reply_text


@pytest.mark.asyncio
async def test_education_callback_router_handles_quiz_answer(mock_update, test_session_factory):
    mock_update.callback_query = MagicMock()
    # User selects option index 0 for question index 0
    mock_update.callback_query.data = "qz_ans:Robotics:0:0"
    mock_update.callback_query.answer = AsyncMock()
    mock_update.callback_query.message = MagicMock()
    mock_update.callback_query.message.reply_text = AsyncMock()

    with (
        patch.object(settings, "allowed_user_ids", [887766]),
        patch("app.bot.handlers.education.get_session_factory", return_value=test_session_factory),
    ):
        await education_callback_router(mock_update, MagicMock())

    mock_update.callback_query.message.reply_text.assert_called_once()
    reply_text = mock_update.callback_query.message.reply_text.call_args[0][0]
    assert "Correct!" in reply_text or "Incorrect" in reply_text
    assert "Explanation:" in reply_text
