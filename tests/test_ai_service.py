"""Tests for the AI Service and heuristic fallback engine."""

from unittest.mock import MagicMock

import pytest

from app.database.models import Article, Category, Source
from app.services.ai_service import AIService


@pytest.mark.asyncio
async def test_ai_service_generates_heuristic_analysis_without_api_key():
    service = AIService(api_key=None)

    mock_source = MagicMock(spec=Source)
    mock_source.name = "TechCrunch"

    mock_category = MagicMock(spec=Category)
    mock_category.name = "Artificial Intelligence"

    mock_article = MagicMock(spec=Article)
    mock_article.title = "Novel Transformer Architecture Slashes Memory by 40%"
    mock_article.description = "Researchers demonstrate a new attention optimization technique."
    mock_article.url = "https://example.com/transformer-news"
    mock_article.source = mock_source
    mock_article.categories = [mock_category]

    analysis = await service.analyze_article(mock_article)

    assert analysis.article_title == mock_article.title
    assert analysis.category == "Artificial Intelligence"
    assert "Memory" in analysis.short_summary
    assert len(analysis.real_world_applications) >= 1
    assert len(analysis.important_concepts) >= 1
    assert analysis.source_url == mock_article.url
