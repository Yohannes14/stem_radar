"""Pydantic request and response schemas for User Bookmarks and Preferences API."""

from typing import List

from pydantic import BaseModel, Field

from app.api.v1.schemas.news import ArticleResponse


class BookmarkRequest(BaseModel):
    """Payload to bookmark an article."""

    article_id: int = Field(..., description="ID of the article to bookmark")


class BookmarkResponse(BaseModel):
    """Result of a bookmark operation."""

    article_id: int = Field(..., description="Target article ID")
    user_id: int = Field(..., description="User Telegram ID")
    saved: bool = Field(..., description="True if article is saved, False if removed/unbookmarked")
    message: str = Field(..., description="Status summary message")


class UserInterestsRequest(BaseModel):
    """Payload to update subscribed STEM categories."""

    categories: List[str] = Field(
        ...,
        description="List of category slugs to subscribe to (e.g. ['ai', 'robotics'])",
    )


class UserInterestsResponse(BaseModel):
    """User preferred STEM categories payload."""

    user_id: int = Field(..., description="User Telegram ID")
    preferred_categories: List[str] = Field(..., description="Active subscribed domain slugs")
    message: str = Field(..., description="Status summary message")


class UserSavedArticlesResponse(BaseModel):
    """User bookmarked articles payload."""

    user_id: int = Field(..., description="User Telegram ID")
    total_saved: int = Field(..., description="Total articles bookmarked by user")
    items: List[ArticleResponse] = Field(..., description="Bookmarked article details")
