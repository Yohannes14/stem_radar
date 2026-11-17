"""API endpoints for legal academic resources, open courseware, and study materials."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_repository
from app.api.exceptions import EntityNotFoundException
from app.api.v1.schemas.academic_resources import (
    AcademicResourceResponse,
    PaginatedAcademicResourcesResponse,
    build_academic_resource_response,
)
from app.api.v1.schemas.common import PaginationMeta
from app.database.repository import Repository

router = APIRouter(prefix="/resources", tags=["Academic Resources & Free Courses"])


@router.get(
    "",
    response_model=PaginatedAcademicResourcesResponse,
    status_code=status.HTTP_200_OK,
    summary="List Legal Academic Resources",
    description="Retrieve open educational courses, textbooks, and lecture materials with resource type filtering.",
)
async def list_academic_resources(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=50, description="Items per page"),
    resource_type: Optional[str] = Query(
        default=None,
        description="Resource type: free_course, lecture_materials, open_textbook, programming_tutorial",
    ),
    stem_discipline: Optional[str] = Query(default=None, description="Discipline (e.g. Computer Science, AI)"),
    repo: Repository = Depends(get_repository),
) -> PaginatedAcademicResourcesResponse:
    """Query vetted open educational resources with legal license metadata."""
    offset = (page - 1) * page_size
    total_items = await repo.count_academic_resources(
        resource_type=resource_type,
        stem_discipline=stem_discipline,
    )
    resources = await repo.get_academic_resources(
        resource_type=resource_type,
        stem_discipline=stem_discipline,
        limit=page_size,
        offset=offset,
    )

    total_pages = max(1, math.ceil(total_items / page_size))
    return PaginatedAcademicResourcesResponse(
        items=[build_academic_resource_response(r) for r in resources],
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
    response_model=AcademicResourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Academic Resource by Slug",
    description="Retrieve individual educational material with license type and verified access link.",
)
async def get_academic_resource_by_slug(
    slug: str,
    repo: Repository = Depends(get_repository),
) -> AcademicResourceResponse:
    """Retrieve individual academic resource by unique slug."""
    res = await repo.get_academic_resource_by_slug(slug)
    if not res:
        raise EntityNotFoundException(message=f"Academic resource with slug '{slug}' not found.")
    return build_academic_resource_response(res)
