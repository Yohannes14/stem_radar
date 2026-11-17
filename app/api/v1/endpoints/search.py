"""API endpoints for unified multi-domain search across STEM intelligence and academic resources."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_repository
from app.api.middleware.rate_limit import search_rate_limiter
from app.api.v1.schemas.ai import AIExplainResponse
from app.api.v1.schemas.common import PaginationMeta
from app.api.v1.schemas.search import (
    SearchAISummarySchema,
    SearchHistoryItemResponse,
    SearchHistoryListResponse,
    SearchResultItemResponse,
    SourceCitationSchema,
    SourceComparisonRequest,
    SourceComparisonSchema,
    UnifiedSearchResponseSchema,
)
from app.database.repository import Repository
from app.services.search.models import SearchResultItem
from app.services.search.service import search_service

router = APIRouter(prefix="/search", tags=["Unified Search Engine"])


@router.get(
    "",
    response_model=UnifiedSearchResponseSchema,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(search_rate_limiter)],
    summary="Unified Multi-Domain Search",
    description="Search across STEM news, research papers, scholarships, universities, and educational courses.",
)
async def unified_search(
    q: str = Query(..., min_length=2, max_length=100, description="Search keyword query"),
    category: Optional[str] = Query(
        default="all",
        description="Filter by domain category: all, news, research, scholarships, universities, courses",
    ),
    sort_by: str = Query(
        default="relevance",
        pattern="^(relevance|date)$",
        description="Rank results by relevance or date",
    ),
    source: str = Query(
        default="all",
        pattern="^(all|internal|external)$",
        description="Search scope: all (unified), internal (database only), or external (live web discovery)",
    ),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=50, description="Items returned per page"),
    user_id: Optional[int] = Query(default=None, description="Optional user ID for consented search history logging"),
    repo: Repository = Depends(get_repository),
) -> UnifiedSearchResponseSchema:
    """Execute unified search and return normalized results with pagination."""
    response = await search_service.search(
        query=q,
        category=category,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
        user_id=user_id,
        source=source,
        repo=repo,
    )

    items = [
        SearchResultItemResponse(
            id=item.id,
            title=item.title,
            snippet=item.snippet,
            source_name=item.source_name,
            published_at=item.published_at,
            category=item.category,
            is_verified=item.is_verified,
            url=item.url,
            score=item.score,
            item_type=item.item_type,
            original_id=item.original_id,
            slug=item.slug,
            metadata=item.metadata,
        )
        for item in response.items
    ]

    pagination = PaginationMeta(
        page=response.page,
        page_size=response.page_size,
        total_items=response.total_items,
        total_pages=response.total_pages,
        has_next=response.page < response.total_pages,
        has_prev=response.page > 1,
    )

    return UnifiedSearchResponseSchema(
        query=response.query,
        category=response.category,
        sort_by=response.sort_by,
        source=response.source,
        items=items,
        pagination=pagination,
    )


@router.get(
    "/history",
    response_model=SearchHistoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Consented Search History",
    description="Retrieve recent search queries for a specific user.",
)
async def get_search_history(
    user_id: int = Query(..., description="User ID"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum history items to return"),
    repo: Repository = Depends(get_repository),
) -> SearchHistoryListResponse:
    """Fetch user's recent search queries."""
    history = await repo.get_user_search_history(user_id=user_id, limit=limit)
    items = [
        SearchHistoryItemResponse(
            id=h.id,
            query=h.query,
            category=h.category,
            results_count=h.results_count,
            created_at=h.created_at,
        )
        for h in history
    ]
    return SearchHistoryListResponse(items=items, total=len(items))


@router.delete(
    "/history",
    status_code=status.HTTP_200_OK,
    summary="Clear Search History",
    description="Delete all search history records for a specific user.",
)
async def clear_search_history(
    user_id: int = Query(..., description="User ID"),
    repo: Repository = Depends(get_repository),
) -> dict:
    """Clear all search history for user upon request."""
    deleted_count = await repo.clear_user_search_history(user_id=user_id)
    return {"message": f"Successfully deleted {deleted_count} search history records.", "deleted_count": deleted_count}


# ------------------ Stage 15: AI Search Assistant Endpoints ------------------


@router.get(
    "/assistant/summary",
    response_model=SearchAISummarySchema,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(search_rate_limiter)],
    summary="AI Search Intelligence Synthesis",
    description="Synthesize an accurate executive overview with explicit numerical source citations [1], [2].",
)
async def ai_search_summary(
    q: str = Query(..., min_length=2, max_length=100, description="Search query topic to synthesize"),
    category: Optional[str] = Query(default="all", description="Category scope filter"),
    source: str = Query(
        default="all",
        pattern="^(all|internal|external)$",
        description="Search scope: all, internal, or external",
    ),
    limit: int = Query(default=5, ge=1, le=10, description="Number of top search results to synthesize"),
    repo: Repository = Depends(get_repository),
) -> SearchAISummarySchema:
    """Execute search query and synthesize grounded multi-source AI summary with citations."""
    summary = await search_service.ai_summarize_query(
        query=q,
        category=category,
        source=source,
        limit=limit,
        repo=repo,
    )
    citations = [
        SourceCitationSchema(
            index=c.index,
            title=c.title,
            url=c.url,
            source_name=c.source_name,
            published_at=c.published_at,
            category=c.category,
            is_verified=c.is_verified,
        )
        for c in summary.source_citations
    ]
    return SearchAISummarySchema(
        query=summary.query,
        executive_summary=summary.executive_summary,
        sourced_facts=summary.sourced_facts,
        analytical_implications=summary.analytical_implications,
        source_citations=citations,
        related_questions=summary.related_questions,
        research_recommendations=summary.research_recommendations,
        disclaimer=summary.disclaimer,
    )


@router.post(
    "/assistant/compare",
    response_model=SourceComparisonSchema,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(search_rate_limiter)],
    summary="AI Source Comparison",
    description="Compare two search findings to evaluate points of consensus, divergence, and recommended usage.",
)
async def ai_source_comparison(
    payload: SourceComparisonRequest,
) -> SourceComparisonSchema:
    """Evaluate two sources comparatively for mutual alignment, methodology divergence, and synthesis."""
    item_a = SearchResultItem(
        id=payload.item_a.id,
        title=payload.item_a.title,
        snippet=payload.item_a.snippet,
        source_name=payload.item_a.source_name,
        published_at=payload.item_a.published_at,
        category=payload.item_a.category,
        is_verified=payload.item_a.is_verified,
        url=payload.item_a.url,
        score=payload.item_a.score,
        item_type=payload.item_a.item_type,
        original_id=payload.item_a.original_id,
        slug=payload.item_a.slug,
        metadata=payload.item_a.metadata,
    )
    item_b = SearchResultItem(
        id=payload.item_b.id,
        title=payload.item_b.title,
        snippet=payload.item_b.snippet,
        source_name=payload.item_b.source_name,
        published_at=payload.item_b.published_at,
        category=payload.item_b.category,
        is_verified=payload.item_b.is_verified,
        url=payload.item_b.url,
        score=payload.item_b.score,
        item_type=payload.item_b.item_type,
        original_id=payload.item_b.original_id,
        slug=payload.item_b.slug,
        metadata=payload.item_b.metadata,
    )

    cmp = await search_service.compare_search_items(item_a, item_b, topic=payload.topic)
    return SourceComparisonSchema(
        topic=cmp.topic,
        source_a=SourceCitationSchema(
            index=cmp.source_a.index,
            title=cmp.source_a.title,
            url=cmp.source_a.url,
            source_name=cmp.source_a.source_name,
            published_at=cmp.source_a.published_at,
            category=cmp.source_a.category,
            is_verified=cmp.source_a.is_verified,
        ),
        source_b=SourceCitationSchema(
            index=cmp.source_b.index,
            title=cmp.source_b.title,
            url=cmp.source_b.url,
            source_name=cmp.source_b.source_name,
            published_at=cmp.source_b.published_at,
            category=cmp.source_b.category,
            is_verified=cmp.source_b.is_verified,
        ),
        common_ground=cmp.common_ground,
        divergent_points=cmp.divergent_points,
        synthesis=cmp.synthesis,
        recommended_context=cmp.recommended_context,
    )


@router.get(
    "/assistant/explain",
    response_model=AIExplainResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(search_rate_limiter)],
    summary="AI Search Topic Explanation",
    description="Explain a STEM concept or search topic tailored to beginner, intermediate, or advanced depth.",
)
async def ai_search_explain(
    topic: str = Query(..., min_length=2, max_length=150, description="Technical concept or topic"),
    mode: str = Query(
        default="intermediate",
        pattern="^(beginner|intermediate|advanced)$",
        description="Depth level: beginner, intermediate, advanced",
    ),
) -> AIExplainResponse:
    """Generate structured multi-tier concept explanation."""
    explanation = await search_service.ai_assistant.ai.explain_concept(concept_name=topic, mode=mode)
    return AIExplainResponse(
        concept_name=explanation.concept_name,
        mode=explanation.mode,
        core_definition=explanation.core_definition,
        how_it_works=explanation.how_it_works,
        analogy_or_example=explanation.analogy_or_example,
        key_components=explanation.key_components,
        common_misconceptions=explanation.common_misconceptions,
        prerequisites_or_related=explanation.prerequisites_or_related,
    )
