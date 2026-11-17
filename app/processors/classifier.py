"""STEM classification engine matching articles to the 19 STEM domains."""

import re
from typing import Dict, List, Tuple

from app.core.taxonomy import CATEGORY_KEYWORDS


class STEMClassifier:
    """Classifies text into STEM categories using keyword analysis and scoring."""

    def __init__(self) -> None:
        # Precompile regex word patterns for fast lookup
        self._patterns: Dict[str, List[re.Pattern]] = {}
        for cat_slug, keywords in CATEGORY_KEYWORDS.items():
            self._patterns[cat_slug] = [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in keywords]

    def classify(self, text: str, max_categories: int = 3) -> List[Tuple[str, float]]:
        """Classify given text into STEM category slugs with confidence scores.
        Returns a list of (category_slug, score) tuples sorted by score descending.
        """
        if not text:
            return [("computer-science", 0.5)]

        scores: Dict[str, float] = {}

        for slug, patterns in self._patterns.items():
            match_count = 0
            for pattern in patterns:
                matches = len(pattern.findall(text))
                if matches > 0:
                    match_count += matches

            if match_count > 0:
                # Normalizing score based on keyword hits
                score = min(1.0, 0.4 + (match_count * 0.15))
                scores[slug] = round(score, 2)

        if not scores:
            # Default fallback when general tech
            return [("emerging-tech", 0.5)]

        sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_categories[:max_categories]


# Global classifier instance
classifier = STEMClassifier()
