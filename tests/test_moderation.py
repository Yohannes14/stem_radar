"""Tests for Stage 16 public submissions, moderation workflow, community reports, and expiry sweep."""

from datetime import datetime, timedelta, timezone

import pytest

from app.database.repository import Repository
from app.services.student_hub_service import StudentHubService


@pytest.mark.asyncio
async def test_public_opportunity_submission_and_isolation(test_session_factory):
    """Verify submitted opportunity is saved as pending_approval and excluded from active listings."""
    service = StudentHubService(session_factory=test_session_factory)
    now = datetime.now(timezone.utc)

    # 1. User submits an opportunity
    success, opp, msg = await service.submit_public_opportunity(
        user_id=12345,
        title="Oxford Quantum Systems Fellowship",
        provider_name="University of Oxford",
        official_url="https://ox.ac.uk/quantum-fellowship",
        country="United Kingdom",
        study_level="postdoctoral",
        funding_type="fully_funded",
        application_deadline=now + timedelta(days=60),
    )

    assert success is True
    assert opp is not None
    assert opp.status == "pending_approval"
    assert opp.verification_tier == "unverified_submission"
    assert "User 12345" in opp.source_attribution

    # 2. Verify opportunity does NOT appear in active public scholarship search
    async with test_session_factory() as session:
        repo = Repository(session)
        active_opps = await repo.get_opportunities(active_only=True)
        assert not any(o.id == opp.id for o in active_opps)

        # 3. Verify it appears in pending moderation list
        pending = await repo.get_pending_opportunities()
        assert any(o.id == opp.id for o in pending)

        # 4. Verify a submission report was automatically generated
        reports = await repo.get_opportunity_reports(status="pending_review")
        assert any(r.opportunity_id == opp.id and r.report_type == "submission" for r in reports)


@pytest.mark.asyncio
async def test_admin_approval_and_verification_tier_assignment(test_session_factory):
    """Verify admin approval transitions opportunity to open, sets trust tier, and publishes it."""
    service = StudentHubService(session_factory=test_session_factory)
    now = datetime.now(timezone.utc)

    # Submit
    _, opp, _ = await service.submit_public_opportunity(
        user_id=54321,
        title="Max Planck AI Doctoral Grant",
        provider_name="Max Planck Society",
        official_url="https://mpg.de/ai-grant",
        country="Germany",
        study_level="phd",
        funding_type="fully_funded",
        application_deadline=now + timedelta(days=90),
    )

    # Admin approves as officially_verified
    approved = await service.approve_opportunity(
        opportunity_id=opp.id,
        admin_user_id=999,
        verification_tier="officially_verified",
        notes="Verified against official MPG research portal.",
    )

    assert approved is not None
    assert approved.status == "open"
    assert approved.verification_tier == "officially_verified"

    # Now it must appear in public active opportunities
    async with test_session_factory() as session:
        repo = Repository(session)
        active_opps = await repo.get_opportunities(active_only=True)
        assert any(o.id == opp.id for o in active_opps)

        # Linked submission report must be marked as resolved
        reports = await repo.get_opportunity_reports(status="verified_resolved")
        assert any(r.opportunity_id == opp.id for r in reports)


@pytest.mark.asyncio
async def test_admin_rejection_workflow(test_session_factory):
    """Verify admin rejection sets status to rejected and dismisses review tickets."""
    service = StudentHubService(session_factory=test_session_factory)
    now = datetime.now(timezone.utc)

    _, opp, _ = await service.submit_public_opportunity(
        user_id=67890,
        title="Unverified Suspicious Coding Prize",
        provider_name="Anonymous Sponsor",
        official_url="https://suspicious-site.example.com",
        country="Unknown",
        study_level="undergraduate",
        application_deadline=now + timedelta(days=10),
    )

    rejected = await service.reject_opportunity(
        opportunity_id=opp.id,
        admin_user_id=999,
        reason="Unverifiable sponsor and broken registration portal.",
    )

    assert rejected is not None
    assert rejected.status == "rejected"

    async with test_session_factory() as session:
        repo = Repository(session)
        # Should not be in active or pending
        active = await repo.get_opportunities(active_only=True)
        pending = await repo.get_pending_opportunities()
        assert not any(o.id == opp.id for o in active)
        assert not any(o.id == opp.id for o in pending)


@pytest.mark.asyncio
async def test_community_issue_reporting_and_resolution(test_session_factory):
    """Verify user can report broken links or expired listings, and admin can resolve."""
    service = StudentHubService(session_factory=test_session_factory)
    now = datetime.now(timezone.utc)

    # Seed an active opportunity
    async with test_session_factory() as session:
        repo = Repository(session)
        opp, _ = await repo.save_opportunity(
            title="Cambridge Biotechnology Masters Bursary",
            slug="cambridge-biotech-bursary",
            opportunity_type="scholarship",
            provider_name="University of Cambridge",
            official_url="https://cam.ac.uk/biotech-bursary",
            country="United Kingdom",
            study_level="masters",
            funding_type="partially_funded",
            application_deadline=now + timedelta(days=30),
            status="open",
        )
        opp_id = opp.id

    # User submits a report flagging that the deadline expired or link broke
    success, msg = await service.report_opportunity(
        user_id=112233,
        opportunity_id=opp_id,
        report_type="expired",
        details="Portal announcement indicates the 2026 application cycle is already closed.",
    )
    assert success is True

    # Check report in queue and opportunity report_count incremented
    reports = await service.get_moderation_reports(status="pending_review")
    target_report = next(r for r in reports if r.opportunity_id == opp_id)
    assert target_report.report_type == "expired"

    # Admin resolves report with action: expire_opportunity
    resolved = await service.resolve_report(
        report_id=target_report.id,
        admin_user_id=999,
        resolution="verified_resolved",
        action_taken="expire_opportunity",
    )
    assert resolved is not None
    assert resolved.status == "verified_resolved"

    # Verify opportunity is now marked expired
    async with test_session_factory() as session:
        repo = Repository(session)
        updated_opp = await repo.get_opportunity_by_id(opp_id)
        assert updated_opp.status == "expired"


@pytest.mark.asyncio
async def test_automated_deadline_expiry_sweep(test_session_factory):
    """Verify lapsed application deadlines are automatically updated to expired."""
    service = StudentHubService(session_factory=test_session_factory)
    now = datetime.now(timezone.utc)

    async with test_session_factory() as session:
        repo = Repository(session)
        # Opportunity A: Lapsed deadline (yesterday)
        await repo.save_opportunity(
            title="Lapsed Deadline Scholarship",
            slug="lapsed-deadline-opp",
            opportunity_type="scholarship",
            provider_name="Lapsed Foundation",
            official_url="https://example.com/lapsed",
            country="United States",
            study_level="masters",
            application_deadline=now - timedelta(days=2),
            is_rolling=False,
            status="open",
        )

        # Opportunity B: Future deadline (30 days ahead)
        await repo.save_opportunity(
            title="Active Future Scholarship",
            slug="active-future-opp",
            opportunity_type="scholarship",
            provider_name="Future Foundation",
            official_url="https://example.com/future",
            country="Canada",
            study_level="masters",
            application_deadline=now + timedelta(days=30),
            is_rolling=False,
            status="open",
        )

        # Opportunity C: Rolling deadline
        await repo.save_opportunity(
            title="Rolling Admissions Scholarship",
            slug="rolling-admissions-opp",
            opportunity_type="scholarship",
            provider_name="Rolling Institute",
            official_url="https://example.com/rolling",
            country="Germany",
            study_level="phd",
            application_deadline=now - timedelta(days=5),
            is_rolling=True,
            status="open",
        )

    # Run automated expiry sweep
    count = await service.expire_lapsed_opportunities(now=now)
    assert count == 1

    # Verify statuses
    async with test_session_factory() as session:
        repo = Repository(session)
        opp_lapsed = await repo.get_opportunity_by_slug("lapsed-deadline-opp")
        opp_future = await repo.get_opportunity_by_slug("active-future-opp")
        opp_rolling = await repo.get_opportunity_by_slug("rolling-admissions-opp")

        assert opp_lapsed.status == "expired"
        assert opp_future.status == "open"
        assert opp_rolling.status == "open"
