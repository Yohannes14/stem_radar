"""Unit tests for SearchAIAssistant, source synthesis, source comparison, and formatting."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.search.ai_assistant import SearchAIAssistant, search_ai_assistant
from app.services.search.models import (
    SearchAISummary,
    SearchResultItem,
    SourceCitation,
    SourceComparison,
)


@pytest.fixture
def sample_search_items():
    now = datetime.now(timezone.utc)
    return [
        SearchResultItem(
            id="paper:1",
            title="Scalable Surface Codes for Fault-Tolerant Quantum Computing",
            snippet="Demonstrating physical threshold error rates below 1% using superconducting qubits.",
            source_name="Physical Review X",
            published_at=now,
            category="Research Papers",
            is_verified=True,
            url="https://journals.aps.org/prx/quantum-surface-codes",
            score=9.5,
            item_type="paper",
        ),
        SearchResultItem(
            id="news:2",
            title="Global Quantum Hardware Consortium Announces 1000-Qubit Processor",
            snippet="Industry alliance achieves 1000 physical qubit benchmark with neutral atoms.",
            source_name="Quantum Computing Report",
            published_at=now,
            category="STEM News",
            is_verified=False,
            url="https://quantumreport.example.com/1000-qubit-processor",
            score=8.2,
            item_type="news",
        ),
    ]


@pytest.mark.asyncio
async def test_summarize_search_results_with_llm_provider(sample_search_items):
    """Verify structured LLM prompt construction, source citation extraction, and result parsing."""
    mock_provider = AsyncMock()
    mock_summary = SearchAISummary(
        query="quantum processors",
        executive_summary="Recent breakthroughs demonstrate viable pathways to physical error suppression and scaling.",
        sourced_facts=[
            "Physical threshold error rates dropped below 1% on superconducting architectures [1].",
            "1000 physical qubit milestone achieved using neutral-atom arrays [2].",
        ],
        analytical_implications=[
            "Fault tolerance transitions from theoretical physics to modular systems engineering.",
        ],
        source_citations=[],
        related_questions=[
            "What is the physical coherence time of neutral-atom qubits?",
            "How do surface codes compare to topological codes?",
        ],
        research_recommendations=[
            "Investigate error mitigation overhead in multi-qubit cross-talk regimes.",
        ],
        disclaimer="AI synthesis derived strictly from cited search results.",
    )
    mock_provider.generate_structured = AsyncMock(return_value=(mock_summary, None))

    mock_ai_engine = MagicMock()
    mock_ai_engine.provider = mock_provider

    assistant = SearchAIAssistant(ai_engine=mock_ai_engine)
    res = await assistant.summarize_search_results(query="quantum processors", items=sample_search_items)

    mock_provider.generate_structured.assert_called_once()
    assert res.query == "quantum processors"
    assert len(res.source_citations) == 2
    assert res.source_citations[0].index == 1
    assert res.source_citations[0].title == "Scalable Surface Codes for Fault-Tolerant Quantum Computing"
    assert res.source_citations[1].index == 2
    assert "[1]" in res.sourced_facts[0]
    assert "[2]" in res.sourced_facts[1]


@pytest.mark.asyncio
async def test_summarize_search_results_heuristic_fallback(sample_search_items):
    """Verify deterministic fallback synthesis when LLM provider is offline or throws error."""
    mock_ai_engine = MagicMock()
    mock_ai_engine.provider = None  # No LLM configured

    assistant = SearchAIAssistant(ai_engine=mock_ai_engine)
    res = await assistant.summarize_search_results(query="quantum error correction", items=sample_search_items)

    assert res.query == "quantum error correction"
    assert "Physical Review X" in res.executive_summary
    assert len(res.sourced_facts) == 2
    assert "[1]" in res.sourced_facts[0]
    assert "[2]" in res.sourced_facts[1]
    assert len(res.source_citations) == 2
    assert res.source_citations[0].url == "https://journals.aps.org/prx/quantum-surface-codes"
    assert len(res.related_questions) >= 2
    assert len(res.research_recommendations) >= 1
    assert "AI synthesis derived strictly from cited search results" in res.disclaimer


@pytest.mark.asyncio
async def test_summarize_search_results_empty_items():
    """Verify clean response when no search items match the query."""
    assistant = SearchAIAssistant(ai_engine=MagicMock(provider=None))
    res = await assistant.summarize_search_results(query="nonexistent_xyz_query", items=[])

    assert "No matching documents" in res.executive_summary
    assert res.sourced_facts == []
    assert res.source_citations == []
    assert len(res.related_questions) >= 1


@pytest.mark.asyncio
async def test_compare_sources_with_llm_provider(sample_search_items):
    """Verify source comparison utilizing LLM structured evaluation."""
    item_a, item_b = sample_search_items[0], sample_search_items[1]

    mock_provider = AsyncMock()
    mock_comparison = SourceComparison(
        topic="Superconducting vs Neutral Atom Quantum Computing",
        source_a=SourceCitation(
            index=1,
            title=item_a.title,
            url=item_a.url,
            source_name=item_a.source_name,
            is_verified=True,
        ),
        source_b=SourceCitation(
            index=2,
            title=item_b.title,
            url=item_b.url,
            source_name=item_b.source_name,
            is_verified=False,
        ),
        common_ground=[
            "Both initiatives aim to overcome physical error limits to achieve scalable quantum utility.",
        ],
        divergent_points=[
            "Source A evaluates cryogenic superconducting surface codes, whereas Source B focuses on neutral atoms.",
        ],
        synthesis=(
            "Neutral atoms demonstrate faster scaling to 1000 qubits, while "
            "surface codes offer deeper fault-tolerance proof."
        ),
        recommended_context=(
            "Use Source A for mathematical error correction and Source B for hardware scale benchmarks."
        ),
    )
    mock_provider.generate_structured = AsyncMock(return_value=(mock_comparison, None))

    assistant = SearchAIAssistant(ai_engine=MagicMock(provider=mock_provider))
    cmp = await assistant.compare_sources(item_a, item_b, topic="Hardware Modalities")

    mock_provider.generate_structured.assert_called_once()
    assert cmp.topic == "Hardware Modalities"
    assert len(cmp.common_ground) >= 1
    assert len(cmp.divergent_points) >= 1
    assert "Neutral atoms" in cmp.synthesis


@pytest.mark.asyncio
async def test_compare_sources_heuristic_fallback(sample_search_items):
    """Verify deterministic source comparison fallback when LLM is unavailable."""
    assistant = SearchAIAssistant(ai_engine=MagicMock(provider=None))
    cmp = await assistant.compare_sources(sample_search_items[0], sample_search_items[1])

    assert cmp.source_a.title == sample_search_items[0].title
    assert cmp.source_b.title == sample_search_items[1].title
    assert len(cmp.common_ground) >= 1
    assert len(cmp.divergent_points) >= 1
    assert "Source A" in cmp.recommended_context
    assert "Source B" in cmp.recommended_context


def test_markdown_formatting_and_keyboards(sample_search_items):
    """Verify Telegram Markdown presentation and interactive keyboard generation."""
    summary = SearchAISummary(
        query="robotics vision",
        executive_summary="Computer vision advances allow sub-millimeter robotic dexterity.",
        sourced_facts=["Stereo vision improves spatial localization [1]."],
        analytical_implications=["Edge compute models minimize control latency."],
        source_citations=[
            SourceCitation(
                index=1,
                title="Stereo Depth Estimation for Quadruped Robots",
                url="https://example.com/quadruped-vision",
                source_name="IEEE Robotics & Automation",
                is_verified=True,
            )
        ],
        related_questions=["How does LiDAR compare with stereo vision?", "What is the compute requirement?"],
        research_recommendations=["Evaluate edge TPUs for real-time localization."],
        disclaimer="AI synthesis based on verified citations.",
    )

    text = search_ai_assistant.format_search_ai_summary(summary)
    assert 'Search Summary — "robotics vision"' in text
    assert "Stereo vision improves spatial localization [1]" in text
    assert "[1] [Stereo Depth Estimation" in text
    assert "IEEE Robotics & Automation" in text

    keyboard = search_ai_assistant.get_search_ai_summary_keyboard(summary, category="all", source="all")
    buttons = keyboard.inline_keyboard
    # Has related question buttons
    assert any(any(b.callback_data.startswith("search:rel_q:") for b in row) for row in buttons)
    # Has back button
    assert any(any(b.text == "Back to Results" for b in row) for row in buttons)
