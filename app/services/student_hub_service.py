"""Service layer for Student Hub, scholarship discovery, filtering, and deadline tracking."""

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from app.bot.ui.design_system import (
    format_ai_notice,
    format_date,
    format_meta,
    format_section,
    sanitize_markdown,
)
from app.database.database import get_session_factory
from app.database.models import AcademicResource, Opportunity, OpportunityReport, UniversityProfile
from app.database.repository import Repository

logger = logging.getLogger(__name__)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is UTC offset-aware for safe comparison and subtraction."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class StudentHubService:
    """Business logic for verified academic opportunities, filtering, and deadline tracking."""

    def __init__(self, session_factory=None) -> None:
        self.session_factory = session_factory or get_session_factory()

    async def get_scholarships(
        self,
        study_level: Optional[str] = None,
        funding_type: Optional[str] = None,
        country: Optional[str] = None,
        stem_field: Optional[str] = None,
        status: Optional[str] = "open",
        opportunity_type: Optional[str] = "scholarship",
        active_only: bool = True,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Opportunity]:
        """Fetch verified opportunities with optional faceted filtering."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.get_opportunities(
                opportunity_type=opportunity_type,
                study_level=study_level,
                funding_type=funding_type,
                country=country,
                stem_field=stem_field,
                status=status,
                active_only=active_only,
                limit=limit,
                offset=offset,
            )

    async def count_scholarships(
        self,
        study_level: Optional[str] = None,
        funding_type: Optional[str] = None,
        country: Optional[str] = None,
        stem_field: Optional[str] = None,
        status: Optional[str] = "open",
        opportunity_type: Optional[str] = "scholarship",
        active_only: bool = True,
    ) -> int:
        """Count opportunities matching active filters for pagination."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.count_opportunities(
                opportunity_type=opportunity_type,
                study_level=study_level,
                funding_type=funding_type,
                country=country,
                stem_field=stem_field,
                status=status,
                active_only=active_only,
            )

    async def get_opportunity_by_slug(self, slug: str) -> Optional[Opportunity]:
        """Retrieve an opportunity record by slug."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.get_opportunity_by_slug(slug)

    async def get_opportunity_by_id(self, opportunity_id: int) -> Optional[Opportunity]:
        """Retrieve an opportunity record by primary key."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.get_opportunity_by_id(opportunity_id)

    async def get_upcoming_deadlines(self, limit: int = 10) -> List[Opportunity]:
        """Fetch upcoming active deadlines ordered chronologically."""
        async with self.session_factory() as session:
            repo = Repository(session)
            # Fetch active opportunities with non-null deadline
            opps = await repo.get_opportunities(
                opportunity_type=None,
                active_only=True,
                limit=limit * 2,
            )
            # Filter strictly for non-null deadlines and sort
            with_deadline = [o for o in opps if o.application_deadline is not None]
            with_deadline.sort(key=lambda x: x.application_deadline)
            return with_deadline[:limit]

    async def report_opportunity(
        self, user_id: int, opportunity_id: int, report_type: str, details: str
    ) -> Tuple[bool, str]:
        """Submit a community verification issue report."""
        try:
            async with self.session_factory() as session:
                repo = Repository(session)
                await repo.submit_opportunity_report(
                    user_id=user_id,
                    opportunity_id=opportunity_id,
                    report_type=report_type,
                    details=details,
                )
            return True, "Report submitted successfully for administrative audit."
        except Exception as exc:
            logger.error("Failed to submit opportunity report: %s", exc)
            return False, f"Failed to submit report: {exc}"

    # ------------------ Stage 16: Public Submissions, Moderation & Trust ------------------

    async def submit_public_opportunity(
        self,
        user_id: int,
        title: str,
        provider_name: str,
        official_url: str,
        country: str,
        study_level: str,
        opportunity_type: str = "scholarship",
        stem_fields: str = "All STEM",
        funding_type: str = "fully_funded",
        application_url: Optional[str] = None,
        eligibility_criteria: str = "",
        application_deadline: Optional[datetime] = None,
        is_rolling: bool = False,
        benefits: Optional[str] = None,
        required_documents: Optional[str] = None,
        repo: Optional[Repository] = None,
    ) -> Tuple[bool, Optional[Opportunity], str]:
        """Submit an opportunity for administrative review and audit before publication."""
        raw_slug = f"{provider_name}-{title}".lower()
        clean_slug = re.sub(r"[^a-z0-9]+", "-", raw_slug).strip("-")[:180]

        async def _do_submit(r: Repository) -> Tuple[bool, Optional[Opportunity], str]:
            opp, created = await r.save_opportunity(
                title=title,
                slug=clean_slug,
                opportunity_type=opportunity_type,
                provider_name=provider_name,
                official_url=official_url,
                country=country,
                study_level=study_level,
                stem_fields=stem_fields,
                funding_type=funding_type,
                application_url=application_url,
                eligibility_criteria=eligibility_criteria or "Refer to official announcement.",
                application_deadline=application_deadline,
                is_rolling=is_rolling,
                benefits=benefits,
                required_documents=required_documents,
                verification_tier="unverified_submission",
                status="pending_approval",
                source_attribution=f"Community Submission (User {user_id})",
            )
            if not created:
                return False, opp, "An opportunity with a matching title/provider is already in the registry."

            # Automatically log a submission report for tracking in the moderation queue
            await r.submit_opportunity_report(
                user_id=user_id,
                opportunity_id=opp.id,
                report_type="submission",
                details=f"Public community submission by User {user_id}: {title}",
            )
            return True, opp, "Opportunity submitted successfully. It will be verified by moderators before publishing."

        try:
            if repo:
                return await _do_submit(repo)
            async with self.session_factory() as session:
                r = Repository(session)
                return await _do_submit(r)
        except Exception as exc:
            logger.error("Failed to submit public opportunity: %s", exc)
            return False, None, f"Submission error: {exc}"

    async def get_pending_submissions(
        self, limit: int = 20, offset: int = 0, repo: Optional[Repository] = None
    ) -> List[Opportunity]:
        """Fetch submitted opportunities awaiting administrative review."""
        if repo:
            return await repo.get_pending_opportunities(limit=limit, offset=offset)
        async with self.session_factory() as session:
            r = Repository(session)
            return await r.get_pending_opportunities(limit=limit, offset=offset)

    async def count_pending_submissions(self, repo: Optional[Repository] = None) -> int:
        """Count opportunities awaiting moderation."""
        if repo:
            return await repo.count_pending_opportunities()
        async with self.session_factory() as session:
            r = Repository(session)
            return await r.count_pending_opportunities()

    async def approve_opportunity(
        self,
        opportunity_id: int,
        admin_user_id: int,
        verification_tier: str = "officially_verified",
        notes: Optional[str] = None,
        repo: Optional[Repository] = None,
    ) -> Optional[Opportunity]:
        """Approve a submitted opportunity, assign verification tier, and publish."""
        if repo:
            return await repo.approve_opportunity(
                opportunity_id=opportunity_id,
                admin_user_id=admin_user_id,
                verification_tier=verification_tier,
                notes=notes,
            )
        async with self.session_factory() as session:
            r = Repository(session)
            return await r.approve_opportunity(
                opportunity_id=opportunity_id,
                admin_user_id=admin_user_id,
                verification_tier=verification_tier,
                notes=notes,
            )

    async def reject_opportunity(
        self,
        opportunity_id: int,
        admin_user_id: int,
        reason: Optional[str] = None,
        repo: Optional[Repository] = None,
    ) -> Optional[Opportunity]:
        """Reject and archive a submitted opportunity."""
        if repo:
            return await repo.reject_opportunity(
                opportunity_id=opportunity_id,
                admin_user_id=admin_user_id,
                reason=reason,
            )
        async with self.session_factory() as session:
            r = Repository(session)
            return await r.reject_opportunity(
                opportunity_id=opportunity_id,
                admin_user_id=admin_user_id,
                reason=reason,
            )

    async def get_moderation_reports(
        self,
        status: str = "pending_review",
        limit: int = 20,
        offset: int = 0,
        repo: Optional[Repository] = None,
    ) -> List[OpportunityReport]:
        """Fetch community issue reports for moderation audit."""
        if repo:
            return await repo.get_opportunity_reports(status=status, limit=limit, offset=offset)
        async with self.session_factory() as session:
            r = Repository(session)
            return await r.get_opportunity_reports(status=status, limit=limit, offset=offset)

    async def count_moderation_reports(self, status: str = "pending_review", repo: Optional[Repository] = None) -> int:
        """Count community issue reports."""
        if repo:
            return await repo.count_opportunity_reports(status=status)
        async with self.session_factory() as session:
            r = Repository(session)
            return await r.count_opportunity_reports(status=status)

    async def resolve_report(
        self,
        report_id: int,
        admin_user_id: int,
        resolution: str = "verified_resolved",
        action_taken: Optional[str] = None,
        repo: Optional[Repository] = None,
    ) -> Optional[OpportunityReport]:
        """Resolve or dismiss a community report with optional action on opportunity."""
        if repo:
            return await repo.resolve_opportunity_report(
                report_id=report_id,
                admin_user_id=admin_user_id,
                resolution=resolution,
                action_taken=action_taken,
            )
        async with self.session_factory() as session:
            r = Repository(session)
            return await r.resolve_opportunity_report(
                report_id=report_id,
                admin_user_id=admin_user_id,
                resolution=resolution,
                action_taken=action_taken,
            )

    async def expire_lapsed_opportunities(self, now: Optional[datetime] = None) -> int:
        """Scan and automatically mark passed deadlines as expired."""
        try:
            async with self.session_factory() as session:
                repo = Repository(session)
                count = await repo.expire_lapsed_opportunities(now=now)
            if count > 0:
                logger.info("Automatically transitioned %d lapsed opportunities to 'expired'.", count)
            return count
        except Exception as exc:
            logger.error("Failed to run automated expiry sweep: %s", exc)
            return 0

    # ------------------ University Profiles ------------------

    async def get_university_profiles(
        self, country: Optional[str] = None, limit: int = 10, offset: int = 0
    ) -> List[UniversityProfile]:
        """Fetch verified university admission profiles."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.get_university_profiles(country=country, limit=limit, offset=offset)

    async def count_university_profiles(self, country: Optional[str] = None) -> int:
        """Count university profiles for pagination."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.count_university_profiles(country=country)

    async def get_university_by_slug(self, slug: str) -> Optional[UniversityProfile]:
        """Retrieve individual university profile by unique slug."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.get_university_by_slug(slug)

    # ------------------ Academic Resources ------------------

    async def get_academic_resources(
        self,
        resource_type: Optional[str] = None,
        stem_discipline: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[AcademicResource]:
        """Fetch copyright-verified educational resources."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.get_academic_resources(
                resource_type=resource_type,
                stem_discipline=stem_discipline,
                limit=limit,
                offset=offset,
            )

    async def count_academic_resources(
        self,
        resource_type: Optional[str] = None,
        stem_discipline: Optional[str] = None,
    ) -> int:
        """Count academic resources for pagination."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.count_academic_resources(
                resource_type=resource_type,
                stem_discipline=stem_discipline,
            )

    async def get_academic_resource_by_slug(self, slug: str) -> Optional[AcademicResource]:
        """Retrieve individual academic resource by unique slug."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.get_academic_resource_by_slug(slug)

    # ------------------ Presentation & Markdown Formatters ------------------

    def format_student_hub_intro(self) -> str:
        """Dashboard overview for the Student Hub."""
        return (
            "*Student Hub*\n\n"
            "Verified STEM scholarships, university admission profiles, "
            "application deadlines, and open educational resources.\n\n"
            "- Scholarships: Undergraduate, Master's, PhD, and Postdoctoral funding.\n"
            "- Deadlines: Chronological tracker for upcoming closing dates.\n"
            "- Universities: Official admission portals and application guidelines.\n"
            "- Courses & Materials: Open courseware, textbooks, and lecture notes.\n\n"
            "Select a section:"
        )

    def format_scholarships_list(
        self,
        opportunities: List[Opportunity],
        page: int = 0,
        total_pages: int = 1,
        level_filter: str = "all",
        funding_filter: str = "all",
        country_filter: str = "all",
        type_label: str = "Scholarships",
    ) -> str:
        """Format an interactive paginated list of opportunities."""
        country_summary = f" · Country: {country_filter.title()}" if country_filter != "all" else ""
        if not opportunities:
            filter_summary = f"Level: {level_filter}, Funding: {funding_filter}{country_summary}"
            return (
                f"*Verified STEM {type_label}*\n\n"
                f"No open {type_label.lower()} match your filters ({filter_summary}).\n\n"
                "Reset filters below, or select Submit Opportunity to contribute a listing for review."
            )

        funding_label = funding_filter.replace("_", " ").capitalize()
        lines = [
            f"*Verified STEM {type_label}*",
            f"Page {page + 1} of {max(1, total_pages)} · "
            f"Level: {level_filter.capitalize()} · Funding: {funding_label}{country_summary}\n",
        ]

        now = datetime.now(timezone.utc)
        for idx, opp in enumerate(opportunities, 1):
            tier_badge = "Officially verified" if opp.verification_tier == "officially_verified" else "Secondary source"
            deadline_utc = ensure_utc(opp.application_deadline)
            is_expired = opp.status == "expired" or (
                deadline_utc and (deadline_utc - now).days < 0 and not opp.is_rolling
            )

            if is_expired:
                status_badge = "Expired"
                dl_str = f"Closed ({format_date(deadline_utc, fallback='Past')})"
            elif deadline_utc:
                days_left = (deadline_utc - now).days
                if days_left > 0:
                    dl_str = f"{format_date(deadline_utc)} ({days_left}d left)"
                else:
                    dl_str = f"Closes today ({format_date(deadline_utc)})"
                status_badge = "Open"
            else:
                status_badge = "Rolling"
                dl_str = "Rolling intake"

            clean_title = sanitize_markdown(opp.title)
            clean_provider = sanitize_markdown(opp.provider_name)
            funding_clean = opp.funding_type.replace("_", " ").capitalize()
            lines.append(
                f"*{idx}. {clean_title}*\n"
                f"Provider: {clean_provider} ({sanitize_markdown(opp.country)})\n"
                f"{opp.study_level.capitalize()} · {funding_clean} · {tier_badge}\n"
                f"Status: {status_badge} · Deadline: {dl_str}\n"
                f"Details: /scholarship_{opp.id}\n"
            )

        lines.append("Select an item below for full eligibility criteria and official links.")
        return "\n".join(lines)

    def format_scholarship_card(self, opp: Opportunity) -> str:
        """Format complete single scholarship record with trust metadata and disclaimers."""
        tier_str = "Officially verified"
        if opp.verification_tier == "secondary_verified":
            tier_str = "Secondary source"
        elif opp.verification_tier == "unverified_submission":
            tier_str = "Unverified community submission (pending review)"

        now = datetime.now(timezone.utc)
        deadline_utc = ensure_utc(opp.application_deadline)
        opens_utc = ensure_utc(opp.application_opens_at)

        is_expired = opp.status == "expired" or (deadline_utc and (deadline_utc - now).days < 0 and not opp.is_rolling)

        if is_expired:
            status_badge = "Expired (Closed)"
            dl_str = f"{format_date(deadline_utc, fallback='Past')} (Closed)"
        elif opp.is_rolling or not deadline_utc:
            status_badge = "Open (Rolling)"
            dl_str = "Rolling intake (confirm cut-off dates on official portal)"
        else:
            days_left = (deadline_utc - now).days
            dl_format = format_date(deadline_utc)
            if days_left > 0:
                status_badge = "Open"
                dl_str = f"{dl_format} ({days_left} days remaining)"
            elif days_left == 0:
                status_badge = "Closes today"
                dl_str = f"{dl_format} (Due today)"
            else:
                status_badge = "Expired (Closed)"
                dl_str = f"{dl_format} (Closed)"

        benefits = sanitize_markdown(
            opp.benefits or "Refer to the official provider announcement for financial coverage details."
        )
        required_docs = sanitize_markdown(
            opp.required_documents or "Official transcripts, CV, and letters of recommendation."
        )
        verified_date = format_date(opp.last_verified_at, fallback="Recently")
        nationalities = sanitize_markdown(opp.eligible_nationalities or "All international applicants")
        stem_fields = sanitize_markdown(opp.stem_fields or "All STEM disciplines")

        window_val = None
        if opens_utc and deadline_utc:
            window_val = f"{format_date(opens_utc)} - {format_date(deadline_utc)}"

        meta = format_meta(
            [
                ("Provider", f"{sanitize_markdown(opp.provider_name)} ({sanitize_markdown(opp.country)})"),
                ("Status", f"{status_badge} · {tier_str}"),
                ("Study level", opp.study_level.capitalize()),
                ("Funding", opp.funding_type.replace("_", " ").capitalize()),
                ("Eligible fields", stem_fields),
                ("Eligible nationalities", nationalities),
                ("Application window", window_val),
                ("Deadline", dl_str),
            ]
        )

        links = [f"[Official Announcement]({opp.official_url})"]
        if opp.application_url:
            links.append(f"[Apply Online]({opp.application_url})")

        sections = [f"*{sanitize_markdown(opp.title)}*", meta]
        if is_expired:
            sections.append(
                "*Notice:* This deadline has passed. Consult the official portal for the next application cycle."
            )

        sections.extend(
            [
                format_section("Coverage & Benefits", benefits),
                format_section("Eligibility", sanitize_markdown(opp.eligibility_criteria)),
                format_section("Required Documents", required_docs),
                format_section("Official Links", " · ".join(links)),
                f"Last verified: {verified_date} · Source: {sanitize_markdown(opp.source_attribution)}",
                format_ai_notice("opportunity"),
            ]
        )
        return "\n\n".join(s for s in sections if s)

    def format_deadline_tracker(self, opportunities: List[Opportunity]) -> str:
        """Format timeline of upcoming scholarship and research deadlines."""
        if not opportunities:
            return (
                "*Upcoming Application Deadlines*\n\n"
                "No upcoming fixed-deadline opportunities are listed right now. "
                "Check rolling admissions or browse all scholarships."
            )

        lines = [
            "*Upcoming Application Deadlines*\n",
        ]

        now = datetime.now(timezone.utc)
        for idx, opp in enumerate(opportunities, 1):
            deadline_utc = ensure_utc(opp.application_deadline)
            if deadline_utc:
                days_left = (deadline_utc - now).days
                if days_left > 1:
                    time_str = f"In {days_left} days ({format_date(deadline_utc)})"
                elif days_left == 1:
                    time_str = f"Tomorrow ({format_date(deadline_utc)})"
                else:
                    time_str = f"Due today ({format_date(deadline_utc)})"
            else:
                time_str = "Rolling intake"

            lines.append(
                f"*{idx}. {sanitize_markdown(opp.title)}*\n"
                f"Provider: {sanitize_markdown(opp.provider_name)} ({sanitize_markdown(opp.country)})\n"
                f"{opp.study_level.capitalize()} · {opp.funding_type.replace('_', ' ').capitalize()}\n"
                f"Deadline: {time_str}\n"
                f"Details: /scholarship_{opp.id}\n"
            )

        lines.append("Submit applications early to allow time for reference letters and document verification.")
        return "\n".join(lines)

    def format_universities_list(
        self,
        universities: List[UniversityProfile],
        page: int = 0,
        total_pages: int = 1,
        country_filter: str = "all",
    ) -> str:
        """Format an interactive paginated list of accredited universities."""
        if not universities:
            return (
                "*University Admissions*\n\n"
                f"No universities found matching country '{country_filter}'.\n\n"
                "Reset filters below or browse all listed institutions."
            )

        lines = [
            "*University Admissions*",
            f"Page {page + 1} of {max(1, total_pages)} · Country: {country_filter.title()}\n",
        ]
        for idx, u in enumerate(universities, 1):
            city_txt = f", {sanitize_markdown(u.city)}" if u.city else ""
            lines.append(
                f"*{idx}. {sanitize_markdown(u.name)}*\n"
                f"Location: {sanitize_markdown(u.country)}{city_txt}\n"
                f"Details: /university_{u.slug}\n"
            )
        lines.append("Select an institution below for admission requirements and official portals.")
        return "\n".join(lines)

    def format_university_card(self, uni: UniversityProfile) -> str:
        """Format complete accredited university profile with official admission links."""
        city_str = f", {sanitize_markdown(uni.city)}" if uni.city else ""
        admissions = sanitize_markdown(
            uni.admission_requirements or "Consult the official university admissions office for current requirements."
        )
        procedures = sanitize_markdown(
            uni.application_procedures
            or "Submit application, academic transcripts, and credentials via the official portal."
        )
        tuition = sanitize_markdown(
            uni.tuition_and_funding or "Tuition rates vary by faculty, nationality, and scholarship eligibility."
        )
        verified_date = format_date(uni.last_verified_at, fallback="Recently")

        sections = [
            f"*{sanitize_markdown(uni.name)}*\nLocation: {sanitize_markdown(uni.country)}{city_str}",
            format_section("Admission Requirements", admissions),
            format_section("Application Procedures", procedures),
            format_section("Tuition & Financial Aid", tuition),
            f"Last verified: {verified_date}",
            (
                "_Confirm current admission criteria, visa requirements, and tuition "
                "directly on the university's official portal._"
            ),
        ]
        return "\n\n".join(s for s in sections if s)

    def format_academic_resources_list(
        self,
        resources: List[AcademicResource],
        page: int = 0,
        total_pages: int = 1,
        type_filter: str = "all",
        discipline_filter: str = "all",
    ) -> str:
        """Format an interactive paginated list of educational resources."""
        if not resources:
            return (
                "*Free Courses & Study Materials*\n\n"
                f"No resources found for Type: {type_filter}, Discipline: {discipline_filter}.\n\n"
                "Reset filters below or browse all open materials."
            )

        lines = [
            "*Free Courses & Study Materials*",
            f"Page {page + 1} of {max(1, total_pages)} · "
            f"Type: {type_filter.capitalize()} · Discipline: {discipline_filter.capitalize()}\n",
        ]
        for idx, r in enumerate(resources, 1):
            lines.append(
                f"*{idx}. {sanitize_markdown(r.title)}*\n"
                f"{sanitize_markdown(r.provider_institution)} · {sanitize_markdown(r.stem_discipline)}\n"
                f"{sanitize_markdown(r.license_type)} · {r.resource_type.replace('_', ' ').title()}\n"
                f"Details: /resource_{r.slug}\n"
            )
        lines.append("Select a resource below for curriculum links and access details.")
        return "\n".join(lines)

    def format_pending_submissions_list(
        self,
        opportunities: List[Opportunity],
        page: int = 0,
        total_pages: int = 1,
    ) -> str:
        """Format pending opportunity submissions for admin moderation."""
        if not opportunities:
            return (
                "*Moderation Queue — Pending Submissions*\n\n"
                "No unverified opportunity submissions are waiting for review."
            )

        lines = [
            "*Moderation Queue — Pending Submissions*",
            f"Page {page + 1} of {max(1, total_pages)} · Pending: {len(opportunities)}\n",
        ]

        for idx, opp in enumerate(opportunities, 1):
            dl_str = format_date(opp.application_deadline, fallback="Rolling")
            lines.append(
                f"*{idx}. [#{opp.id}] {sanitize_markdown(opp.title)}*\n"
                f"Provider: {sanitize_markdown(opp.provider_name)} ({sanitize_markdown(opp.country)})\n"
                f"Level: {opp.study_level.capitalize()} · Funding: {opp.funding_type}\n"
                f"Deadline: {dl_str} · [Official Announcement]({opp.official_url})\n"
                f"Source: {sanitize_markdown(opp.source_attribution)}\n"
                f"/mod_approve_{opp.id} · /mod_reject_{opp.id}\n"
            )
        lines.append("Use the action buttons below to approve or reject submissions.")
        return "\n".join(lines)

    def format_moderation_reports_list(
        self,
        reports: List[OpportunityReport],
        page: int = 0,
        total_pages: int = 1,
    ) -> str:
        """Format community issue reports for admin moderation."""
        if not reports:
            return "*Moderation Queue — Community Reports*\n\nNo open community issue reports are pending review."

        lines = [
            "*Moderation Queue — Community Reports*",
            f"Page {page + 1} of {max(1, total_pages)} · Open reports: {len(reports)}\n",
        ]

        for idx, rep in enumerate(reports, 1):
            opp_ref = f"Opportunity #{rep.opportunity_id}" if rep.opportunity_id else "General submission"
            lines.append(
                f"*{idx}. [Report #{rep.id}] {rep.report_type.upper()}*\n"
                f"Target: {opp_ref} · Reporter: `{rep.user_id}`\n"
                f"Details: {sanitize_markdown(rep.details)}\n"
                f"Reported: {format_date(rep.created_at)}\n"
                f"/mod_resolve_{rep.id} · /mod_dismiss_{rep.id}\n"
            )
        lines.append("Use the actions below to resolve, dismiss, or expire affected listings.")
        return "\n".join(lines)

    def format_academic_resource_card(self, res: AcademicResource) -> str:
        """Format vetted legal educational resource card with copyright and open licensing."""
        desc = sanitize_markdown(res.description or "Open academic reference and technical study material.")
        verified_date = format_date(res.last_verified_at, fallback="Recently")

        meta = format_meta(
            [
                ("Institution", sanitize_markdown(res.provider_institution)),
                ("Discipline", sanitize_markdown(res.stem_discipline)),
                ("Type", res.resource_type.replace("_", " ").title()),
                ("License", sanitize_markdown(res.license_type)),
                ("Copyright status", "Verified open access / free authorized material"),
            ]
        )

        sections = [
            f"*{sanitize_markdown(res.title)}*",
            meta,
            format_section("Overview", desc),
            f"Last verified: {verified_date}",
            "_STEM RADAR indexes authorized open educational resources and official university materials only._",
        ]
        return "\n\n".join(s for s in sections if s)


student_hub_service = StudentHubService()
