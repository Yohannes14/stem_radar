"""News and article querying endpoints."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_repository
from app.api.exceptions import EntityNotFoundException
from app.api.v1.schemas.common import PaginationMeta
from app.api.v1.schemas.news import ArticleResponse, PaginatedNewsResponse
from app.database.repository import Repository

router = APIRouter(prefix="/news", tags=["News"])


@router.get(
    "",
    response_model=PaginatedNewsResponse,
    status_code=status.HTTP_200_OK,
    summary="List News & Research Articles",
    description="Retrieve paginated news, articles, and research papers with category, source, and search filters.",
)
async def list_news(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=50, description="Items per page (max 50)"),
    category: Optional[str] = Query(default=None, description="STEM category slug (e.g. 'ai', 'robotics')"),
    source_type: Optional[str] = Query(default=None, description="Source type filter ('rss', 'arxiv', 'github')"),
    q: Optional[str] = Query(
        default=None, min_length=2, max_length=100, description="Keyword search in title & description"
    ),
    repo: Repository = Depends(get_repository),
) -> PaginatedNewsResponse:
    """Fetch paginated articles with optional domain filtering and text search."""
    offset = (page - 1) * page_size
    total_items = await repo.count_articles(
        category_slug=category,
        source_type=source_type,
        query=q,
    )

    articles = await repo.get_recent_articles(
        limit=page_size,
        offset=offset,
        category_slug=category,
        source_type=source_type,
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

    items = [ArticleResponse.model_validate(a) for a in articles]
    return PaginatedNewsResponse(items=items, pagination=pagination)


@router.get(
    "/{article_id}",
    response_model=ArticleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Article Details",
    description="Fetch a single article or research paper by its unique database ID.",
)
async def get_article(
    article_id: int,
    repo: Repository = Depends(get_repository),
) -> ArticleResponse:
    """Retrieve full article details by ID."""
    article = await repo.get_article_by_id(article_id)
    if not article:
        raise EntityNotFoundException(message=f"Article with ID {article_id} not found.")

    return ArticleResponse.model_validate(article)
