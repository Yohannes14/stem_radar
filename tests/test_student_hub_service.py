"""Tests for StudentHubService business logic, filters, and markdown card formatters."""

from datetime import datetime, timedelta, timezone

import pytest

from app.database.repository import Repository
from app.services.student_hub_service import StudentHubService


@pytest.mark.asyncio
async def test_student_hub_service_filters_and_queries(test_session_factory):
    """Verify StudentHubService correctly proxies filters for degree level and funding."""
    service = StudentHubService(test_session_factory)

    async with test_session_factory() as session:
        repo = Repository(session)
        future_dl = datetime.now(timezone.utc) + timedelta(days=45)

        # 1. Master's Fully Funded
        await repo.save_opportunity(
            title="DAAD Master's in CS",
            slug="daad-cs-masters-test",
            opportunity_type="scholarship",
            provider_name="DAAD",
            official_url="https://daad.de/cs",
            country="Germany",
            study_level="masters",
            funding_type="fully_funded",
            application_deadline=future_dl,
        )

        # 2. PhD Partially Funded
        await repo.save_opportunity(
            title="Stanford Quantum PhD Tuition Waiver",
            slug="stanford-quantum-phd-test",
            opportunity_type="scholarship",
            provider_name="Stanford University",
            official_url="https://stanford.edu/quantum",
            country="United States",
            study_level="phd",
            funding_type="partially_funded",
            application_deadline=future_dl,
        )

    # Query Masters
    masters = await service.get_scholarships(study_level="masters")
    assert len(masters) == 1
    assert masters[0].slug == "daad-cs-masters-test"

    # Count Masters
    count_masters = await service.count_scholarships(study_level="masters")
    assert count_masters == 1

    # Query Fully Funded
    fully = await service.get_scholarships(funding_type="fully_funded")
    assert len(fully) == 1
    assert fully[0].slug == "daad-cs-masters-test"

    # Query Slug
    fetched = await service.get_opportunity_by_slug("stanford-quantum-phd-test")
    assert fetched is not None
    assert fetched.provider_name == "Stanford University"


@pytest.mark.asyncio
async def test_student_hub_service_upcoming_deadlines(test_session_factory):
    """Verify get_upcoming_deadlines sorts ascending by nearest deadline."""
    service = StudentHubService(test_session_factory)
    now = datetime.now(timezone.utc)

    async with test_session_factory() as session:
        repo = Repository(session)

        # Closer deadline: 10 days
        await repo.save_opportunity(
            title="Soon Deadline Award",
            slug="soon-deadline-award",
            opportunity_type="scholarship",
            provider_name="Test Sponsor",
            official_url="https://example.com/soon",
            country="Germany",
            study_level="masters",
            application_deadline=now + timedelta(days=10),
        )

        # Later deadline: 50 days
        await repo.save_opportunity(
            title="Later Deadline Award",
            slug="later-deadline-award",
            opportunity_type="scholarship",
            provider_name="Test Sponsor",
            official_url="https://example.com/later",
            country="Germany",
            study_level="masters",
            application_deadline=now + timedelta(days=50),
        )

    deadlines = await service.get_upcoming_deadlines(limit=5)
    assert len(deadlines) >= 2
    # Verify chronological sorting
    assert deadlines[0].slug == "soon-deadline-award"
    assert deadlines[1].slug == "later-deadline-award"


@pytest.mark.asyncio
async def test_student_hub_service_formatters(test_session_factory):
    """Verify layout formatters, trust badges, and mandatory disclaimers."""
    service = StudentHubService(test_session_factory)

    # 1. Intro formatter
    intro = service.format_student_hub_intro()
    assert "*Student Hub*" in intro
    assert "Scholarships" in intro

    # 2. Card formatter with disclaimer
    async with test_session_factory() as session:
        repo = Repository(session)
        opp, _ = await repo.save_opportunity(
            title="Fulbright STEM Fellowship",
            slug="fulbright-format-test",
            opportunity_type="scholarship",
            provider_name="U.S. Department of State",
            official_url="https://fulbright.state.gov",
            country="United States",
            study_level="masters",
            funding_type="fully_funded",
            eligibility_criteria="Bachelor degree with GPA 3.5+",
            verification_tier="officially_verified",
            application_deadline=datetime.now(timezone.utc) + timedelta(days=20),
        )

    card = service.format_scholarship_card(opp)
    assert "Fulbright STEM Fellowship" in card
    assert "Officially verified" in card
    assert "U.S. Department of State" in card
    assert "STEM RADAR does not guarantee selection" in card

    # 3. List formatter
    opp_list = service.format_scholarships_list([opp], page=0, total_pages=1, level_filter="masters")
    assert "Verified STEM Scholarships" in opp_list
    assert "Fulbright STEM Fellowship" in opp_list
    assert "Level: Masters" in opp_list

    # 4. Deadline tracker
    dl_text = service.format_deadline_tracker([opp])
    assert "Upcoming Application Deadlines" in dl_text
    assert "Fulbright STEM Fellowship" in dl_text
    assert "In 19 days" in dl_text or "In 20 days" in dl_text


@pytest.mark.asyncio
async def test_student_hub_service_report_opportunity(test_session_factory):
    """Verify report_opportunity records community feedback."""
    service = StudentHubService(test_session_factory)

    async with test_session_factory() as session:
        repo = Repository(session)
        opp, _ = await repo.save_opportunity(
            title="Reportable Award",
            slug="reportable-award",
            opportunity_type="scholarship",
            provider_name="Testing Co",
            official_url="https://example.com/test",
            country="Global",
            study_level="phd",
        )
        opp_id = opp.id

    success, msg = await service.report_opportunity(
        user_id=889900,
        opportunity_id=opp_id,
        report_type="expired",
        details="Deadline is closed.",
    )
    assert success is True
    assert "submitted successfully" in msg
