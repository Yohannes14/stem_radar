"""Tests for information collectors with mocked network responses."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.collectors.arxiv_collector import ArxivCollector
from app.collectors.rss_collector import RSSCollector
from tests.conftest import SAMPLE_ARXIV_ATOM, SAMPLE_RSS_XML


@pytest.mark.asyncio
async def test_rss_collector_parses_feed():
    collector = RSSCollector(
        source_name="Sample Tech",
        source_slug="sample-tech",
        url="https://example.com/feed.xml",
    )

    mock_response = httpx.Response(
        status_code=200,
        text=SAMPLE_RSS_XML,
        request=httpx.Request("GET", "https://example.com/feed.xml"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        articles = await collector.collect()

    assert len(articles) == 2
    assert "Humanoid Robotics" in articles[0].title
    # Verify HTML tags were stripped from description
    assert "<p>" not in articles[0].description
    assert articles[0].source_slug == "sample-tech"


@pytest.mark.asyncio
async def test_arxiv_collector_parses_atom():
    collector = ArxivCollector(
        source_name="arXiv AI",
        source_slug="arxiv-ai",
        url="http://export.arxiv.org/api/query?search_query=cat:cs.AI",
    )

    mock_response = httpx.Response(
        status_code=200,
        text=SAMPLE_ARXIV_ATOM,
        request=httpx.Request("GET", "http://export.arxiv.org/api/query"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        articles = await collector.collect()

    assert len(articles) == 1
    assert "[Paper]" in articles[0].title
    assert "Diffusion Models" in articles[0].title
    assert "Alice Smith" in articles[0].description


@pytest.mark.asyncio
async def test_rss_collector_handles_http_errors_gracefully():
    collector = RSSCollector(
        source_name="Failing Source",
        source_slug="failing-source",
        url="https://example.com/error.xml",
    )

    mock_response = httpx.Response(
        status_code=500,
        text="Internal Server Error",
        request=httpx.Request("GET", "https://example.com/error.xml"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        articles = await collector.collect()

    # Collector should not raise an exception, returning an empty list gracefully
    assert articles == []
