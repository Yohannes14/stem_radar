"""Tests for NewsService ingestion pipeline, deduplication, and failure isolation."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.collectors.base import CollectedArticle
from app.database.repository import Repository
from app.services.news_service import NewsService


@pytest.mark.asyncio
async def test_news_service_collects_and_classifies(test_session_factory):
    service = NewsService(session_factory=test_session_factory)

    mock_articles = [
        CollectedArticle(
            title="Transformer Scaling Laws for Large Language Models",
            url="https://example.com/transformer-scaling",
            source_slug="techcrunch",
            source_name="TechCrunch",
            description="Analysis of deep learning architectures and artificial intelligence neural networks.",
            published_at=datetime.now(timezone.utc),
        ),
        CollectedArticle(
            title="Dynamic Bipedal Walking Controller for Humanoid Robots",
            url="https://example.com/humanoid-walking",
            source_slug="techcrunch",
            source_name="TechCrunch",
            description="Inverse kinematics and motor actuator algorithms for robotics balance.",
            published_at=datetime.now(timezone.utc),
        ),
    ]

    with patch("app.collectors.rss_collector.RSSCollector.collect", new_callable=AsyncMock) as mock_collect:
        mock_collect.return_value = mock_articles

        async with test_session_factory() as session:
            repo = Repository(session)
            source = await repo.get_source_by_slug("techcrunch")

        saved = await service.collect_from_source(source)
        assert saved == 2

    # Verify database persistence and categorization
    async with test_session_factory() as session:
        repo = Repository(session)
        articles = await repo.get_recent_articles(limit=10)
        assert len(articles) == 2

        # Check classification
        ai_article = next(a for a in articles if "Transformer" in a.title)
        robotics_article = next(a for a in articles if "Humanoid" in a.title)

        ai_categories = [c.slug for c in ai_article.categories]
        assert "ai" in ai_categories or "machine-learning" in ai_categories

        robotics_categories = [c.slug for c in robotics_article.categories]
        assert "robotics" in robotics_categories

        # Check source health updated
        refreshed_source = await repo.get_source_by_slug("techcrunch")
        assert refreshed_source.error_count == 0
        assert refreshed_source.last_collected_at is not None


@pytest.mark.asyncio
async def test_news_service_deduplicates_incoming_articles(test_session_factory):
    service = NewsService(session_factory=test_session_factory)

    article_batch = [
        CollectedArticle(
            title="Quantum Superconducting Circuit",
            url="https://example.com/quantum-chip?utm_source=rss",
            source_slug="techcrunch",
            source_name="TechCrunch",
            description="New quantum processor fabricated.",
            published_at=datetime.now(timezone.utc),
        )
    ]

    with patch("app.collectors.rss_collector.RSSCollector.collect", new_callable=AsyncMock) as mock_collect:
        mock_collect.return_value = article_batch

        async with test_session_factory() as session:
            repo = Repository(session)
            source = await repo.get_source_by_slug("techcrunch")

        # First collection
        saved_first = await service.collect_from_source(source)
        assert saved_first == 1

        # Second collection with same URL (different query params)
        article_batch[0].url = "https://example.com/quantum-chip?ref=newsletter"
        saved_second = await service.collect_from_source(source)
        # Deduplicator should recognize it as the same URL and not re-insert
        assert saved_second == 0


@pytest.mark.asyncio
async def test_news_service_failure_isolation(test_session_factory):
    service = NewsService(session_factory=test_session_factory)

    # Disable all sources except two to test isolation
    async with test_session_factory() as session:
        repo = Repository(session)
        sources = await repo.get_sources()
        for s in sources:
            if s.slug not in ("techcrunch", "theverge"):
                s.is_active = False
        await session.commit()

    async def side_effect_collect(self_collector):
        if self_collector.source_slug == "techcrunch":
            raise RuntimeError("DNS resolution failed for techcrunch.com")
        return [
            CollectedArticle(
                title="Apple Releases New M-Series Chip Architecture",
                url="https://theverge.com/m-series-chip",
                source_slug="theverge",
                source_name="The Verge",
                description="Semiconductor and electronics microarchitecture analysis.",
                published_at=datetime.now(timezone.utc),
            )
        ]

    with patch("app.collectors.rss_collector.RSSCollector.collect", autospec=True, side_effect=side_effect_collect):
        results = await service.collect_from_all_sources()

    # TechCrunch failed, but Verge succeeded
    assert results.get("techcrunch") == 0
    assert results.get("theverge") == 1

    # Check health telemetry in database
    async with test_session_factory() as session:
        repo = Repository(session)
        tc_source = await repo.get_source_by_slug("techcrunch")
        assert tc_source.error_count == 1
        assert "DNS resolution failed" in tc_source.last_error

        verge_source = await repo.get_source_by_slug("theverge")
        assert verge_source.error_count == 0
        assert verge_source.last_collected_at is not None


@pytest.mark.asyncio
async def test_news_service_source_type_filtering(test_session_factory):
    service = NewsService(session_factory=test_session_factory)

    async with test_session_factory() as session:
        repo = Repository(session)
        arxiv_source = await repo.get_source_by_slug("arxiv-ai")
        github_source = await repo.get_source_by_slug("github-trending")

        # Save an arXiv paper
        await repo.save_article(
            title="[Paper] Graph Neural Networks for Molecule Generation",
            url="https://arxiv.org/abs/2611.99999",
            source_id=arxiv_source.id,
            description="Deep learning for biotechnology.",
        )

        # Save a GitHub repo
        await repo.save_article(
            title="[Repo] autonomous-systems/core (Rust)",
            url="https://github.com/autonomous-systems/core",
            source_id=github_source.id,
            description="Robotics framework.",
        )

    # Filter by source_type="arxiv"
    arxiv_articles = await service.get_recent_news(source_type="arxiv")
    assert len(arxiv_articles) == 1
    assert "Graph Neural Networks" in arxiv_articles[0].title

    # Filter by source_type="github"
    github_articles = await service.get_recent_news(source_type="github")
    assert len(github_articles) == 1
    assert "autonomous-systems/core" in github_articles[0].title
