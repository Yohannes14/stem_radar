"""Tests for /api/v1/search endpoints (query, categories, sorting, pagination, history)."""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from app.database.repository import Repository


@pytest.mark.asyncio
async def test_api_unified_search_endpoint(api_client: AsyncClient, test_session_factory):
    """Test GET /api/v1/search with keywords, categories, and pagination."""
    now = datetime.now(timezone.utc)
    async with test_session_factory() as session:
        repo = Repository(session)
        sources = await repo.get_sources()

        # Seed test article
        await repo.save_article(
            title="Graph Neural Networks in Molecular Chemistry",
            url="https://example.com/gnn-chemistry-api-test",
            source_id=sources[0].id,
            description="Deep learning for chemical synthesis and molecular discovery.",
            published_at=now,
        )

        # Seed test scholarship
        await repo.save_opportunity(
            title="Computational Chemistry PhD Award",
            slug="comp-chem-phd-api-test",
            opportunity_type="scholarship",
            provider_name="Max Planck Institute",
            official_url="https://example.org/chemistry-phd",
            country="Germany",
            study_level="phd",
            funding_type="fully_funded",
            stem_fields="Chemistry, Computer Science",
        )

    # 1. Broad query
    res = await api_client.get("/api/v1/search?q=Chemistry&page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert data["query"] == "Chemistry"
    assert data["pagination"]["total_items"] >= 2
    items = data["items"]
    assert any("Graph Neural Networks" in it["title"] for it in items)
    assert any("Computational Chemistry" in it["title"] for it in items)

    # 2. Filter by category=scholarships
    res_sch = await api_client.get("/api/v1/search?q=Chemistry&category=scholarships")
    assert res_sch.status_code == 200
    data_sch = res_sch.json()
    assert all(it["item_type"] == "scholarship" for it in data_sch["items"])

    # 3. Validation error: query too short
    res_short = await api_client.get("/api/v1/search?q=a")
    assert res_short.status_code == 422


@pytest.mark.asyncio
async def test_api_search_history_endpoints(api_client: AsyncClient, test_session_factory):
    """Test GET and DELETE /api/v1/search/history."""
    user_id = 445566
    async with test_session_factory() as session:
        repo = Repository(session)
        pref = await repo.get_or_create_preference(user_id)
        pref.search_history_enabled = True
        await session.commit()
        await repo.save_search_query_log(query="photovoltaics", user_id=user_id, category="all", results_count=5)
        await repo.save_search_query_log(query="aerodynamics", user_id=user_id, category="all", results_count=3)

    # 1. Fetch history
    res = await api_client.get(f"/api/v1/search/history?user_id={user_id}&limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 2
    queries = [item["query"] for item in data["items"]]
    assert "photovoltaics" in queries
    assert "aerodynamics" in queries

    # 2. Delete history
    res_del = await api_client.delete(f"/api/v1/search/history?user_id={user_id}")
    assert res_del.status_code == 200
    assert res_del.json()["deleted_count"] >= 2

    # 3. Confirm empty
    res_empty = await api_client.get(f"/api/v1/search/history?user_id={user_id}&limit=10")
    assert res_empty.status_code == 200
    assert res_empty.json()["total"] == 0

