"""STEM categories registry endpoints."""

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_repository
from app.api.v1.schemas.categories import CategoryDetailResponse, CategoryListResponse
from app.database.repository import Repository

router = APIRouter(prefix="/categories", tags=["Intelligence"])


@router.get(
    "",
    response_model=CategoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="List STEM Categories",
    description="Retrieve all configured Science, Technology, Engineering, and Math domain categories.",
)
async def list_categories(
    repo: Repository = Depends(get_repository),
) -> CategoryListResponse:
    """Fetch all supported STEM categories."""
    categories = await repo.get_categories()
    items = [CategoryDetailResponse.model_validate(c) for c in categories]
    return CategoryListResponse(items=items, total=len(items))
