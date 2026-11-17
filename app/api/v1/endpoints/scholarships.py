"""API endpoints for Student Hub scholarship discovery and deadline tracking."""

import math
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_repository
from app.api.exceptions import BadRequestException, EntityNotFoundException
from app.api.v1.schemas.common import PaginationMeta
from app.api.v1.schemas.scholarships import (
    OpportunityReportRequest,
    OpportunityReportResponse,
    OpportunityResponse,
    OpportunitySubmissionRequest,
    OpportunitySubmissionResponse,
    PaginatedScholarshipsResponse,
    build_opportunity_response,
)
from app.database.repository import Repository
from app.services.student_hub_service import student_hub_service

router = APIRouter(prefix="/scholarships", tags=["Student Hub & Scholarships"])


@router.get(
    "",
    response_model=PaginatedScholarshipsResponse,
    status_code=status.HTTP_200_OK,
    summary="List Verified Scholarships",
    description="Retrieve paginated scholarships with degree level, funding, country, and discipline filters.",
)
async def list_scholarships(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=50, description="Items per page"),
    level: Optional[str] = Query(default=None, description="Degree level: undergraduate, masters, phd, postdoctoral"),
    funding: Optional[str] = Query(default=None, description="Funding type: fully_funded, partially_funded"),
    country: Optional[str] = Query(default=None, description="Host country (e.g. Germany, Ethiopia, United States)"),
    stem_field: Optional[str] = Query(default=None, description="Keyword in eligible disciplines"),
    active_only: bool = Query(default=True, description="Filter for open opportunities before application deadline"),
    repo: Repository = Depends(get_repository),
) -> PaginatedScholarshipsResponse:
    """Query verified scholarships with multi-faceted filtering."""
    offset = (page - 1) * page_size
    total_items = await repo.count_opportunities(
        opportunity_type="scholarship",
        study_level=level,
        funding_type=funding,
        country=country,
        stem_field=stem_field,
        active_only=active_only,
    )

    opps = await repo.get_opportunities(
        opportunity_type="scholarship",
        study_level=level,
        funding_type=funding,
        country=country,
        stem_field=stem_field,
        active_only=active_only,
        limit=page_size,
        offset=offset,
    )

    total_pages = max(1, math.ceil(total_items / page_size))
    return PaginatedScholarshipsResponse(
        items=[build_opportunity_response(o) for o in opps],
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


@router.get(
    "/deadlines/upcoming",
    response_model=List[OpportunityResponse],
    status_code=status.HTTP_200_OK,
    summary="List Upcoming Application Deadlines",
    description="Retrieve upcoming application cut-off dates ordered chronologically.",
)
async def get_upcoming_deadlines(
    limit: int = Query(default=10, ge=1, le=50, description="Number of upcoming deadlines to return"),
) -> List[OpportunityResponse]:
    """Retrieve chronological timeline of upcoming deadlines."""
    deadlines = await student_hub_service.get_upcoming_deadlines(limit=limit)
    return [build_opportunity_response(o) for o in deadlines]


@router.get(
    "/{slug}",
    response_model=OpportunityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Scholarship Details by Slug",
    description="Retrieve complete scholarship details, trust tier, eligibility criteria, and official URLs.",
)
async def get_scholarship_by_slug(
    slug: str,
    repo: Repository = Depends(get_repository),
) -> OpportunityResponse:
    """Retrieve individual scholarship record by unique slug."""
    opp = await repo.get_opportunity_by_slug(slug)
    if not opp:
        raise EntityNotFoundException(message=f"Opportunity with slug '{slug}' not found.")
    return build_opportunity_response(opp)


# ------------------ Stage 16: Public Submissions & Issue Reporting ------------------


@router.post(
    "/submit",
    response_model=OpportunitySubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Academic Opportunity for Review",
    description="Submit a scholarship, fellowship, or research grant for administrative moderation.",
)
async def submit_opportunity(
    payload: OpportunitySubmissionRequest,
    repo: Repository = Depends(get_repository),
) -> OpportunitySubmissionResponse:
    """Submit a new opportunity record. Saved with pending_approval status until reviewed."""
    success, opp, message = await student_hub_service.submit_public_opportunity(
        user_id=payload.user_id or 0,
        title=payload.title,
        provider_name=payload.provider_name,
        official_url=payload.official_url,
        country=payload.country,
        study_level=payload.study_level,
        opportunity_type=payload.opportunity_type,
        stem_fields=payload.stem_fields,
        funding_type=payload.funding_type,
        application_url=payload.application_url,
        eligibility_criteria=payload.eligibility_criteria or "",
        application_deadline=payload.application_deadline,
        is_rolling=payload.is_rolling,
        benefits=payload.benefits,
        required_documents=payload.required_documents,
        repo=repo,
    )
    if not success or not opp:
        raise BadRequestException(message=message)

    return OpportunitySubmissionResponse(
        id=opp.id,
        title=opp.title,
        status=opp.status,
        verification_tier=opp.verification_tier,
        message=message,
    )


@router.post(
    "/{opportunity_id}/report",
    response_model=OpportunityReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report Opportunity Issue",
    description="Report an expired deadline, broken official link, inaccurate requirement, or fraudulent listing.",
)
async def report_opportunity(
    opportunity_id: int,
    payload: OpportunityReportRequest,
    repo: Repository = Depends(get_repository),
) -> OpportunityReportResponse:
    """Submit a community issue report regarding an opportunity."""
    opp = await repo.get_opportunity_by_id(opportunity_id)
    if not opp:
        raise EntityNotFoundException(message=f"Opportunity with ID {opportunity_id} not found.")

    report = await repo.submit_opportunity_report(
        user_id=payload.user_id or 0,
        opportunity_id=opportunity_id,
        report_type=payload.report_type,
        details=payload.details,
    )
    return OpportunityReportResponse(
        id=report.id,
        opportunity_id=report.opportunity_id,
        report_type=report.report_type,
        status=report.status,
        message="Issue report received. Our moderation team will audit the provider source.",
    )
