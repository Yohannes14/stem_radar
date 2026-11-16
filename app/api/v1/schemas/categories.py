"""Pydantic schemas for STEM categories registry."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryDetailResponse(BaseModel):
    """Detailed category metadata."""

    id: int = Field(..., description="Category unique ID")
    name: str = Field(..., description="Display name of category")
    slug: str = Field(..., description="Unique URL and filter slug")
    description: Optional[str] = Field(default=None, description="Scope and sub-disciplines description")

    model_config = ConfigDict(from_attributes=True)


class CategoryListResponse(BaseModel):
    """List of all registered STEM domains."""

    items: List[CategoryDetailResponse] = Field(..., description="Array of STEM domains")
    total: int = Field(..., description="Total count of categories")
