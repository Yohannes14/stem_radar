"""Tests for information collectors with mocked network responses."""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.collectors.arxiv_collector import ArxivCollector
from app.collectors.github_collector import GitHubCollector
from app.collectors.rss_collector import RSSCollector, is_valid_url
from tests.conftest import SAMPLE_ARXIV_ATOM, SAMPLE_RSS_XML

SAMPLE_ATOM_XML = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Engineering Innovations</title>
  <link href="https://example.org/feed.atom" rel="self"/>
  <link href="https://example.org/"/>
  <updated>2026-11-14T18:00:00Z</updated>
  <id>tag:example.org,2026:feed</id>
  <entry>
    <title>Next-Gen Solid State Battery Architectures</title>
    <link rel="alternate" type="text/html" href="https://example.org/battery-breakthrough"/>
    <id>tag:example.org,2026:entry-1</id>
    <updated>2026-11-14T18:00:00Z</updated>
    <summary>Novel solid-state electrolyte triples energy density in laboratory cells.</summary>
  </entry>
</feed>
"""

SAMPLE_FEEDBURNER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:feedburner="http://rssnamespace.org/feedburner/ext/1.0">
  <channel>
    <title>Quantum Frontiers</title>
    <link>http://feeds.example.com/quantum</link>
    <item>
      <title>Fault-Tolerant Logical Qubits Demonstrated</title>
      <link>http://feedproxy.google.com/~r/quantum/~3/abc12345/story.html</link>
      <feedburner:origLink>https://example.com/quantum/fault-tolerant-qubits</feedburner:origLink>
      <description>Experimental team creates 100 error-corrected logical qubits.</description>
      <pubDate>Thu, 13 Nov 2026 09:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

SAMPLE_RECOVERABLE_BOZO_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Imperfect Feed</title>
    <link>https://example.com</link>
    <item>
      <title>AI & Robotics Synergy</title>
      <link>https://example.com/ai-robotics</link>
      <description>Unescaped & in text causing bozo flag but entries are present.</description>
    </item>
  </channel>
</rss>
"""

SAMPLE_UNRECOVERABLE_XML = "This is not XML at all, just arbitrary plain text with no RSS structure."


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
async def test_rss_collector_parses_atom_feed():
    collector = RSSCollector(
        source_name="Engineering Feed",
        source_slug="engineering-feed",
        url="https://example.org/feed.atom",
    )

    mock_response = httpx.Response(
        status_code=200,
        text=SAMPLE_ATOM_XML,
        request=httpx.Request("GET", "https://example.org/feed.atom"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        articles = await collector.collect()

    assert len(articles) == 1
    assert "Solid State Battery" in articles[0].title
    assert articles[0].url == "https://example.org/battery-breakthrough"
    assert "energy density" in articles[0].description


@pytest.mark.asyncio
async def test_rss_collector_preserves_feedburner_original_url():
    collector = RSSCollector(
        source_name="Quantum Feed",
        source_slug="quantum-feed",
        url="http://feeds.example.com/quantum",
    )

    mock_response = httpx.Response(
        status_code=200,
        text=SAMPLE_FEEDBURNER_XML,
        request=httpx.Request("GET", "http://feeds.example.com/quantum"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        articles = await collector.collect()

    assert len(articles) == 1
    # Original canonical link should be preserved instead of proxy link
    assert articles[0].url == "https://example.com/quantum/fault-tolerant-qubits"


def test_rss_url_validation():
    assert is_valid_url("https://techcrunch.com/feed/") is True
    assert is_valid_url("http://export.arxiv.org/api/query") is True
    assert is_valid_url("ftp://example.com/feed.xml") is False
    assert is_valid_url("not_a_valid_url") is False
    assert is_valid_url("") is False
    assert is_valid_url(None) is False


@pytest.mark.asyncio
async def test_rss_collector_rejects_invalid_url():
    collector = RSSCollector(
        source_name="Bad URL Source",
        source_slug="bad-url",
        url="invalid-url-string",
    )
    articles = await collector.collect()
    assert articles == []


@pytest.mark.asyncio
async def test_rss_collector_handles_recoverable_bozo_xml():
    collector = RSSCollector(
        source_name="Bozo Recoverable",
        source_slug="bozo-rec",
        url="https://example.com/bozo.xml",
    )

    mock_response = httpx.Response(
        status_code=200,
        text=SAMPLE_RECOVERABLE_BOZO_XML,
        request=httpx.Request("GET", "https://example.com/bozo.xml"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        articles = await collector.collect()

    assert len(articles) == 1
    assert "AI & Robotics Synergy" in articles[0].title


@pytest.mark.asyncio
async def test_rss_collector_handles_unrecoverable_malformed_feed():
    collector = RSSCollector(
        source_name="Bozo Fatal",
        source_slug="bozo-fatal",
        url="https://example.com/fatal.xml",
    )

    mock_response = httpx.Response(
        status_code=200,
        text=SAMPLE_UNRECOVERABLE_XML,
        request=httpx.Request("GET", "https://example.com/fatal.xml"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        articles = await collector.collect()

    assert articles == []


@pytest.mark.asyncio
async def test_rss_collector_handles_empty_response():
    collector = RSSCollector(
        source_name="Empty Source",
        source_slug="empty-source",
        url="https://example.com/empty.xml",
    )

    mock_response = httpx.Response(
        status_code=200,
        text="   ",
        request=httpx.Request("GET", "https://example.com/empty.xml"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        articles = await collector.collect()

    assert articles == []


@pytest.mark.asyncio
async def test_rss_collector_handles_network_timeout():
    collector = RSSCollector(
        source_name="Timeout Source",
        source_slug="timeout-source",
        url="https://example.com/timeout.xml",
    )

    with (
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_get.side_effect = httpx.TimeoutException("Connection timed out")
        articles = await collector.collect()

    assert articles == []


@pytest.mark.asyncio
async def test_arxiv_collector_parses_atom():
    collector = ArxivCollector(
        source_name="arXiv AI",
        source_slug="arxiv-ai",
        url="https://export.arxiv.org/api/query?search_query=cat:cs.AI",
    )

    mock_response = httpx.Response(
        status_code=200,
        text=SAMPLE_ARXIV_ATOM,
        request=httpx.Request("GET", "https://export.arxiv.org/api/query"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        articles = await collector.collect()

    assert len(articles) == 1
    assert "[Paper]" in articles[0].title
    assert "Diffusion Models" in articles[0].title
    assert "Alice Smith" in articles[0].description
    assert articles[0].raw_data["authors"] == ["Alice Smith", "Bob Jones"]


def test_arxiv_collector_builds_query_url():
    collector = ArxivCollector(
        source_name="arXiv Multi-Category",
        source_slug="arxiv-multi",
        categories=["cs.AI", "cs.RO", "quant-ph"],
        max_results=20,
    )
    assert "cat:cs.AI+OR+cat:cs.RO+OR+cat:quant-ph" in collector.url
    assert "max_results=20" in collector.url


@pytest.mark.asyncio
async def test_arxiv_collector_handles_http_failure():
    collector = ArxivCollector(
        source_name="arXiv Outage",
        source_slug="arxiv-outage",
        url="https://export.arxiv.org/api/query?search_query=cat:cs.AI",
    )

    mock_response = httpx.Response(
        status_code=503,
        text="Service Temporarily Unavailable",
        request=httpx.Request("GET", "https://export.arxiv.org/api/query"),
    )

    with (
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_get.return_value = mock_response
        articles = await collector.collect()

    assert articles == []


@pytest.mark.asyncio
async def test_arxiv_collector_handles_empty_response():
    collector = ArxivCollector(
        source_name="arXiv Empty",
        source_slug="arxiv-empty",
        url="https://export.arxiv.org/api/query?search_query=cat:cs.AI",
    )

    mock_response = httpx.Response(
        status_code=200,
        text="",
        request=httpx.Request("GET", "https://export.arxiv.org/api/query"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        articles = await collector.collect()

    assert articles == []


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

    with (
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_get.return_value = mock_response
        articles = await collector.collect()

    # Collector should not raise an exception, returning an empty list gracefully
    assert articles == []


SAMPLE_GITHUB_SEARCH_JSON = {
    "total_count": 1,
    "items": [
        {
            "id": 123456,
            "name": "open-robotics-core",
            "full_name": "robotics-lab/open-robotics-core",
            "html_url": "https://github.com/robotics-lab/open-robotics-core",
            "description": "State of the art open source robotics kinematics and control platform.",
            "stargazers_count": 3420,
            "forks_count": 512,
            "language": "Python",
            "topics": ["robotics", "kinematics", "autonomous-systems"],
            "updated_at": "2026-11-14T20:15:00Z",
            "pushed_at": "2026-11-14T20:15:00Z",
        }
    ],
}


@pytest.mark.asyncio
async def test_github_collector_parses_repositories():
    collector = GitHubCollector(
        source_name="GitHub Trending",
        source_slug="github-trending",
        url="https://api.github.com/search/repositories?q=stars:>500",
    )

    mock_response = httpx.Response(
        status_code=200,
        text=json.dumps(SAMPLE_GITHUB_SEARCH_JSON),
        request=httpx.Request("GET", "https://api.github.com/search/repositories?q=stars:>500"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        articles = await collector.collect()

    assert len(articles) == 1
    repo = articles[0]
    assert "[Repo] robotics-lab/open-robotics-core (Python)" == repo.title
    assert repo.url == "https://github.com/robotics-lab/open-robotics-core"
    assert "Stars: ⭐ 3,420" in repo.description
    assert "Forks: 🍴 512" in repo.description
    assert "robotics" in repo.description
    assert repo.raw_data["stars"] == 3420
    assert repo.raw_data["language"] == "Python"
    assert repo.published_at is not None


@pytest.mark.asyncio
async def test_github_collector_handles_rate_limiting():
    collector = GitHubCollector(
        source_name="GitHub Rate Limited",
        source_slug="github-rate-limited",
        url="https://api.github.com/search/repositories?q=stars:>500",
    )

    headers = {
        "x-ratelimit-remaining": "0",
        "x-ratelimit-reset": "1731672000",
    }
    mock_response = httpx.Response(
        status_code=403,
        headers=headers,
        text=json.dumps({"message": "API rate limit exceeded"}),
        request=httpx.Request("GET", "https://api.github.com/search/repositories?q=stars:>500"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        articles = await collector.collect()

    assert articles == []


@pytest.mark.asyncio
async def test_github_collector_handles_http_errors():
    collector = GitHubCollector(
        source_name="GitHub Error",
        source_slug="github-error",
        url="https://api.github.com/search/repositories?q=stars:>500",
    )

    mock_response = httpx.Response(
        status_code=500,
        text="Internal Server Error",
        request=httpx.Request("GET", "https://api.github.com/search/repositories?q=stars:>500"),
    )

    with (
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_get.return_value = mock_response
        articles = await collector.collect()

    assert articles == []


def test_github_collector_custom_topics_and_stars():
    collector = GitHubCollector(
        topics=["quantum-computing", "robotics"],
        min_stars=1000,
        per_page=10,
    )
    assert "topic:quantum-computing+OR+topic:robotics" in collector.url
    assert "stars:>1000" in collector.url
    assert "per_page=10" in collector.url
