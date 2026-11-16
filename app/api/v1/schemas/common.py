"""Common reusable Pydantic schemas across all API endpoints."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(default="healthy", description="Application health status")
    version: str = Field(default="0.1.0", description="Application version")
    database: str = Field(default="connected", description="Database connectivity status")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Current UTC timestamp",
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional health telemetry metadata",
    )


class ErrorDetail(BaseModel):
    """Structured error payload."""

    code: str = Field(..., description="Machine-readable error identifier")
    message: str = Field(..., description="Human-readable explanation of error")
    details: Optional[Any] = Field(default=None, description="Detailed validation payload")


class ErrorResponse(BaseModel):
    """Standardized top-level API error envelope."""

    error: ErrorDetail


class PaginationMeta(BaseModel):
    """Pagination metadata included in list responses."""

    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total_items: int = Field(..., ge=0, description="Total number of items matching criteria")
    total_pages: int = Field(..., ge=0, description="Total pages available")
    has_next: bool = Field(..., description="Whether a next page exists")
    has_prev: bool = Field(..., description="Whether a previous page exists")
