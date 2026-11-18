"""Telegram bot handlers and callback routers for Student Hub and scholarship discovery."""

import logging
import math
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.filters.auth import admin_only, authorized_only
from app.bot.keyboards.navigation import nav_back_home_row
from app.bot.keyboards.student_hub import (
    get_academic_resource_detail_keyboard,
    get_academic_resources_keyboard,
    get_country_filter_keyboard,
    get_funding_filter_keyboard,
    get_moderation_dashboard_keyboard,
    get_moderation_report_keyboard,
    get_moderation_submission_keyboard,
    get_report_options_keyboard,
    get_scholarship_detail_keyboard,
    get_scholarships_filter_keyboard,
    get_student_hub_keyboard,
    get_study_level_keyboard,
    get_submission_guide_keyboard,
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
    country: str = "all",
    opp_type: str = "scholarship",
    is_edit: bool = True,
) -> None:
    """Fetch and render paginated opportunities list with multi-criteria filtering."""
    type_labels = {
        "scholarship": "Scholarships",
        "internship": "Internships & Fellowships",
        "grant": "Grants & Seed Funding",
        "competition": "STEM Competitions",
        "research_opp": "Research Opportunities",
    }
    type_label = type_labels.get(opp_type, "Scholarships")

    country_arg = country if country != "all" else None
    total_count = await student_hub_service.count_scholarships(
        study_level=level if level != "all" else None,
        funding_type=funding if funding != "all" else None,
        country=country_arg,
        opportunity_type=opp_type,
        active_only=True,
    )
    total_pages = max(1, math.ceil(total_count / SCHOLARSHIPS_PER_PAGE))
    safe_page = max(0, min(page, total_pages - 1))

    opportunities = await student_hub_service.get_scholarships(
        study_level=level if level != "all" else None,
        funding_type=funding if funding != "all" else None,
        country=country_arg,
        opportunity_type=opp_type,
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
        country_filter=country,
        type_label=type_label,
    )

    markup = get_scholarships_filter_keyboard(
        opportunities=opportunities,
        page=safe_page,
        total_pages=total_pages,
        level=level,
        funding=funding,
        country=country,
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
        await render_scholarships_view(update, page=0, level="all", funding="all", country="all", is_edit=True)
        return

    # 3. View Deadlines Tracker
    if data == "hub:deadlines":
        await deadlines_command(update, context)
        return

    # 4. Paginated scholarship navigation: hub:sch_page:<page>:<level>:<funding>[:<country>]
    if data.startswith("hub:sch_page:"):
        parts = data.split(":")
        page = int(parts[2]) if len(parts) > 2 else 0
        level = parts[3] if len(parts) > 3 else "all"
        funding = parts[4] if len(parts) > 4 else "all"
        country = parts[5] if len(parts) > 5 else "all"
        await render_scholarships_view(update, page=page, level=level, funding=funding, country=country, is_edit=True)
        return

    # 5. Level filter picker: hub:pick_level:<page>:<level>:<funding>[:<country>]
    if data.startswith("hub:pick_level:"):
        parts = data.split(":")
        page = int(parts[2]) if len(parts) > 2 else 0
        funding = parts[4] if len(parts) > 4 else "all"
        country = parts[5] if len(parts) > 5 else "all"
        text = "*Filter by Study Level*\n\nSelect a degree level:"
        markup = get_study_level_keyboard(page=page, current_funding=funding, current_country=country)
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return

    # 6. Funding filter picker: hub:pick_funding:<page>:<level>:<funding>[:<country>]
    if data.startswith("hub:pick_funding:"):
        parts = data.split(":")
        page = int(parts[2]) if len(parts) > 2 else 0
        level = parts[3] if len(parts) > 3 else "all"
        country = parts[5] if len(parts) > 5 else "all"
        text = "*Filter by Funding*\n\nSelect a funding type:"
        markup = get_funding_filter_keyboard(page=page, current_level=level, current_country=country)
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return

    # 6b. Country filter picker: hub:pick_country:<page>:<level>:<funding>[:<country>]
    if data.startswith("hub:pick_country:"):
        parts = data.split(":")
        page = int(parts[2]) if len(parts) > 2 else 0
        level = parts[3] if len(parts) > 3 else "all"
        funding = parts[4] if len(parts) > 4 else "all"
        text = "*Filter by Country*\n\nSelect a host country:"
        markup = get_country_filter_keyboard(page=page, current_level=level, current_funding=funding)
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return

    # 7. Opportunity Detailed Card: hub:view:<slug>
    if data.startswith("hub:view:"):
        slug = data.split(":", 2)[2]
        opp = await student_hub_service.get_opportunity_by_slug(slug)
        if not opp:
            await safe_edit_or_reply(
                update,
                "*Opportunity Not Found*\n\nThis listing may have expired or been archived.",
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
        text = "*Report Listing Issue*\n\nSelect the issue you noticed with this opportunity:"
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
            "*Report Submitted*\n\n"
            "Moderators will review the official provider source and update or archive this listing.\n\n"
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
                "*University Profile Not Found*\n\nThis institution profile is unavailable.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        card_text = student_hub_service.format_university_card(uni)
        card_markup = get_university_detail_keyboard(uni, back_target="hub:admissions")
        await safe_edit_or_reply(update, card_text, reply_markup=card_markup, parse_mode=ParseMode.MARKDOWN)
        return

    # 11. Free Courses & Academic Learning Materials
    if data == "hub:courses":
        await render_academic_resources_view(update, page=0, res_type="free_course", discipline="all", is_edit=True)
        return

    if data == "hub:materials":
        await render_academic_resources_view(
            update, page=0, res_type="lecture_materials", discipline="all", is_edit=True
        )
        return

    if data in ("hub:resources", "hub:academic_resources"):
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
                "*Academic Resource Not Found*\n\nThis material record is unavailable.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        card_text = student_hub_service.format_academic_resource_card(res)
        card_markup = get_academic_resource_detail_keyboard(res, back_target="hub:courses")
        await safe_edit_or_reply(update, card_text, reply_markup=card_markup, parse_mode=ParseMode.MARKDOWN)
        return

    # 12. Internships, Fellowships, Grants, Competitions & Research Opportunities
    if data == "hub:internships":
        await render_scholarships_view(update, page=0, level="all", funding="all", opp_type="internship", is_edit=True)
        return

    if data == "hub:grants":
        await render_scholarships_view(update, page=0, level="all", funding="all", opp_type="grant", is_edit=True)
        return

    if data == "hub:competitions":
        await render_scholarships_view(update, page=0, level="all", funding="all", opp_type="competition", is_edit=True)
        return

    if data == "hub:research_opps":
        await render_scholarships_view(
            update, page=0, level="all", funding="all", opp_type="research_opp", is_edit=True
        )
        return

    if data == "hub:report_start":
        text = (
            "*Report an Issue or Outdated Listing*\n\n"
            "- Specific listing: Open the opportunity card and select *Report Issue*.\n"
            "- General feedback: Run `/feedback <your message>`.\n\n"
            "Moderators verify every report against official institutional sources."
        )
        markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Browse Scholarships", callback_data="hub:scholarships")],
                nav_back_home_row(back_target="hub:student_hub", home_target="menu:home"),
            ]
        )
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return

    if data in ("hub:submit_start", "hub:submit_guide", "hub:submit_template"):
        text = (
            "*Submit an Academic Opportunity*\n\n"
            "Submissions are verified by moderators against official institutional sources before publication.\n\n"
            "Command format:\n"
            "`/submit_opportunity Title | Provider | Official URL | Country | Level | Funding`\n\n"
            "Example:\n"
            "`/submit_opportunity CERN Fellowship | CERN | https://cern.ch | Switzerland | masters | fully_funded`\n\n"
            "Levels: undergraduate, masters, phd, postdoctoral\n"
            "Funding: fully_funded, partially_funded"
        )
        markup = get_submission_guide_keyboard()
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return

    if data == "hub:noop":
        return


# ------------------ Stage 16: Moderation & Submission Handlers ------------------


@authorized_only
async def submit_opportunity_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Public submission command allowing community contributors to submit opportunities for review."""
    user = update.effective_user
    user_id = user.id if user else 0
    raw_text = " ".join(context.args) if context.args else ""
    if not raw_text or "|" not in raw_text:
        text = (
            "*Submit an Academic Opportunity*\n\n"
            "Submissions are verified by moderators against official institutional sources before publication.\n\n"
            "Format:\n"
            "`/submit_opportunity Title | Provider | Official URL | Country | Level | Funding`\n\n"
            "Example:\n"
            "`/submit_opportunity CERN Fellowship | CERN | https://cern.ch | Switzerland | masters | fully_funded`\n\n"
            "Levels: undergraduate, masters, phd, postdoctoral\n"
            "Funding: fully_funded, partially_funded"
        )
        markup = get_submission_guide_keyboard()
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return

    parts = [p.strip() for p in raw_text.split("|")]
    if len(parts) < 6:
        text = (
            "*Incomplete Submission Format*\n\n"
            "Provide all 6 fields separated by vertical bars (`|`):\n"
            "`Title | Provider | Official URL | Country | Level | Funding`"
        )
        await safe_edit_or_reply(update, text, parse_mode=ParseMode.MARKDOWN)
        return

    title, provider, url, country, level, funding = parts[:6]
    success, opp, msg = await student_hub_service.submit_public_opportunity(
        user_id=user_id,
        title=title,
        provider_name=provider,
        official_url=url,
        country=country,
        study_level=level.lower(),
        funding_type=funding.lower(),
    )
    if success and opp:
        text = (
            f"*Submission Received (ID #{opp.id})*\n\n"
            f"*{opp.title}*\n"
            f"Provider: {opp.provider_name} ({opp.country})\n"
            f"Level: {opp.study_level.capitalize()} · Funding: {opp.funding_type}\n"
            f"[Official Announcement]({opp.official_url})\n\n"
            f"_{msg}_"
        )
    else:
        text = f"*Submission Error*\n\n{msg}"
    await safe_edit_or_reply(update, text, parse_mode=ParseMode.MARKDOWN)


@admin_only
async def moderation_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin moderation center for approving submissions and handling community reports."""
    await render_moderation_dashboard(update, is_edit=False)


async def render_moderation_dashboard(update: Update, is_edit: bool = False) -> None:
    """Render the central admin moderation dashboard."""
    pending_subs = await student_hub_service.count_pending_submissions()
    pending_reps = await student_hub_service.count_moderation_reports(status="pending_review")
    text = (
        "*Moderation Center*\n\n"
        f"Pending submissions: {pending_subs}\n"
        f"Open community reports: {pending_reps}\n\n"
        "*Verification Standards*\n"
        "- Live listings must link to official institutional sources.\n"
        "- Expired deadlines must be moved out of active listings.\n"
        "- Unverified or fraudulent listings must be rejected."
    )
    markup = get_moderation_dashboard_keyboard(pending_subs, pending_reps)
    await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)


async def render_pending_submissions_view(update: Update, page: int = 0, is_edit: bool = True) -> None:
    """Render paginated list of pending submissions with inline review actions."""
    limit = 1
    total = await student_hub_service.count_pending_submissions()
    total_pages = max(1, total)
    safe_page = max(0, min(page, total_pages - 1))

    subs = await student_hub_service.get_pending_submissions(limit=limit, offset=safe_page)
    if not subs:
        text = "*Pending Submissions*\n\nNo unverified opportunity submissions are waiting for review."
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("Moderation Hub", callback_data="mod:dash")]])
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return

    opp = subs[0]
    dl_str = opp.application_deadline.strftime("%d %b %Y") if opp.application_deadline else "Rolling"
    text = (
        f"*Submission Review #{opp.id}* ({safe_page + 1} of {total_pages})\n\n"
        f"*{opp.title}*\n"
        f"Provider: {opp.provider_name} ({opp.country})\n"
        f"Level: {opp.study_level.capitalize()} · Funding: {opp.funding_type}\n"
        f"Fields: {opp.stem_fields}\n"
        f"Deadline: {dl_str}\n"
        f"Link: [Official Announcement]({opp.official_url})\n"
        f"Source: {opp.source_attribution}\n\n"
        "Select a moderation action:"
    )
    markup = get_moderation_submission_keyboard(opp.id, page=safe_page, total_pages=total_pages)
    await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)


async def render_moderation_reports_view(update: Update, page: int = 0, is_edit: bool = True) -> None:
    """Render paginated list of community reports with corrective actions."""
    limit = 1
    total = await student_hub_service.count_moderation_reports(status="pending_review")
    total_pages = max(1, total)
    safe_page = max(0, min(page, total_pages - 1))

    reports = await student_hub_service.get_moderation_reports(status="pending_review", limit=limit, offset=safe_page)
    if not reports:
        text = "*Community Issue Reports*\n\nNo unresolved community issue reports are pending review."
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("Moderation Hub", callback_data="mod:dash")]])
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return

    rep = reports[0]
    opp_ref = f"Opportunity #{rep.opportunity_id}" if rep.opportunity_id else "General submission"
    text = (
        f"*Community Report #{rep.id}* ({safe_page + 1} of {total_pages})\n\n"
        f"Type: {rep.report_type.upper()}\n"
        f"Target: {opp_ref}\n"
        f"Reporter ID: `{rep.user_id}`\n"
        f"Reported: {rep.created_at.strftime('%d %b %Y, %H:%M UTC')}\n\n"
        f"*Details*\n{rep.details}\n\n"
        "Select a resolution action:"
    )
    markup = get_moderation_report_keyboard(
        rep.id, opportunity_id=rep.opportunity_id, page=safe_page, total_pages=total_pages
    )
    await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)


@admin_only
async def moderation_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback router handling admin moderation actions and report resolutions."""
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data
    user = update.effective_user
    user_id = user.id if user else 1

    if is_duplicate_callback(user_id, data):
        await query.answer()
        return

    await query.answer()

    if data == "mod:dash":
        await render_moderation_dashboard(update, is_edit=True)
        return

    if data.startswith("mod:subs:"):
        page = int(data.split(":")[2])
        await render_pending_submissions_view(update, page=page, is_edit=True)
        return

    if data.startswith("mod:appr_v:"):
        parts = data.split(":")
        opp_id = int(parts[2])
        page = int(parts[3])
        await student_hub_service.approve_opportunity(
            opportunity_id=opp_id,
            admin_user_id=user_id,
            verification_tier="officially_verified",
        )
        await render_pending_submissions_view(update, page=page, is_edit=True)
        return

    if data.startswith("mod:appr_s:"):
        parts = data.split(":")
        opp_id = int(parts[2])
        page = int(parts[3])
        await student_hub_service.approve_opportunity(
            opportunity_id=opp_id,
            admin_user_id=user_id,
            verification_tier="secondary_verified",
        )
        await render_pending_submissions_view(update, page=page, is_edit=True)
        return

    if data.startswith("mod:rej:"):
        parts = data.split(":")
        opp_id = int(parts[2])
        page = int(parts[3])
        await student_hub_service.reject_opportunity(
            opportunity_id=opp_id,
            admin_user_id=user_id,
        )
        await render_pending_submissions_view(update, page=page, is_edit=True)
        return

    if data.startswith("mod:reps:"):
        page = int(data.split(":")[2])
        await render_moderation_reports_view(update, page=page, is_edit=True)
        return

    if data.startswith("mod:rep_exp:"):
        parts = data.split(":")
        rep_id = int(parts[2])
        page = int(parts[3])
        await student_hub_service.resolve_report(
            report_id=rep_id,
            admin_user_id=user_id,
            resolution="verified_resolved",
            action_taken="expire_opportunity",
        )
        await render_moderation_reports_view(update, page=page, is_edit=True)
        return

    if data.startswith("mod:rep_res:"):
        parts = data.split(":")
        rep_id = int(parts[2])
        page = int(parts[3])
        await student_hub_service.resolve_report(
            report_id=rep_id,
            admin_user_id=user_id,
            resolution="verified_resolved",
        )
        await render_moderation_reports_view(update, page=page, is_edit=True)
        return

    if data.startswith("mod:rep_dsm:"):
        parts = data.split(":")
        rep_id = int(parts[2])
        page = int(parts[3])
        await student_hub_service.resolve_report(
            report_id=rep_id,
            admin_user_id=user_id,
            resolution="dismissed",
        )
        await render_moderation_reports_view(update, page=page, is_edit=True)
        return

    if data == "mod:sweep":
        count = await student_hub_service.expire_lapsed_opportunities()
        text = (
            "*Expiry Sweep Complete*\n\n"
            f"Transitioned {count} lapsed opportunities to expired.\n\n"
            "Expired listings have been excluded from active views."
        )
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("Moderation Hub", callback_data="mod:dash")]])
        await safe_edit_or_reply(update, text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        return


# ------------------ Quick Deep-Link Commands ------------------


@authorized_only
async def quick_opportunity_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle direct deep-link commands like /scholarship_42 or /opp_42."""
    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text.strip()
    match = re.search(r"/(?:scholarship|opp)_(\d+)", text)
    if not match:
        return

    opp_id = int(match.group(1))
    opp = await student_hub_service.get_opportunity_by_id(opp_id)
    if not opp:
        await message.reply_text(
            "*Opportunity Not Found*\n\nThis listing may have expired or been archived.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    card_text = student_hub_service.format_scholarship_card(opp)
    card_markup = get_scholarship_detail_keyboard(opp, back_target="hub:scholarships")
    await message.reply_text(card_text, reply_markup=card_markup, parse_mode=ParseMode.MARKDOWN)


@authorized_only
async def quick_university_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle direct deep-link commands like /university_<slug>."""
    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text.strip()
    match = re.search(r"/university_([a-zA-Z0-9_\-]+)", text)
    if not match:
        return

    slug = match.group(1)
    uni = await student_hub_service.get_university_by_slug(slug)
    if not uni:
        await message.reply_text(
            "*University Profile Not Found*\n\nThis institution profile is unavailable.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    card_text = student_hub_service.format_university_card(uni)
    card_markup = get_university_detail_keyboard(uni, back_target="hub:admissions")
    await message.reply_text(card_text, reply_markup=card_markup, parse_mode=ParseMode.MARKDOWN)


@authorized_only
async def quick_resource_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle direct deep-link commands like /resource_<slug>."""
    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text.strip()
    match = re.search(r"/resource_([a-zA-Z0-9_\-]+)", text)
    if not match:
        return

    slug = match.group(1)
    res = await student_hub_service.get_academic_resource_by_slug(slug)
    if not res:
        await message.reply_text(
            "*Academic Resource Not Found*\n\nThis material record is unavailable.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    card_text = student_hub_service.format_academic_resource_card(res)
    card_markup = get_academic_resource_detail_keyboard(res, back_target="hub:courses")
    await message.reply_text(card_text, reply_markup=card_markup, parse_mode=ParseMode.MARKDOWN)
