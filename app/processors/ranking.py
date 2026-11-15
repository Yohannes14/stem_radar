"""Intelligence ranking engine scoring articles by recency, domain depth, and impact."""

import re
from datetime import datetime, timezone
from typing import List, Tuple

# High-impact technological milestones & intelligence signals
IMPACT_KEYWORDS = [
    "breakthrough",
    "milestone",
    "novel",
    "state of the art",
    "sota",
    "benchmark",
    "open source",
    "open-source",
    "first ever",
    "discovered",
    "unveiled",
    "humanoid",
    "superconductor",
    "quantum advantage",
    "fda approved",
    "paradigm",
]

_IMPACT_PATTERNS = [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in IMPACT_KEYWORDS]


class ArticleRanker:
    """Calculates multi-factor intelligence scores for articles to power trending & digest feeds."""

    @staticmethod
    def calculate_score(
        title: str,
        description: str | None = None,
        published_at: datetime | None = None,
        categories: List[Tuple[str, float]] | None = None,
    ) -> float:
        """Calculate composite intelligence score (0.0 to 100.0)."""
        score = 50.0  # Base baseline score

        # 1. Recency Factor (Max +25 points)
        if published_at:
            now = datetime.now(timezone.utc)
            # Ensure timezone awareness
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)

            age_hours = max(0.0, (now - published_at).total_seconds() / 3600.0)
            if age_hours <= 12:
                score += 25.0
            elif age_hours <= 24:
                score += 20.0
            elif age_hours <= 48:
                score += 15.0
            elif age_hours <= 168:  # 1 week
                score += 5.0
            else:
                score -= 10.0

        # 2. Impact Keyword Signals (Max +20 points)
        text_corpus = f"{title} {description or ''}"
        impact_matches = 0
        for pattern in _IMPACT_PATTERNS:
            if pattern.search(text_corpus):
                impact_matches += 1

        score += min(20.0, impact_matches * 5.0)

        # 3. Category Confidence Depth (Max +15 points)
        if categories:
            top_confidence = categories[0][1] if categories else 0.5
            score += top_confidence * 15.0

        # 4. Content Completeness (Max +5 points)
        if description and len(description.strip()) > 150:
            score += 5.0

        return round(max(0.0, min(100.0, score)), 2)


ranker = ArticleRanker()
