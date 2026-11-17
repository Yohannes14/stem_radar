"""Pydantic schemas for open educational resources and courses."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.schemas.common import PaginationMeta
from app.database.models import AcademicResource


class AcademicResourceResponse(BaseModel):
    """Normalized response schema for a legal open educational resource."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique resource ID")
    title: str = Field(..., description="Course or resource title")
    slug: str = Field(..., description="URL-safe unique identifier")
    resource_type: str = Field(..., description="Type: free_course, lecture_materials, open_textbook, etc.")
    stem_discipline: str = Field(..., description="Academic STEM field")
    provider_institution: str = Field(..., description="Institution, university, or platform providing the resource")
    official_access_url: str = Field(..., description="Authorized direct access URL")
    license_type: str = Field(..., description="Open licensing type (e.g. Creative Commons, MIT, Public Domain)")
    is_copyright_verified: bool = Field(..., description="Verification of legal distribution status")
    description: Optional[str] = Field(None, description="Curriculum or content overview")
    last_verified_at: datetime = Field(..., description="Date record was last audited")


class PaginatedAcademicResourcesResponse(BaseModel):
    """Paginated collection of academic resources."""

    items: List[AcademicResourceResponse] = Field(..., description="List of matching resource records")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


def build_academic_resource_response(res: AcademicResource) -> AcademicResourceResponse:
    """Helper to convert ORM AcademicResource model into Pydantic schema."""
    return AcademicResourceResponse.model_validate(res)
