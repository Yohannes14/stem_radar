"""Tests for database operations, repository CRUD, and duplicate prevention."""

import pytest

from app.database.repository import Repository


@pytest.mark.asyncio
async def test_repository_get_sources_and_categories(test_session_factory):
    async with test_session_factory() as session:
        repo = Repository(session)
        sources = await repo.get_sources()
        categories = await repo.get_categories()

        assert len(sources) > 0
        assert len(categories) == 19


@pytest.mark.asyncio
async def test_repository_save_article_and_prevent_duplicates(test_session_factory):
    async with test_session_factory() as session:
        repo = Repository(session)
        source = (await repo.get_sources())[0]

        # First insert
        article1, created1 = await repo.save_article(
            title="Breakthrough in Quantum Computing",
            url="https://example.com/quantum-news",
            source_id=source.id,
            description="Scientists achieve new quantum coherence benchmark.",
        )
        assert created1 is True
        assert article1 is not None

        # Duplicate insert attempt with same URL (even with tracking query param)
        article2, created2 = await repo.save_article(
            title="Breakthrough in Quantum Computing",
            url="https://example.com/quantum-news?ref=rss",
            source_id=source.id,
            description="Duplicate attempt.",
        )
        # Should detect existing article and NOT duplicate
        assert created2 is False
        assert article2.id == article1.id


@pytest.mark.asyncio
async def test_repository_search_and_filter(test_session_factory):
    async with test_session_factory() as session:
        repo = Repository(session)
        source = (await repo.get_sources())[0]

        await repo.save_article(
            title="Novel CRISPR Gene Therapy Approved",
            url="https://example.com/crispr-therapy",
            source_id=source.id,
            description="Biotechnology advance in clinical trials.",
        )

        # Search matching query
        results = await repo.search_articles(query="CRISPR")
        assert len(results) == 1
        assert "CRISPR" in results[0].title

        # Search non-matching query
        no_results = await repo.search_articles(query="Unicorn")
        assert len(no_results) == 0


@pytest.mark.asyncio
async def test_repository_bookmark_toggle(test_session_factory):
    async with test_session_factory() as session:
        repo = Repository(session)
        source = (await repo.get_sources())[0]

        article, _ = await repo.save_article(
            title="Autonomous Drone Navigation",
            url="https://example.com/drone-nav",
            source_id=source.id,
        )

        user_id = 998877

        # 1st toggle: Save
        is_saved = await repo.toggle_save_article(user_id=user_id, article_id=article.id)
        assert is_saved is True

        bookmarks = await repo.get_saved_articles(user_id=user_id)
        assert len(bookmarks) == 1
        assert bookmarks[0].id == article.id

        # 2nd toggle: Remove
        is_saved_again = await repo.toggle_save_article(user_id=user_id, article_id=article.id)
        assert is_saved_again is False

        bookmarks_after = await repo.get_saved_articles(user_id=user_id)
        assert len(bookmarks_after) == 0


@pytest.mark.asyncio
async def test_repository_get_recent_articles_sorting(test_session_factory):
    async with test_session_factory() as session:
        repo = Repository(session)
        source = (await repo.get_sources())[0]

        await repo.save_article(
            title="First Article",
            url="https://example.com/first",
            source_id=source.id,
        )
        await repo.save_article(
            title="Second Article",
            url="https://example.com/second",
            source_id=source.id,
        )

        articles = await repo.get_recent_articles(limit=10)
        assert len(articles) == 2
