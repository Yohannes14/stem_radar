"""Tests for URL normalization and duplicate hash calculation."""

from app.processors.deduplicator import compute_article_hash, normalize_url


def test_normalize_url_strips_tracking_params():
    raw = "https://techcrunch.com/2026/11/10/ai-chip-breakthrough/?utm_source=twitter&utm_medium=social&ref=tech"
    expected = "https://techcrunch.com/2026/11/10/ai-chip-breakthrough"
    assert normalize_url(raw) == expected


def test_normalize_url_handles_trailing_slash_and_case():
    raw = "HTTPS://Example.COM/Article/123/"
    expected = "https://example.com/Article/123"
    assert normalize_url(raw) == expected


def test_compute_article_hash_stability():
    url1 = "https://example.com/robotics?utm_source=rss"
    url2 = "https://example.com/robotics"
    title = "Next-Gen Humanoid Robot"

    hash1 = compute_article_hash(title, url1)
    hash2 = compute_article_hash(title, url2)

    # Identical content with different tracking params must produce matching hashes
    assert hash1 == hash2
