"""API endpoints for accredited universities and admission guidelines."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_repository
from app.api.exceptions import EntityNotFoundException
from app.api.v1.schemas.common import PaginationMeta
from app.api.v1.schemas.universities import (
    PaginatedUniversitiesResponse,
    UniversityProfileResponse,
    build_university_response,
)
from app.database.repository import Repository

router = APIRouter(prefix="/universities", tags=["University Admissions & Guidelines"])


@router.get(
    "",
    response_model=PaginatedUniversitiesResponse,
    status_code=status.HTTP_200_OK,
    summary="List Accredited Universities",
    description="Retrieve paginated universities with optional country filtering and official admission links.",
)
async def list_universities(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=50, description="Items per page"),
    country: Optional[str] = Query(default=None, description="Host country (e.g. United States, United Kingdom)"),
    repo: Repository = Depends(get_repository),
) -> PaginatedUniversitiesResponse:
    """Query accredited universities with admission portal links."""
    offset = (page - 1) * page_size
    total_items = await repo.count_university_profiles(country=country)
    unis = await repo.get_university_profiles(country=country, limit=page_size, offset=offset)

    total_pages = max(1, math.ceil(total_items / page_size))
    return PaginatedUniversitiesResponse(
        items=[build_university_response(u) for u in unis],
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
    "/{slug}",
    response_model=UniversityProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get University Profile by Slug",
    description="Retrieve full university admission requirements, application procedures, tuition, and guidelines.",
)
async def get_university_by_slug(
    slug: str,
    repo: Repository = Depends(get_repository),
) -> UniversityProfileResponse:
    """Retrieve individual university profile by unique slug."""
    uni = await repo.get_university_by_slug(slug)
    if not uni:
        raise EntityNotFoundException(message=f"University with slug '{slug}' not found.")
    return build_university_response(uni)
