"""Scientific research and academic paper intelligence endpoints."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_repository
from app.api.v1.schemas.common import PaginationMeta
from app.api.v1.schemas.news import CategorySummary
from app.api.v1.schemas.research import PaginatedResearchResponse, ResearchPaperResponse
from app.database.repository import Repository

router = APIRouter(prefix="/research", tags=["Intelligence"])


@router.get(
    "",
    response_model=PaginatedResearchResponse,
    status_code=status.HTTP_200_OK,
    summary="List Scientific Research Papers",
    description="Query arXiv research papers across STEM domains with abstracts and category tags.",
)
async def list_research_papers(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=50, description="Items per page (max 50)"),
    category: Optional[str] = Query(default=None, description="STEM domain slug filter (e.g. 'ai', 'robotics')"),
    q: Optional[str] = Query(
        default=None, min_length=2, max_length=100, description="Search keyword in title/abstract"
    ),
    repo: Repository = Depends(get_repository),
) -> PaginatedResearchResponse:
    """Fetch paginated scientific papers from arXiv and academic sources."""
    offset = (page - 1) * page_size
    total_items = await repo.count_articles(
        category_slug=category,
        source_type="arxiv",
        query=q,
    )

    articles = await repo.get_recent_articles(
        limit=page_size,
        offset=offset,
        category_slug=category,
        source_type="arxiv",
        query=q,
    )

    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0

    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )

    items = [
        ResearchPaperResponse(
            id=a.id,
            title=a.title,
            url=a.url,
            abstract=a.description or a.content,
            published_at=a.published_at,
            collected_at=a.collected_at,
            source_name=a.source.name if a.source else "arXiv",
            categories=[CategorySummary.model_validate(c) for c in a.categories],
            ai_analysis=a.ai_analysis,
        )
        for a in articles
    ]

    return PaginatedResearchResponse(items=items, pagination=pagination)
