"""Pydantic schemas for Student Hub scholarships and opportunities."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.schemas.common import PaginationMeta
from app.database.models import Opportunity


class OpportunityResponse(BaseModel):
    """Normalized response schema for an academic opportunity or scholarship."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique opportunity ID")
    title: str = Field(..., description="Opportunity title")
    slug: str = Field(..., description="URL-safe unique identifier")
    opportunity_type: str = Field(..., description="Type: scholarship, fellowship, internship, grant, competition")
    provider_name: str = Field(..., description="Sponsoring organization or university")
    provider_type: str = Field(..., description="Provider category: university, government, foundation, corporate")
    official_url: str = Field(..., description="Official announcement URL")
    application_url: Optional[str] = Field(None, description="Official online application portal")
    country: str = Field(..., description="Host or provider country")
    eligible_nationalities: str = Field(..., description="Eligibility criteria by nationality")
    study_level: str = Field(..., description="Target degree level (undergraduate, masters, phd, postdoctoral)")
    stem_fields: str = Field(..., description="Eligible STEM subjects and disciplines")
    funding_type: str = Field(..., description="Financial structure (fully_funded, partially_funded, etc.)")
    benefits: Optional[str] = Field(None, description="Financial coverage, stipend, and allowance details")
    eligibility_criteria: str = Field(..., description="Required qualifications, GPA, and language benchmarks")
    required_documents: Optional[str] = Field(None, description="Application submission requirements")
    application_opens_at: Optional[datetime] = Field(None, description="Opening date")
    application_deadline: Optional[datetime] = Field(None, description="Submission deadline")
    is_rolling: bool = Field(False, description="Whether opportunity operates on rolling cut-offs")
    published_at: datetime = Field(..., description="Record publication date")
    last_verified_at: datetime = Field(..., description="Date source was last verified")
    status: str = Field(..., description="Current status: open, upcoming, closed, expired")
    verification_tier: str = Field(..., description="Trust verification level")
    source_attribution: str = Field(..., description="Origin source or accredited organization")


class PaginatedScholarshipsResponse(BaseModel):
    """Paginated collection of scholarships."""

    items: List[OpportunityResponse] = Field(..., description="List of matching scholarship records")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


def build_opportunity_response(opp: Opportunity) -> OpportunityResponse:
    """Helper to convert ORM Opportunity model into Pydantic schema."""
    return OpportunityResponse.model_validate(opp)
