"""Tests for the Modular AI Intelligence Engine, adapters, caching, and cost tracking."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.models import Article, Category, Source
from app.services.ai import (
    AIService,
    BaseAIProvider,
    NewsSummary,
    ResearchPaperAnalysis,
    SlideOutline,
    STEMContentPackage,
    TokenUsage,
    VideoScript,
    VocabularyTerm,
    ai_cache,
    cost_tracker,
)


@pytest.fixture(autouse=True)
def clean_ai_state():
    """Reset AI cache and cost tracker between tests."""
    ai_cache.clear()
    cost_tracker.reset()
    yield
    ai_cache.clear()
    cost_tracker.reset()


@pytest.fixture
def sample_article():
    mock_source = MagicMock(spec=Source)
    mock_source.name = "MIT Technology Review"

    mock_category = MagicMock(spec=Category)
    mock_category.name = "Robotics"

    article = MagicMock(spec=Article)
    article.id = 101
    article.title = "High-Torque Actuators Power Next-Gen Humanoids"
    article.description = "Engineers develop planar magnetic actuators reducing heat by 60%."
    article.url = "https://example.com/actuator-breakthrough"
    article.source = mock_source
    article.categories = [mock_category]
    return article


@pytest.mark.asyncio
async def test_ai_service_generates_heuristic_analysis_without_api_key(sample_article):
    service = AIService(api_key=None)
    analysis = await service.analyze_article(sample_article)

    assert analysis.article_title == sample_article.title
    assert analysis.category == "Robotics"
    assert "Actuators" in analysis.short_summary
    assert len(analysis.real_world_applications) >= 1
    assert len(analysis.important_concepts) >= 1
    assert analysis.source_url == sample_article.url


@pytest.mark.asyncio
async def test_ai_news_summarization_with_mocked_provider(sample_article):
    mock_provider = MagicMock(spec=BaseAIProvider)
    expected_summary = NewsSummary(
        headline="Planar Magnetic Actuators Slash Humanoid Joint Heating",
        short_summary="A breakthrough in joint actuators lowers motor heat by 60% for humanoid robots.",
        key_facts=[
            "Developed planar magnetic motor coils.",
            "Demonstrated 60% thermal dissipation improvement in continuous bench tests.",
        ],
        why_it_matters="Solves continuous thermal throttling during bipedal locomotion.",
        potential_applications=["Industrial humanoid robots", "Prosthetic limbs"],
        technical_difficulty="intermediate",
        original_source="MIT Technology Review",
        source_url="https://example.com/actuator-breakthrough",
    )
    mock_usage = TokenUsage(prompt_tokens=400, completion_tokens=150, total_tokens=550, estimated_cost_usd=0.00015)
    mock_provider.generate_structured = AsyncMock(return_value=(expected_summary, mock_usage))

    service = AIService(provider=mock_provider)
    summary = await service.summarize_news(sample_article, mode="intermediate")

    assert summary.headline == expected_summary.headline
    assert len(summary.key_facts) == 2
    assert summary.technical_difficulty == "intermediate"
    assert summary.original_source == "MIT Technology Review"
    mock_provider.generate_structured.assert_called_once()

    # Second call should be served from cache without calling provider again
    cached_summary = await service.summarize_news(sample_article, mode="intermediate")
    assert cached_summary.headline == expected_summary.headline
    assert mock_provider.generate_structured.call_count == 1
    assert ai_cache.hits == 1


@pytest.mark.asyncio
async def test_research_paper_analysis_with_mocked_provider(sample_article):
    mock_provider = MagicMock(spec=BaseAIProvider)
    expected_analysis = ResearchPaperAnalysis(
        paper_title="Planar Magnetic Actuators for High-Payload Humanoid Locomotion",
        research_problem="Thermal dissipation limits torque density in high-payload humanoid joints.",
        methodology="Fabricated carbon-doped planar coils and benchmarked under 200 Nm continuous loads.",
        main_findings=[
            "60% reduction in thermal resistance.",
            "Sustained 2.5x higher torque output before thermal saturation.",
        ],
        limitations=[
            "Coil manufacturing cost currently exceeds traditional radial motors.",
            "Requires custom high-frequency switching inverter drivers.",
        ],
        practical_applications=[
            "Dynamic bipedal sprint control",
            "Heavy-lift quadruped industrial robotics",
        ],
        further_research_questions=[
            "Can automated winding techniques reduce unit fabrication cost?",
            "What is the mean-time-between-failures under high shock impact?",
        ],
        original_paper_url="https://example.com/actuator-breakthrough",
    )
    mock_usage = TokenUsage(prompt_tokens=500, completion_tokens=250, total_tokens=750, estimated_cost_usd=0.000225)
    mock_provider.generate_structured = AsyncMock(return_value=(expected_analysis, mock_usage))

    service = AIService(provider=mock_provider)
    analysis = await service.analyze_research_paper(sample_article)

    assert analysis.paper_title == expected_analysis.paper_title
    assert "Thermal dissipation" in analysis.research_problem
    assert len(analysis.main_findings) == 2
    assert len(analysis.limitations) == 2
    assert len(analysis.further_research_questions) == 2
    assert analysis.original_paper_url == sample_article.url


@pytest.mark.asyncio
async def test_concept_explanation_multi_mode():
    service = AIService(api_key=None)  # Use deterministic heuristics

    # 1. Beginner mode
    beginner = await service.explain_concept("Direct Drive Actuator", mode="beginner")
    assert beginner.mode == "beginner"
    assert "assembly line" in beginner.analogy_or_example.lower() or "like" in beginner.analogy_or_example.lower()

    # 2. Intermediate mode
    intermediate = await service.explain_concept("Direct Drive Actuator", mode="intermediate")
    assert intermediate.mode == "intermediate"
    assert len(intermediate.key_components) >= 3

    # 3. Advanced mode
    advanced = await service.explain_concept("Direct Drive Actuator", mode="advanced")
    assert advanced.mode == "advanced"
    assert "algorithmic" in advanced.core_definition.lower() or "complexity" in advanced.core_definition.lower()


@pytest.mark.asyncio
async def test_technology_impact_analysis(sample_article):
    service = AIService(api_key=None)
    impact = await service.analyze_impact(sample_article)

    assert impact.technology_name == sample_article.title
    assert len(impact.industry_disruption) >= 2
    assert impact.confidence_score > 0.0
    assert "adoption" in impact.adoption_timeline.lower()


@pytest.mark.asyncio
async def test_stem_content_opportunity_generation(sample_article):
    mock_provider = MagicMock(spec=BaseAIProvider)
    slides = [
        SlideOutline(slide_number=i, title=f"Slide {i} Title", bullet_points=["Point A", "Point B"])
        for i in range(1, 6)
    ]
    expected_package = STEMContentPackage(
        headline="How Planar Actuators Revolutionize Humanoid Joint Torque",
        target_audience="Robotics engineers, hardware developers, and mechanical students.",
        linkedin_post="🤖 The future of humanoids just took a major leap forward...",
        carousel_slides=slides,
        video_script=VideoScript(
            hook="Did you know why today's humanoid robots overheat?",
            body="Here is the breakdown of planar magnetic actuators and why they change everything.",
            call_to_action="Follow STEM RADAR for daily breakthroughs in robotics and hardware engineering!",
        ),
        technical_vocabulary=[
            VocabularyTerm(term="Planar Actuator", definition="A flat coil electromagnetic motor architecture."),
            VocabularyTerm(
                term="Thermal Resistance",
                definition="The measure of a material's opposition to heat flow.",
            ),
        ],
        source_attribution="Originally reported by MIT Technology Review",
    )
    mock_usage = TokenUsage(prompt_tokens=600, completion_tokens=300, total_tokens=900, estimated_cost_usd=0.00027)
    mock_provider.generate_structured = AsyncMock(return_value=(expected_package, mock_usage))

    service = AIService(provider=mock_provider)
    content = await service.generate_stem_content(sample_article)

    assert len(content.carousel_slides) == 5
    assert content.video_script.hook is not None
    assert len(content.technical_vocabulary) == 2
    assert "MIT Technology Review" in content.source_attribution


@pytest.mark.asyncio
async def test_provider_outage_fallback_resilience(sample_article):
    mock_provider = MagicMock(spec=BaseAIProvider)
    # Simulate OpenAI outage / Timeout
    mock_provider.generate_structured = AsyncMock(side_effect=RuntimeError("OpenAI 503 Service Unavailable"))

    service = AIService(provider=mock_provider)

    # Should NOT raise an exception, but gracefully fall back to deterministic heuristic summary
    summary = await service.summarize_news(sample_article, mode="intermediate")
    assert summary is not None
    assert summary.headline == sample_article.title
    assert summary.original_source == "MIT Technology Review"


def test_cost_tracker_calculation():
    # gpt-4o-mini rates: $0.15 / 1M prompt, $0.60 / 1M completion
    # For 100,000 prompt tokens: (100,000 / 1,000,000) * 0.15 = $0.015
    # For 50,000 completion tokens: (50,000 / 1,000,000) * 0.60 = $0.030
    # Total = $0.045
    cost = cost_tracker.record_usage("gpt-4o-mini", prompt_tokens=100_000, completion_tokens=50_000)
    assert abs(cost - 0.045) < 0.0001
    assert cost_tracker.total_requests == 1
    assert cost_tracker.total_prompt_tokens == 100_000
    assert cost_tracker.total_completion_tokens == 50_000
    assert abs(cost_tracker.total_cost_usd - 0.045) < 0.0001
