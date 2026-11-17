"""Inline keyboards for Student Hub, scholarship filters, deadline tracking, and trust actions."""

from typing import List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.navigation import nav_back_home_row
from app.database.models import AcademicResource, Opportunity, UniversityProfile


def get_student_hub_keyboard() -> InlineKeyboardMarkup:
    """Flagship 10-section sub-menu for the Student Hub."""
    buttons = [
        [
            InlineKeyboardButton("🎁 Scholarships", callback_data="hub:scholarships"),
            InlineKeyboardButton("⏰ Deadlines Tracker", callback_data="hub:deadlines"),
        ],
        [
            InlineKeyboardButton("🏛️ University Admissions", callback_data="hub:admissions"),
            InlineKeyboardButton("📋 University Guidelines", callback_data="hub:guidelines"),
        ],
        [
            InlineKeyboardButton("💼 Internships & Fellowships", callback_data="hub:internships"),
            InlineKeyboardButton("🔬 Research Opportunities", callback_data="hub:research_opps"),
        ],
        [
            InlineKeyboardButton("💻 Free Online Courses", callback_data="hub:courses"),
            InlineKeyboardButton("📖 Study Materials", callback_data="hub:materials"),
        ],
        [
            InlineKeyboardButton("🏆 STEM Competitions", callback_data="hub:competitions"),
            InlineKeyboardButton("💰 Grants & Funding", callback_data="hub:grants"),
        ],
        [
            InlineKeyboardButton("🚩 Report Issue / Expired Link", callback_data="hub:report_start"),
            InlineKeyboardButton("➕ Submit Opportunity", callback_data="hub:submit_start"),
        ],
        nav_back_home_row(back_target="menu:home", home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(buttons)


def get_scholarships_filter_keyboard(
    opportunities: List[Opportunity],
    page: int = 0,
    total_pages: int = 1,
    level: str = "all",
    funding: str = "all",
) -> InlineKeyboardMarkup:
    """Interactive paginated scholarship browser with level and funding filter chips."""
    buttons: List[List[InlineKeyboardButton]] = []

    # Individual Opportunity Quick-Select Cards
    for idx, opp in enumerate(opportunities, 1):
        btn_title = f"{idx}. {opp.title[:38]}..."
        buttons.append([InlineKeyboardButton(btn_title, callback_data=f"hub:view:{opp.slug}")])

    # Filter selector controls
    level_label = f"🎯 Level: {level.capitalize() if level != 'all' else 'All'}"
    funding_label = f"💰 Funding: {funding.replace('_', ' ').capitalize() if funding != 'all' else 'All'}"
    buttons.append(
        [
            InlineKeyboardButton(level_label, callback_data=f"hub:pick_level:{page}:{level}:{funding}"),
            InlineKeyboardButton(funding_label, callback_data=f"hub:pick_funding:{page}:{level}:{funding}"),
        ]
    )

    # Pagination navigation
    nav_row: List[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"hub:sch_page:{page - 1}:{level}:{funding}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page + 1}/{max(1, total_pages)}", callback_data="hub:noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"hub:sch_page:{page + 1}:{level}:{funding}"))
    buttons.append(nav_row)

    # Action row (Reset Filters & Deadlines)
    buttons.append(
        [
            InlineKeyboardButton("🔄 Reset Filters", callback_data="hub:sch_page:0:all:all"),
            InlineKeyboardButton("⏰ View Deadlines", callback_data="hub:deadlines"),
        ]
    )

    # Back / Home
    buttons.append(nav_back_home_row(back_target="menu:student_hub", home_target="menu:home"))
    return InlineKeyboardMarkup(buttons)


def get_scholarship_detail_keyboard(
    opportunity: Opportunity,
    back_target: str = "hub:scholarships",
) -> InlineKeyboardMarkup:
    """Card keyboard with verified official external links and community reporting."""
    rows: List[List[InlineKeyboardButton]] = []

    # Official Action Links
    link_buttons: List[InlineKeyboardButton] = []
    if opportunity.official_url:
        link_buttons.append(InlineKeyboardButton("🔗 Official Announcement", url=opportunity.official_url))
    if opportunity.application_url:
        link_buttons.append(InlineKeyboardButton("📝 Apply Online", url=opportunity.application_url))
    if link_buttons:
        rows.append(link_buttons)

    # Trust & Reporting button
    rows.append(
        [
            InlineKeyboardButton("🚩 Report Issue / Expired Link", callback_data=f"hub:report:{opportunity.id}"),
        ]
    )

    # Navigation
    rows.append(nav_back_home_row(back_target=back_target, home_target="menu:home"))
    return InlineKeyboardMarkup(rows)


def get_study_level_keyboard(page: int, current_funding: str) -> InlineKeyboardMarkup:
    """Picker keyboard to filter by academic degree level."""
    levels = [
        ("🎓 All Study Levels", "all"),
        ("🏛️ Undergraduate (BSc)", "undergraduate"),
        ("🔬 Master's (MSc)", "masters"),
        ("🧪 Doctoral (PhD)", "phd"),
        ("🔬 Postdoctoral", "postdoctoral"),
    ]
    rows: List[List[InlineKeyboardButton]] = []
    for label, slug in levels:
        rows.append([InlineKeyboardButton(label, callback_data=f"hub:sch_page:0:{slug}:{current_funding}")])
    back_data = f"hub:sch_page:{page}:all:{current_funding}"
    rows.append([InlineKeyboardButton("⬅️ Back to Scholarships", callback_data=back_data)])
    return InlineKeyboardMarkup(rows)


def get_funding_filter_keyboard(page: int, current_level: str) -> InlineKeyboardMarkup:
    """Picker keyboard to filter by financial coverage."""
    fundings = [
        ("🌐 All Funding Types", "all"),
        ("💎 Fully Funded (Full Ride)", "fully_funded"),
        ("💵 Partially Funded", "partially_funded"),
        ("🎓 Tuition Waiver Only", "tuition_waiver"),
        ("🪙 Monthly Stipend Only", "stipend_only"),
    ]
    rows: List[List[InlineKeyboardButton]] = []
    for label, slug in fundings:
        rows.append([InlineKeyboardButton(label, callback_data=f"hub:sch_page:0:{current_level}:{slug}")])
    back_data = f"hub:sch_page:{page}:{current_level}:all"
    rows.append([InlineKeyboardButton("⬅️ Back to Scholarships", callback_data=back_data)])
    return InlineKeyboardMarkup(rows)


def get_report_options_keyboard(opportunity_id: int) -> InlineKeyboardMarkup:
    """Picker for reporting an opportunity."""
    options = [
        ("⏰ Deadline Has Passed / Expired", f"hub:do_rep:{opportunity_id}:expired"),
        ("🔗 Broken / Dead Official Link", f"hub:do_rep:{opportunity_id}:broken_link"),
        ("⚠️ Inaccurate Information / Rules", f"hub:do_rep:{opportunity_id}:inaccurate"),
        ("🚨 Suspicious / Fraudulent Listing", f"hub:do_rep:{opportunity_id}:fraudulent"),
    ]
    rows: List[List[InlineKeyboardButton]] = []
    for label, cdata in options:
        rows.append([InlineKeyboardButton(label, callback_data=cdata)])
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="hub:scholarships")])
    return InlineKeyboardMarkup(rows)


def get_universities_keyboard(
    universities: List[UniversityProfile],
    page: int = 0,
    total_pages: int = 1,
    country: str = "all",
) -> InlineKeyboardMarkup:
    """Interactive paginated university directory browser."""
    buttons: List[List[InlineKeyboardButton]] = []

    for idx, u in enumerate(universities, 1):
        btn_text = f"{idx}. {u.name[:38]}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"hub:uni_view:{u.slug}")])

    # Pagination navigation
    nav_row: List[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"hub:uni_page:{page - 1}:{country}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page + 1}/{max(1, total_pages)}", callback_data="hub:noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"hub:uni_page:{page + 1}:{country}"))
    buttons.append(nav_row)

    buttons.append(nav_back_home_row(back_target="hub:student_hub", home_target="menu:home"))
    return InlineKeyboardMarkup(buttons)


def get_university_detail_keyboard(
    uni: UniversityProfile,
    back_target: str = "hub:admissions",
) -> InlineKeyboardMarkup:
    """Card keyboard with direct verified links to official admission portals and guidelines."""
    rows: List[List[InlineKeyboardButton]] = []

    # Row 1: Admissions Portal & Official Website
    rows.append(
        [
            InlineKeyboardButton("📑 Admissions Portal", url=uni.admissions_portal_url),
            InlineKeyboardButton("🌐 Official Website", url=uni.official_portal_url),
        ]
    )

    # Row 2: Secondary guidelines if available
    row2: List[InlineKeyboardButton] = []
    if getattr(uni, "international_guidelines_url", None):
        row2.append(InlineKeyboardButton("🛂 Int'l Guidelines", url=uni.international_guidelines_url))
    if getattr(uni, "academic_regulations_url", None):
        row2.append(InlineKeyboardButton("📜 Regulations", url=uni.academic_regulations_url))
    if row2:
        rows.append(row2)

    # Row 3: Research portals if available
    row3: List[InlineKeyboardButton] = []
    if getattr(uni, "research_opportunities_url", None):
        row3.append(InlineKeyboardButton("🔬 Research Portals", url=uni.research_opportunities_url))
    if row3:
        rows.append(row3)

    rows.append(nav_back_home_row(back_target=back_target, home_target="menu:home"))
    return InlineKeyboardMarkup(rows)


def get_academic_resources_keyboard(
    resources: List[AcademicResource],
    page: int = 0,
    total_pages: int = 1,
    res_type: str = "all",
    discipline: str = "all",
) -> InlineKeyboardMarkup:
    """Interactive paginated browser for open educational resources."""
    buttons: List[List[InlineKeyboardButton]] = []

    for idx, r in enumerate(resources, 1):
        btn_text = f"{idx}. {r.title[:38]}..."
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"hub:res_view:{r.slug}")])

    # Pagination navigation
    nav_row: List[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"hub:res_page:{page - 1}:{res_type}:{discipline}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page + 1}/{max(1, total_pages)}", callback_data="hub:noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"hub:res_page:{page + 1}:{res_type}:{discipline}"))
    buttons.append(nav_row)

    buttons.append(nav_back_home_row(back_target="hub:student_hub", home_target="menu:home"))
    return InlineKeyboardMarkup(buttons)


def get_academic_resource_detail_keyboard(
    res: AcademicResource,
    back_target: str = "hub:courses",
) -> InlineKeyboardMarkup:
    """Card keyboard with direct access to open educational resources and courses."""
    rows: List[List[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton("🔗 Open Official Course / Material", url=res.official_access_url),
        ],
        nav_back_home_row(back_target=back_target, home_target="menu:home"),
    ]
    return InlineKeyboardMarkup(rows)
