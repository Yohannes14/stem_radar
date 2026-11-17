"""Tests for Student Hub Telegram handlers, filter interactions, and callback routing."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import CallbackQuery, Chat, Message, Update, User

from app.bot.handlers.base import main_menu_callback_router
from app.bot.handlers.student_hub import (
    courses_command,
    deadlines_command,
    moderation_callback_router,
    moderation_command,
    quick_opportunity_command,
    quick_resource_command,
    quick_university_command,
    scholarships_command,
    student_hub_callback_router,
    student_hub_command,
    submit_opportunity_command,
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


@pytest.fixture
def sample_opportunity():
    now = datetime.now(timezone.utc)
    return Opportunity(
        id=42,
        title="Erasmus Mundus Joint Masters in Artificial Intelligence",
        slug="erasmus-mundus-ai-fellowship",
        opportunity_type="scholarship",
        provider_name="European Commission",
        official_url="https://example.org/erasmus-ai",
        application_url="https://example.org/apply",
        country="European Union",
        eligible_nationalities="All",
        study_level="masters",
        stem_fields="Artificial Intelligence, Computer Science",
        funding_type="fully_funded",
        benefits="1400 EUR monthly stipend, tuition waiver, health insurance",
        eligibility_criteria="BSc in Computer Science or related STEM field with minimum 3.0 GPA.",
        required_documents="Transcripts, CV, 2 recommendation letters, statement of purpose",
        application_deadline=now + timedelta(days=45),
        is_rolling=False,
        verification_tier="officially_verified",
        status="open",
        source_attribution="European Commission Official Portal",
    )


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

    # 2b. Country filter picker
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "hub:pick_country:0:all:all"
    mock_hub_update.callback_query.message.edit_text.reset_mock()
    with patch.object(settings, "allowed_user_ids", [554433]):
        await student_hub_callback_router(mock_hub_update, MagicMock())

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    assert "Select Destination Host Country" in mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]

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


@pytest.mark.asyncio
async def test_student_hub_opportunity_type_routing(mock_hub_update):
    """Verify hub:internships, hub:grants, and hub:competitions route to real opportunity queries."""
    # 1. hub:internships
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "hub:internships"
    mock_hub_update.callback_query.message.edit_text.reset_mock()

    with patch("app.bot.handlers.student_hub.render_scholarships_view", AsyncMock()) as mock_render:
        with patch.object(settings, "allowed_user_ids", [554433]):
            await student_hub_callback_router(mock_hub_update, MagicMock())
        mock_render.assert_called_once()
        assert mock_render.call_args[1]["opp_type"] == "internship"

    # 2. hub:grants
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "hub:grants"
    with patch("app.bot.handlers.student_hub.render_scholarships_view", AsyncMock()) as mock_render:
        with patch.object(settings, "allowed_user_ids", [554433]):
            await student_hub_callback_router(mock_hub_update, MagicMock())
        mock_render.assert_called_once()
        assert mock_render.call_args[1]["opp_type"] == "grant"

    # 3. hub:report_start
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "hub:report_start"
    mock_hub_update.callback_query.message.edit_text.reset_mock()

    with patch.object(settings, "allowed_user_ids", [554433]):
        await student_hub_callback_router(mock_hub_update, MagicMock())
    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    rep_text = mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "Report Listing Issue or Outdated Information" in rep_text


@pytest.mark.asyncio
async def test_submit_opportunity_command_flow(mock_hub_update, sample_opportunity):
    """Verify /submit_opportunity command renders guide without args and parses piped submission."""
    # 1. Without args: renders guide
    context = MagicMock()
    context.args = []
    with patch.object(settings, "allowed_user_ids", [554433]):
        await submit_opportunity_command(mock_hub_update, context)

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    guide_text = mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "Submit an Academic Opportunity" in guide_text
    assert "/submit_opportunity Title | Provider" in guide_text

    # 2. With valid piped args
    context.args = [
        "Oxford",
        "Robotics",
        "Fellowship",
        "|",
        "Oxford",
        "|",
        "https://ox.ac.uk",
        "|",
        "UK",
        "|",
        "masters",
        "|",
        "fully_funded",
    ]
    mock_hub_update.callback_query = None
    mock_hub_update.effective_message.reply_text.reset_mock()

    with patch(
        "app.services.student_hub_service.student_hub_service.submit_public_opportunity",
        AsyncMock(return_value=(True, sample_opportunity, "Submission received")),
    ):
        with patch.object(settings, "allowed_user_ids", [554433]):
            await submit_opportunity_command(mock_hub_update, context)

    mock_hub_update.effective_message.reply_text.assert_called_once()
    confirm_text = mock_hub_update.effective_message.reply_text.call_args[1]["text"]
    assert "Submission Received for Review" in confirm_text
    assert "Erasmus Mundus" in confirm_text


@pytest.mark.asyncio
async def test_admin_moderation_command_and_callback_router(mock_hub_update, sample_opportunity):
    """Verify /moderation command and moderation callback router (mod:subs, mod:appr_v, mod:reps, mod:sweep)."""
    # 1. /moderation command
    context = MagicMock()
    with patch(
        "app.services.student_hub_service.student_hub_service.count_pending_submissions", AsyncMock(return_value=2)
    ):
        with patch(
            "app.services.student_hub_service.student_hub_service.count_moderation_reports", AsyncMock(return_value=1)
        ):
            with patch.object(settings, "allowed_user_ids", [554433]):
                await moderation_command(mock_hub_update, context)

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    dash_text = mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "Administrative Moderation Center" in dash_text
    assert "Pending Submissions:* `2`" in dash_text

    # 2. Callback mod:subs:0
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "mod:subs:0"
    mock_hub_update.callback_query.message.edit_text.reset_mock()
    with patch(
        "app.services.student_hub_service.student_hub_service.get_pending_submissions",
        AsyncMock(return_value=[sample_opportunity]),
    ):
        with patch(
            "app.services.student_hub_service.student_hub_service.count_pending_submissions",
            AsyncMock(return_value=1),
        ):
            with patch.object(settings, "allowed_user_ids", [554433]):
                await moderation_callback_router(mock_hub_update, context)

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    sub_text = mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "Moderation Review: Submission" in sub_text

    # 3. Callback mod:appr_v:42:0
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "mod:appr_v:42:0"
    mock_hub_update.callback_query.message.edit_text.reset_mock()
    with patch(
        "app.services.student_hub_service.student_hub_service.approve_opportunity",
        AsyncMock(return_value=sample_opportunity),
    ) as mock_appr:
        with patch(
            "app.services.student_hub_service.student_hub_service.get_pending_submissions",
            AsyncMock(return_value=[]),
        ):
            with patch(
                "app.services.student_hub_service.student_hub_service.count_pending_submissions",
                AsyncMock(return_value=0),
            ):
                with patch.object(settings, "allowed_user_ids", [554433]):
                    await moderation_callback_router(mock_hub_update, context)

    mock_appr.assert_called_once()
    assert mock_appr.call_args[1]["opportunity_id"] == 42
    assert mock_appr.call_args[1]["verification_tier"] == "officially_verified"

    # 4. Callback mod:sweep
    _RECENT_CALLBACKS.clear()
    mock_hub_update.callback_query.data = "mod:sweep"
    mock_hub_update.callback_query.message.edit_text.reset_mock()
    with patch(
        "app.services.student_hub_service.student_hub_service.expire_lapsed_opportunities",
        AsyncMock(return_value=3),
    ):
        with patch.object(settings, "allowed_user_ids", [554433]):
            await moderation_callback_router(mock_hub_update, context)

    mock_hub_update.callback_query.message.edit_text.assert_called_once()
    sweep_text = mock_hub_update.callback_query.message.edit_text.call_args[1]["text"]
    assert "Automated Expiry Sweep Complete" in sweep_text
    assert "transitioned `3` lapsed opportunities to 'expired'" in sweep_text


@pytest.mark.asyncio
async def test_quick_deep_link_commands(mock_hub_update, sample_opportunity):
    """Verify quick deep-link commands (/scholarship_42, /university_<slug>, /resource_<slug>)."""
    # 1. /scholarship_42
    mock_hub_update.effective_message.text = "/scholarship_42"
    mock_hub_update.effective_message.reply_text.reset_mock()

    with patch(
        "app.services.student_hub_service.student_hub_service.get_opportunity_by_id",
        AsyncMock(return_value=sample_opportunity),
    ):
        with patch.object(settings, "allowed_user_ids", [554433]):
            await quick_opportunity_command(mock_hub_update, MagicMock())

    mock_hub_update.effective_message.reply_text.assert_called_once()
    text = mock_hub_update.effective_message.reply_text.call_args[0][0]
    assert sample_opportunity.title in text
    assert "Officially Verified Source" in text

    # 2. /university_addis-ababa-university
    mock_hub_update.effective_message.text = "/university_addis-ababa-university"
    mock_hub_update.effective_message.reply_text.reset_mock()

    mock_uni = UniversityProfile(
        id=1,
        name="Addis Ababa University",
        slug="addis-ababa-university",
        country="Ethiopia",
        city="Addis Ababa",
        official_portal_url="https://aau.edu.et",
        admissions_portal_url="https://portal.aau.edu.et",
        admission_requirements="GAT entrance examination",
        application_procedures="Online submission",
        tuition_and_funding="Government subsidized",
        international_guidelines_url="https://portal.aau.edu.et/intl",
        research_opportunities_url="https://aau.edu.et/research",
    )

    with patch(
        "app.services.student_hub_service.student_hub_service.get_university_by_slug",
        AsyncMock(return_value=mock_uni),
    ):
        with patch.object(settings, "allowed_user_ids", [554433]):
            await quick_university_command(mock_hub_update, MagicMock())

    mock_hub_update.effective_message.reply_text.assert_called_once()
    uni_text = mock_hub_update.effective_message.reply_text.call_args[0][0]
    assert "Addis Ababa University" in uni_text

    # 3. /resource_cs50
    mock_hub_update.effective_message.text = "/resource_cs50"
    mock_hub_update.effective_message.reply_text.reset_mock()

    mock_res = AcademicResource(
        id=1,
        title="CS50: Introduction to Computer Science",
        slug="cs50",
        resource_type="free_course",
        provider_institution="Harvard University / edX",
        official_access_url="https://cs50.harvard.edu",
        description="Comprehensive foundations of computer science.",
        stem_discipline="Computer Science",
        license_type="CC BY-NC-SA 4.0",
        is_copyright_verified=True,
    )

    with patch(
        "app.services.student_hub_service.student_hub_service.get_academic_resource_by_slug",
        AsyncMock(return_value=mock_res),
    ):
        with patch.object(settings, "allowed_user_ids", [554433]):
            await quick_resource_command(mock_hub_update, MagicMock())

    mock_hub_update.effective_message.reply_text.assert_called_once()
    res_text = mock_hub_update.effective_message.reply_text.call_args[0][0]
    assert "CS50: Introduction to Computer Science" in res_text
