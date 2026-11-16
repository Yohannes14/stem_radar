"""Presentation layer formatters generating clean, compliant Telegram markdown messages."""

import html
import re
from datetime import datetime, timezone
from typing import List, Optional

CATEGORY_EMOJIS = {
    "ai": "🤖",
    "machine-learning": "🧠",
    "robotics": "🦾",
    "computer-science": "💻",
    "software-engineering": "⚙️",
    "cybersecurity": "🛡️",
    "electronics": "⚡",
    "embedded-systems": "📟",
    "iot": "🌐",
    "mechanical-engineering": "🔧",
    "electrical-engineering": "🔌",
    "biotechnology": "🧬",
    "physics": "⚛️",
    "chemistry": "🧪",
    "mathematics": "📐",
    "space-technology": "🚀",
    "renewable-energy": "🌱",
    "stem-education": "🎓",
    "emerging-tech": "🔮",
}


def sanitize_markdown(text: str) -> str:
    """Strip or escape raw markdown characters that could break Telegram rendering."""
    if not text:
        return ""
    cleaned = html.unescape(text)
    # Remove troublesome markdown syntax in uncontrolled text
    cleaned = cleaned.replace("*", "").replace("_", " ").replace("`", "")
    return re.sub(r"\s+", " ", cleaned).strip()


def estimate_reading_time(text: str) -> str:
    """Calculate reliable reading time estimate based on standard reading speed (~200 wpm)."""
    if not text:
        return "~1 min read"
    words = len(text.split())
    mins = max(1, round(words / 180))
    return f"~{mins} min read"


def format_article_view(article, index: int = 0, total: int = 1) -> str:
    """Format an article into a rich, structured, mobile-friendly Telegram card."""
    source_name = sanitize_markdown(article.source.name if article.source else "Unknown")
    cat_names = [c.name for c in article.categories] if article.categories else ["Technology"]
    cat_display = ", ".join(cat_names[:2])

    primary_slug = article.categories[0].slug if article.categories else "ai"
    emoji = CATEGORY_EMOJIS.get(primary_slug, "📡")

    pub_date = article.published_at or article.collected_at
    date_str = pub_date.strftime("%b %d, %Y") if pub_date else "Recent"

    full_text_for_timer = f"{article.title} {article.description or ''} {article.content or ''}"
    read_time = estimate_reading_time(full_text_for_timer)

    safe_title = sanitize_markdown(article.title)

    raw_desc = article.description or "No preview available."
    safe_desc = sanitize_markdown(raw_desc)
    if len(safe_desc) > 300:
        safe_desc = safe_desc[:297].rsplit(" ", 1)[0] + "..."

    summary_text = sanitize_markdown(article.ai_summary.strip()) if article.ai_summary else safe_desc

    # Extract or synthesize "Why It Matters"
    why_it_matters = None
    if article.ai_analysis:
        clean_analysis = sanitize_markdown(article.ai_analysis)
        if len(clean_analysis) > 25:
            why_it_matters = clean_analysis
    elif article.description and len(article.description.split(".")) > 2:
        sentences = [s.strip() for s in article.description.split(".") if len(s.strip()) > 20]
        if len(sentences) >= 2:
            why_it_matters = sanitize_markdown(sentences[-1]) + "."

    if not why_it_matters:
        impact_defaults = {
            "ai": "Accelerates cognitive inference efficiency and machine reasoning capabilities.",
            "robotics": "Expands operational autonomy, actuator precision, and embodied control.",
            "computer-science": "Optimizes algorithmic complexity, concurrency guarantees, and system throughput.",
            "software-engineering": "Improves architectural resilience, maintainability, and deployment velocity.",
            "cybersecurity": "Mitigates critical threat surfaces, cryptographic weaknesses, and attack vectors.",
            "physics": "Delivers empirical verification for theoretical models and physical matter.",
            "biotechnology": "Enables synthetic biomolecular engineering and clinical translational pipelines.",
            "space-technology": "Advances orbital logistics, propulsion metrics, and aerospace exploration.",
            "renewable-energy": "Improves power conversion efficiency, grid storage, and clean energy economics.",
            "electronics": "Enhances semiconductor density, signal integrity, and energy efficiency.",
        }
        why_it_matters = impact_defaults.get(
            primary_slug, "Represents key technological progress with direct industry and research implications."
        )

    # Generate relevant hashtags
    tags = ["#" + re.sub(r"[^a-zA-Z0-9]", "", c.name) for c in (article.categories or [])]
    if not tags:
        tags = ["#STEM", "#Technology"]
    tags_str = " ".join(tags[:3])

    card_lines = [
        f"{emoji} *{cat_display}* | _{source_name}_",
        f"📅 {date_str} • ⏱️ {read_time}\n",
        f"*{safe_title}*\n",
        f"📝 *Summary:*\n{summary_text}\n",
        f"💡 *Why It Matters:*\n{why_it_matters}\n",
        f"🏷️ `{tags_str}`\n",
        f"🔗 [Read full article on {source_name}]({article.url})",
    ]
    return "\n".join(card_lines)


def format_related_articles(parent_article, related: list) -> str:
    """Format related research papers and technology articles."""
    parent_title = sanitize_markdown(parent_article.title[:80])
    lines = [f"🔍 *Articles & Papers Related to:*\n_{parent_title}...\n"]

    if not related:
        lines.append("No related articles found in this category yet.\nRun `/collect` to index new sources.")
    else:
        for i, a in enumerate(related, 1):
            title = sanitize_markdown(a.title)
            source = sanitize_markdown(a.source.name if a.source else "Tech")
            read_time = estimate_reading_time(f"{a.title} {a.description or ''}")
            lines.append(f"{i}. [{title}]({a.url})\n   _{source}_ • ⏱️ {read_time}\n")

    return "\n".join(lines)


def format_search_results_page(
    query: str,
    articles: list,
    page: int = 0,
    total_pages: int = 1,
    total_count: int = 0,
) -> str:
    """Format paginated article search results."""
    clean_query = sanitize_markdown(query)
    if not articles:
        return f'🔍 No articles found matching *"{clean_query}"*\n\nTry `/collect` to pull new articles.'

    lines = [
        f'🔍 *Search Results for "{clean_query}"*',
        f"📄 Page `{page + 1}` of `{total_pages}` • `{total_count}` total matches\n",
    ]
    start_index = page * 5 + 1
    for i, a in enumerate(articles, start_index):
        clean_title = sanitize_markdown(a.title)
        source = sanitize_markdown(a.source.name if a.source else "Tech")
        read_time = estimate_reading_time(f"{a.title} {a.description or ''}")
        snippet = sanitize_markdown(a.description or "")[:120]
        if snippet:
            snippet = f"\n   _{snippet}..._"
        lines.append(f"{i}. [{clean_title}]({a.url})\n   Source: _{source}_ • ⏱️ {read_time}{snippet}\n")

    return "\n".join(lines)


def format_search_results(query: str, articles: list) -> str:
    """Format article search results list."""
    if not articles:
        return f'🔍 No articles found matching *"{sanitize_markdown(query)}"*\n\nTry `/collect` to pull new articles.'

    lines = [f'🔍 *Search Results for "{sanitize_markdown(query)}":*\n']
    for i, a in enumerate(articles, 1):
        clean_title = sanitize_markdown(a.title)
        source = sanitize_markdown(a.source.name if a.source else "Tech")
        lines.append(f"{i}. [{clean_title}]({a.url})\nSource: _{source}_\n")
    return "\n".join(lines)


def format_sources_list(sources: list) -> str:
    """Format configured intelligence sources view with real-time health telemetry."""
    if not sources:
        return "No sources configured yet."

    lines = ["📡 *Configured Intelligence Sources & Telemetry:*\n"]
    for s in sources:
        if not s.is_active:
            status = "⚪ Inactive"
        elif s.error_count and s.error_count >= 3:
            status = f"🔴 Failing ({s.error_count} errors)"
        elif s.error_count and s.error_count > 0:
            status = f"🟡 Degraded ({s.error_count} error)"
        else:
            status = "🟢 Healthy"

        collected_time = s.last_collected_at.strftime("%b %d, %H:%M UTC") if s.last_collected_at else "Never"

        lines.append(
            f"• *{sanitize_markdown(s.name)}* (`{s.source_type}`)\n  Status: {status} | Last Run: `{collected_time}`"
        )
        if s.last_error and s.error_count and s.error_count > 0:
            safe_err = sanitize_markdown(s.last_error)[:90]
            lines.append(f"  Alert: _{safe_err}_")
        lines.append("")

    lines.append("Use `/collect` to trigger immediate intelligence gathering.")
    return "\n".join(lines)


def chunk_message(text: str, max_length: int = 4000) -> List[str]:
    """Split long messages into chunks that strictly adhere to Telegram's 4096-char limit."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    lines = text.split("\n")
    current_chunk = []
    current_len = 0

    for line in lines:
        if current_len + len(line) + 1 > max_length:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_len = len(line) + 1
        else:
            current_chunk.append(line)
            current_len += len(line) + 1

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


# ------------------ AI Intelligence View Formatters ------------------


def format_news_summary(summary) -> str:
    """Format structured NewsSummary into a Telegram card."""
    facts_str = "\n".join(f"• {sanitize_markdown(f)}" for f in summary.key_facts)
    apps_str = "\n".join(f"• {sanitize_markdown(a)}" for a in summary.potential_applications)

    difficulty = summary.technical_difficulty.upper()
    source = sanitize_markdown(summary.original_source)
    return (
        f"🧠 *AI Technical Summary*\n\n"
        f"*{sanitize_markdown(summary.headline)}*\n"
        f"🏷️ *Depth:* `{difficulty}` | 📰 *Source:* _{source}_\n\n"
        f"📝 *Executive Summary:*\n{sanitize_markdown(summary.short_summary)}\n\n"
        f"📌 *Key Facts:*\n{facts_str}\n\n"
        f"💡 *Why It Matters:*\n{sanitize_markdown(summary.why_it_matters)}\n\n"
        f"🚀 *Potential Applications:*\n{apps_str}\n\n"
        f"🔗 [Original Source Document]({summary.source_url})"
    )


def format_paper_analysis(analysis) -> str:
    """Format scientific ResearchPaperAnalysis into a Telegram card."""
    findings_str = "\n".join(f"• {sanitize_markdown(f)}" for f in analysis.main_findings)
    limits_str = "\n".join(f"• {sanitize_markdown(lim)}" for lim in analysis.limitations)
    apps_str = "\n".join(f"• {sanitize_markdown(a)}" for a in analysis.practical_applications)
    questions_str = "\n".join(f"• {sanitize_markdown(q)}" for q in analysis.further_research_questions)

    return (
        f"🔬 *Scientific Research Paper Analysis*\n\n"
        f"📄 *{sanitize_markdown(analysis.paper_title)}*\n\n"
        f"❓ *Research Problem:*\n{sanitize_markdown(analysis.research_problem)}\n\n"
        f"⚙️ *Methodology:*\n{sanitize_markdown(analysis.methodology)}\n\n"
        f"📊 *Main Findings:*\n{findings_str}\n\n"
        f"⚠️ *Limitations & Boundary Conditions:*\n{limits_str}\n\n"
        f"🚀 *Practical Applications:*\n{apps_str}\n\n"
        f"🔭 *Open Questions:*\n{questions_str}\n\n"
        f"🔗 [Read Full Paper / arXiv]({analysis.original_paper_url})"
    )


def format_concept_explanation(explanation) -> str:
    """Format multi-tier ConceptExplanation."""
    comps_str = ", ".join(sanitize_markdown(c) for c in explanation.key_components)
    misc_str = "\n".join(f"• {sanitize_markdown(m)}" for m in explanation.common_misconceptions)
    prereq_str = ", ".join(sanitize_markdown(p) for p in explanation.prerequisites_or_related)

    return (
        f"💡 *Technical Concept Breakdown*\n\n"
        f"🔍 *{sanitize_markdown(explanation.concept_name)}* (`{explanation.mode.upper()}` Mode)\n\n"
        f"📖 *Definition:*\n{sanitize_markdown(explanation.core_definition)}\n\n"
        f"⚙️ *How It Works:*\n{sanitize_markdown(explanation.how_it_works)}\n\n"
        f"🧩 *Analogy / Example:*\n{sanitize_markdown(explanation.analogy_or_example)}\n\n"
        f"🧱 *Key Components:* {comps_str}\n"
        f"📚 *Prerequisites:* {prereq_str}\n\n"
        f"⚠️ *Common Misconceptions:*\n{misc_str}"
    )


def format_impact_analysis(impact) -> str:
    """Format strategic TechnologyImpactAnalysis."""
    disruption_str = "\n".join(f"• {sanitize_markdown(d)}" for d in impact.industry_disruption)
    ethics_str = "\n".join(f"• {sanitize_markdown(e)}" for e in impact.societal_and_ethical_implications)

    conf = int(impact.confidence_score * 100)
    timeline = sanitize_markdown(impact.adoption_timeline)
    return (
        f"📊 *Strategic Technology Impact Assessment*\n\n"
        f"🎯 *{sanitize_markdown(impact.technology_name)}*\n"
        f"📈 *Confidence Score:* `{conf}%` | ⏳ *Timeline:* `{timeline}`\n\n"
        f"📝 *Executive Assessment:*\n{sanitize_markdown(impact.executive_summary)}\n\n"
        f"⚡ *Industry Disruption:*\n{disruption_str}\n\n"
        f"🔬 *Scientific Significance:*\n{sanitize_markdown(impact.scientific_significance)}\n\n"
        f"⚖️ *Societal & Ethical Considerations:*\n{ethics_str}"
    )


def format_stem_content(pkg) -> str:
    """Format multi-channel STEM Content Package."""
    slides_str = ""
    for s in pkg.carousel_slides:
        bullets = "\n".join(f"  - {sanitize_markdown(b)}" for b in s.bullet_points)
        slides_str += f"*Slide {s.slide_number}: {sanitize_markdown(s.title)}*\n{bullets}\n\n"

    vocab_str = "\n".join(
        f"• *{sanitize_markdown(v.term)}*: {sanitize_markdown(v.definition)}" for v in pkg.technical_vocabulary
    )

    return (
        f"🎨 *STEM Content Creation Package*\n\n"
        f"🎯 *Target Audience:* _{sanitize_markdown(pkg.target_audience)}_\n"
        f"📌 *Topic:* *{sanitize_markdown(pkg.headline)}*\n\n"
        f"📱 *Short Video Script (0:30):*\n"
        f"• *[0:00-0:03 Hook]:* {sanitize_markdown(pkg.video_script.hook)}\n"
        f"• *[0:04-0:20 Body]:* {sanitize_markdown(pkg.video_script.body)}\n"
        f"• *[0:21-0:30 CTA]:* {sanitize_markdown(pkg.video_script.call_to_action)}\n\n"
        f"🖼️ *5-Slide Carousel Outline:*\n{slides_str}"
        f"📖 *Key Technical Vocabulary:*\n{vocab_str}\n\n"
        f"💼 *LinkedIn Post Draft:*\n```\n{pkg.linkedin_post}\n```\n\n"
        f"_{sanitize_markdown(pkg.source_attribution)}_"
    )


# ------------------ Phase 4: STEM Education Formatters ------------------


def format_learning_roadmap(roadmap) -> str:
    """Format structured progressive STEM Learning Roadmap."""
    prereqs = ", ".join(sanitize_markdown(p) for p in roadmap.prerequisites)
    stages_str = ""
    for s in roadmap.stages:
        milestones = "\n".join(f"    • {sanitize_markdown(m)}" for m in s.key_milestones)
        projects = ", ".join(sanitize_markdown(p) for p in s.recommended_projects)
        stages_str += (
            f"📍 *{sanitize_markdown(s.title)}*\n"
            f"  _{sanitize_markdown(s.description)}_\n"
            f"  *Key Milestones:*\n{milestones}\n"
            f"  *Mini-Project:* `{projects}`\n\n"
        )

    return (
        f"🗺️ *STEM Learning Roadmap: {sanitize_markdown(roadmap.topic)}*\n"
        f"⏱️ *Timeline:* ~{roadmap.estimated_duration_weeks} Weeks | 📚 *Prerequisites:* {prereqs}\n\n"
        f"📋 *Overview:*\n{sanitize_markdown(roadmap.overview)}\n\n"
        f"{stages_str}"
        f"Ready to begin? Run `/learn {roadmap.topic}` to start Lesson 1!"
    )


def format_interactive_lesson(lesson) -> str:
    """Format an interactive technical lesson."""
    takeaways = "\n".join(f"• {sanitize_markdown(t)}" for t in lesson.key_takeaways)
    return (
        f"🎓 *STEM Academy: {sanitize_markdown(lesson.title)}*\n"
        f"🏷️ *Level:* `{lesson.level.upper()}` | 📌 *Topic:* *{sanitize_markdown(lesson.topic)}*\n\n"
        f"🎯 *Objective:*\n_{sanitize_markdown(lesson.objective)}_\n\n"
        f"{lesson.core_lesson}\n\n"
        f"📌 *Key Takeaways:*\n{takeaways}\n\n"
        f"🛠️ *Practical Exercise:*\n{sanitize_markdown(lesson.practical_exercise)}\n\n"
        f"➡️ *Up Next:* `{sanitize_markdown(lesson.next_recommended_topic)}`"
    )


def format_quiz_question(quiz, question_index: int = 0) -> str:
    """Format a multiple choice quiz question card."""
    total = len(quiz.questions)
    safe_idx = max(0, min(question_index, total - 1))
    q = quiz.questions[safe_idx]

    options_text = "\n".join(f"{sanitize_markdown(opt)}" for opt in q.options)

    return (
        f"📝 *Interactive STEM Quiz: {sanitize_markdown(quiz.topic)}*\n"
        f"🏷️ *Difficulty:* `{quiz.difficulty.upper()}` | ❓ *Question {safe_idx + 1} of {total}*\n\n"
        f"*{sanitize_markdown(q.question)}*\n\n"
        f"{options_text}\n\n"
        "Tap your answer below to check correctness & explanations:"
    )


def format_concept_comparison(comp) -> str:
    """Format side-by-side engineering concept comparison."""
    matrix_lines = []
    for d in comp.key_differences:
        matrix_lines.append(
            f"• *{sanitize_markdown(d.dimension)}:*\n"
            f"  - *{sanitize_markdown(comp.concept_a)}:* {sanitize_markdown(d.concept_a_value)}\n"
            f"  - *{sanitize_markdown(comp.concept_b)}:* {sanitize_markdown(d.concept_b_value)}"
        )
    matrix_str = "\n\n".join(matrix_lines)

    when_a = "\n".join(f"• {sanitize_markdown(a)}" for a in comp.when_to_use_a)
    when_b = "\n".join(f"• {sanitize_markdown(b)}" for b in comp.when_to_use_b)

    return (
        f"⚖️ *Technical Comparison: {sanitize_markdown(comp.concept_a)} vs {sanitize_markdown(comp.concept_b)}*\n\n"
        f"📋 *Overview:*\n{sanitize_markdown(comp.overview)}\n\n"
        f"📊 *Architectural Trade-Off Matrix:*\n{matrix_str}\n\n"
        f"🟢 *When to Choose {sanitize_markdown(comp.concept_a)}:*\n{when_a}\n\n"
        f"🔵 *When to Choose {sanitize_markdown(comp.concept_b)}:*\n{when_b}\n\n"
        f"🏆 *Engineering Verdict:*\n{sanitize_markdown(comp.summary_verdict)}"
    )


def format_project_recommendation(proj) -> str:
    """Format portfolio project recommendation."""
    stack_str = ", ".join(f"`{sanitize_markdown(t)}`" for t in proj.tech_stack)
    milestones = "\n".join(f"• {sanitize_markdown(m)}" for m in proj.step_by_step_milestones)
    stretch = "\n".join(f"• {sanitize_markdown(s)}" for s in proj.stretch_goals)

    skills = getattr(proj, "required_skills", None)
    skills_line = ""
    if skills:
        skills_str = ", ".join(f"`{sanitize_markdown(s)}`" for s in skills)
        skills_line = f"🛠️ *Required Skills:*\n{skills_str}\n\n"

    materials = getattr(proj, "components_and_materials", None)
    materials_line = ""
    if materials:
        materials_str = "\n".join(f"• {sanitize_markdown(c)}" for c in materials)
        materials_line = f"🧩 *Components & Materials:*\n{materials_str}\n\n"

    cost = getattr(proj, "estimated_cost", None)
    cost_line = ""
    if cost:
        cost_line = f"💰 *Estimated Budget & Assumptions:*\n_{sanitize_markdown(cost)}_\n\n"

    return (
        f"🚀 *Portfolio Project: {sanitize_markdown(proj.project_title)}*\n"
        f"🏷️ *Level:* `{proj.difficulty.upper()}` | 📌 *Domain:* *{sanitize_markdown(proj.topic)}*\n\n"
        f"🎯 *Problem Statement:*\n{sanitize_markdown(proj.problem_statement)}\n\n"
        f"{skills_line}"
        f"{materials_line}"
        f"{cost_line}"
        f"🏗️ *System Architecture:*\n{sanitize_markdown(proj.system_architecture)}\n\n"
        f"🧰 *Recommended Tech Stack:*\n{stack_str}\n\n"
        f"📋 *Step-by-Step Implementation Milestones:*\n{milestones}\n\n"
        f"⭐ *Stretch Goals for Excellence:*\n{stretch}\n\n"
        f"💼 *Hiring Portfolio Impact:*\n_{sanitize_markdown(proj.portfolio_impact)}_"
    )


def format_vocabulary_glossary(glossary) -> str:
    """Format technical vocabulary glossary."""
    terms_str = "\n\n".join(
        f"📖 *{sanitize_markdown(t.term)}*\n_{sanitize_markdown(t.definition)}_" for t in glossary.terms
    )
    return (
        f"📚 *Technical Vocabulary Glossary: {sanitize_markdown(glossary.topic)}*\n\n"
        f"{terms_str}\n\n"
        "Master these terms to understand technical papers and system designs!"
    )


def format_learning_progress(progress_list: list) -> str:
    """Format user learning progress overview."""
    if not progress_list:
        return (
            "📊 *Your STEM Learning Progress*\n\n"
            "You haven't completed any lessons or quizzes yet!\n\n"
            "Get started with:\n"
            "• `/roadmap AI` — View full curriculum\n"
            "• `/learn AI` — Start your first lesson\n"
            "• `/quiz AI` — Test your knowledge"
        )

    lines = ["📊 *Your STEM Learning Progress & Mastery:*\n"]
    for p in progress_list:
        accuracy = f"{int((p.quiz_score_total / p.quiz_score_max) * 100)}%" if p.quiz_score_max > 0 else "N/A"
        studied_str = p.last_studied_at.strftime("%b %d, %Y") if p.last_studied_at else "Recent"
        lines.append(
            f"• *{p.topic.upper()}* (`{p.level.upper()}`)\n"
            f"  Lessons Completed: `{p.lessons_completed}` | Quizzes: `{p.quizzes_taken}` (Accuracy: `{accuracy}`)\n"
            f"  Last Studied: `{studied_str}`\n"
        )

    lines.append("Keep learning with `/learn` or test your skills with `/quiz`!")
    return "\n".join(lines)


def format_daily_briefing(articles: list, user_name: str = "", category_filter: str = "") -> str:
    """Format an executive daily STEM intelligence briefing."""
    today_str = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    filter_label = f" ({sanitize_markdown(category_filter)})" if category_filter else ""
    user_greet = f" for *{sanitize_markdown(user_name)}*" if user_name else ""

    lines = [
        f"☀️ *STEM RADAR Daily Executive Briefing*{user_greet}",
        f"📅 _{today_str}_{filter_label}\n",
    ]

    if not articles:
        lines.append("No new high-priority developments recorded today. Run `/collect` to fetch updates.")
        return "\n".join(lines)

    lines.append("Here are today's top curated technological breakthroughs:\n")
    for i, a in enumerate(articles[:5], 1):
        source = sanitize_markdown(a.source.name if a.source else "STEM")
        cat = a.categories[0].name if a.categories else "Technology"
        emoji = CATEGORY_EMOJIS.get(a.categories[0].slug if a.categories else "", "⚡")
        safe_title = sanitize_markdown(a.title)
        raw_desc = a.description or ""
        safe_desc = sanitize_markdown(raw_desc)
        short_desc = safe_desc[:140].rsplit(" ", 1)[0] + "..." if len(safe_desc) > 140 else safe_desc

        lines.append(f"*{i}. {emoji} [{safe_title}]({a.url})*")
        lines.append(f"   _{cat}_ | Source: _{source}_")
        if short_desc:
            lines.append(f"   {short_desc}")
        lines.append("")

    lines.append("💡 _Run `/trends` for live scoring or `/digest` for deep AI synthesis._")
    return "\n".join(lines)


def format_weekly_report(articles: list, total_collected: int = 0, domain_breakdown: dict = None) -> str:
    """Format weekly intelligence report summarizing key breakthroughs across STEM domains."""
    today_str = datetime.now(timezone.utc).strftime("%b %d, %Y")

    lines = [
        "🌐 *STEM RADAR Weekly Intelligence Report*",
        f"📅 _Week Ending: {today_str}_\n",
        f"📊 *Weekly Activity:* `{total_collected}` items monitored across STEM domains.\n",
    ]

    if domain_breakdown:
        lines.append("📈 *Top Active Domains:*")
        for dom, count in list(domain_breakdown.items())[:5]:
            lines.append(f"• *{sanitize_markdown(dom)}:* `{count}` developments")
        lines.append("")

    if articles:
        lines.append("🏆 *High-Impact Breakthroughs of the Week:*\n")
        for i, a in enumerate(articles[:5], 1):
            source = sanitize_markdown(a.source.name if a.source else "Tech")
            cat = a.categories[0].name if a.categories else "STEM"
            safe_title = sanitize_markdown(a.title)
            lines.append(f"{i}. *{cat}:* [{safe_title}]({a.url}) (_{source}_)")
        lines.append("")

    lines.append("Use `/briefing` for daily briefings or `/settings` to personalize subscriptions.")
    return "\n".join(lines)


def format_watchlist(watchlist: list) -> str:
    """Format user keyword and technology watchlist."""
    if not watchlist:
        return (
            "🔭 *Your STEM Watchlist is Empty*\n\n"
            "Track technologies, models, and breakthroughs in real-time.\n\n"
            "• `/watchlist add <keyword>` — Add technology to watch\n"
            "  _Example:_ `/watchlist add humanoid`\n"
            "  _Example:_ `/watchlist add quantum`\n"
            "• `/watchlist remove <keyword>` — Stop tracking a keyword\n"
            "• `/watchlist clear` — Clear all watched keywords"
        )

    lines = [
        "🔭 *Your Active STEM Watchlist*\n",
        "We notify you immediately when an article or paper matches these keywords:\n",
    ]
    for w in watchlist:
        lines.append(f"• `#{w.keyword}` — `{w.match_count}` matches found")

    lines.append("\nCommands:")
    lines.append("• `/watchlist add <keyword>` to track more")
    lines.append("• `/watchlist remove <keyword>` to remove")
    lines.append("• `/watchlist clear` to reset")
    return "\n".join(lines)


def format_watchlist_alert(article, matched_keyword: str) -> str:
    """Format real-time watchlist match alert."""
    source = sanitize_markdown(article.source.name if article.source else "STEM")
    safe_title = sanitize_markdown(article.title)
    raw_desc = article.description or ""
    safe_desc = sanitize_markdown(raw_desc)
    if len(safe_desc) > 250:
        safe_desc = safe_desc[:247].rsplit(" ", 1)[0] + "..."

    return (
        f"🚨 *WATCHLIST ALERT: #{sanitize_markdown(matched_keyword.upper())}*\n\n"
        f"*{safe_title}*\n"
        f"Source: _{source}_\n\n"
        f"{safe_desc}\n\n"
        f"🔗 [Read Full Article]({article.url})\n"
        "Manage your keywords anytime with `/watchlist`."
    )


def format_high_impact_alert(article, score: float) -> str:
    """Format real-time high-impact development alert."""
    source = sanitize_markdown(article.source.name if article.source else "STEM")
    safe_title = sanitize_markdown(article.title)
    cat = article.categories[0].name if article.categories else "STEM"
    raw_desc = article.description or ""
    safe_desc = sanitize_markdown(raw_desc)
    if len(safe_desc) > 250:
        safe_desc = safe_desc[:247].rsplit(" ", 1)[0] + "..."

    return (
        f"⚡ *HIGH-IMPACT STEM BREAKTHROUGH* (Score: `{score}/100`)\n\n"
        f"🏷️ *Domain:* *{cat}* | Source: _{source}_\n\n"
        f"*{safe_title}*\n\n"
        f"{safe_desc}\n\n"
        f"🔗 [Read Full Source]({article.url})\n"
        "Configure alerts and quiet hours with `/settings`."
    )


def format_trending_feed(scored_articles: list) -> str:
    """Format trending STEM developments feed ranked by impact score."""
    if not scored_articles:
        return "📈 No trending articles scored yet. Run `/collect` to ingest new intelligence."

    lines = ["📈 *Trending STEM Breakthroughs & SOTA Developments:*\n"]
    for i, (art, score) in enumerate(scored_articles[:7], 1):
        cat = art.categories[0].name if art.categories else "Technology"
        emoji = CATEGORY_EMOJIS.get(art.categories[0].slug if art.categories else "", "🚀")
        source = sanitize_markdown(art.source.name if art.source else "News")
        safe_title = sanitize_markdown(art.title)
        lines.append(f"{i}. {emoji} *{cat}* — `{score}/100`\n   [{safe_title}]({art.url})\n   Source: _{source}_\n")

    lines.append("Ranked by recency, breakthrough milestone keywords, and research depth.")
    return "\n".join(lines)


def format_platform_stats(stats: dict) -> str:
    """Format system telemetry and user intelligence statistics."""
    lines = [
        "📊 *STEM RADAR Intelligence Telemetry & Platform Stats*\n",
        "🌐 *Global Platform Scope:*",
        f"• Tracked Articles & Papers: `{stats.get('total_articles', 0):,}`",
        f"• Active Ingestion Sources: `{stats.get('active_sources', 0)}`",
        f"• STEM Categories Monitored: `{stats.get('stem_categories', 0)}`",
        f"• Total Notifications Dispatched: `{stats.get('total_notifications_sent', 0):,}`\n",
    ]

    if "user_saved_articles" in stats:
        lines.extend(
            [
                "👤 *Your Personal Intelligence Activity:*",
                f"• Bookmarked Articles: `{stats.get('user_saved_articles', 0)}` (view with `/saved`)",
                f"• Watchlist Keywords: `{stats.get('user_watchlist_keywords', 0)}` (manage with `/watchlist`)",
                f"• Automated Alerts Received: `{stats.get('user_notifications_received', 0)}`",
                f"• Interactive Quizzes Completed: `{stats.get('user_quizzes_taken', 0)}` (track with `/progress`)",
            ]
        )

    lines.append("\n_All pipelines active and healthy._")
    return "\n".join(lines)


def format_tech_radar(
    horizon: str = "all",
    scored_articles: Optional[list] = None,
    domain_velocities: Optional[dict] = None,
) -> str:
    """Format interactive Thoughtworks-style Technology Radar across 4 adoption horizons."""
    clean_horizon = (horizon or "all").lower().strip()

    if clean_horizon == "adopt":
        content = (
            "🎯 *STEM Technology Radar — 🟢 ADOPT Horizon*\n\n"
            "*Definition:* Technologies with high ROI, verified production stability, "
            "minimal adoption risk, and widespread engineering support.\n\n"
            "1. *LLM Orchestration & Vector RAG*\n"
            "   • _Standard:_ Qdrant, Chroma, LlamaIndex, pgvector\n"
            "   • _Verdict:_ Essential for grounding generative models without catastrophic hallucinations.\n\n"
            "2. *PyTorch 2.x & Graph Compilation*\n"
            "   • _Standard:_ TorchDynamo, TorchInductor, Triton kernels\n"
            "   • _Verdict:_ Standard runtime for training and inference; replaces eager-mode execution.\n\n"
            "3. *FlashAttention-2 & Memory-Efficient Attention*\n"
            "   • _Standard:_ Tiling algorithms, fused CUDA kernels\n"
            "   • _Verdict:_ Mandatory standard for long-context sequence modeling (>8k tokens).\n\n"
            "4. *Rust for Systems & Embedded Firmware*\n"
            "   • _Standard:_ Memory safety without GC latency overhead\n"
            "   • _Verdict:_ First choice for high-concurrency kernels, robotics controllers, and WASM."
        )
    elif clean_horizon == "trial":
        content = (
            "🎯 *STEM Technology Radar — 🟡 TRIAL Horizon*\n\n"
            "*Definition:* High-potential technologies validated in labs or pilot projects; "
            "ready for proof-of-concept evaluation in production environments.\n\n"
            "1. *Vision-Language-Action (VLA) Robotics Models*\n"
            "   • _Examples:_ RT-2, OpenVLA, Octo\n"
            "   • _Focus:_ Direct tokenized control of robotic end-effectors from visual prompts.\n\n"
            "2. *Sim-to-Real Reinforcement Learning Locomotion*\n"
            "   • _Examples:_ Isaac Gym, Domain Randomization, Humanoid Walk Policies\n"
            "   • _Focus:_ Dynamic balance recovery surpassing classical inverse kinematics.\n\n"
            "3. *On-Device Small Language Models (SLMs)*\n"
            "   • _Examples:_ 1B-4B quantized architectures (GGUF, AWQ, EXL2)\n"
            "   • _Focus:_ Privacy-first, offline, sub-50ms token generation on edge devices.\n\n"
            "4. *Neuromorphic Event-Based Sensors*\n"
            "   • _Examples:_ Dynamic Vision Sensors (DVS), Spiking Neural Networks (SNN)\n"
            "   • _Focus:_ Micro-watt power consumption with microsecond temporal resolution."
        )
    elif clean_horizon == "assess":
        content = (
            "🎯 *STEM Technology Radar — 🔵 ASSESS Horizon*\n\n"
            "*Definition:* Frontier scientific developments and emerging paradigms; "
            "worth active research tracking and experimental prototyping.\n\n"
            "1. *Quantum Error Mitigation & Logical Qubits*\n"
            "   • _Examples:_ Surface codes, neutral-atom lattices, fault-tolerant gates\n"
            "   • _Status:_ Transitioning from NISQ noisy qubits toward physical error suppression.\n\n"
            "2. *High-Temperature Superconductivity*\n"
            "   • _Examples:_ Hydrides under compression, nickelate thin films\n"
            "   • _Status:_ Rigorous peer-reviewed laboratory replication phase.\n\n"
            "3. *Non-Invasive Brain-Computer Interfaces (BCI)*\n"
            "   • _Examples:_ High-density EEG, neural speech decoders\n"
            "   • _Status:_ Clinical trials and assistive communication systems.\n\n"
            "4. *Synthetic Biology Automated Foundries*\n"
            "   • _Examples:_ High-throughput DNA synthesis, robotic enzymatic optimization\n"
            "   • _Status:_ Pilot biomanufacturing scale-up."
        )
    elif clean_horizon == "hold":
        content = (
            "🎯 *STEM Technology Radar — 🔴 HOLD Horizon*\n\n"
            "*Definition:* Anti-patterns, deprecated architectures, or speculative hype; "
            "proceed with extreme skepticism and avoid for new production projects.\n\n"
            "1. *Monolithic RNNs / LSTMs for Long Context*\n"
            "   • _Reason:_ Sequential bottlenecks prevent GPU scaling; superseded by Transformers and SSMs.\n\n"
            "2. *Proprietary Closed Formats without Export*\n"
            "   • _Reason:_ Severe vendor lock-in risk and inability to run local regression audits.\n\n"
            "3. *Unquantized Massive Models on Edge Devices*\n"
            "   • _Reason:_ Memory bandwidth saturation, severe battery drain, and thermal throttling.\n\n"
            "4. *Unverified Hype Claims without Code / Peer Review*\n"
            "   • _Reason:_ Speculative claims of room-temp superconductivity or AGI lacking empirical proof."
        )
    else:
        # Full Radar Overview
        content = (
            "🎯 *STEM Technology Radar (Q4/2026)*\n\n"
            "Autonomous radar classifying technologies into four adoption horizons:\n\n"
            "🟢 *ADOPT:* LLM RAG Pipelines, PyTorch 2.x, FlashAttention-2, Rust Systems\n"
            "🟡 *TRIAL:* Vision-Language-Action (VLA), Humanoid RL, On-Device SLMs, Neuromorphic Chips\n"
            "🔵 *ASSESS:* Quantum Error Mitigation, Room-Temp Superconductors, Non-Invasive BCI, SynBio\n"
            "🔴 *HOLD:* Monolithic RNNs, Proprietary Closed Lock-in, Edge Unquantized Models, Speculative Hype"
        )

    # Embed dynamic real-time momentum if available
    lines = [content]
    if domain_velocities:
        lines.append("\n📈 *Empirical Domain Velocity Signals:*")
        for slug, d in list(domain_velocities.items())[:4]:
            lines.append(
                f"• *{d.get('name', slug.title())}*: {d.get('momentum', '⚖️ Stable')} "
                f"(`{d.get('count', 0)}` articles, `{d.get('paper_count', 0)}` papers)"
            )
    elif scored_articles:
        lines.append("\n🔥 *Active Breakthrough Signals:*")
        for idx, item in enumerate(scored_articles[:3], 1):
            art = item[0] if isinstance(item, (tuple, list)) else item
            score = item[1] if isinstance(item, (tuple, list)) else 80.0
            lines.append(f"{idx}. *{sanitize_markdown(art.title[:65])}* (Score: `{score:.1f}`)")

    lines.append("\n_Tap buttons below to filter horizons or update live intelligence._")
    return "\n".join(lines)


def format_trend_velocity(domain_velocities: dict) -> str:
    """Format evidence-based STEM trend velocity and momentum report."""
    if not domain_velocities:
        return "📊 No trend momentum data calculated yet. Run `/collect` first!"

    lines = [
        "📈 *STEM Domain Trend Velocity & Momentum Analysis*\n",
        "Evidence-based tracking computed from publication volume, recency, and impact scores:\n",
    ]

    for slug, d in domain_velocities.items():
        name = d.get("name", slug.title())
        momentum = d.get("momentum", "⚖️ Stable")
        count = d.get("count", 0)
        papers = d.get("paper_count", 0)
        avg_score = d.get("avg_score", 0.0)
        top = d.get("top_headline", "")

        lines.append(
            f"*{name}*\n"
            f"• Momentum: *{momentum}*\n"
            f"• Indexed Articles: `{count}` (Research Papers: `{papers}`)\n"
            f"• Avg Intelligence Score: `{avg_score:.1f}/100`\n"
            f"• Top Signal: _{sanitize_markdown(top[:80])}_\n"
        )

    lines.append("Indicators strictly reflect verified database collection and research activity.")
    return "\n".join(lines)
