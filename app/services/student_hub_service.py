"""Service layer for Student Hub, scholarship discovery, filtering, and deadline tracking."""

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple

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
            "🎓 *STEM RADAR — Student Hub*\n\n"
            "Discover verified academic opportunities, global scholarship programs, "
            "accredited university admissions, and legal learning resources.\n\n"
            "• *Verified Scholarships:* Undergraduate, Master's, PhD, and Postdoc awards.\n"
            "• *Application Deadlines:* Real-time tracking to ensure zero missed applications.\n"
            "• *University Admissions:* Requirements, portals, and international guidelines.\n"
            "• *Academic Resources:* Open courseware, textbooks, and research repositories.\n\n"
            "Select an academic hub category below:"
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
        if "Scholarship" in type_label:
            emoji = "🎁"
        elif "Internship" in type_label:
            emoji = "💼"
        elif "Grant" in type_label:
            emoji = "💰"
        else:
            emoji = "🏆"

        country_summary = f" | Country: `{country_filter.upper()}`" if country_filter != "all" else ""
        if not opportunities:
            filter_summary = f"`Level: {level_filter}`, `Funding: {funding_filter}`{country_summary}"
            return (
                f"{emoji} *Verified STEM {type_label}*\n\n"
                f"No open {type_label.lower()} found matching ({filter_summary}).\n\n"
                "💡 *Know an opportunity?* Tap *Submit Opportunity* below to contribute for moderator verification!"
            )

        lines = [
            f"{emoji} *Verified STEM {type_label}*",
            f"Showing Page `{page + 1}` of `{max(1, total_pages)}` | "
            f"Level: `{level_filter.upper()}` | Funding: `{funding_filter.upper()}`{country_summary}\n",
        ]

        now = datetime.now(timezone.utc)
        for idx, opp in enumerate(opportunities, 1):
            tier_badge = "🟢 Verified" if opp.verification_tier == "officially_verified" else "🟡 Secondary Source"
            deadline_utc = ensure_utc(opp.application_deadline)
            is_expired = opp.status == "expired" or (
                deadline_utc and (deadline_utc - now).days < 0 and not opp.is_rolling
            )

            if is_expired:
                status_badge = "🔴 EXPIRED"
                dl_str = f"⏰ Closed ({deadline_utc.strftime('%b %d, %Y') if deadline_utc else 'Past'})"
            elif deadline_utc:
                days_left = (deadline_utc - now).days
                if days_left > 0:
                    urgency = "🟢" if days_left > 14 else ("🟡" if days_left > 3 else "🔴")
                    dl_str = f"⏰ {urgency} {days_left}d left ({deadline_utc.strftime('%b %d, %Y')})"
                else:
                    dl_str = f"⏰ 🔴 Today ({deadline_utc.strftime('%b %d')})"
                status_badge = "🟢 OPEN"
            else:
                status_badge = "🔄 ROLLING"
                dl_str = "⏰ Rolling Applications"

            lines.append(
                f"*{idx}. {opp.title}*\n"
                f"🏛️ _{opp.provider_name}_ ({opp.country})\n"
                f"🎯 `{opp.study_level.upper()}` | 💰 `{opp.funding_type.replace('_', ' ').title()}` | {tier_badge}\n"
                f"Status: `{status_badge}` | {dl_str}\n"
                f"👉 /scholarship_{opp.id} (or tap card below)\n"
            )

        lines.append("💡 *Tip:* Tap an item below for full eligibility criteria and official links.")
        return "\n".join(lines)

    def format_scholarship_card(self, opp: Opportunity) -> str:
        """Format complete single scholarship record with trust metadata and disclaimers."""
        tier_str = "🟢 Officially Verified Source"
        if opp.verification_tier == "secondary_verified":
            tier_str = "🟡 Verified via Recognized Secondary Source"
        elif opp.verification_tier == "unverified_submission":
            tier_str = "⚪ Community Submission (Pending Audit)"

        now = datetime.now(timezone.utc)
        deadline_utc = ensure_utc(opp.application_deadline)
        opens_utc = ensure_utc(opp.application_opens_at)

        is_expired = opp.status == "expired" or (deadline_utc and (deadline_utc - now).days < 0 and not opp.is_rolling)

        if is_expired:
            status_badge = "🔴 Expired / Closed (Intake Completed)"
            dl_str = f"📅 *{deadline_utc.strftime('%B %d, %Y') if deadline_utc else 'Past'}* (`Lapsed / Closed`)"
        elif opp.is_rolling or not deadline_utc:
            status_badge = "🟢 Active (Rolling Intake)"
            dl_str = "🔄 *Rolling Applications (Check official portal for cut-off dates)*"
        else:
            days_left = (deadline_utc - now).days
            dl_format = deadline_utc.strftime("%B %d, %Y")
            if days_left > 0:
                status_badge = "🟢 Active & Open for Applications"
                dl_str = f"📅 *{dl_format}* (`{days_left} days remaining`)"
            elif days_left == 0:
                status_badge = "🟡 Closes Today"
                dl_str = f"📅 *{dl_format}* (`Due Today!`)"
            else:
                status_badge = "🔴 Expired / Closed"
                dl_str = f"📅 *{dl_format}* (`Lapsed / Closed`)"

        benefits = (
            opp.benefits or "Refer to the official provider announcement for complete financial coverage details."
        )
        required_docs = opp.required_documents or "Official transcripts, CV, and letters of recommendation."
        verified_date = opp.last_verified_at.strftime("%b %d, %Y") if opp.last_verified_at else "Recently"
        nationalities = opp.eligible_nationalities or "All International Applicants"
        stem_fields = opp.stem_fields or "All STEM Disciplines"

        # Application window if opening date is recorded
        window_line = ""
        if opens_utc and deadline_utc:
            window_line = (
                f"🗓️ *Application Window:* {opens_utc.strftime('%b %d, %Y')} – {deadline_utc.strftime('%b %d, %Y')}\n"
            )

        expired_alert = ""
        if is_expired:
            expired_alert = (
                "⚠️ *Notice: This opportunity has expired or its deadline has passed. "
                "Consult the official portal for future cycle announcements.*\n\n"
            )

        official_links_line = f"• *Announcement:* [Official Announcement]({opp.official_url})\n"
        if opp.application_url:
            official_links_line += f"• *Application Portal:* [Apply Online]({opp.application_url})\n"

        return (
            f"🎓 *{opp.title}*\n"
            f"🏷️ *Trust Tier:* `{tier_str}`\n"
            f"📊 *Status:* `{status_badge}`\n\n"
            f"{expired_alert}"
            f"🏛️ *Provider / Sponsor:* {opp.provider_name} ({opp.country})\n"
            f"🌍 *Eligible Nationalities:* {nationalities}\n"
            f"🎯 *Study Level:* `{opp.study_level.upper()}`\n"
            f"🔬 *Eligible Disciplines:* `{stem_fields}`\n"
            f"💰 *Funding Structure:* `{opp.funding_type.replace('_', ' ').upper()}`\n\n"
            f"✨ *Benefits & Financial Coverage:*\n{benefits}\n\n"
            f"📋 *Eligibility Criteria:*\n{opp.eligibility_criteria}\n\n"
            f"📁 *Required Application Documents:*\n{required_docs}\n\n"
            f"{window_line}"
            f"⏰ *Application Deadline:*\n{dl_str}\n\n"
            f"🔗 *Verified Official Links:*\n{official_links_line}\n"
            f"🗓️ *Last Verified:* `{verified_date}`\n"
            f"📰 *Attribution:* _{opp.source_attribution}_\n\n"
            "⚠️ *Official Trust Disclaimer:*\n"
            "_Eligibility must be confirmed directly against the official provider's rules. "
            "STEM RADAR does not guarantee selection, funding, or award issuance._"
        )

    def format_deadline_tracker(self, opportunities: List[Opportunity]) -> str:
        """Format timeline of upcoming scholarship and research deadlines."""
        if not opportunities:
            return (
                "⏰ *Upcoming STEM Application Deadlines*\n\n"
                "No upcoming fixed-deadline opportunities found. Check back soon or view rolling admissions!"
            )

        lines = [
            "⏰ *Upcoming STEM Application Deadlines*",
            "Track critical submission cut-offs for global scholarships, fellowships, and grants:\n",
        ]

        now = datetime.now(timezone.utc)
        for idx, opp in enumerate(opportunities, 1):
            deadline_utc = ensure_utc(opp.application_deadline)
            if deadline_utc:
                days_left = (deadline_utc - now).days
                if days_left > 1:
                    urgency = "🟢" if days_left > 30 else ("🟡" if days_left > 7 else "🔴")
                    time_str = f"{urgency} *In {days_left} days* ({deadline_utc.strftime('%b %d, %Y')})"
                elif days_left == 1:
                    time_str = "🔴 *Tomorrow!*"
                else:
                    time_str = "🔴 *Due Today!*"
            else:
                time_str = "🔄 *Rolling Applications*"

            lines.append(
                f"*{idx}. {opp.title}*\n"
                f"🏛️ _{opp.provider_name}_ ({opp.country})\n"
                f"🎯 `{opp.study_level.upper()}` | 💰 `{opp.funding_type.replace('_', ' ').title()}`\n"
                f"⏳ Deadline: {time_str}\n"
                f"👉 /scholarship_{opp.id}\n"
            )

        lines.append("💡 *Tip:* Submit at least 2 weeks before deadlines to account for referee letter delays.")
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
                "🏛️ *University Admissions & Guidelines*\n\n"
                f"No universities found matching country `{country_filter}`.\n\n"
                "Tap *Reset Filters* below or browse all accredited institutions."
            )

        lines = [
            "🏛️ *University Admissions & Academic Guidelines*",
            f"Showing Page `{page + 1}` of `{max(1, total_pages)}` | Filter: `{country_filter.upper()}`\n",
        ]
        for idx, u in enumerate(universities, 1):
            city_txt = f", {u.city}" if u.city else ""
            lines.append(f"*{idx}. {u.name}*\n📍 `{u.country}{city_txt}`\n👉 /university_{u.slug}\n")
        lines.append(
            "💡 *Tip:* Tap an institution below to view admission requirements, guidelines, and official portals."
        )
        return "\n".join(lines)

    def format_university_card(self, uni: UniversityProfile) -> str:
        """Format complete accredited university profile with official admission links."""
        city_str = f", {uni.city}" if uni.city else ""
        admissions = (
            uni.admission_requirements or "Consult the official university admissions office for departmental cutoffs."
        )
        procedures = (
            uni.application_procedures
            or "Submit application, academic transcripts, and credentials via the official portal."
        )
        tuition = uni.tuition_and_funding or "Tuition rates vary by faculty, nationality, and scholarship eligibility."
        verified_date = uni.last_verified_at.strftime("%b %d, %Y") if uni.last_verified_at else "Recently"

        lines = [
            f"🏛️ *{uni.name}*",
            f"📍 *Location:* `{uni.country}{city_str}`\n",
            "📋 *Admission Requirements:*",
            f"{admissions}\n",
            "📝 *Application Procedures:*",
            f"{procedures}\n",
            "💵 *Tuition & Financial Aid:*",
            f"{tuition}\n",
            f"🗓️ *Last Verified:* `{verified_date}`\n",
            "⚠️ *Official Trust Disclaimer:*\n"
            "_Never rely on third-party estimates. Admission criteria, visa regulations, and fees "
            "must always be verified directly on the university's official portal._",
        ]
        return "\n".join(lines)

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
                "📚 *Free STEM Courses & Study Materials*\n\n"
                f"No resources found for (`Type: {type_filter}`, `Discipline: {discipline_filter}`).\n\n"
                "Tap *Reset Filters* below or explore all open materials."
            )

        lines = [
            "📚 *Free STEM Courses & Study Materials*",
            f"Showing Page `{page + 1}` of `{max(1, total_pages)}` | "
            f"Type: `{type_filter.upper()}` | Discipline: `{discipline_filter.upper()}`\n",
        ]
        for idx, r in enumerate(resources, 1):
            lines.append(
                f"*{idx}. {r.title}*\n"
                f"🏛️ _{r.provider_institution}_ | `{r.stem_discipline}`\n"
                f"⚖️ `{r.license_type}` | 🏷️ `{r.resource_type.replace('_', ' ').title()}`\n"
                f"👉 /resource_{r.slug}\n"
            )
        lines.append("💡 *Tip:* Tap an item below for course curriculum, textbook links, and lecture materials.")
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
                "🛡️ *Admin Moderation Queue — Pending Submissions*\n\n"
                "✅ *All caught up!* There are currently no unverified opportunity submissions waiting for review."
            )

        lines = [
            "🛡️ *Admin Moderation Queue — Pending Submissions*",
            f"Page `{page + 1}` of `{max(1, total_pages)}` | Pending: `{len(opportunities)}`\n",
        ]

        for idx, opp in enumerate(opportunities, 1):
            dl_str = opp.application_deadline.strftime("%b %d, %Y") if opp.application_deadline else "Rolling"
            lines.append(
                f"*{idx}. [#{opp.id}] {opp.title}*\n"
                f"🏛️ Provider: _{opp.provider_name}_ ({opp.country})\n"
                f"🎯 Level: `{opp.study_level.upper()}` | Funding: `{opp.funding_type}`\n"
                f"⏰ Deadline: `{dl_str}` | Link: [Official Announcement]({opp.official_url})\n"
                f"Attribution: _{opp.source_attribution}_\n"
                f"👉 /mod_approve_{opp.id} | /mod_reject_{opp.id}\n"
            )
        lines.append("💡 *Actions:* Use the inline action buttons below or commands to approve/reject.")
        return "\n".join(lines)

    def format_moderation_reports_list(
        self,
        reports: List[OpportunityReport],
        page: int = 0,
        total_pages: int = 1,
    ) -> str:
        """Format community issue reports for admin moderation."""
        if not reports:
            return (
                "🚩 *Admin Moderation Queue — Community Issue Reports*\n\n"
                "✅ *All clean!* There are no unresolved community issue reports pending review."
            )

        lines = [
            "🚩 *Admin Moderation Queue — Community Issue Reports*",
            f"Page `{page + 1}` of `{max(1, total_pages)}` | Pending Reports: `{len(reports)}`\n",
        ]

        for idx, rep in enumerate(reports, 1):
            opp_ref = f"Opportunity ID #{rep.opportunity_id}" if rep.opportunity_id else "General Submission"
            lines.append(
                f"*{idx}. [Report #{rep.id}] Type: `{rep.report_type.upper()}`*\n"
                f"🎯 Target: {opp_ref} | Reporter User: `{rep.user_id}`\n"
                f"📝 Details: _{rep.details}_\n"
                f"📅 Reported: `{rep.created_at.strftime('%b %d, %Y %H:%M')}`\n"
                f"👉 /mod_resolve_{rep.id} | /mod_dismiss_{rep.id}\n"
            )
        lines.append("💡 *Actions:* Tap the actions below to resolve, dismiss, or expire opportunities.")
        return "\n".join(lines)

    def format_academic_resource_card(self, res: AcademicResource) -> str:
        """Format vetted legal educational resource card with copyright and open licensing."""
        desc = res.description or "High-quality academic reference and technical study material."
        verified_date = res.last_verified_at.strftime("%b %d, %Y") if res.last_verified_at else "Recently"

        lines = [
            f"📖 *{res.title}*",
            f"🏛️ *Institution / Provider:* {res.provider_institution}",
            f"🔬 *Discipline:* `{res.stem_discipline}`",
            f"🏷️ *Resource Type:* `{res.resource_type.replace('_', ' ').title()}`",
            f"⚖️ *License:* `{res.license_type}`",
            "🛡️ *Copyright Status:* `Verified Open Access / Free Legal Material`\n",
            "📝 *Overview:*",
            f"{desc}\n",
            f"🗓️ *Last Verified:* `{verified_date}`\n",
            "ℹ️ *Copyright Policy:*\n"
            "_STEM RADAR strictly indexes authorized open educational resources, official university lecture "
            "materials, and legal open-access publications. We never distribute pirated or restricted content._",
        ]
        return "\n".join(lines)


student_hub_service = StudentHubService()
