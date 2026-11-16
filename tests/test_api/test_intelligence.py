"""Tests for Intelligence API endpoints: /categories, /trending, and /research."""

import pytest
from httpx import AsyncClient

from app.database.models import Source
from app.database.repository import Repository


@pytest.mark.asyncio
async def test_list_categories(api_client: AsyncClient):
    """Test retrieving STEM categories registry."""
    response = await api_client.get("/api/v1/categories")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] >= 19
    slugs = [c["slug"] for c in data["items"]]
    assert "ai" in slugs
    assert "robotics" in slugs
    assert "computer-science" in slugs
    assert "physics" in slugs


@pytest.mark.asyncio
async def test_get_trending_developments(api_client: AsyncClient, test_session_factory):
    """Test trending technological breakthroughs ranked by ArticleRanker score."""
    async with test_session_factory() as session:
        repo = Repository(session)
        sources = await repo.get_sources()
        src = sources[0]

        # Seed breakthrough article with impact keywords
        await repo.save_article(
            title="State of the art breakthrough in superconductor materials unveiled",
            url="https://example.com/breakthrough-superconductor",
            source_id=src.id,
            description="Researchers discovered novel room temperature superconductors with first ever benchmarks.",
        )

    response = await api_client.get("/api/v1/trending?limit=5")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] >= 1
    assert len(data["items"]) <= 5
    first = data["items"][0]
    assert first["rank"] == 1
    assert first["score"] > 50.0
    assert first["impact_level"] in ("breakthrough", "high", "standard")
    assert "article" in first


@pytest.mark.asyncio
async def test_list_research_papers(api_client: AsyncClient, test_session_factory):
    """Test research papers endpoint specifically querying academic arXiv papers."""
    async with test_session_factory() as session:
        # Create an arxiv source
        src_arxiv = Source(name="arXiv CS", slug="arxiv-cs-test", url="https://arxiv.org", source_type="arxiv")
        session.add(src_arxiv)
        await session.commit()
        await session.refresh(src_arxiv)

        repo = Repository(session)
        cat_cs = await repo.get_category_by_slug("computer-science")

        # Seed research paper
        await repo.save_article(
            title="Formal Verification of Neural Network Controllers",
            url="https://arxiv.org/abs/2611.12345",
            source_id=src_arxiv.id,
            description="Abstract: We present an end-to-end framework for formal verification.",
            category_ids=[cat_cs.id],
        )

    # 1. Fetch all research papers
    response = await api_client.get("/api/v1/research?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()

    assert data["pagination"]["total_items"] >= 1
    titles = [p["title"] for p in data["items"]]
    assert "Formal Verification of Neural Network Controllers" in titles

    paper = data["items"][0]
    assert "abstract" in paper
    assert "source_name" in paper

    # 2. Filter by category
    res_filtered = await api_client.get("/api/v1/research?category=computer-science")
    assert res_filtered.status_code == 200
    filtered_data = res_filtered.json()
    assert filtered_data["pagination"]["total_items"] >= 1

