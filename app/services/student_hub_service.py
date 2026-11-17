"""Service layer for Student Hub, scholarship discovery, filtering, and deadline tracking."""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from app.database.database import get_session_factory
from app.database.models import AcademicResource, Opportunity, UniversityProfile
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
        active_only: bool = True,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Opportunity]:
        """Fetch verified scholarships with optional faceted filtering."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.get_opportunities(
                opportunity_type="scholarship",
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
        active_only: bool = True,
    ) -> int:
        """Count scholarships matching active filters for pagination."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.count_opportunities(
                opportunity_type="scholarship",
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
    ) -> str:
        """Format an interactive paginated list of scholarships."""
        if not opportunities:
            return (
                "🎁 *Verified STEM Scholarships*\n\n"
                f"No scholarships found for (`Level: {level_filter}`, `Funding: {funding_filter}`).\n\n"
                "Tap *Reset Filters* below or browse all opportunities."
            )

        lines = [
            "🎁 *Verified STEM Scholarships*",
            f"Showing Page `{page + 1}` of `{max(1, total_pages)}` | "
            f"Level: `{level_filter.upper()}` | Funding: `{funding_filter.upper()}`\n",
        ]

        now = datetime.now(timezone.utc)
        for idx, opp in enumerate(opportunities, 1):
            tier_badge = "🟢 Verified" if opp.verification_tier == "officially_verified" else "🟡 Secondary Source"
            dl_str = "Rolling Deadline"
            deadline_utc = ensure_utc(opp.application_deadline)
            if deadline_utc:
                days_left = (deadline_utc - now).days
                if days_left > 0:
                    dl_str = f"⏰ {days_left}d left ({deadline_utc.strftime('%b %d, %Y')})"
                else:
                    dl_str = f"⏰ Today ({deadline_utc.strftime('%b %d')})"

            lines.append(
                f"*{idx}. {opp.title}*\n"
                f"🏛️ _{opp.provider_name}_ ({opp.country})\n"
                f"🎯 `{opp.study_level.upper()}` | 💰 `{opp.funding_type.replace('_', ' ').title()}` | {tier_badge}\n"
                f"{dl_str}\n"
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
        if opp.is_rolling or not deadline_utc:
            dl_str = "🔄 *Rolling Applications (Check official portal for cut-off dates)*"
        else:
            days_left = (deadline_utc - now).days
            dl_format = deadline_utc.strftime("%B %d, %Y")
            if days_left > 0:
                dl_str = f"📅 *{dl_format}* (`{days_left} days remaining`)"
            elif days_left == 0:
                dl_str = f"📅 *{dl_format}* (`Due Today!`)"
            else:
                dl_str = f"📅 *{dl_format}* (`Lapsed / Closed`)"

        benefits = (
            opp.benefits or "Refer to the official provider announcement for complete financial coverage details."
        )
        required_docs = opp.required_documents or "Official transcripts, CV, and letters of recommendation."
        verified_date = opp.last_verified_at.strftime("%b %d, %Y") if opp.last_verified_at else "Recently"

        return (
            f"🎓 *{opp.title}*\n"
            f"🏷️ *Trust Tier:* `{tier_str}`\n\n"
            f"🏛️ *Provider / Sponsor:* {opp.provider_name} ({opp.country})\n"
            f"🌍 *Eligible Nationalities:* {opp.eligible_nationalities}\n"
            f"🎯 *Study Level:* `{opp.study_level.upper()}`\n"
            f"🔬 *Eligible Disciplines:* `{opp.stem_fields}`\n"
            f"💰 *Funding Structure:* `{opp.funding_type.replace('_', ' ').upper()}`\n\n"
            f"✨ *Benefits & Financial Coverage:*\n{benefits}\n\n"
            f"📋 *Eligibility Criteria:*\n{opp.eligibility_criteria}\n\n"
            f"📁 *Required Application Documents:*\n{required_docs}\n\n"
            f"⏰ *Application Deadline:*\n{dl_str}\n\n"
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
