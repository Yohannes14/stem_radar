"""Tests for the /api/v1/news endpoints (listing, pagination, filtering, details)."""

import pytest
from httpx import AsyncClient

from app.database.repository import Repository


@pytest.mark.asyncio
async def test_list_news_empty(api_client: AsyncClient):
    """Test listing news when no articles are present."""
    response = await api_client.get("/api/v1/news")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["pagination"]["total_items"] == 0
    assert data["pagination"]["total_pages"] == 0
    assert data["pagination"]["has_next"] is False
    assert data["pagination"]["has_prev"] is False


@pytest.mark.asyncio
async def test_list_news_with_data_and_pagination(api_client: AsyncClient, test_session_factory):
    """Test news listing with populated articles and pagination bounds."""
    async with test_session_factory() as session:
        repo = Repository(session)
        # Fetch pre-seeded categories and sources
        sources = await repo.get_sources()
        src = sources[0]
        cat_ai = await repo.get_category_by_slug("ai")
        cat_robotics = await repo.get_category_by_slug("robotics")

        # Seed 15 test articles
        for i in range(1, 16):
            cat_ids = [cat_ai.id] if i % 2 == 0 else [cat_robotics.id]
            await repo.save_article(
                title=f"Breakthrough Article #{i}",
                url=f"https://example.com/article-{i}",
                source_id=src.id,
                description=f"Detailed description for research item #{i}",
                category_ids=cat_ids,
            )

    # 1. Page 1 with page_size=10
    res_p1 = await api_client.get("/api/v1/news?page=1&page_size=10")
    assert res_p1.status_code == 200
    p1_data = res_p1.json()
    assert len(p1_data["items"]) == 10
    assert p1_data["pagination"]["page"] == 1
    assert p1_data["pagination"]["total_items"] == 15
    assert p1_data["pagination"]["total_pages"] == 2
    assert p1_data["pagination"]["has_next"] is True
    assert p1_data["pagination"]["has_prev"] is False

    # 2. Page 2 with page_size=10
    res_p2 = await api_client.get("/api/v1/news?page=2&page_size=10")
    assert res_p2.status_code == 200
    p2_data = res_p2.json()
    assert len(p2_data["items"]) == 5
    assert p2_data["pagination"]["page"] == 2
    assert p2_data["pagination"]["has_next"] is False
    assert p2_data["pagination"]["has_prev"] is True

    # 3. Filter by category
    res_cat = await api_client.get("/api/v1/news?category=robotics")
    assert res_cat.status_code == 200
    cat_data = res_cat.json()
    assert cat_data["pagination"]["total_items"] == 8

    # 4. Filter by keyword search
    res_search = await api_client.get("/api/v1/news", params={"q": "Article #1"})
    assert res_search.status_code == 200
    search_data = res_search.json()
    assert search_data["pagination"]["total_items"] >= 1
    for item in search_data["items"]:
        assert "Article #1" in item["title"]


@pytest.mark.asyncio
async def test_get_article_by_id_success_and_not_found(api_client: AsyncClient, test_session_factory):
    """Test retrieving single article by ID and 404 behavior."""
    async with test_session_factory() as session:
        repo = Repository(session)
        sources = await repo.get_sources()
        src = sources[0]

        article, _ = await repo.save_article(
            title="Scalable Transformers for Quantum Chemistry",
            url="https://arxiv.org/abs/2611.9999",
            source_id=src.id,
            description="Quantum mechanics simulated with deep learning.",
        )
        article_id = article.id

    # 1. Existing article
    res_ok = await api_client.get(f"/api/v1/news/{article_id}")
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["id"] == article_id
    assert data["title"] == "Scalable Transformers for Quantum Chemistry"
    assert data["source"]["id"] == src.id

    # 2. Non-existent article returns 404
    res_404 = await api_client.get("/api/v1/news/99999")
    assert res_404.status_code == 404
    err_data = res_404.json()
    assert err_data["error"]["code"] == "NOT_FOUND"
    assert "99999" in err_data["error"]["message"]


@pytest.mark.asyncio
async def test_list_news_validation_errors(api_client: AsyncClient):
    """Test validation errors for invalid pagination query parameters."""
    # Invalid page (page < 1)
    res_bad_page = await api_client.get("/api/v1/news?page=0")
    assert res_bad_page.status_code == 422
    err_data = res_bad_page.json()
    assert err_data["error"]["code"] == "VALIDATION_ERROR"

    # Invalid page size (page_size > 50)
    res_bad_size = await api_client.get("/api/v1/news?page_size=100")
    assert res_bad_size.status_code == 422

    # Invalid article_id type in path
    res_bad_id = await api_client.get("/api/v1/news/invalid-id")
    assert res_bad_id.status_code == 422
