"""Admin moderation endpoints for managing submissions, community reports, and verification tiers."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_repository, require_api_key
from app.api.exceptions import EntityNotFoundException
from app.api.v1.schemas.scholarships import (
    OpportunityReportResponse,
    OpportunityResponse,
    build_opportunity_response,
)
from app.database.repository import Repository
from app.services.student_hub_service import student_hub_service

router = APIRouter(
    prefix="/moderation",
    tags=["Admin Moderation & Trust Verification"],
    dependencies=[Depends(require_api_key)],
)


@router.get(
    "/pending",
    response_model=List[OpportunityResponse],
    status_code=status.HTTP_200_OK,
    summary="List Pending Opportunity Submissions",
    description="Retrieve all community submissions awaiting administrative moderation.",
)
async def list_pending_submissions(
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Offset"),
    repo: Repository = Depends(get_repository),
) -> List[OpportunityResponse]:
    """Fetch unverified opportunity submissions awaiting approval."""
    opps = await student_hub_service.get_pending_submissions(limit=limit, offset=offset, repo=repo)
    return [build_opportunity_response(o) for o in opps]


@router.post(
    "/opportunities/{opportunity_id}/approve",
    response_model=OpportunityResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve Opportunity Submission",
    description="Approve and publish a pending opportunity with an accredited verification tier.",
)
async def approve_opportunity_submission(
    opportunity_id: int,
    verification_tier: str = Query(
        default="officially_verified",
        pattern="^(officially_verified|secondary_verified)$",
        description="Assigned verification tier",
    ),
    admin_id: int = Query(default=1, description="Admin user ID"),
    notes: Optional[str] = Query(default=None, description="Audit review notes"),
    repo: Repository = Depends(get_repository),
) -> OpportunityResponse:
    """Approve submission, transition status to open, and assign trust tier."""
    opp = await student_hub_service.approve_opportunity(
        opportunity_id=opportunity_id,
        admin_user_id=admin_id,
        verification_tier=verification_tier,
        notes=notes,
        repo=repo,
    )
    if not opp:
        raise EntityNotFoundException(message=f"Pending opportunity with ID {opportunity_id} not found.")
    return build_opportunity_response(opp)


@router.post(
    "/opportunities/{opportunity_id}/reject",
    response_model=OpportunityResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject Opportunity Submission",
    description="Reject and archive an unverified opportunity submission.",
)
async def reject_opportunity_submission(
    opportunity_id: int,
    admin_id: int = Query(default=1, description="Admin user ID"),
    reason: Optional[str] = Query(default=None, description="Rejection reason"),
    repo: Repository = Depends(get_repository),
) -> OpportunityResponse:
    """Reject an opportunity submission."""
    opp = await student_hub_service.reject_opportunity(
        opportunity_id=opportunity_id,
        admin_user_id=admin_id,
        reason=reason,
        repo=repo,
    )
    if not opp:
        raise EntityNotFoundException(message=f"Opportunity with ID {opportunity_id} not found.")
    return build_opportunity_response(opp)


@router.get(
    "/reports",
    response_model=List[OpportunityReportResponse],
    status_code=status.HTTP_200_OK,
    summary="List Community Reports",
    description="Retrieve community issue reports flagged by users.",
)
async def list_moderation_reports(
    status_filter: str = Query(
        default="pending_review",
        pattern="^(pending_review|verified_resolved|dismissed|all)$",
        description="Filter reports by status",
    ),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Offset"),
    repo: Repository = Depends(get_repository),
) -> List[OpportunityReportResponse]:
    """Retrieve community issue reports."""
    reports = await student_hub_service.get_moderation_reports(
        status=status_filter, limit=limit, offset=offset, repo=repo
    )
    return [
        OpportunityReportResponse(
            id=r.id,
            opportunity_id=r.opportunity_id,
            report_type=r.report_type,
            status=r.status,
            message=r.details,
        )
        for r in reports
    ]


@router.post(
    "/reports/{report_id}/resolve",
    response_model=OpportunityReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve Community Report",
    description="Resolve or dismiss a community report, optionally expiring the target opportunity.",
)
async def resolve_moderation_report(
    report_id: int,
    resolution: str = Query(
        default="verified_resolved",
        pattern="^(verified_resolved|dismissed)$",
        description="Resolution status",
    ),
    action: Optional[str] = Query(
        default="none",
        pattern="^(none|expire_opportunity)$",
        description="Action to take on the linked opportunity",
    ),
    admin_id: int = Query(default=1, description="Admin user ID"),
    repo: Repository = Depends(get_repository),
) -> OpportunityReportResponse:
    """Resolve report and execute corrective action."""
    action_taken = action if action != "none" else None
    report = await student_hub_service.resolve_report(
        report_id=report_id,
        admin_user_id=admin_id,
        resolution=resolution,
        action_taken=action_taken,
        repo=repo,
    )
    if not report:
        raise EntityNotFoundException(message=f"Report with ID {report_id} not found.")
    return OpportunityReportResponse(
        id=report.id,
        opportunity_id=report.opportunity_id,
        report_type=report.report_type,
        status=report.status,
        message=f"Report marked as {resolution}.",
    )


@router.post(
    "/sweep-expired",
    status_code=status.HTTP_200_OK,
    summary="Run Expiry Sweep",
    description="Scan database and transition any opportunities with passed application deadlines to 'expired'.",
)
async def trigger_expiry_sweep() -> dict:
    """Manually trigger automated deadline expiry pass."""
    count = await student_hub_service.expire_lapsed_opportunities()
    return {
        "expired_count": count,
        "message": f"Successfully transitioned {count} lapsed opportunities to 'expired'.",
    }
