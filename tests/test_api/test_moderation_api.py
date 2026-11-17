"""Tests for moderation and submission REST API endpoints."""

import pytest
from httpx import AsyncClient

from app.database.repository import Repository


@pytest.mark.asyncio
async def test_api_public_submission_and_report_endpoints(api_client: AsyncClient, test_session_factory):
    """Test public submission and community issue report endpoints."""
    # 1. POST /api/v1/scholarships/submit
    submit_payload = {
        "title": "Stanford Renewable Energy Fellowship",
        "provider_name": "Stanford University",
        "official_url": "https://energy.stanford.edu/fellowship",
        "country": "United States",
        "study_level": "phd",
        "funding_type": "fully_funded",
        "stem_fields": "Renewable Energy, Chemical Engineering",
    }
    res_sub = await api_client.post("/api/v1/scholarships/submit", json=submit_payload)
    assert res_sub.status_code == 201
    data_sub = res_sub.json()
    assert data_sub["status"] == "pending_approval"
    assert data_sub["verification_tier"] == "unverified_submission"
    opp_id = data_sub["id"]

    # 2. POST /api/v1/scholarships/{id}/report
    report_payload = {
        "report_type": "broken_link",
        "details": "The application portal link leads to a 404 page.",
        "user_id": 9988,
    }
    res_rep = await api_client.post(f"/api/v1/scholarships/{opp_id}/report", json=report_payload)
    assert res_rep.status_code == 201
    data_rep = res_rep.json()
    assert data_rep["report_type"] == "broken_link"
    assert data_rep["status"] == "pending_review"


@pytest.mark.asyncio
async def test_api_admin_moderation_workflow(api_client: AsyncClient, test_session_factory):
    """Test admin moderation endpoints: list pending, approve, reject, reports, sweep."""
    async with test_session_factory() as session:
        repo = Repository(session)
        # Create a pending submission
        opp_pend, _ = await repo.save_opportunity(
            title="MIT Robotics Innovation Grant",
            slug="mit-robotics-innovation-grant",
            opportunity_type="scholarship",
            provider_name="MIT",
            official_url="https://mit.edu/robotics-grant",
            country="United States",
            study_level="masters",
            status="pending_approval",
            verification_tier="unverified_submission",
        )
        opp_pend_id = opp_pend.id

        # Create a community report
        rep = await repo.submit_opportunity_report(
            user_id=123,
            opportunity_id=opp_pend_id,
            report_type="inaccurate",
            details="Eligibility specifies GPA threshold is 3.5 not 3.0",
        )
        rep_id = rep.id

    # 1. GET /api/v1/moderation/pending
    res_pend = await api_client.get("/api/v1/moderation/pending")
    assert res_pend.status_code == 200
    data_pend = res_pend.json()
    assert any(o["id"] == opp_pend_id for o in data_pend)

    # 2. POST /api/v1/moderation/opportunities/{id}/approve
    res_appr = await api_client.post(
        f"/api/v1/moderation/opportunities/{opp_pend_id}/approve?verification_tier=officially_verified&admin_id=1"
    )
    assert res_appr.status_code == 200
    data_appr = res_appr.json()
    assert data_appr["status"] == "open"
    assert data_appr["verification_tier"] == "officially_verified"

    # 3. GET /api/v1/moderation/reports
    res_reps = await api_client.get("/api/v1/moderation/reports?status_filter=pending_review")
    assert res_reps.status_code == 200
    data_reps = res_reps.json()
    assert any(r["id"] == rep_id for r in data_reps)

    # 4. POST /api/v1/moderation/reports/{id}/resolve
    res_res = await api_client.post(
        f"/api/v1/moderation/reports/{rep_id}/resolve?resolution=verified_resolved&admin_id=1"
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "verified_resolved"

    # 5. POST /api/v1/moderation/sweep-expired
    res_sweep = await api_client.post("/api/v1/moderation/sweep-expired")
    assert res_sweep.status_code == 200
    assert "expired_count" in res_sweep.json()
