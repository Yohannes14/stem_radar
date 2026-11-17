"""Pydantic schemas for university profiles and admission guidelines."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.schemas.common import PaginationMeta
from app.database.models import UniversityProfile


class UniversityProfileResponse(BaseModel):
    """Normalized response schema for an accredited university profile."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique university record ID")
    name: str = Field(..., description="Official university name")
    slug: str = Field(..., description="URL-safe unique identifier")
    country: str = Field(..., description="Host country")
    city: Optional[str] = Field(None, description="City or primary campus location")
    official_portal_url: str = Field(..., description="Official university main portal")
    admissions_portal_url: str = Field(..., description="Official online admissions portal")
    admission_requirements: Optional[str] = Field(None, description="Entry requirements and academic benchmarks")
    application_procedures: Optional[str] = Field(None, description="Application timeline and submission steps")
    tuition_and_funding: Optional[str] = Field(None, description="Tuition fees and university funding options")
    international_guidelines_url: Optional[str] = Field(None, description="International student office URL")
    academic_regulations_url: Optional[str] = Field(None, description="Academic catalog and regulations URL")
    research_opportunities_url: Optional[str] = Field(None, description="Research institutes and lab portal URL")
    last_verified_at: datetime = Field(..., description="Date profile was last audited")


class PaginatedUniversitiesResponse(BaseModel):
    """Paginated collection of university profiles."""

    items: List[UniversityProfileResponse] = Field(..., description="List of matching university records")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


def build_university_response(uni: UniversityProfile) -> UniversityProfileResponse:
    """Helper to convert ORM UniversityProfile model into Pydantic schema."""
    return UniversityProfileResponse.model_validate(uni)
