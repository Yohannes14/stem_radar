"""User bookmarks and STEM interests management REST endpoints."""

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_repository
from app.api.exceptions import EntityNotFoundException
from app.api.v1.schemas.news import build_article_response
from app.api.v1.schemas.user import (
    BookmarkRequest,
    BookmarkResponse,
    UserInterestsRequest,
    UserInterestsResponse,
    UserSavedArticlesResponse,
)
from app.database.repository import Repository

router = APIRouter(prefix="/user", tags=["User Intelligence"])


# ------------------ 1. Bookmarks Endpoints ------------------


@router.get(
    "/bookmarks",
    response_model=UserSavedArticlesResponse,
    status_code=status.HTTP_200_OK,
    summary="List User Bookmarked Articles",
    description="Retrieve articles saved and bookmarked by a user.",
)
async def list_user_bookmarks(
    user_id: int = Query(..., description="User Telegram ID"),
    limit: int = Query(default=20, ge=1, le=100, description="Max bookmarked articles to fetch"),
    repo: Repository = Depends(get_repository),
) -> UserSavedArticlesResponse:
    """Retrieve bookmarked articles for a user."""
    articles = await repo.get_saved_articles(user_id=user_id, limit=limit)
    items = [build_article_response(a) for a in articles]
    return UserSavedArticlesResponse(
        user_id=user_id,
        total_saved=len(items),
        items=items,
    )


@router.post(
    "/bookmarks",
    response_model=BookmarkResponse,
    status_code=status.HTTP_200_OK,
    summary="Save / Bookmark Article",
    description="Add an article to user's saved reading list.",
)
async def bookmark_article(
    payload: BookmarkRequest,
    user_id: int = Query(..., description="User Telegram ID"),
    repo: Repository = Depends(get_repository),
) -> BookmarkResponse:
    """Add an article to user bookmarks."""
    article = await repo.get_article_by_id(payload.article_id)
    if not article:
        raise EntityNotFoundException(message=f"Article with ID {payload.article_id} not found.")

    saved = await repo.save_article_bookmark(user_id=user_id, article_id=payload.article_id)
    msg = "Article successfully bookmarked." if saved else "Article was already in bookmarks."
    return BookmarkResponse(
        article_id=payload.article_id,
        user_id=user_id,
        saved=True,
        message=msg,
    )


@router.delete(
    "/bookmarks/{article_id}",
    response_model=BookmarkResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove Bookmarked Article",
    description="Remove an article from user's saved list.",
)
async def unbookmark_article(
    article_id: int,
    user_id: int = Query(..., description="User Telegram ID"),
    repo: Repository = Depends(get_repository),
) -> BookmarkResponse:
    """Remove an article from bookmarks."""
    removed = await repo.remove_saved_article(user_id=user_id, article_id=article_id)
    if not removed:
        raise EntityNotFoundException(message=f"Bookmark for article ID {article_id} not found.")

    return BookmarkResponse(
        article_id=article_id,
        user_id=user_id,
        saved=False,
        message="Bookmark removed successfully.",
    )


# ------------------ 2. Interests / Preferred Categories ------------------


@router.get(
    "/interests",
    response_model=UserInterestsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User STEM Subscriptions",
    description="Retrieve user's active STEM category subscriptions.",
)
async def get_user_interests(
    user_id: int = Query(..., description="User Telegram ID"),
    repo: Repository = Depends(get_repository),
) -> UserInterestsResponse:
    """Retrieve subscribed categories for personalization."""
    categories = await repo.get_user_preferred_categories(user_id)
    return UserInterestsResponse(
        user_id=user_id,
        preferred_categories=categories,
        message="Subscribed categories fetched successfully.",
    )


@router.put(
    "/interests",
    response_model=UserInterestsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update User STEM Subscriptions",
    description="Update user's subscribed STEM categories.",
)
async def update_user_interests(
    payload: UserInterestsRequest,
    user_id: int = Query(..., description="User Telegram ID"),
    repo: Repository = Depends(get_repository),
) -> UserInterestsResponse:
    """Update user subscribed categories."""
    updated = await repo.update_user_preferred_categories(user_id, payload.categories)
    return UserInterestsResponse(
        user_id=user_id,
        preferred_categories=updated,
        message="Subscribed categories updated successfully.",
    )
