"""API endpoints for unified multi-domain search across STEM intelligence and academic resources."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_repository
from app.api.middleware.rate_limit import search_rate_limiter
from app.api.v1.schemas.common import PaginationMeta
from app.api.v1.schemas.search import (
    SearchHistoryItemResponse,
    SearchHistoryListResponse,
    SearchResultItemResponse,
    UnifiedSearchResponseSchema,
)
from app.database.repository import Repository
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
