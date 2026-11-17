"""Telegram bot handlers and callback routers for Student Hub and scholarship discovery."""

import logging
import math

from telegram import InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.filters.auth import authorized_only
from app.bot.keyboards.navigation import nav_back_home_row
from app.bot.keyboards.student_hub import (
    get_academic_resource_detail_keyboard,
    get_academic_resources_keyboard,
    get_funding_filter_keyboard,
    get_report_options_keyboard,
    get_scholarship_detail_keyboard,
    get_scholarships_filter_keyboard,
    get_student_hub_keyboard,
    get_study_level_keyboard,
    get_universities_keyboard,
    get_university_detail_keyboard,
)
from app.bot.ui.menu import is_duplicate_callback, safe_edit_or_reply
from app.services.student_hub_service import student_hub_service

logger = logging.getLogger(__name__)
SCHOLARSHIPS_PER_PAGE = 4


@authorized_only
async def student_hub_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entrypoint command for the Student Hub dashboard."""
    text = student_hub_service.format_student_hub_intro()
    markup = get_student_hub_keyboard()
    await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)


@authorized_only
async def scholarships_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display verified scholarship listings with interactive filters."""
    await render_scholarships_view(update, page=0, level="all", funding="all", is_edit=False)


@authorized_only
async def deadlines_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display upcoming scholarship and academic application deadlines."""
    deadlines = await student_hub_service.get_upcoming_deadlines(limit=8)
    text = student_hub_service.format_deadline_tracker(deadlines)
    markup = InlineKeyboardMarkup(
        [
            nav_back_home_row(back_target="hub:scholarships", home_target="menu:home"),
        ]
    )
    await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)


@authorized_only
async def universities_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display accredited university admissions guidelines and portals."""
    await render_universities_view(update, page=0, country="all", is_edit=False)


@authorized_only
async def courses_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display free online STEM courses and study materials."""
    await render_academic_resources_view(update, page=0, res_type="all", discipline="all", is_edit=False)


async def render_universities_view(
    update: Update,
    page: int = 0,
    country: str = "all",
    is_edit: bool = True,
) -> None:
    """Fetch and render paginated university profiles."""
    total_count = await student_hub_service.count_university_profiles(country=country if country != "all" else None)
    total_pages = max(1, math.ceil(total_count / SCHOLARSHIPS_PER_PAGE))
    safe_page = max(0, min(page, total_pages - 1))

    unis = await student_hub_service.get_university_profiles(
        country=country if country != "all" else None,
        limit=SCHOLARSHIPS_PER_PAGE,
        offset=safe_page * SCHOLARSHIPS_PER_PAGE,
    )

    text = student_hub_service.format_universities_list(
        universities=unis,
        page=safe_page,
        total_pages=total_pages,
        country_filter=country,
    )

    markup = get_universities_keyboard(
        universities=unis,
        page=safe_page,
        total_pages=total_pages,
        country=country,
    )
    await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)


async def render_academic_resources_view(
    update: Update,
    page: int = 0,
    res_type: str = "all",
    discipline: str = "all",
    is_edit: bool = True,
) -> None:
    """Fetch and render paginated legal educational resources."""
    total_count = await student_hub_service.count_academic_resources(
        resource_type=res_type if res_type != "all" else None,
        stem_discipline=discipline if discipline != "all" else None,
    )
    total_pages = max(1, math.ceil(total_count / SCHOLARSHIPS_PER_PAGE))
    safe_page = max(0, min(page, total_pages - 1))

    resources = await student_hub_service.get_academic_resources(
        resource_type=res_type if res_type != "all" else None,
        stem_discipline=discipline if discipline != "all" else None,
        limit=SCHOLARSHIPS_PER_PAGE,
        offset=safe_page * SCHOLARSHIPS_PER_PAGE,
    )

    text = student_hub_service.format_academic_resources_list(
        resources=resources,
        page=safe_page,
        total_pages=total_pages,
        type_filter=res_type,
        discipline_filter=discipline,
    )

    markup = get_academic_resources_keyboard(
        resources=resources,
        page=safe_page,
        total_pages=total_pages,
        res_type=res_type,
        discipline=discipline,
    )
    await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)


async def render_scholarships_view(
    update: Update,
    page: int = 0,
    level: str = "all",
    funding: str = "all",
    is_edit: bool = True,
) -> None:
    """Fetch and render paginated scholarships list."""
    total_count = await student_hub_service.count_scholarships(
        study_level=level if level != "all" else None,
        funding_type=funding if funding != "all" else None,
        active_only=True,
    )
    total_pages = max(1, math.ceil(total_count / SCHOLARSHIPS_PER_PAGE))
    safe_page = max(0, min(page, total_pages - 1))

    opportunities = await student_hub_service.get_scholarships(
        study_level=level if level != "all" else None,
        funding_type=funding if funding != "all" else None,
        active_only=True,
        limit=SCHOLARSHIPS_PER_PAGE,
        offset=safe_page * SCHOLARSHIPS_PER_PAGE,
    )

    text = student_hub_service.format_scholarships_list(
        opportunities=opportunities,
        page=safe_page,
        total_pages=total_pages,
        level_filter=level,
        funding_filter=funding,
    )

    markup = get_scholarships_filter_keyboard(
        opportunities=opportunities,
        page=safe_page,
        total_pages=total_pages,
        level=level,
        funding=funding,
    )

    await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)


@authorized_only
async def student_hub_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route all hub:* interactive callback submissions."""
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data
    user = update.effective_user
    user_id = user.id if user else 0

    if is_duplicate_callback(user_id, data):
        await query.answer()
        return

    await query.answer()

    # 1. Main Hub launcher
    if data in ("hub:student_hub", "hub:home", "menu:student_hub"):
        text = student_hub_service.format_student_hub_intro()
        markup = get_student_hub_keyboard()
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return

    # 2. Browse Scholarships
    if data in ("hub:scholarships", "menu:scholarships"):
        await render_scholarships_view(update, page=0, level="all", funding="all", is_edit=True)
        return

    # 3. View Deadlines Tracker
    if data == "hub:deadlines":
        await deadlines_command(update, context)
        return

    # 4. Paginated scholarship navigation: hub:sch_page:<page>:<level>:<funding>
    if data.startswith("hub:sch_page:"):
        parts = data.split(":")
        page = int(parts[2]) if len(parts) > 2 else 0
        level = parts[3] if len(parts) > 3 else "all"
        funding = parts[4] if len(parts) > 4 else "all"
        await render_scholarships_view(update, page=page, level=level, funding=funding, is_edit=True)
        return

    # 5. Level filter picker: hub:pick_level:<page>:<level>:<funding>
    if data.startswith("hub:pick_level:"):
        parts = data.split(":")
        page = int(parts[2]) if len(parts) > 2 else 0
        funding = parts[4] if len(parts) > 4 else "all"
        text = "🎯 *Select Academic Degree Level Filter:*\n\nChoose the target degree level to refine available awards:"
        markup = get_study_level_keyboard(page=page, current_funding=funding)
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return

    # 6. Funding filter picker: hub:pick_funding:<page>:<level>:<funding>
    if data.startswith("hub:pick_funding:"):
        parts = data.split(":")
        page = int(parts[2]) if len(parts) > 2 else 0
        level = parts[3] if len(parts) > 3 else "all"
        text = "💰 *Select Financial Coverage Filter:*\n\nChoose the funding package to filter scholarship results:"
        markup = get_funding_filter_keyboard(page=page, current_level=level)
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return

    # 7. Opportunity Detailed Card: hub:view:<slug>
    if data.startswith("hub:view:"):
        slug = data.split(":", 2)[2]
        opp = await student_hub_service.get_opportunity_by_slug(slug)
        if not opp:
            await safe_edit_or_reply(
                update,
                "⚠️ *Opportunity Not Found*\n\nThis listing may have expired or been archived.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        card_text = student_hub_service.format_scholarship_card(opp)
        card_markup = get_scholarship_detail_keyboard(opp, back_target="hub:scholarships")
        await safe_edit_or_reply(update, card_text, reply_markup=card_markup, parse_mode=ParseMode.MARKDOWN)
        return

    # 8. Report start: hub:report:<id>
    if data.startswith("hub:report:"):
        opp_id = int(data.split(":")[2])
        text = (
            "🚩 *Community Trust & Listing Issue Report*\n\n"
            "Help maintain 100% verified accuracy across STEM RADAR listings.\n"
            "Select the issue you observed with this opportunity:"
        )
        markup = get_report_options_keyboard(opportunity_id=opp_id)
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return

    # 9. Execute Report: hub:do_rep:<id>:<report_type>
    if data.startswith("hub:do_rep:"):
        parts = data.split(":")
        opp_id = int(parts[2])
        rep_type = parts[3]
        success, msg = await student_hub_service.report_opportunity(
            user_id=user_id,
            opportunity_id=opp_id,
            report_type=rep_type,
            details=f"Community flag: {rep_type}",
        )
        confirm_text = (
            "✅ *Thank You for Your Report*\n\n"
            "Our moderators will inspect the official provider source and update or archive the listing promptly.\n\n"
            f"_{msg}_"
        )
        markup = InlineKeyboardMarkup([nav_back_home_row(back_target="hub:scholarships", home_target="menu:home")])
        await safe_edit_or_reply(update, confirm_text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return

    # 10. University Admissions & Guidelines Directory
    if data in ("hub:admissions", "hub:guidelines", "hub:universities"):
        await render_universities_view(update, page=0, country="all", is_edit=True)
        return

    if data.startswith("hub:uni_page:"):
        parts = data.split(":")
        page = int(parts[2]) if len(parts) > 2 else 0
        country = parts[3] if len(parts) > 3 else "all"
        await render_universities_view(update, page=page, country=country, is_edit=True)
        return

    if data.startswith("hub:uni_view:"):
        slug = data.split(":", 2)[2]
        uni = await student_hub_service.get_university_by_slug(slug)
        if not uni:
            await safe_edit_or_reply(
                update,
                "⚠️ *University Profile Not Found*\n\nThis institution profile is unavailable.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        card_text = student_hub_service.format_university_card(uni)
        card_markup = get_university_detail_keyboard(uni, back_target="hub:admissions")
        await safe_edit_or_reply(update, card_text, reply_markup=card_markup, parse_mode=ParseMode.MARKDOWN)
        return

    # 11. Free Courses & Academic Learning Materials
    if data in ("hub:courses", "hub:materials", "hub:resources"):
        await render_academic_resources_view(update, page=0, res_type="all", discipline="all", is_edit=True)
        return

    if data.startswith("hub:res_page:"):
        parts = data.split(":")
        page = int(parts[2]) if len(parts) > 2 else 0
        res_type = parts[3] if len(parts) > 3 else "all"
        discipline = parts[4] if len(parts) > 4 else "all"
        await render_academic_resources_view(update, page=page, res_type=res_type, discipline=discipline, is_edit=True)
        return

    if data.startswith("hub:res_view:"):
        slug = data.split(":", 2)[2]
        res = await student_hub_service.get_academic_resource_by_slug(slug)
        if not res:
            await safe_edit_or_reply(
                update,
                "⚠️ *Academic Resource Not Found*\n\nThis material record is unavailable.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        card_text = student_hub_service.format_academic_resource_card(res)
        card_markup = get_academic_resource_detail_keyboard(res, back_target="hub:courses")
        await safe_edit_or_reply(update, card_text, reply_markup=card_markup, parse_mode=ParseMode.MARKDOWN)
        return

    # 12. Preview Placeholders for remaining Student Hub sections (Internships, Competitions, etc.)
    section_titles = {
        "hub:internships": (
            "💼 Internships & Fellowships",
            "Hands-on engineering fellowships and corporate STEM internships.",
        ),
        "hub:research_opps": (
            "🔬 Research Opportunities",
            "Funded lab positions, research grants, and conference paper calls.",
        ),
        "hub:competitions": (
            "🏆 STEM Competitions",
            "Hackathons, robotics challenges, and international Olympiads.",
        ),
        "hub:grants": (
            "💰 Grants & Seed Funding",
            "Research project grants, student travel stipends, and hardware subsidies.",
        ),
        "hub:report_start": (
            "🚩 Report an Opportunity",
            "Report broken links or outdated deadlines across any listing.",
        ),
        "hub:submit_start": (
            "➕ Submit an Opportunity",
            "Submit an official university scholarship or competition for moderator review.",
        ),
    }

    if data in section_titles:
        title, desc = section_titles[data]
        text = f"*{title}*\n\n{desc}\n\n💡 *Coming Soon:* Curated guides, alerts, and checklists."
        markup = InlineKeyboardMarkup([nav_back_home_row(back_target="hub:student_hub", home_target="menu:home")])
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return

    if data == "hub:noop":
        return
