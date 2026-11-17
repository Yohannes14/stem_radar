"""Tests for the AI intelligence endpoints: /api/v1/ai/summarize and /api/v1/ai/explain."""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_ai_service
from app.api.main import app
from app.database.repository import Repository
from app.services.ai.interface import BaseAIProvider
from app.services.ai.schemas import ConceptExplanation, NewsSummary
from app.services.ai.service import AIService


@pytest.mark.asyncio
async def test_ai_summarize_existing_article(api_client: AsyncClient, test_session_factory):
    """Test AI news summarization using an existing article ID."""
    async with test_session_factory() as session:
        repo = Repository(session)
        sources = await repo.get_sources()
        src = sources[0]

        article, _ = await repo.save_article(
            title="Breakthrough in Quantum Computing Qubit Coherence",
            url="https://example.com/quantum-qubit",
            source_id=src.id,
            description="Physicists stabilized superconducting qubits at room temperature for 10 milliseconds.",
        )
        article_id = article.id

    payload = {
        "article_id": article_id,
        "mode": "intermediate",
    }
    response = await api_client.post("/api/v1/ai/summarize", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "headline" in data
    assert "short_summary" in data
    assert len(data["key_facts"]) >= 1
    assert "why_it_matters" in data
    assert "potential_applications" in data
    assert data["technical_difficulty"] == "intermediate"


@pytest.mark.asyncio
async def test_ai_summarize_raw_text(api_client: AsyncClient):
    """Test AI news summarization using raw content payload without prior database persistence."""
    payload = {
        "title": "Novel Solid-State Battery Chemistry Unveiled",
        "content": "Engineers published benchmarks showing 800 Wh/kg energy density with ceramic electrolyte.",
        "url": "https://example.com/battery-paper",
        "mode": "beginner",
    }
    response = await api_client.post("/api/v1/ai/summarize", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["headline"] == "Novel Solid-State Battery Chemistry Unveiled"
    assert data["technical_difficulty"] == "beginner"
    assert len(data["key_facts"]) >= 1


@pytest.mark.asyncio
async def test_ai_summarize_validation_and_404(api_client: AsyncClient):
    """Test validation errors and 404 handling in summarize endpoint."""
    # 1. Neither article_id nor title/content provided
    res_bad = await api_client.post("/api/v1/ai/summarize", json={"mode": "intermediate"})
    assert res_bad.status_code == 422
    assert res_bad.json()["error"]["code"] == "VALIDATION_ERROR"

    # 2. Non-existent article_id
    res_404 = await api_client.post("/api/v1/ai/summarize", json={"article_id": 99999})
    assert res_404.status_code == 404
    assert res_404.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_ai_explain_concept_multi_mode(api_client: AsyncClient):
    """Test multi-tier conceptual explanations (beginner, intermediate, advanced)."""
    for mode in ["beginner", "intermediate", "advanced"]:
        payload = {
            "concept": "Transformer Attention Mechanism",
            "mode": mode,
            "context": "natural language processing",
        }
        response = await api_client.post("/api/v1/ai/explain", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["concept_name"] == "Transformer Attention Mechanism"
        assert data["mode"] == mode
        assert "core_definition" in data
        assert "how_it_works" in data
        assert "analogy_or_example" in data
        assert len(data["key_components"]) >= 1


@pytest.mark.asyncio
async def test_ai_explain_validation_error(api_client: AsyncClient):
    """Test concept explanation validation bounds."""
    # Concept too short (< 2 chars)
    res_short = await api_client.post("/api/v1/ai/explain", json={"concept": "A"})
    assert res_short.status_code == 422


@pytest.mark.asyncio
async def test_ai_endpoints_with_mocked_provider(api_client: AsyncClient):
    """Verify endpoint behavior when backed by a mocked LLM provider."""
    mock_provider = AsyncMock(spec=BaseAIProvider)
    mock_summary = NewsSummary(
        headline="Synthetic Biology Breakthrough",
        short_summary="Engineers designed novel metabolic pathways.",
        key_facts=["Fact 1", "Fact 2"],
        why_it_matters="Accelerates enzyme synthesis.",
        potential_applications=["Pharmaceuticals"],
        technical_difficulty="advanced",
        original_source="Nature Biotechnology",
        source_url="https://nature.com/example",
    )
    mock_explanation = ConceptExplanation(
        concept_name="CRISPR-Cas9",
        mode="intermediate",
        core_definition="RNA-guided gene editing endonuclease system.",
        how_it_works="Cas9 forms a complex with guide RNA to cut target DNA.",
        analogy_or_example="Like a molecular word processor with find-and-replace.",
        key_components=["Cas9 protein", "guide RNA", "PAM site"],
        common_misconceptions=["Works with 100% precision without off-targets."],
        prerequisites_or_related=["DNA repair mechanisms"],
    )

    mock_provider.generate_structured.side_effect = [
        (mock_summary, {"prompt_tokens": 100, "completion_tokens": 50, "total_cost_usd": 0.001}),
        (mock_explanation, {"prompt_tokens": 120, "completion_tokens": 80, "total_cost_usd": 0.002}),
    ]

    mock_ai_service = AIService(provider=mock_provider, api_key="sk-test-key", model="gpt-4o-mini")
    app.dependency_overrides[get_ai_service] = lambda: mock_ai_service

    try:
        # 1. Summarize with mocked provider
        res_sum = await api_client.post(
            "/api/v1/ai/summarize",
            json={"title": "Synthetic Biology", "content": "Metabolic engineering details", "mode": "advanced"},
        )
        assert res_sum.status_code == 200
        assert res_sum.json()["headline"] == "Synthetic Biology Breakthrough"

        # 2. Explain with mocked provider
        res_exp = await api_client.post(
            "/api/v1/ai/explain",
            json={"concept": "CRISPR-Cas9", "mode": "intermediate"},
        )
        assert res_exp.status_code == 200
        assert res_exp.json()["concept_name"] == "CRISPR-Cas9"
    finally:
        app.dependency_overrides.pop(get_ai_service, None)
