"""Tests for the /api/v1/scholarships endpoints (listing, pagination, filtering, details, deadlines)."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.database.repository import Repository


@pytest.mark.asyncio
async def test_list_scholarships_api(api_client: AsyncClient, test_session_factory):
    """Test listing scholarships with filtering and pagination."""
    now = datetime.now(timezone.utc)
    async with test_session_factory() as session:
        repo = Repository(session)

        # 1. Master's in Germany
        await repo.save_opportunity(
            title="DAAD Master's Fellowship",
            slug="daad-masters-api-test",
            opportunity_type="scholarship",
            provider_name="DAAD",
            official_url="https://daad.de",
            country="Germany",
            study_level="masters",
            funding_type="fully_funded",
            application_deadline=now + timedelta(days=40),
        )

        # 2. PhD in USA
        await repo.save_opportunity(
            title="MIT Quantum PhD Grant",
            slug="mit-quantum-phd-api-test",
            opportunity_type="scholarship",
            provider_name="MIT",
            official_url="https://mit.edu",
            country="United States",
            study_level="phd",
            funding_type="fully_funded",
            application_deadline=now + timedelta(days=60),
        )

    # List all
    res = await api_client.get("/api/v1/scholarships?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) >= 2
    assert data["pagination"]["total_items"] >= 2

    # Filter by level=masters
    res_masters = await api_client.get("/api/v1/scholarships?level=masters")
    assert res_masters.status_code == 200
    data_masters = res_masters.json()
    assert any(item["slug"] == "daad-masters-api-test" for item in data_masters["items"])
    assert not any(item["slug"] == "mit-quantum-phd-api-test" for item in data_masters["items"])


@pytest.mark.asyncio
async def test_get_scholarship_by_slug_api(api_client: AsyncClient, test_session_factory):
    """Test fetching an individual scholarship by slug."""
    now = datetime.now(timezone.utc)
    async with test_session_factory() as session:
        repo = Repository(session)
        await repo.save_opportunity(
            title="Fulbright Foreign Student Fellowship",
            slug="fulbright-api-test",
            opportunity_type="scholarship",
            provider_name="U.S. Department of State",
            official_url="https://foreign.fulbrightonline.org",
            country="United States",
            study_level="masters",
            funding_type="fully_funded",
            eligibility_criteria="Bachelor degree with GPA 3.5+",
            application_deadline=now + timedelta(days=90),
        )

    # 1. Valid slug
    res = await api_client.get("/api/v1/scholarships/fulbright-api-test")
    assert res.status_code == 200
    data = res.json()
    assert data["slug"] == "fulbright-api-test"
    assert data["provider_name"] == "U.S. Department of State"
    assert data["verification_tier"] == "officially_verified"

    # 2. Invalid slug (404)
    res_404 = await api_client.get("/api/v1/scholarships/non-existent-scholarship-slug")
    assert res_404.status_code == 404
    err_data = res_404.json()
    assert err_data["error"]["code"] == "NOT_FOUND"
    assert "not found" in err_data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_get_upcoming_deadlines_api(api_client: AsyncClient, test_session_factory):
    """Test retrieving chronological deadlines timeline."""
    now = datetime.now(timezone.utc)
    async with test_session_factory() as session:
        repo = Repository(session)
        await repo.save_opportunity(
            title="Early Deadline Award",
            slug="early-dl-award",
            opportunity_type="scholarship",
            provider_name="Early Sponsor",
            official_url="https://example.com/early",
            country="Germany",
            study_level="masters",
            application_deadline=now + timedelta(days=15),
        )

    res = await api_client.get("/api/v1/scholarships/deadlines/upcoming?limit=5")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["application_deadline"] is not None
