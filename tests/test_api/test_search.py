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

    # 3. Filter by source=internal vs external
    res_internal = await api_client.get("/api/v1/search?q=Chemistry&source=internal")
    assert res_internal.status_code == 200
    assert res_internal.json()["source"] == "internal"

    res_external = await api_client.get("/api/v1/search?q=Chemistry&source=external")
    assert res_external.status_code == 200
    assert res_external.json()["source"] == "external"

    # 4. Validation error: query too short or invalid source
    res_short = await api_client.get("/api/v1/search?q=a")
    assert res_short.status_code == 422

    res_bad_source = await api_client.get("/api/v1/search?q=Chemistry&source=unsupported")
    assert res_bad_source.status_code == 422


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


@pytest.mark.asyncio
async def test_api_search_assistant_endpoints(api_client: AsyncClient, test_session_factory):
    """Test AI Search Assistant endpoints: summary, compare, and explain."""
    now = datetime.now(timezone.utc)
    async with test_session_factory() as session:
        repo = Repository(session)
        sources = await repo.get_sources()
        await repo.save_article(
            title="Bio-Inspired Soft Grippers in Robotics",
            url="https://example.com/soft-grippers-study",
            source_id=sources[0].id,
            description="Elastomeric actuators achieving fragile object manipulation without sensory feedback.",
            published_at=now,
        )

    # 1. GET /api/v1/search/assistant/summary
    res_sum = await api_client.get("/api/v1/search/assistant/summary?q=grippers&limit=3")
    assert res_sum.status_code == 200
    data_sum = res_sum.json()
    assert data_sum["query"] == "grippers"
    assert "executive_summary" in data_sum
    assert len(data_sum["source_citations"]) >= 1
    assert any("[1]" in f for f in data_sum["sourced_facts"])
    assert len(data_sum["related_questions"]) >= 1

    # 2. POST /api/v1/search/assistant/compare
    payload = {
        "topic": "Soft Grippers vs Rigid Grippers",
        "item_a": {
            "id": "item:1",
            "title": "Bio-Inspired Soft Grippers in Robotics",
            "snippet": "Elastomeric actuators achieving fragile manipulation.",
            "source_name": "Robotics Journal",
            "category": "Research Papers",
            "url": "https://example.com/soft-grippers",
            "item_type": "paper",
        },
        "item_b": {
            "id": "item:2",
            "title": "Industrial High-Payload Rigid Grippers",
            "snippet": "Pneumatic two-jaw precision grippers for manufacturing.",
            "source_name": "Automation Today",
            "category": "STEM News",
            "url": "https://example.com/rigid-grippers",
            "item_type": "news",
        },
    }
    res_cmp = await api_client.post("/api/v1/search/assistant/compare", json=payload)
    assert res_cmp.status_code == 200
    data_cmp = res_cmp.json()
    assert data_cmp["topic"] == "Soft Grippers vs Rigid Grippers"
    assert len(data_cmp["common_ground"]) >= 1
    assert len(data_cmp["divergent_points"]) >= 1
    assert "synthesis" in data_cmp
    assert "recommended_context" in data_cmp

    # 3. GET /api/v1/search/assistant/explain
    res_exp = await api_client.get("/api/v1/search/assistant/explain?topic=Pneumatic+Actuators&mode=intermediate")
    assert res_exp.status_code == 200
    data_exp = res_exp.json()
    assert data_exp["concept_name"] == "Pneumatic Actuators"
    assert "core_definition" in data_exp
    assert "how_it_works" in data_exp
