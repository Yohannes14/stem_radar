"""Unit tests for centralized STEM RADAR Information Architecture & Taxonomy Service."""

from app.core.taxonomy import (
    CATEGORY_KEYWORDS,
    DEFAULT_CATEGORIES,
    STEM_DOMAINS,
    taxonomy,
)


def test_taxonomy_primary_domains_count():
    """Verify exactly 12 core foundational STEM disciplines are defined."""
    primary = taxonomy.get_primary_domains()
    assert len(primary) == 12

    expected_slugs = {
        "ai",
        "computer-science",
        "software-engineering",
        "cybersecurity",
        "robotics",
        "electronics",
        "mechanical-engineering",
        "physics",
        "space-technology",
        "renewable-energy",
        "biotechnology",
        "emerging-tech",
    }
    assert {d.slug for d in primary} == expected_slugs


def test_taxonomy_cross_cutting_domains():
    """Verify regional and policy domains are classified as cross-cutting."""
    cross = taxonomy.get_cross_cutting_domains()
    assert len(cross) == 4
    cross_slugs = {d.slug for d in cross}
    assert cross_slugs == {"ethiopia-tech", "ethiopia-affairs", "global-politics", "tech-policy"}


def test_taxonomy_total_domains_count():
    """Verify total rich domain registry contains all 16 domains."""
    all_domains = taxonomy.get_all_domains()
    assert len(all_domains) == 16
    assert len(STEM_DOMAINS) == 16


def test_taxonomy_backward_compatible_database_seeds():
    """Verify all 23 historical database seed categories remain intact."""
    assert len(DEFAULT_CATEGORIES) == 23
    slugs = [slug for _, slug, _ in DEFAULT_CATEGORIES]
    assert "ai" in slugs
    assert "machine-learning" in slugs
    assert "robotics" in slugs
    assert "iot" in slugs
    assert "stem-education" in slugs
    assert "ethiopia-tech" in slugs


def test_taxonomy_alias_resolution():
    """Verify historical slugs resolve to their canonical primary STEM domain."""
    # Machine Learning resolves to AI & Data Science
    domain_ml = taxonomy.get_domain("machine-learning")
    assert domain_ml is not None
    assert domain_ml.slug == "ai"
    assert "Machine Learning" in domain_ml.name or "Artificial Intelligence" in domain_ml.name
    assert taxonomy.resolve_canonical_slug("machine-learning") == "ai"

    # Embedded Systems resolves to Electronics
    domain_emb = taxonomy.get_domain("embedded-systems")
    assert domain_emb is not None
    assert domain_emb.slug == "electronics"
    assert taxonomy.resolve_canonical_slug("embedded-systems") == "electronics"

    # IoT resolves to Electronics
    assert taxonomy.resolve_canonical_slug("iot") == "electronics"

    # Electrical Engineering resolves to Applied Engineering (mechanical-engineering)
    assert taxonomy.resolve_canonical_slug("electrical-engineering") == "mechanical-engineering"

    # Chemistry and Mathematics resolve to Natural Sciences (physics)
    assert taxonomy.resolve_canonical_slug("chemistry") == "physics"
    assert taxonomy.resolve_canonical_slug("mathematics") == "physics"


def test_taxonomy_keyword_lookup():
    """Verify complete keyword definitions for classification."""
    assert len(CATEGORY_KEYWORDS) == 23
    assert "ai" in CATEGORY_KEYWORDS
    assert "neural network" in CATEGORY_KEYWORDS["ai"]
    assert "humanoid" in CATEGORY_KEYWORDS["robotics"]

    # Method lookup
    kw_ai = taxonomy.get_keywords_for_slug("ai")
    assert len(kw_ai) >= 10
    kw_ml = taxonomy.get_keywords_for_slug("machine-learning")
    assert "pytorch" in kw_ml


def test_taxonomy_interests_options_formatting():
    """Verify options format for user onboarding and interest selection."""
    options = taxonomy.get_interests_options()
    assert len(options) == 16
    for name, slug, emoji in options:
        assert isinstance(name, str) and len(name) > 0
        assert isinstance(slug, str) and len(slug) > 0
        assert isinstance(emoji, str) and len(emoji) > 0
