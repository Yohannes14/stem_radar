"""Tests for Student Hub Telegram handlers, filter interactions, and callback routing."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import CallbackQuery, Chat, Message, Update, User

from app.bot.handlers.base import main_menu_callback_router
from app.bot.handlers.student_hub import (
    courses_command,
    deadlines_command,
    scholarships_command,
    student_hub_callback_router,
    student_hub_command,
    universities_command,
)
from app.bot.ui.menu import _RECENT_CALLBACKS
from app.config import settings
from app.database.models import AcademicResource, Opportunity, UniversityProfile


@pytest.fixture
def mock_hub_update():
    """Mock Telegram update for student hub handler testing."""
    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = 554433
    user.first_name = "Grace"
    user.username = "hopper"

    chat = MagicMock(spec=Chat)
    chat.id = 554433

    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()
    message.edit_text = AsyncMock()

    query = MagicMock(spec=CallbackQuery)
    query.id = "query_hub_1"
    query.data = "hub:student_hub"
    query.message = message
    query.answer = AsyncMock()

    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = message
    update.callback_query = query
    return update


@pytest.mark.asyncio
async def test_student_hub_command_renders_intro(mock_hub_update):
    """Verify /studenthub command renders the flagship 10-section hub."""
    with patch.object(settings, "allowed_user_ids", [554433]):
        await student_hub_command(mock_hub_update, MagicMock())

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    call_args = mock_hub_update.callback_query.message.edit_text.call_args[1]
    text = call_args["text"]
    assert "STEM RADAR — Student Hub" in text
    assert "Verified Scholarships" in text


@pytest.mark.asyncio
async def test_scholarships_command_renders_list(mock_hub_update):
    """Verify /scholarships renders the interactive list with filter chips."""
    _RECENT_CALLBACKS.clear()
    with patch.object(settings, "allowed_user_ids", [554433]):
        await scholarships_command(mock_hub_update, MagicMock())

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    text = mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "Verified STEM Scholarships" in text


@pytest.mark.asyncio
async def test_deadlines_command_renders_tracker(mock_hub_update):
    """Verify /deadlines renders upcoming application cut-offs."""
    _RECENT_CALLBACKS.clear()
    with patch.object(settings, "allowed_user_ids", [554433]):
        await deadlines_command(mock_hub_update, MagicMock())

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    text = mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "Upcoming STEM Application Deadlines" in text


@pytest.mark.asyncio
async def test_student_hub_callback_router_interactions(mock_hub_update):
    """Verify interactive callback routing across filter pickers, card views, and reports."""
    sample_opp = Opportunity(
        id=77,
        title="DAAD Helmut-Schmidt Scholarship",
        slug="daad-helmut-schmidt-test",
        opportunity_type="scholarship",
        provider_name="DAAD Germany",
        provider_type="government",
        official_url="https://daad.de",
        application_url="https://apply.daad.de",
        country="Germany",
        eligible_nationalities="Developing Countries",
        study_level="masters",
        stem_fields="Computer Science, Public Policy",
        funding_type="fully_funded",
        benefits="Full tuition and living stipend",
        eligibility_criteria="Bachelor degree with honors",
        required_documents="CV, motivation letter",
        verification_tier="officially_verified",
        status="open",
        source_attribution="DAAD Official",
    )

    # 1. Level filter picker
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "hub:pick_level:0:all:all"
    mock_hub_update.callback_query.message.edit_text.reset_mock()
    with patch.object(settings, "allowed_user_ids", [554433]):
        await student_hub_callback_router(mock_hub_update, MagicMock())

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    assert (
        "Select Academic Degree Level Filter" in mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]
    )

    # 2. Funding filter picker
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "hub:pick_funding:0:all:all"
    mock_hub_update.callback_query.message.edit_text.reset_mock()
    with patch.object(settings, "allowed_user_ids", [554433]):
        await student_hub_callback_router(mock_hub_update, MagicMock())

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    assert "Select Financial Coverage Filter" in mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]

    # 3. View detail card
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "hub:view:daad-helmut-schmidt-test"
    mock_hub_update.callback_query.message.edit_text.reset_mock()
    with patch(
        "app.services.student_hub_service.student_hub_service.get_opportunity_by_slug",
        AsyncMock(return_value=sample_opp),
    ):
        with patch.object(settings, "allowed_user_ids", [554433]):
            await student_hub_callback_router(mock_hub_update, MagicMock())

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    card_text = mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "DAAD Helmut-Schmidt Scholarship" in card_text
    assert "Official Trust Disclaimer" in card_text

    # 4. Report picker
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "hub:report:77"
    mock_hub_update.callback_query.message.edit_text.reset_mock()
    with patch.object(settings, "allowed_user_ids", [554433]):
        await student_hub_callback_router(mock_hub_update, MagicMock())

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    assert (
        "Community Trust & Listing Issue Report"
        in mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]
    )

    # 5. Confirm report execution
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "hub:do_rep:77:expired"
    mock_hub_update.callback_query.message.edit_text.reset_mock()
    with patch(
        "app.services.student_hub_service.student_hub_service.report_opportunity",
        AsyncMock(return_value=(True, "Recorded")),
    ):
        with patch.object(settings, "allowed_user_ids", [554433]):
            await student_hub_callback_router(mock_hub_update, MagicMock())

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    assert "Thank You for Your Report" in mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]


@pytest.mark.asyncio
async def test_main_menu_routes_student_hub_and_scholarships(mock_hub_update):
    """Verify clicking menu:student_hub and menu:scholarships routes correctly from flagship main menu."""
    # 1. menu:student_hub
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "menu:student_hub"
    mock_hub_update.callback_query.message.edit_text.reset_mock()

    with patch.object(settings, "allowed_user_ids", [554433]):
        await main_menu_callback_router(mock_hub_update, MagicMock())

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    assert "STEM RADAR — Student Hub" in mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]

    # 2. menu:scholarships
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "menu:scholarships"
    mock_hub_update.callback_query.message.edit_text.reset_mock()

    with patch.object(settings, "allowed_user_ids", [554433]):
        await main_menu_callback_router(mock_hub_update, MagicMock())

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    assert "Verified STEM Scholarships" in mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]


@pytest.mark.asyncio
async def test_universities_command_renders_list(mock_hub_update):
    """Verify /universities renders accredited universities directory."""
    _RECENT_CALLBACKS.clear()
    with patch.object(settings, "allowed_user_ids", [554433]):
        await universities_command(mock_hub_update, MagicMock())

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    text = mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "University Admissions & Academic Guidelines" in text


@pytest.mark.asyncio
async def test_courses_command_renders_list(mock_hub_update):
    """Verify /courses renders free courses and learning materials."""
    _RECENT_CALLBACKS.clear()
    with patch.object(settings, "allowed_user_ids", [554433]):
        await courses_command(mock_hub_update, MagicMock())

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    text = mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "Free STEM Courses & Study Materials" in text


@pytest.mark.asyncio
async def test_student_hub_callback_router_universities_and_resources(mock_hub_update):
    """Verify callback routing for university guidelines and academic resources."""
    sample_uni = UniversityProfile(
        id=12,
        name="Addis Ababa University Test",
        slug="aau-test",
        country="Ethiopia",
        city="Addis Ababa",
        official_portal_url="http://www.aau.edu.et",
        admissions_portal_url="http://www.aau.edu.et/admissions",
        admission_requirements="Ethiopian Higher Education Entrance Certificate Examination or equivalent.",
        application_procedures="Online submission through AAU student portal.",
        tuition_and_funding="Subsidized state education for national students.",
    )

    sample_res = AcademicResource(
        id=24,
        title="MIT 6.006 Introduction to Algorithms",
        slug="mit-6006-test",
        resource_type="free_course",
        stem_discipline="Computer Science",
        provider_institution="Massachusetts Institute of Technology",
        official_access_url="https://ocw.mit.edu",
        license_type="CC BY-NC-SA 4.0",
        is_copyright_verified=True,
        description="Core algorithmic paradigms and data structures.",
    )

    # 1. hub:admissions
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "hub:admissions"
    mock_hub_update.callback_query.message.edit_text.reset_mock()
    with patch.object(settings, "allowed_user_ids", [554433]):
        await student_hub_callback_router(mock_hub_update, MagicMock())

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    assert (
        "University Admissions & Academic Guidelines"
        in mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]
    )

    # 2. hub:uni_view:aau-test
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "hub:uni_view:aau-test"
    mock_hub_update.callback_query.message.edit_text.reset_mock()
    with patch(
        "app.services.student_hub_service.student_hub_service.get_university_by_slug",
        AsyncMock(return_value=sample_uni),
    ):
        with patch.object(settings, "allowed_user_ids", [554433]):
            await student_hub_callback_router(mock_hub_update, MagicMock())

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    uni_text = mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "Addis Ababa University Test" in uni_text
    assert "Official Trust Disclaimer" in uni_text

    # 3. hub:courses
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "hub:courses"
    mock_hub_update.callback_query.message.edit_text.reset_mock()
    with patch.object(settings, "allowed_user_ids", [554433]):
        await student_hub_callback_router(mock_hub_update, MagicMock())

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    assert (
        "Free STEM Courses & Study Materials" in mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]
    )

    # 4. hub:res_view:mit-6006-test
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "hub:res_view:mit-6006-test"
    mock_hub_update.callback_query.message.edit_text.reset_mock()
    with patch(
        "app.services.student_hub_service.student_hub_service.get_academic_resource_by_slug",
        AsyncMock(return_value=sample_res),
    ):
        with patch.object(settings, "allowed_user_ids", [554433]):
            await student_hub_callback_router(mock_hub_update, MagicMock())

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    res_text = mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "MIT 6.006 Introduction to Algorithms" in res_text
    assert "Copyright Policy" in res_text
