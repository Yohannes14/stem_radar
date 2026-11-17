"""Tests for Student Hub data models, opportunities, universities, resources, and trust reporting."""

from datetime import datetime, timedelta, timezone

import pytest

from app.database.repository import Repository


@pytest.mark.asyncio
async def test_opportunity_model_creation_and_fields(test_session_factory):
    """Verify creating and retrieving an Opportunity with full metadata."""
    async with test_session_factory() as session:
        repo = Repository(session)
        deadline = datetime.now(timezone.utc) + timedelta(days=60)

        opp, created = await repo.save_opportunity(
            title="Max Planck Quantum Computing Doctoral Fellowship",
            slug="max-planck-quantum-phd",
            opportunity_type="fellowship",
            provider_name="Max Planck Institute",
            provider_type="research_institute",
            official_url="https://www.mpg.de/fellowships",
            application_url="https://apply.mpg.de/quantum",
            country="Germany",
            eligible_nationalities="International",
            study_level="phd",
            stem_fields="Quantum Computing, Physics, Computer Science",
            funding_type="fully_funded",
            benefits="Full salary contract, research budget, relocation allowance",
            eligibility_criteria="Master's in Physics or CS with honors",
            required_documents="CV, Transcripts, Research Proposal",
            application_deadline=deadline,
            is_rolling=False,
            verification_tier="officially_verified",
            status="open",
            source_attribution="Max Planck Official Portal",
        )

        assert created is True
        assert opp.id is not None
        assert opp.title == "Max Planck Quantum Computing Doctoral Fellowship"
        assert opp.funding_type == "fully_funded"
        assert opp.study_level == "phd"
        assert opp.is_rolling is False
        assert opp.verification_tier == "officially_verified"


@pytest.mark.asyncio
async def test_opportunity_duplicate_prevention_by_slug(test_session_factory):
    """Verify duplicate slugs are prevented without failing."""
    async with test_session_factory() as session:
        repo = Repository(session)

        opp1, created1 = await repo.save_opportunity(
            title="DAAD Study Scholarship",
            slug="daad-study-scholarship-unique",
            opportunity_type="scholarship",
            provider_name="DAAD",
            official_url="https://daad.de",
            country="Germany",
            study_level="masters",
        )
        assert created1 is True

        # Second attempt with same slug
        opp2, created2 = await repo.save_opportunity(
            title="DAAD Study Scholarship Duplicate",
            slug="daad-study-scholarship-unique",
            opportunity_type="scholarship",
            provider_name="DAAD",
            official_url="https://daad.de",
            country="Germany",
            study_level="masters",
        )
        assert created2 is False
        assert opp2.id == opp1.id


@pytest.mark.asyncio
async def test_opportunity_multi_facet_filtering(test_session_factory):
    """Verify filtering opportunities by study level, funding type, country, and STEM field."""
    async with test_session_factory() as session:
        repo = Repository(session)
        future_dl = datetime.now(timezone.utc) + timedelta(days=90)

        # 1. Undergrad partially funded in US
        await repo.save_opportunity(
            title="US Robotics Undergrad Grant",
            slug="us-robotics-undergrad",
            opportunity_type="scholarship",
            provider_name="Robotics Foundation",
            official_url="https://example.com/robotics",
            country="United States",
            study_level="undergraduate",
            stem_fields="Robotics, Mechanical Engineering",
            funding_type="partially_funded",
            application_deadline=future_dl,
        )

        # 2. Masters fully funded in Ethiopia
        await repo.save_opportunity(
            title="Addis AI Masters Excellence Award",
            slug="addis-ai-masters",
            opportunity_type="scholarship",
            provider_name="Ethiopian AI Institute",
            official_url="https://eaii.gov.et/award",
            country="Ethiopia",
            study_level="masters",
            stem_fields="Artificial Intelligence, Computer Science",
            funding_type="fully_funded",
            application_deadline=future_dl,
        )

        # 3. PhD fully funded in Germany
        await repo.save_opportunity(
            title="German BioTech PhD Fellowship",
            slug="german-biotech-phd",
            opportunity_type="fellowship",
            provider_name="DFG",
            official_url="https://dfg.de",
            country="Germany",
            study_level="phd",
            stem_fields="Biotechnology, Chemistry",
            funding_type="fully_funded",
            application_deadline=future_dl,
        )

        # Test study_level filter
        masters_list = await repo.get_opportunities(study_level="masters")
        assert len(masters_list) == 1
        assert masters_list[0].slug == "addis-ai-masters"

        # Test funding_type filter
        fully_funded = await repo.get_opportunities(funding_type="fully_funded")
        assert len(fully_funded) == 2

        # Test country filter
        et_list = await repo.get_opportunities(country="Ethiopia")
        assert len(et_list) == 1
        assert et_list[0].slug == "addis-ai-masters"

        # Test stem_field keyword filter
        bio_list = await repo.get_opportunities(stem_field="Biotechnology")
        assert len(bio_list) == 1
        assert bio_list[0].slug == "german-biotech-phd"

        # Test counting
        count = await repo.count_opportunities(funding_type="fully_funded")
        assert count == 2


@pytest.mark.asyncio
async def test_opportunity_deadline_filtering_and_expiry(test_session_factory):
    """Verify that expired deadlines are excluded from active feeds and transitioned correctly."""
    async with test_session_factory() as session:
        repo = Repository(session)
        now = datetime.now(timezone.utc)
        past_dl = now - timedelta(days=5)
        future_dl = now + timedelta(days=30)

        # Lapsed opportunity
        await repo.save_opportunity(
            title="Lapsed Spring Internship",
            slug="lapsed-spring-internship",
            opportunity_type="internship",
            provider_name="Tech Corp",
            official_url="https://example.com/lapsed",
            country="Germany",
            study_level="undergraduate",
            application_deadline=past_dl,
            is_rolling=False,
            status="open",
        )

        # Active opportunity
        await repo.save_opportunity(
            title="Active Autumn Fellowship",
            slug="active-autumn-fellowship",
            opportunity_type="fellowship",
            provider_name="Tech Corp",
            official_url="https://example.com/active",
            country="Germany",
            study_level="masters",
            application_deadline=future_dl,
            is_rolling=False,
            status="open",
        )

        # Rolling deadline opportunity
        await repo.save_opportunity(
            title="Rolling Research Grant",
            slug="rolling-research-grant",
            opportunity_type="grant",
            provider_name="Open Research",
            official_url="https://example.com/rolling",
            country="Global",
            study_level="phd",
            application_deadline=None,
            is_rolling=True,
            status="open",
        )

        # Active query should only return the future deadline + rolling deadline
        active_opps = await repo.get_opportunities(active_only=True)
        active_slugs = {o.slug for o in active_opps}
        assert "lapsed-spring-internship" not in active_slugs
        assert "active-autumn-fellowship" in active_slugs
        assert "rolling-research-grant" in active_slugs

        # Execute automated expiry reaper
        lapsed_count = await repo.expire_lapsed_opportunities(now=now)
        assert lapsed_count == 1

        # Check lapsed item in DB now has status="expired"
        lapsed_opp = await repo.get_opportunity_by_slug("lapsed-spring-internship")
        assert lapsed_opp is not None
        assert lapsed_opp.status == "expired"


@pytest.mark.asyncio
async def test_university_profile_crud_and_queries(test_session_factory):
    """Verify UniversityProfile creation, uniqueness, and country querying."""
    async with test_session_factory() as session:
        repo = Repository(session)

        uni1, created1 = await repo.save_university_profile(
            name="Addis Ababa University",
            slug="aau-test",
            country="Ethiopia",
            official_portal_url="http://www.aau.edu.et",
            admissions_portal_url="https://portal.aau.edu.et",
            admission_requirements="GAT entrance test",
            city="Addis Ababa",
        )
        assert created1 is True
        assert uni1.name == "Addis Ababa University"

        # Duplicate check
        uni2, created2 = await repo.save_university_profile(
            name="Addis Ababa University",
            slug="aau-test",
            country="Ethiopia",
            official_portal_url="http://www.aau.edu.et",
            admissions_portal_url="https://portal.aau.edu.et",
        )
        assert created2 is False
        assert uni2.id == uni1.id

        # Query by country
        et_unis = await repo.get_university_profiles(country="Ethiopia")
        assert len(et_unis) == 1
        assert et_unis[0].slug == "aau-test"


@pytest.mark.asyncio
async def test_academic_resource_crud_and_copyright_verification(test_session_factory):
    """Verify AcademicResource storage and copyright verification flag enforcement."""
    async with test_session_factory() as session:
        repo = Repository(session)

        res, created = await repo.save_academic_resource(
            title="MIT 6.006 Intro to Algorithms",
            slug="mit-6006-test",
            resource_type="lecture_materials",
            stem_discipline="Computer Science",
            provider_institution="MIT",
            official_access_url="https://ocw.mit.edu/courses/6-006/",
            license_type="Creative Commons BY-NC-SA",
            is_copyright_verified=True,
            description="Algorithmic thinking and dynamic programming.",
        )
        assert created is True
        assert res.is_copyright_verified is True

        fetched = await repo.get_academic_resources(resource_type="lecture_materials")
        assert len(fetched) == 1
        assert fetched[0].slug == "mit-6006-test"


@pytest.mark.asyncio
async def test_opportunity_report_submission_and_count_increment(test_session_factory):
    """Verify reporting an opportunity increments report_count and enters moderation queue."""
    async with test_session_factory() as session:
        repo = Repository(session)

        opp, _ = await repo.save_opportunity(
            title="Flagged Scholarship",
            slug="flagged-scholarship",
            opportunity_type="scholarship",
            provider_name="Unknown Entity",
            official_url="https://example.com/unknown",
            country="Global",
            study_level="masters",
        )
        assert opp.report_count == 0

        # Submit report
        report = await repo.submit_opportunity_report(
            user_id=123456,
            opportunity_id=opp.id,
            report_type="expired",
            details="The link returns 404 and provider website states programme has concluded.",
        )
        assert report.id is not None
        assert report.status == "pending_review"

        # Check opportunity report_count incremented
        updated_opp = await repo.get_opportunity_by_id(opp.id)
        assert updated_opp is not None
        assert updated_opp.report_count == 1

        # Check moderation list
        pending = await repo.get_opportunity_reports(status="pending_review")
        assert len(pending) == 1
        assert pending[0].report_type == "expired"
        assert pending[0].user_id == 123456
