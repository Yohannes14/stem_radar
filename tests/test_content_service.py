"""Tests for STEM Content Opportunity Finder service."""

from unittest.mock import MagicMock

from app.database.models import Article, Category, Source
from app.services.content_service import ContentService


def test_content_service_generates_full_package():
    service = ContentService()

    mock_source = MagicMock(spec=Source)
    mock_source.name = "MIT Technology Review"
    mock_source.source_type = "rss"

    mock_category = MagicMock(spec=Category)
    mock_category.name = "Robotics"

    mock_article = MagicMock(spec=Article)
    mock_article.title = "Next-Gen Humanoid Actuator Architecture"
    mock_article.url = "https://example.com/robotics-breakthrough"
    mock_article.description = "A new electric actuator enables high-torque dynamic walking in bipedal robots."
    mock_article.source = mock_source
    mock_article.categories = [mock_category]

    opportunity = service.generate_opportunity(mock_article)

    assert opportunity.article_title == mock_article.title
    assert "Actuator" in opportunity.article_title
    assert len(opportunity.carousel_slides) == 5
    assert len(opportunity.vocabulary) > 0
    assert "LinkedIn" in opportunity.linkedin_post or "#STEM" in opportunity.linkedin_post
    assert "[Hook" in opportunity.video_script
    assert opportunity.difficulty_level in ("Intermediate", "Advanced")
