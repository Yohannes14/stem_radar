"""Tests for the /api/v1/universities and /api/v1/resources endpoints."""

import pytest
from httpx import AsyncClient

from app.database.repository import Repository


@pytest.mark.asyncio
async def test_list_universities_api(api_client: AsyncClient, test_session_factory):
    """Test listing universities with pagination and country filtering."""
    async with test_session_factory() as session:
        repo = Repository(session)
        await repo.save_university_profile(
            name="ETH Zurich Test",
            slug="eth-zurich-test",
            country="Switzerland",
            city="Zurich",
            official_portal_url="https://ethz.ch",
            admissions_portal_url="https://ethz.ch/admissions",
            admission_requirements="Excellent secondary education with strong math background.",
            tuition_and_funding="CHF 730 per semester.",
        )
        await repo.save_university_profile(
            name="Addis Ababa University Test",
            slug="aau-ethiopia-test",
            country="Ethiopia",
            city="Addis Ababa",
            official_portal_url="http://www.aau.edu.et",
            admissions_portal_url="http://www.aau.edu.et/admissions",
        )

    # 1. List all
    res = await api_client.get("/api/v1/universities?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) >= 2
    assert data["pagination"]["total_items"] >= 2

    # 2. Filter by country
    res_filtered = await api_client.get("/api/v1/universities?country=Switzerland")
    assert res_filtered.status_code == 200
    data_filtered = res_filtered.json()
    assert any(u["slug"] == "eth-zurich-test" for u in data_filtered["items"])
    assert not any(u["slug"] == "aau-ethiopia-test" for u in data_filtered["items"])


@pytest.mark.asyncio
async def test_get_university_by_slug_api(api_client: AsyncClient, test_session_factory):
    """Test fetching an individual university profile by slug."""
    async with test_session_factory() as session:
        repo = Repository(session)
        await repo.save_university_profile(
            name="Technical University of Munich Test",
            slug="tum-germany-test",
            country="Germany",
            city="Munich",
            official_portal_url="https://www.tum.de",
            admissions_portal_url="https://www.tum.de/admissions",
            admission_requirements="Abitur or equivalent university entrance qualification.",
        )

    # Valid slug
    res = await api_client.get("/api/v1/universities/tum-germany-test")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Technical University of Munich Test"
    assert data["country"] == "Germany"
    assert data["official_portal_url"] == "https://www.tum.de"

    # Non-existent slug (404)
    res_404 = await api_client.get("/api/v1/universities/non-existent-uni-slug")
    assert res_404.status_code == 404
    err_data = res_404.json()
    assert err_data["error"]["code"] == "NOT_FOUND"
    assert "not found" in err_data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_list_academic_resources_api(api_client: AsyncClient, test_session_factory):
    """Test listing academic resources with type and discipline filters."""
    async with test_session_factory() as session:
        repo = Repository(session)
        await repo.save_academic_resource(
            title="MIT OpenCourseWare: Intro to Algorithms",
            slug="mit-6006-algorithms-test",
            resource_type="free_course",
            stem_discipline="Computer Science",
            provider_institution="MIT",
            official_access_url="https://ocw.mit.edu/courses/6-006",
            license_type="CC BY-NC-SA 4.0",
        )
        await repo.save_academic_resource(
            title="OpenStax Calculus Volume 1",
            slug="openstax-calculus-1-test",
            resource_type="open_textbook",
            stem_discipline="Mathematics",
            provider_institution="OpenStax Rice University",
            official_access_url="https://openstax.org/details/books/calculus-volume-1",
            license_type="CC BY 4.0",
        )

    # 1. List all
    res = await api_client.get("/api/v1/resources?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) >= 2

    # 2. Filter by resource_type
    res_courses = await api_client.get("/api/v1/resources?resource_type=free_course")
    assert res_courses.status_code == 200
    data_courses = res_courses.json()
    assert any(r["slug"] == "mit-6006-algorithms-test" for r in data_courses["items"])
    assert not any(r["slug"] == "openstax-calculus-1-test" for r in data_courses["items"])

    # 3. Filter by stem_discipline
    res_math = await api_client.get("/api/v1/resources?stem_discipline=Mathematics")
    assert res_math.status_code == 200
    data_math = res_math.json()
    assert any(r["slug"] == "openstax-calculus-1-test" for r in data_math["items"])


@pytest.mark.asyncio
async def test_get_academic_resource_by_slug_api(api_client: AsyncClient, test_session_factory):
    """Test fetching an individual academic resource by slug."""
    async with test_session_factory() as session:
        repo = Repository(session)
        await repo.save_academic_resource(
            title="Stanford CS229: Machine Learning Lecture Notes",
            slug="stanford-cs229-ml-notes-test",
            resource_type="lecture_materials",
            stem_discipline="Artificial Intelligence",
            provider_institution="Stanford University",
            official_access_url="https://cs229.stanford.edu",
            license_type="Free Open Material",
        )

    # Valid slug
    res = await api_client.get("/api/v1/resources/stanford-cs229-ml-notes-test")
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Stanford CS229: Machine Learning Lecture Notes"
    assert data["license_type"] == "Free Open Material"
    assert data["is_copyright_verified"] is True

    # Non-existent slug (404)
    res_404 = await api_client.get("/api/v1/resources/non-existent-resource-slug")
    assert res_404.status_code == 404
    err_data = res_404.json()
    assert err_data["error"]["code"] == "NOT_FOUND"
    assert "not found" in err_data["error"]["message"].lower()
