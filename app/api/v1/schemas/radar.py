"""Pydantic schemas for Technology Radar and Velocity API."""

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class HorizonItem(BaseModel):
    """Specific technology on the radar."""

    technology: str = Field(..., description="Technology name")
    focus_or_standard: str = Field(..., description="Standard pattern, ecosystem tools, or focus")
    verdict: str = Field(..., description="Adoption verdict or status")


class HorizonDetail(BaseModel):
    """Detailed view of an adoption horizon."""

    horizon: str = Field(..., description="Horizon name: adopt, trial, assess, hold")
    definition: str = Field(..., description="Criteria defining this horizon")
    items: List[HorizonItem] = Field(default_factory=list, description="Technologies in this horizon")


class RadarResponse(BaseModel):
    """Complete Technology Radar payload."""

    horizons: Dict[str, HorizonDetail] = Field(..., description="All adoption horizons mapped by key")
    domain_velocities: Dict[str, Any] = Field(
        default_factory=dict, description="Active empirical domain momentum metrics"
    )
    timestamp: datetime = Field(..., description="Timestamp of radar synthesis")


class DomainVelocityItem(BaseModel):
    """Velocity telemetry for a single STEM domain."""

    slug: str = Field(..., description="Domain slug")
    name: str = Field(..., description="Domain display name")
    count: int = Field(..., description="Total articles collected")
    paper_count: int = Field(..., description="Scientific research papers collected")
    avg_score: float = Field(..., description="Average composite impact score")
    momentum: str = Field(..., description="Momentum indicator: 🔥 Surging, 📈 Rising, ⚖️ Stable")
    top_headline: str = Field(..., description="Highest-scoring development headline")


class DomainVelocityResponse(BaseModel):
    """Aggregated domain momentum and velocity response."""

    domains: List[DomainVelocityItem] = Field(..., description="Velocity metrics per domain")
    total_domains: int = Field(..., description="Number of tracked domains")
    timestamp: datetime = Field(..., description="Calculation timestamp")
