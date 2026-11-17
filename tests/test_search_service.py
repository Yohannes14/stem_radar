"""Tests for SearchService, InternalSearchProvider, ExternalSearchProvider, and history logging."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.database.repository import Repository
from app.services.search.models import SearchCategory, SearchSort
from app.services.search.providers.external import ExternalSearchProvider
from app.services.search.providers.internal import calculate_relevance_score
from app.services.search.service import SearchService


@pytest.mark.asyncio
async def test_relevance_scoring_algorithm():
    """Verify keyword match calculation, exact match bonus, and verified boost."""
    now = datetime.now(timezone.utc)
    # Exact phrase in title should score highest
    score_exact = calculate_relevance_score(
        query="quantum computing",
        title="Breakthrough in Quantum Computing Architecture",
        snippet="A new quantum chip",
        is_verified=True,
        published_at=now,
    )

    # Partial match
    score_partial = calculate_relevance_score(
        query="quantum computing",
        title="Physics experiment results",
        snippet="Mentioning quantum mechanics",
        is_verified=False,
        published_at=now - timedelta(days=120),
    )

    assert score_exact > score_partial
    assert score_exact >= 8.0


@pytest.mark.asyncio
async def test_internal_search_multi_domain_discovery(test_session_factory):
    """Verify cross-domain search indexing articles, scholarships, universities, and courses."""
    now = datetime.now(timezone.utc)
    async with test_session_factory() as session:
        repo = Repository(session)
        sources = await repo.get_sources()
        cat = await repo.get_category_by_slug("ai")

        # 1. Article
        await repo.save_article(
            title="Deep Reinforcement Learning for Autonomous Robotics",
            url="https://example.com/robotics-rl-search-test",
            source_id=sources[0].id,
            description="Reinforcement learning applied to humanoid robots.",
            category_ids=[cat.id],
            published_at=now,
        )

        # 2. Scholarship
        await repo.save_opportunity(
            title="Robotics & AI International Masters Fellowship",
            slug="robotics-ai-fellowship-test",
            opportunity_type="scholarship",
            provider_name="European Robotics Institute",
            official_url="https://example.org/robotics-fellowship",
            country="Germany",
            study_level="masters",
            funding_type="fully_funded",
            stem_fields="Robotics, Artificial Intelligence",
            application_deadline=now + timedelta(days=45),
        )

        # 3. University Profile
        await repo.save_university_profile(
            name="Robotics Innovation University Test",
            slug="robotics-uni-test",
            country="Japan",
            city="Tokyo",
            official_portal_url="https://example.jp",
            admissions_portal_url="https://example.jp/admissions",
            admission_requirements="Top quartile BSc in engineering or robotics.",
        )

        # 4. Academic Resource
        await repo.save_academic_resource(
            title="MIT Underactuated Robotics Courseware",
            slug="mit-underactuated-robotics-test",
            resource_type="free_course",
            stem_discipline="Robotics",
            provider_institution="MIT",
            official_access_url="https://underactuated.mit.edu",
            license_type="CC BY-NC-SA 4.0",
        )

    service = SearchService(session_factory=test_session_factory)

    # 1. Broad query across all domains
    res_all = await service.search(query="robotics", category="all", sort_by="relevance", page=1, page_size=10)
    assert res_all.total_items >= 4
    item_types = {item.item_type for item in res_all.items}
    assert "news" in item_types or "paper" in item_types
    assert "scholarship" in item_types
    assert "university" in item_types
    assert "course" in item_types

    # 2. Category filter: scholarships only
    res_sch = await service.search(query="robotics", category=SearchCategory.SCHOLARSHIPS.value, page=1, page_size=10)
    assert len(res_sch.items) >= 1
    assert all(item.item_type == "scholarship" for item in res_sch.items)

    # 3. Category filter: universities only
    res_uni = await service.search(query="robotics", category=SearchCategory.UNIVERSITIES.value, page=1, page_size=10)
    assert len(res_uni.items) >= 1
    assert all(item.item_type == "university" for item in res_uni.items)

    # 4. Category filter: courses only
    res_crs = await service.search(query="robotics", category=SearchCategory.COURSES.value, page=1, page_size=10)
    assert len(res_crs.items) >= 1
    assert all(item.item_type == "course" for item in res_crs.items)


@pytest.mark.asyncio
async def test_search_service_sorting_and_pagination(test_session_factory):
    """Verify sorting by relevance vs date and pagination boundaries."""
    now = datetime.now(timezone.utc)
    async with test_session_factory() as session:
        repo = Repository(session)
        sources = await repo.get_sources()

        # Item A: High keyword match, older date
        await repo.save_article(
            title="Quantum Quantum Quantum Computing",
            url="https://example.com/quantum-high-score",
            source_id=sources[0].id,
            description="High score article",
            published_at=now - timedelta(days=20),
        )

        # Item B: Lower keyword match, newer date
        await repo.save_article(
            title="Introductory Notes on Quantum Physics",
            url="https://example.com/quantum-newest-date",
            source_id=sources[0].id,
            description="Recent release",
            published_at=now,
        )

    service = SearchService(session_factory=test_session_factory)

    # Sort by relevance: high score first
    res_rel = await service.search(query="quantum", sort_by=SearchSort.RELEVANCE.value, page=1, page_size=2)
    assert "Quantum Quantum Quantum Computing" in res_rel.items[0].title

    # Sort by date: newest first
    res_date = await service.search(query="quantum", sort_by=SearchSort.DATE.value, page=1, page_size=2)
    assert "Introductory Notes on Quantum Physics" in res_date.items[0].title


@pytest.mark.asyncio
async def test_search_history_consented_logging(test_session_factory):
    """Verify consented search query logging and history retrieval/clearing."""
    user_id = 998877
    service = SearchService(session_factory=test_session_factory)

    # Enable search history in user preference
    async with test_session_factory() as session:
        repo = Repository(session)
        pref = await repo.get_or_create_preference(user_id)
        pref.search_history_enabled = True
        await session.commit()

    # Perform search with user_id
    await service.search(query="semiconductors", category="all", user_id=user_id)
    await service.search(query="neuroscience", category="all", user_id=user_id)

    # Retrieve history
    history = await service.get_user_search_history(user_id=user_id, limit=5)
    assert len(history) >= 2
    queries = [h.query for h in history]
    assert "neuroscience" in queries
    assert "semiconductors" in queries

    # Clear history
    deleted = await service.clear_user_search_history(user_id=user_id)
    assert deleted >= 2

    # Verify cleared
    empty_history = await service.get_user_search_history(user_id=user_id)
    assert len(empty_history) == 0


@pytest.mark.asyncio
async def test_external_search_provider_fallback_and_handling():
    """Verify external provider handles timeouts and network failures without crashing."""
    provider = ExternalSearchProvider(
        api_key="mock_key",
        endpoint_url="https://mock-search.example.com/api",
        timeout_seconds=0.1,
    )
    assert provider.is_available() is True

    # 1. Timeout handling
    with patch("httpx.AsyncClient.get", AsyncMock(side_effect=httpx.TimeoutException("Timeout"))):
        items, count = await provider.search("fusion energy")
        assert items == []
        assert count == 0

    # 2. HTTP error handling
    mock_resp = AsyncMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        items, count = await provider.search("fusion energy")
        assert items == []
        assert count == 0

    # 3. Unconfigured provider cleanly reports unavailable
    unconfigured = ExternalSearchProvider(api_key=None, endpoint_url=None)
    assert unconfigured.is_available() is False
    res, total = await unconfigured.search("anything")
    assert res == []
    assert total == 0
