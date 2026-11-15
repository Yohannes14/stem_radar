"""Tests for the intelligence ranking and scoring engine."""

from datetime import datetime, timedelta, timezone

from app.processors.ranking import ArticleRanker


def test_article_ranker_recent_scores_higher_than_old():
    now = datetime.now(timezone.utc)
    recent_date = now - timedelta(hours=2)
    old_date = now - timedelta(days=30)

    recent_score = ArticleRanker.calculate_score(
        title="Standard Tech Update",
        published_at=recent_date,
    )
    old_score = ArticleRanker.calculate_score(
        title="Standard Tech Update",
        published_at=old_date,
    )

    assert recent_score > old_score


def test_article_ranker_boosts_impact_keywords():
    now = datetime.now(timezone.utc)
    normal_score = ArticleRanker.calculate_score(
        title="Company updates software package",
        published_at=now,
    )
    breakthrough_score = ArticleRanker.calculate_score(
        title="Breakthrough in Quantum Computing with SOTA Benchmark Unveiled",
        published_at=now,
    )

    assert breakthrough_score > normal_score
