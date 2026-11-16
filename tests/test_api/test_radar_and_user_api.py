"""Tests for Stage 8: Technology Radar and User Bookmarks/Interests REST endpoints."""

import pytest
from httpx import AsyncClient

from app.database.repository import Repository


@pytest.mark.asyncio
async def test_get_tech_radar_full_and_filtered(api_client: AsyncClient):
    """Test GET /api/v1/radar returns full radar or filtered horizon."""
    # 1. Full Radar
    res_full = await api_client.get("/api/v1/radar")
    assert res_full.status_code == 200
    data = res_full.json()
    assert "horizons" in data
    assert "adopt" in data["horizons"]
    assert "trial" in data["horizons"]
    assert "assess" in data["horizons"]
    assert "hold" in data["horizons"]
    assert len(data["horizons"]["adopt"]["items"]) > 0

    # 2. Filtered Horizon (Adopt)
    res_adopt = await api_client.get("/api/v1/radar?horizon=adopt")
    assert res_adopt.status_code == 200
    data_adopt = res_adopt.json()
    assert "adopt" in data_adopt["horizons"]
    assert "trial" not in data_adopt["horizons"]


@pytest.mark.asyncio
async def test_get_radar_velocity(api_client: AsyncClient):
    """Test GET /api/v1/radar/velocity returns domain publication momentum."""
    res = await api_client.get("/api/v1/radar/velocity")
    assert res.status_code == 200
    data = res.json()
    assert "domains" in data
    assert "total_domains" in data
    assert isinstance(data["domains"], list)


@pytest.mark.asyncio
async def test_user_bookmarks_crud(api_client: AsyncClient, test_session_factory):
    """Test GET, POST, and DELETE /api/v1/user/bookmarks."""
    user_id = 998811

    # Seed an article to bookmark
    async with test_session_factory() as session:
        repo = Repository(session)
        sources = await repo.get_sources()
        cat_ai = await repo.get_category_by_slug("ai")
        article, _ = await repo.save_article(
            title="FastAPI Integration Article",
            url="https://example.com/fastapi-article",
            source_id=sources[0].id,
            description="High-performance async APIs with FastAPI and SQLite.",
            category_ids=[cat_ai.id],
        )
        art_id = article.id

    # 1. Initially no bookmarks
    res_empty = await api_client.get(f"/api/v1/user/bookmarks?user_id={user_id}")
    assert res_empty.status_code == 200
    assert res_empty.json()["total_saved"] == 0

    # 2. Bookmark the article
    res_post = await api_client.post(
        f"/api/v1/user/bookmarks?user_id={user_id}",
        json={"article_id": art_id},
    )
    assert res_post.status_code == 200
    assert res_post.json()["saved"] is True
    assert res_post.json()["article_id"] == art_id

    # 3. List bookmarks now returns 1 item
    res_list = await api_client.get(f"/api/v1/user/bookmarks?user_id={user_id}")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total_saved"] == 1
    assert list_data["items"][0]["id"] == art_id
    assert list_data["items"][0]["title"] == "FastAPI Integration Article"
    assert list_data["items"][0]["reading_time_minutes"] >= 1
    assert "#ai" in list_data["items"][0]["tags"]

    # 4. Delete the bookmark
    res_del = await api_client.delete(f"/api/v1/user/bookmarks/{art_id}?user_id={user_id}")
    assert res_del.status_code == 200
    assert res_del.json()["saved"] is False

    # 5. List bookmarks is empty again
    res_after = await api_client.get(f"/api/v1/user/bookmarks?user_id={user_id}")
    assert res_after.status_code == 200
    assert res_after.json()["total_saved"] == 0

    # 6. Deleting non-existent bookmark returns 404
    res_404 = await api_client.delete(f"/api/v1/user/bookmarks/{art_id}?user_id={user_id}")
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_user_interests_get_and_put(api_client: AsyncClient):
    """Test GET and PUT /api/v1/user/interests."""
    user_id = 998822

    # 1. Get default empty interests
    res_get = await api_client.get(f"/api/v1/user/interests?user_id={user_id}")
    assert res_get.status_code == 200
    assert res_get.json()["preferred_categories"] == []

    # 2. Update interests with PUT
    res_put = await api_client.put(
        f"/api/v1/user/interests?user_id={user_id}",
        json={"categories": ["ai", "robotics", "cybersecurity"]},
    )
    assert res_put.status_code == 200
    put_data = res_put.json()
    assert put_data["preferred_categories"] == ["ai", "robotics", "cybersecurity"]

    # 3. Verify updated interests persist on subsequent GET
    res_get2 = await api_client.get(f"/api/v1/user/interests?user_id={user_id}")
    assert res_get2.status_code == 200
    assert res_get2.json()["preferred_categories"] == ["ai", "robotics", "cybersecurity"]


@pytest.mark.asyncio
async def test_news_endpoint_enriched_fields(api_client: AsyncClient, test_session_factory):
    """Test GET /api/v1/news returns enriched reading_time, tags, why_it_matters, and is_paper fields."""
    async with test_session_factory() as session:
        repo = Repository(session)
        sources = await repo.get_sources()
        cat_ai = await repo.get_category_by_slug("ai")
        await repo.save_article(
            title="Enriched Metadata Article",
            url="https://example.com/enriched-article",
            source_id=sources[0].id,
            description="Transformers have revolutionized sequence transduction tasks across computer science.",
            category_ids=[cat_ai.id],
        )

    res = await api_client.get("/api/v1/news?page=1&page_size=5")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) > 0
    item = next(it for it in items if it["title"] == "Enriched Metadata Article")
    assert "reading_time_minutes" in item
    assert item["reading_time_minutes"] >= 1
    assert "why_it_matters" in item
    assert "Transformers have revolutionized" in item["why_it_matters"]
    assert "tags" in item
    assert "#ai" in item["tags"]
    assert "is_paper" in item
