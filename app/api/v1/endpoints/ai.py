"""AI intelligence endpoints: summarization and conceptual explanation."""

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_ai_service, get_repository, require_api_key
from app.api.exceptions import EntityNotFoundException
from app.api.middleware.rate_limit import ai_rate_limiter
from app.api.v1.schemas.ai import (
    AIExplainRequest,
    AIExplainResponse,
    AISummarizeRequest,
    AISummarizeResponse,
)
from app.database.models import Article
from app.database.repository import Repository
from app.services.ai.service import AIService

router = APIRouter(
    prefix="/ai",
    tags=["AI Intelligence"],
    dependencies=[Depends(require_api_key), Depends(ai_rate_limiter)],
)


@router.post(
    "/summarize",
    response_model=AISummarizeResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate AI News Summary",
    description="Generate a structured executive technical summary for an existing article or arbitrary text payload.",
)
async def summarize_news(
    payload: AISummarizeRequest,
    repo: Repository = Depends(get_repository),
    ai: AIService = Depends(get_ai_service),
) -> AISummarizeResponse:
    """Summarize an article or raw content with structured key facts and applications."""
    if payload.article_id is not None:
        article = await repo.get_article_by_id(payload.article_id)
        if not article:
            raise EntityNotFoundException(message=f"Article with ID {payload.article_id} not found.")
    else:
        # Construct an ephemeral article instance for analysis
        article = Article(
            id=0,
            title=payload.title or "Technology Intelligence Item",
            url=payload.url or "https://stemradar.local",
            description=payload.content,
            source_id=0,
        )

    summary = await ai.summarize_news(article=article, mode=payload.mode)
    return AISummarizeResponse.model_validate(summary)


@router.post(
    "/explain",
    response_model=AIExplainResponse,
    status_code=status.HTTP_200_OK,
    summary="Explain Technical Concept",
    description="Generate a multi-tier conceptual breakdown adapted to beginner, intermediate, or advanced levels.",
)
async def explain_concept(
    payload: AIExplainRequest,
    ai: AIService = Depends(get_ai_service),
) -> AIExplainResponse:
    """Generate structured conceptual explanation for technical algorithms or systems."""
    explanation = await ai.explain_concept(
        concept_name=payload.concept,
        mode=payload.mode,
        context=payload.context,
    )
    return AIExplainResponse.model_validate(explanation)
