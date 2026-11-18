"""STEM Content Opportunity Finder transforming tech news into educational content."""

import logging
from dataclasses import dataclass
from typing import List

from app.database.models import Article

logger = logging.getLogger(__name__)


@dataclass
class ContentOpportunity:
    """Structured educational content package derived from a technology development."""

    article_title: str
    source_name: str
    url: str
    news_discovery: str
    technical_explanation: str
    educational_value: str
    difficulty_level: str
    vocabulary: List[str]
    linkedin_post: str
    carousel_slides: List[str]
    video_script: str


class ContentService:
    """Transforms technology intelligence into high-value STEM educational content opportunities."""

    def generate_opportunity(self, article: Article) -> ContentOpportunity:
        """Transform an article record into an 8-part STEM educational content opportunity."""
        title = article.title
        source = article.source.name if article.source else "Technology Source"
        desc = article.description or "Recent technological breakthrough."
        url = article.url

        # Determine difficulty level based on vocabulary and source type
        is_paper = "[Paper]" in title or (article.source and article.source.source_type == "arxiv")
        difficulty = "Advanced" if is_paper else "Intermediate"

        # Extract technical vocabulary
        categories = [c.name for c in article.categories] if article.categories else ["Science & Technology"]
        vocab_pool = ["Architecture", "System Optimization", "Scalability", "Algorithmic Efficiency"]
        if categories:
            vocab_pool = [categories[0], "Latency", "Throughput", "Empirical Evaluation"]

        # News discovery
        news_discovery = f"{title}. Reported by {source}."

        # Technical explanation
        technical_explanation = (
            f"The core technical mechanism focuses on: {desc[:200]}... "
            f"This addresses fundamental bottlenecks in {categories[0] if categories else 'engineering'}."
        )

        # Educational value
        educational_value = (
            "Demonstrates real-world engineering problem solving, trade-offs between "
            "computational complexity and practical performance, and modern implementation standards."
        )

        # LinkedIn Post
        linkedin_post = (
            f"Update in {categories[0] if categories else 'STEM'}:\n\n"
            f"{title}\n\n"
            f"Summary:\n{desc[:180]}...\n\n"
            f"Why it matters:\n"
            f"- Advances practical engineering and applied research\n"
            f"- Highlights ongoing improvements in system efficiency\n\n"
            f"Source: {url}\n\n"
            f"#STEM #Technology #Engineering #{categories[0].replace(' ', '') if categories else 'Innovation'}"
        )

        # Carousel Outline (5 Slides)
        carousel_slides = [
            f"Slide 1: {title} (The Breakdown)",
            f"Slide 2: The Problem (What was holding {categories[0] if categories else 'tech'} back?)",
            f"Slide 3: How the Solution Works ({desc[:100]}...)",
            "Slide 4: Key Takeaway for Developers & Engineers",
            f"Slide 5: Summary & Where to Learn More (Read: {url})",
        ]

        # Short Video Script (TikTok/Reels/Shorts format)
        video_script = (
            f"[Hook - 0:00-0:03]: Did you see what just happened in {categories[0] if categories else 'tech'}?\n"
            f"[Body - 0:04-0:20]: {title}. Here is why this is important: {desc[:120]}...\n"
            f"[Call to Action - 0:21-0:30]: Check out the full source link and follow STEM RADAR for more updates!"
        )

        return ContentOpportunity(
            article_title=title,
            source_name=source,
            url=url,
            news_discovery=news_discovery,
            technical_explanation=technical_explanation,
            educational_value=educational_value,
            difficulty_level=difficulty,
            vocabulary=vocab_pool,
            linkedin_post=linkedin_post,
            carousel_slides=carousel_slides,
            video_script=video_script,
        )


content_service = ContentService()
