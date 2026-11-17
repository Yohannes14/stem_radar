"""Tests for SearchService, InternalSearchProvider, ExternalSearchProvider, and history logging."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.database.repository import Repository
from app.services.search.models import SearchCategory, SearchResultItem, SearchSort
from app.services.search.providers.brave import BraveSearchProvider
from app.services.search.providers.duckduckgo import DuckDuckGoProvider
from app.services.search.providers.external import ExternalSearchProvider
from app.services.search.providers.google import GoogleSearchProvider
from app.services.search.providers.internal import calculate_relevance_score
from app.services.search.providers.registry import ExternalSearchRegistry
from app.services.search.providers.semantic_scholar import SemanticScholarProvider
from app.services.search.providers.wikipedia import WikipediaProvider
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


@pytest.mark.asyncio
async def test_semantic_scholar_provider_success_and_normalization():
    """Verify Semantic Scholar queries, parses openAccessPdf, authors, and citations."""
    provider = SemanticScholarProvider(api_key="mock_s2_key", timeout_seconds=5.0)
    mock_payload = {
        "total": 1,
        "data": [
            {
                "paperId": "abcdef1234567890abcdef",
                "title": "Quantum Error Correction via Surface Codes",
                "abstract": "We demonstrate fault-tolerant quantum error correction.",
                "venue": "Nature Quantum",
                "year": 2025,
                "publicationDate": "2025-06-15",
                "citationCount": 42,
                "authors": [{"name": "Dr. Alice Turing"}, {"name": "Prof. Bob Shannon"}],
                "openAccessPdf": {"url": "https://arxiv.org/pdf/2506.00001.pdf"},
                "url": "https://www.semanticscholar.org/paper/abcdef1234567890abcdef",
            }
        ],
    }

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(return_value=mock_payload)

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        items, total = await provider.search("quantum error correction", category="research")

    assert total == 1
    assert len(items) == 1
    item = items[0]
    assert "[Paper] Quantum Error Correction" in item.title
    assert item.url == "https://arxiv.org/pdf/2506.00001.pdf"
    assert item.source_name == "Semantic Scholar (Nature Quantum)"
    assert item.is_verified is True
    assert item.metadata["citations"] == 42
    assert "Dr. Alice Turing" in item.metadata["authors"]


@pytest.mark.asyncio
async def test_semantic_scholar_provider_rate_limits_and_category_skipping():
    """Verify provider skips unrelated non-academic categories and handles HTTP 429 cleanly."""
    provider = SemanticScholarProvider()

    # Non-academic category should skip immediately
    items, total = await provider.search("python", category="scholarships")
    assert items == []
    assert total == 0

    # Rate limit 429 handling
    mock_resp = AsyncMock()
    mock_resp.status_code = 429
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        items_429, total_429 = await provider.search("quantum", category="research")
        assert items_429 == []
        assert total_429 == 0


@pytest.mark.asyncio
async def test_brave_search_provider_availability_and_search():
    """Verify Brave Search API query normalization, domain extraction, and availability check."""
    # 1. Unavailable when no API key
    unavail = BraveSearchProvider(api_key=None)
    assert unavail.is_available() is False
    res, count = await unavail.search("robotics")
    assert res == []
    assert count == 0

    # 2. Available with API key
    provider = BraveSearchProvider(api_key="brave_test_token")
    assert provider.is_available() is True

    mock_payload = {
        "web": {
            "total": 1,
            "results": [
                {
                    "title": "Autonomous Robotics Lab - Breakthrough Demonstration",
                    "url": "https://robotics.mit.edu/news/breakthrough",
                    "description": "Researchers at MIT demo autonomous bipedal navigation.",
                    "page_age": "2026-03-01T12:00:00Z",
                }
            ],
        }
    }
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(return_value=mock_payload)

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        items, total = await provider.search("robotics breakthrough")

    assert total == 1
    assert len(items) == 1
    it = items[0]
    assert it.title == "Autonomous Robotics Lab - Breakthrough Demonstration"
    assert it.source_name == "robotics.mit.edu"
    assert it.category == "Web Discovery"
    assert it.url == "https://robotics.mit.edu/news/breakthrough"


@pytest.mark.asyncio
async def test_google_search_provider_availability_and_search():
    """Verify Google Programmable Search availability and JSON result normalization."""
    # 1. Missing CX or API key
    unavail = GoogleSearchProvider(api_key="key", cx=None)
    assert unavail.is_available() is False

    provider = GoogleSearchProvider(api_key="test_key", cx="test_cx")
    assert provider.is_available() is True

    mock_payload = {
        "searchInformation": {"totalResults": "100"},
        "items": [
            {
                "title": "Quantum Computing Architecture Overview",
                "link": "https://research.google.com/quantum/overview",
                "snippet": "Google Quantum AI lab architecture paper.",
            }
        ],
    }
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(return_value=mock_payload)

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        items, total = await provider.search("quantum architecture")

    assert total == 100
    assert len(items) == 1
    assert items[0].url == "https://research.google.com/quantum/overview"
    assert items[0].source_name == "research.google.com"


@pytest.mark.asyncio
async def test_duckduckgo_provider_availability_and_search():
    """Verify DuckDuckGo zero-config web search provider normalization."""
    provider = DuckDuckGoProvider()
    assert provider.is_available() is True

    mock_payload = {
        "Heading": "Autonomous Drone Navigation",
        "AbstractText": "Computer vision and SLAM methods for unmanned aerial robotics navigation in GPS-denied areas.",
        "AbstractURL": "https://en.wikipedia.org/wiki/Robot_navigation",
        "RelatedTopics": [
            {
                "Text": "Simultaneous localization and mapping - A computational method for spatial tracking.",
                "FirstURL": "https://en.wikipedia.org/wiki/Simultaneous_localization_and_mapping",
            }
        ],
    }
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(return_value=mock_payload)

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        items, total = await provider.search("robotics navigation")

    assert total == 2
    assert len(items) == 2
    assert items[0].title == "Autonomous Drone Navigation"
    assert items[0].url == "https://en.wikipedia.org/wiki/Robot_navigation"
    assert items[1].url == "https://en.wikipedia.org/wiki/Simultaneous_localization_and_mapping"
    assert items[0].score >= 3.5


@pytest.mark.asyncio
async def test_external_search_registry_concurrency_deduplication_and_resilience():
    """Verify ExternalSearchRegistry concurrently queries providers, deduplicates URLs, and handles failures."""
    item1 = SearchResultItem(
        id="item1",
        title="Title 1",
        url="https://example.com/shared-paper?utm_source=twitter",
        source_name="Provider A",
        category="Research Papers",
        score=5.0,
        item_type="paper",
    )
    # Duplicate URL with different query parameters (should normalize and deduplicate)
    item2 = SearchResultItem(
        id="item2",
        title="Title 1 (Mirror)",
        url="https://example.com/shared-paper?utm_source=facebook",
        source_name="Provider B",
        category="Web Discovery",
        score=4.0,
        item_type="external",
    )
    item3 = SearchResultItem(
        id="item3",
        title="Title 3",
        url="https://example.org/unique-paper",
        source_name="Provider C",
        category="Research Papers",
        score=6.0,
        item_type="paper",
    )

    prov_a = MagicMock()
    prov_a.is_available.return_value = True
    prov_a.search = AsyncMock(return_value=([item1], 1))

    prov_b = MagicMock()
    prov_b.is_available.return_value = True
    prov_b.search = AsyncMock(return_value=([item2], 1))

    prov_c = MagicMock()
    prov_c.is_available.return_value = True
    prov_c.search = AsyncMock(return_value=([item3], 1))

    # Provider D fails with exception
    prov_d = MagicMock()
    prov_d.is_available.return_value = True
    prov_d.search = AsyncMock(side_effect=RuntimeError("Network down"))

    registry = ExternalSearchRegistry(providers=[prov_a, prov_b, prov_c, prov_d])
    results, total = await registry.search_all_external("quantum", category="all", sort_by="relevance")

    # item1 and item2 have the same canonical URL (https://example.com/shared-paper), so deduplicated to 1
    assert len(results) == 2
    urls = [r.url for r in results]
    assert "https://example.org/unique-paper" in urls
    assert any("shared-paper" in u for u in urls)
    # Rank ordering: score 6.0 should come before score 5.0
    assert results[0].score >= results[1].score


@pytest.mark.asyncio
async def test_search_service_source_scope_internal_external_unified(test_session_factory):
    """Verify source parameter properly scopes search execution to internal, external, or unified."""
    # Seed internal item
    now = datetime.now(timezone.utc)
    async with test_session_factory() as session:
        repo = Repository(session)
        sources = await repo.get_sources()
        await repo.save_article(
            title="Internal Database Nanotechnology Paper",
            url="https://example.com/internal-nanotech-paper",
            source_id=sources[0].id,
            description="Stored in local database.",
            published_at=now,
        )

    ext_item = SearchResultItem(
        id="ext:1",
        title="Live Web External Nanotechnology Breakthrough",
        url="https://example.org/external-nanotech-paper",
        source_name="Nature Nano",
        category="Research Papers",
        score=7.0,
        item_type="paper",
    )

    mock_registry = AsyncMock()
    mock_registry.search_all_external = AsyncMock(return_value=([ext_item], 1))
    mock_registry.providers = []

    service = SearchService(session_factory=test_session_factory, external_registry=mock_registry)

    # 1. source="internal" -> only local database
    res_int = await service.search(query="nanotechnology", source="internal")
    assert res_int.source == "internal"
    mock_registry.search_all_external.assert_not_called()
    assert any("Internal Database" in it.title for it in res_int.items)
    assert not any("Live Web External" in it.title for it in res_int.items)

    # 2. source="external" -> only external registry
    mock_registry.search_all_external.reset_mock()
    res_ext = await service.search(query="nanotechnology", source="external")
    assert res_ext.source == "external"
    mock_registry.search_all_external.assert_called_once()
    assert any("Live Web External" in it.title for it in res_ext.items)
    assert not any("Internal Database" in it.title for it in res_ext.items)

    # 3. source="all" -> unified discovery
    mock_registry.search_all_external.reset_mock()
    res_all = await service.search(query="nanotechnology", source="all")
    assert res_all.source == "all"
    mock_registry.search_all_external.assert_called_once()
    titles = [it.title for it in res_all.items]
    assert any("Internal Database" in t for t in titles)
    assert any("Live Web External" in t for t in titles)


@pytest.mark.asyncio
async def test_duckduckgo_html_search_fallback():
    """Verify DuckDuckGo falls back to HTML web discovery when JSON API returns zero results."""
    provider = DuckDuckGoProvider()

    # 1. Mock JSON API returning empty data
    mock_json_resp = AsyncMock()
    mock_json_resp.status_code = 200
    mock_json_resp.json = MagicMock(return_value={"Heading": "", "AbstractText": "", "RelatedTopics": []})

    # 2. Mock HTML API returning live web search results
    sample_html = """
    <div class="result results_links results_links_deep web-result">
      <div class="links_main links_deep result__body">
        <h2 class="result__title">
          <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Ffastapi.tiangolo.com%2F">FastAPI</a>
        </h2>
        <a class="result__snippet" href="#">FastAPI is a modern, fast web framework for building APIs with Python.</a>
      </div>
    </div>
    """
    mock_html_resp = AsyncMock()
    mock_html_resp.status_code = 200
    mock_html_resp.text = sample_html

    with (
        patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_json_resp)),
        patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_html_resp)),
    ):
        items, total = await provider.search("fastapi python framework")

    assert total == 1
    assert len(items) == 1
    assert items[0].title == "FastAPI"
    assert items[0].url == "https://fastapi.tiangolo.com/"
    assert items[0].source_name == "fastapi.tiangolo.com"
    assert "modern, fast web framework" in items[0].snippet


@pytest.mark.asyncio
async def test_wikipedia_provider_opensearch():
    """Verify Wikipedia OpenSearch API integration for definitions and concept cards."""
    provider = WikipediaProvider()
    assert provider.is_available() is True

    sample_wiki_json = [
        "quantum computing",
        ["Quantum computing", "Quantum algorithm"],
        [
            "Quantum computing is a rapidly-emerging technology that harnesses quantum mechanics.",
            "A quantum algorithm is an algorithm which runs on a realistic model of quantum computation.",
        ],
        [
            "https://en.wikipedia.org/wiki/Quantum_computing",
            "https://en.wikipedia.org/wiki/Quantum_algorithm",
        ],
    ]
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(return_value=sample_wiki_json)

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
        items, total = await provider.search("quantum computing")

    assert total == 2
    assert len(items) == 2
    assert items[0].title == "Quantum computing"
    assert items[0].url == "https://en.wikipedia.org/wiki/Quantum_computing"
    assert items[0].source_name == "Wikipedia"
    assert items[0].category == "Reference & Concept"
    assert items[0].is_verified is True


@pytest.mark.asyncio
async def test_external_registry_default_providers():
    """Verify ExternalSearchRegistry contains Semantic Scholar, Wikipedia, Brave, Google, and DuckDuckGo."""
    registry = ExternalSearchRegistry()
    provider_names = [p.name for p in registry.providers]
    assert "semantic_scholar" in provider_names
    assert "wikipedia" in provider_names
    assert "brave_search" in provider_names
    assert "google_search" in provider_names
    assert "duckduckgo" in provider_names
