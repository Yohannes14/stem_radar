"""Presentation layer formatters generating clean, editorial Telegram Markdown messages."""

from datetime import datetime, timezone
from typing import List, Optional

from app.bot.ui.design_system import (
    format_ai_notice,
    format_date,
    format_datetime,
    format_meta,
    format_section,
    sanitize_markdown,
)


def estimate_reading_time(text: str) -> str:
    """Calculate reading time estimate based on standard reading speed (~180 wpm)."""
    if not text:
        return "1 min read"
    words = len(text.split())
    mins = max(1, round(words / 180))
    return f"{mins} min read"


def format_article_view(article, index: int = 0, total: int = 1) -> str:
    """Format an article or paper into a clean, editorial Telegram card."""
    source_name = sanitize_markdown(article.source.name if article.source else "Unknown")
    cat_names = [sanitize_markdown(c.name) for c in article.categories] if article.categories else ["Technology"]
    cat_display = ", ".join(cat_names[:2])

    pub_date = article.published_at or article.collected_at
    date_str = format_date(pub_date, fallback="Recent")

    full_text_for_timer = f"{article.title} {article.description or ''} {article.content or ''}"
    read_time = estimate_reading_time(full_text_for_timer)

    safe_title = sanitize_markdown(article.title)

    raw_desc = article.description or "No summary available."
    safe_desc = sanitize_markdown(raw_desc)
    if len(safe_desc) > 320:
        safe_desc = safe_desc[:317].rsplit(" ", 1)[0] + "..."

    summary_text = sanitize_markdown(article.ai_summary.strip()) if article.ai_summary else safe_desc

    # Only include "Why it matters" when real analysis or a distinct concluding sentence exists
    why_it_matters = None
    if article.ai_analysis:
        clean_analysis = sanitize_markdown(article.ai_analysis)
        if len(clean_analysis) > 25:
            why_it_matters = clean_analysis
    elif article.description and len(article.description.split(".")) > 2:
        sentences = [s.strip() for s in article.description.split(".") if len(s.strip()) > 20]
        if len(sentences) >= 2:
            candidate = sanitize_markdown(sentences[-1]) + "."
            if candidate not in summary_text:
                why_it_matters = candidate

    meta_block = format_meta(
        [
            ("Source", source_name),
            ("Published", f"{date_str} · {read_time}"),
            ("Category", cat_display),
        ]
    )

    sections = [
        f"*{safe_title}*",
        meta_block,
        summary_text,
    ]
    if why_it_matters:
        sections.append(format_section("Why it matters", why_it_matters))

    sections.append(f"[Read original on {source_name}]({article.url})")
    return "\n\n".join(s for s in sections if s)


def format_related_articles(parent_article, related: list) -> str:
    """Format related research papers and technology articles."""
    parent_title = sanitize_markdown(parent_article.title[:80])
    lines = [f"*Related to:*\n_{parent_title}_\n"]

    if not related:
        lines.append("No related articles found in this category yet.\nRun `/collect` to index new sources.")
    else:
        for i, a in enumerate(related, 1):
            title = sanitize_markdown(a.title)
            source = sanitize_markdown(a.source.name if a.source else "Source")
            read_time = estimate_reading_time(f"{a.title} {a.description or ''}")
            lines.append(f"{i}. [{title}]({a.url})\n   {source} · {read_time}\n")

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
        return f'No articles found matching "{clean_query}".\n\nTry broader keywords or run `/collect`.'

    lines = [
        f'*Search Results — "{clean_query}"*',
        f"Page {page + 1} of {total_pages} · {total_count} matches\n",
    ]
    start_index = page * 5 + 1
    for i, a in enumerate(articles, start_index):
        clean_title = sanitize_markdown(a.title)
        source = sanitize_markdown(a.source.name if a.source else "Source")
        read_time = estimate_reading_time(f"{a.title} {a.description or ''}")
        snippet = sanitize_markdown(a.description or "")[:120]
        snippet_line = f"\n   {snippet}..." if snippet else ""
        lines.append(f"{i}. [{clean_title}]({a.url})\n   {source} · {read_time}{snippet_line}\n")

    return "\n".join(lines)


def format_search_results(query: str, articles: list) -> str:
    """Format article search results list."""
    clean_query = sanitize_markdown(query)
    if not articles:
        return f'No articles found matching "{clean_query}".\n\nTry broader keywords or run `/collect`.'

    lines = [f'*Search Results — "{clean_query}"*\n']
    for i, a in enumerate(articles, 1):
        clean_title = sanitize_markdown(a.title)
        source = sanitize_markdown(a.source.name if a.source else "Source")
        lines.append(f"{i}. [{clean_title}]({a.url})\n   Source: {source}\n")
    return "\n".join(lines)


def format_sources_list(sources: list) -> str:
    """Format configured intelligence sources view with health status."""
    if not sources:
        return "No sources configured yet."

    lines = ["*Configured Sources*\n"]
    for s in sources:
        if not s.is_active:
            status = "Inactive"
        elif s.error_count and s.error_count >= 3:
            status = f"Failing ({s.error_count} errors)"
        elif s.error_count and s.error_count > 0:
            status = f"Degraded ({s.error_count} error)"
        else:
            status = "Healthy"

        collected_time = format_datetime(s.last_collected_at, fallback="Never")

        lines.append(
            f"- *{sanitize_markdown(s.name)}* ({s.source_type})\n  Status: {status} · Last run: {collected_time}"
        )
        if s.last_error and s.error_count and s.error_count > 0:
            safe_err = sanitize_markdown(s.last_error)[:90]
            lines.append(f"  Error: {safe_err}")
        lines.append("")

    lines.append("Run `/collect` to trigger a collection pass.")
    return "\n".join(lines)


def chunk_message(text: str, max_length: int = 4000) -> List[str]:
    """Split long messages into chunks adhering to Telegram's 4096-character limit."""
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
    """Format structured NewsSummary into an editorial Telegram card."""
    difficulty = summary.technical_difficulty.capitalize()
    source = sanitize_markdown(summary.original_source)
    meta = format_meta([("Source", source), ("Level", difficulty)])

    sections = [
        f"*{sanitize_markdown(summary.headline)}*",
        meta,
        format_section("Summary", sanitize_markdown(summary.short_summary)),
        format_section("Key facts", summary.key_facts),
        format_section("Why it matters", sanitize_markdown(summary.why_it_matters)),
        format_section("Potential applications", summary.potential_applications),
        f"[Original source]({summary.source_url})",
        format_ai_notice("general"),
    ]
    return "\n\n".join(s for s in sections if s)


def format_paper_analysis(analysis) -> str:
    """Format scientific ResearchPaperAnalysis into an editorial Telegram card."""
    links = [f"[Read Full Paper]({analysis.original_paper_url})"]
    if getattr(analysis, "code_repository_url", None):
        links.append(f"[Code & Replication Repository]({analysis.code_repository_url})")

    sections = [
        f"*Research Paper Analysis*\n\n*{sanitize_markdown(analysis.paper_title)}*",
        format_section("Research problem", sanitize_markdown(analysis.research_problem)),
        format_section("Methodology", sanitize_markdown(analysis.methodology)),
        format_section("Main findings", analysis.main_findings),
        format_section("Limitations", analysis.limitations),
        format_section("Practical applications", analysis.practical_applications),
        format_section("Open questions", analysis.further_research_questions),
        format_section("Links", " · ".join(links)),
        format_ai_notice("paper"),
    ]
    return "\n\n".join(s for s in sections if s)


def format_concept_explanation(explanation) -> str:
    """Format multi-tier ConceptExplanation."""
    comps_str = ", ".join(sanitize_markdown(c) for c in explanation.key_components)
    prereq_str = ", ".join(sanitize_markdown(p) for p in explanation.prerequisites_or_related)
    meta = format_meta([("Level", explanation.mode.capitalize())])

    sections = [
        f"*{sanitize_markdown(explanation.concept_name)}*\n{meta}",
        format_section("Definition", sanitize_markdown(explanation.core_definition)),
        format_section("How it works", sanitize_markdown(explanation.how_it_works)),
        format_section("Example", sanitize_markdown(explanation.analogy_or_example)),
        format_meta([("Key components", comps_str), ("Prerequisites", prereq_str)]),
        format_section("Common misconceptions", explanation.common_misconceptions),
        format_ai_notice("general"),
    ]
    return "\n\n".join(s for s in sections if s)


def format_impact_analysis(impact) -> str:
    """Format strategic TechnologyImpactAnalysis."""
    conf = int(impact.confidence_score * 100)
    timeline = sanitize_markdown(impact.adoption_timeline)
    meta = format_meta([("Confidence", f"{conf}%"), ("Adoption timeline", timeline)])

    sections = [
        f"*Technology Impact Assessment*\n\n*{sanitize_markdown(impact.technology_name)}*\n{meta}",
        format_section("Overview", sanitize_markdown(impact.executive_summary)),
        format_section("Industry impact", impact.industry_disruption),
        format_section("Scientific significance", sanitize_markdown(impact.scientific_significance)),
        format_section("Societal and ethical considerations", impact.societal_and_ethical_implications),
        format_ai_notice("general"),
    ]
    return "\n\n".join(s for s in sections if s)


def format_stem_content(pkg) -> str:
    """Format multi-channel STEM Content Package."""
    slides_parts = []
    for s in pkg.carousel_slides:
        bullets = "\n".join(f"  - {sanitize_markdown(b)}" for b in s.bullet_points)
        slides_parts.append(f"*Slide {s.slide_number}: {sanitize_markdown(s.title)}*\n{bullets}")
    slides_str = "\n\n".join(slides_parts)

    vocab_str = "\n".join(
        f"- *{sanitize_markdown(v.term)}*: {sanitize_markdown(v.definition)}" for v in pkg.technical_vocabulary
    )
    meta = format_meta([("Audience", sanitize_markdown(pkg.target_audience))])

    sections = [
        f"*STEM Content Package*\n\n*{sanitize_markdown(pkg.headline)}*\n{meta}",
        (
            "*Short Video Script (30s)*\n"
            f"- 0:00-0:03 Hook: {sanitize_markdown(pkg.video_script.hook)}\n"
            f"- 0:04-0:20 Body: {sanitize_markdown(pkg.video_script.body)}\n"
            f"- 0:21-0:30 Closing: {sanitize_markdown(pkg.video_script.call_to_action)}"
        ),
        f"*5-Slide Outline*\n\n{slides_str}",
        f"*Technical Vocabulary*\n{vocab_str}",
        f"*Post Draft*\n```\n{pkg.linkedin_post}\n```",
        f"_{sanitize_markdown(pkg.source_attribution)}_",
    ]
    return "\n\n".join(s for s in sections if s)


# ------------------ Phase 4: STEM Education Formatters ------------------


def format_learning_roadmap(roadmap) -> str:
    """Format structured progressive STEM Learning Roadmap."""
    prereqs = ", ".join(sanitize_markdown(p) for p in roadmap.prerequisites)
    meta = format_meta(
        [
            ("Estimated duration", f"~{roadmap.estimated_duration_weeks} weeks"),
            ("Prerequisites", prereqs),
        ]
    )

    stage_blocks = []
    for s in roadmap.stages:
        milestones = "\n".join(f"  - {sanitize_markdown(m)}" for m in s.key_milestones)
        projects = ", ".join(sanitize_markdown(p) for p in s.recommended_projects)
        stage_blocks.append(
            f"*{sanitize_markdown(s.title)}*\n"
            f"{sanitize_markdown(s.description)}\n"
            f"Milestones:\n{milestones}\n"
            f"Project: {projects}"
        )

    sections = [
        f"*Learning Roadmap: {sanitize_markdown(roadmap.topic)}*\n{meta}",
        format_section("Overview", sanitize_markdown(roadmap.overview)),
        "\n\n".join(stage_blocks),
        f"Run `/learn {roadmap.topic}` to begin Lesson 1.",
    ]
    return "\n\n".join(s for s in sections if s)


def format_interactive_lesson(lesson) -> str:
    """Format an interactive technical lesson."""
    meta = format_meta(
        [
            ("Topic", sanitize_markdown(lesson.topic)),
            ("Level", lesson.level.capitalize()),
        ]
    )
    sections = [
        f"*{sanitize_markdown(lesson.title)}*\n{meta}",
        format_section("Objective", sanitize_markdown(lesson.objective)),
        lesson.core_lesson,
        format_section("Key takeaways", lesson.key_takeaways),
        format_section("Practical exercise", sanitize_markdown(lesson.practical_exercise)),
        f"Next topic: {sanitize_markdown(lesson.next_recommended_topic)}",
    ]
    return "\n\n".join(s for s in sections if s)


def format_quiz_question(quiz, question_index: int = 0) -> str:
    """Format a multiple choice quiz question card."""
    total = len(quiz.questions)
    safe_idx = max(0, min(question_index, total - 1))
    q = quiz.questions[safe_idx]

    options_text = "\n".join(f"{sanitize_markdown(opt)}" for opt in q.options)
    meta = format_meta(
        [
            ("Level", quiz.difficulty.capitalize()),
            ("Question", f"{safe_idx + 1} of {total}"),
        ]
    )

    return (
        f"*Quiz: {sanitize_markdown(quiz.topic)}*\n"
        f"{meta}\n\n"
        f"*{sanitize_markdown(q.question)}*\n\n"
        f"{options_text}\n\n"
        "Select an answer below:"
    )


def format_concept_comparison(comp) -> str:
    """Format side-by-side engineering concept comparison."""
    matrix_lines = []
    for d in comp.key_differences:
        matrix_lines.append(
            f"*{sanitize_markdown(d.dimension)}*\n"
            f"- {sanitize_markdown(comp.concept_a)}: {sanitize_markdown(d.concept_a_value)}\n"
            f"- {sanitize_markdown(comp.concept_b)}: {sanitize_markdown(d.concept_b_value)}"
        )
    matrix_str = "\n\n".join(matrix_lines)

    sections = [
        f"*Comparison: {sanitize_markdown(comp.concept_a)} vs {sanitize_markdown(comp.concept_b)}*",
        format_section("Overview", sanitize_markdown(comp.overview)),
        f"*Key Differences*\n\n{matrix_str}",
        format_section(f"When to choose {sanitize_markdown(comp.concept_a)}", comp.when_to_use_a),
        format_section(f"When to choose {sanitize_markdown(comp.concept_b)}", comp.when_to_use_b),
        format_section("Summary", sanitize_markdown(comp.summary_verdict)),
    ]
    return "\n\n".join(s for s in sections if s)


def format_project_recommendation(proj) -> str:
    """Format portfolio project recommendation with engineering specifications."""
    stack_str = ", ".join(sanitize_markdown(t) for t in proj.tech_stack)
    time_str = getattr(proj, "estimated_time", "1-2 weeks (~15-25 hours)")

    skills = getattr(proj, "required_skills", None)
    skills_str = ", ".join(sanitize_markdown(s) for s in skills) if skills else None
    cost = getattr(proj, "estimated_cost", None)

    meta = format_meta(
        [
            ("Topic", sanitize_markdown(proj.topic)),
            ("Level", proj.difficulty.capitalize()),
            ("Estimated time", sanitize_markdown(time_str)),
            ("Estimated cost", sanitize_markdown(cost) if cost else None),
        ]
    )

    sections = [
        f"*Project: {sanitize_markdown(proj.project_title)}*\n{meta}",
        format_section("Problem statement", sanitize_markdown(proj.problem_statement)),
        format_section("Learning outcomes", getattr(proj, "learning_outcomes", None)),
        format_section("Required Skills", skills_str),
        format_section("Components & Materials", getattr(proj, "components_and_materials", None)),
        format_section("System architecture", sanitize_markdown(proj.system_architecture)),
        format_section("Tech stack", stack_str),
        format_section("Implementation milestones", proj.step_by_step_milestones),
        format_section("Verification and testing", getattr(proj, "verification_steps", None)),
        format_section("Common pitfalls", getattr(proj, "common_pitfalls", None)),
        format_section("Stretch goals", proj.stretch_goals),
        format_section("Portfolio value", sanitize_markdown(proj.portfolio_impact)),
    ]
    return "\n\n".join(s for s in sections if s)


def format_vocabulary_glossary(glossary) -> str:
    """Format technical vocabulary glossary."""
    terms_str = "\n\n".join(f"*{sanitize_markdown(t.term)}*\n{sanitize_markdown(t.definition)}" for t in glossary.terms)
    return f"*Technical Glossary: {sanitize_markdown(glossary.topic)}*\n\n{terms_str}"


def format_learning_progress(progress_list: list) -> str:
    """Format user learning progress overview."""
    if not progress_list:
        return (
            "*Learning Progress*\n\n"
            "You have not completed any lessons or quizzes yet.\n\n"
            "Get started with:\n"
            "- `/roadmap AI` — View a curriculum\n"
            "- `/learn AI` — Start a lesson\n"
            "- `/quiz AI` — Take a quiz"
        )

    lines = ["*Learning Progress*\n"]
    for p in progress_list:
        accuracy = f"{int((p.quiz_score_total / p.quiz_score_max) * 100)}%" if p.quiz_score_max > 0 else "N/A"
        studied_str = format_date(p.last_studied_at, fallback="Recent")
        lines.append(
            f"- *{sanitize_markdown(p.topic.title())}* ({p.level.capitalize()})\n"
            f"  Lessons: {p.lessons_completed} · Quizzes: {p.quizzes_taken} (Accuracy: {accuracy})\n"
            f"  Last studied: {studied_str}\n"
        )

    lines.append("Continue with `/learn` or `/quiz`.")
    return "\n".join(lines)


def format_daily_briefing(articles: list, user_name: str = "", category_filter: str = "") -> str:
    """Format daily STEM intelligence briefing."""
    today_str = datetime.now(timezone.utc).strftime("%A, %d %B %Y").replace(" 0", " ")
    filter_label = f" · {sanitize_markdown(category_filter)}" if category_filter else ""
    user_greet = f" — {sanitize_markdown(user_name)}" if user_name else ""

    lines = [
        f"*Daily STEM Briefing*{user_greet}",
        f"{today_str}{filter_label}\n",
    ]

    if not articles:
        lines.append("No new developments recorded today. Run `/collect` to fetch recent updates.")
        return "\n".join(lines)

    for i, a in enumerate(articles[:5], 1):
        source = sanitize_markdown(a.source.name if a.source else "Source")
        cat = sanitize_markdown(a.categories[0].name if a.categories else "Technology")
        safe_title = sanitize_markdown(a.title)
        raw_desc = a.description or ""
        safe_desc = sanitize_markdown(raw_desc)
        short_desc = safe_desc[:140].rsplit(" ", 1)[0] + "..." if len(safe_desc) > 140 else safe_desc

        lines.append(f"{i}. [{safe_title}]({a.url})")
        lines.append(f"   {cat} · {source}")
        if short_desc:
            lines.append(f"   {short_desc}")
        lines.append("")

    lines.append("Use `/trends` for ranked developments or `/digest` for a concise summary.")
    return "\n".join(lines)


def format_weekly_report(articles: list, total_collected: int = 0, domain_breakdown: dict = None) -> str:
    """Format weekly intelligence report summarizing key developments across STEM domains."""
    today_str = format_date(datetime.now(timezone.utc))

    lines = [
        "*Weekly STEM Intelligence Report*",
        f"Week ending {today_str} · {total_collected} items indexed\n",
    ]

    if domain_breakdown:
        lines.append("*Most Active Domains*")
        for dom, count in list(domain_breakdown.items())[:5]:
            lines.append(f"- {sanitize_markdown(dom)}: {count}")
        lines.append("")

    if articles:
        lines.append("*Notable Developments*\n")
        for i, a in enumerate(articles[:5], 1):
            source = sanitize_markdown(a.source.name if a.source else "Source")
            cat = sanitize_markdown(a.categories[0].name if a.categories else "STEM")
            safe_title = sanitize_markdown(a.title)
            lines.append(f"{i}. [{safe_title}]({a.url})\n   {cat} · {source}")
        lines.append("")

    lines.append("Use `/briefing` for daily updates or `/settings` to manage subscriptions.")
    return "\n".join(lines)


def format_watchlist(watchlist: list) -> str:
    """Format user keyword and technology watchlist."""
    if not watchlist:
        return (
            "*Watchlist*\n\n"
            "You are not tracking any keywords yet.\n\n"
            "- `/watchlist add <keyword>` — Track a technology or topic\n"
            "- `/watchlist remove <keyword>` — Stop tracking a keyword\n"
            "- `/watchlist clear` — Remove all keywords\n\n"
            "Example: `/watchlist add humanoid`"
        )

    lines = [
        "*Active Watchlist*\n",
        "You will be notified when matching articles or papers arrive:\n",
    ]
    for w in watchlist:
        lines.append(f"- `#{w.keyword}` — {w.match_count} matches")

    lines.append("\nCommands: `/watchlist add <keyword>`, `/watchlist remove <keyword>`, `/watchlist clear`")
    return "\n".join(lines)


def format_watchlist_alert(article, matched_keyword: str) -> str:
    """Format real-time watchlist match alert."""
    source = sanitize_markdown(article.source.name if article.source else "Source")
    safe_title = sanitize_markdown(article.title)
    raw_desc = article.description or ""
    safe_desc = sanitize_markdown(raw_desc)
    if len(safe_desc) > 250:
        safe_desc = safe_desc[:247].rsplit(" ", 1)[0] + "..."

    return (
        f"*Watchlist Match: #{sanitize_markdown(matched_keyword)}*\n\n"
        f"*{safe_title}*\n"
        f"Source: {source}\n\n"
        f"{safe_desc}\n\n"
        f"[Read original]({article.url})\n"
        "Manage keywords with `/watchlist`."
    )


def format_high_impact_alert(article, score: float) -> str:
    """Format real-time high-impact development alert."""
    source = sanitize_markdown(article.source.name if article.source else "Source")
    safe_title = sanitize_markdown(article.title)
    cat = sanitize_markdown(article.categories[0].name if article.categories else "STEM")
    raw_desc = article.description or ""
    safe_desc = sanitize_markdown(raw_desc)
    if len(safe_desc) > 250:
        safe_desc = safe_desc[:247].rsplit(" ", 1)[0] + "..."

    return (
        f"*High-Impact Development* (Score: {score}/100)\n\n"
        f"*{safe_title}*\n"
        f"Category: {cat} · Source: {source}\n\n"
        f"{safe_desc}\n\n"
        f"[Read original]({article.url})\n"
        "Manage alerts and quiet hours with `/settings`."
    )


def format_trending_feed(scored_articles: list) -> str:
    """Format trending STEM developments feed ranked by impact score."""
    if not scored_articles:
        return "No trending articles scored yet. Run `/collect` to fetch recent updates."

    lines = ["*Trending STEM Developments*\n"]
    for i, (art, score) in enumerate(scored_articles[:7], 1):
        cat = sanitize_markdown(art.categories[0].name if art.categories else "Technology")
        source = sanitize_markdown(art.source.name if art.source else "Source")
        safe_title = sanitize_markdown(art.title)
        lines.append(f"{i}. [{safe_title}]({art.url})\n   {cat} · {source} · Score: {score}/100\n")

    lines.append("Ranked by recency, technical signal, and research depth.")
    return "\n".join(lines)


def format_platform_stats(stats: dict) -> str:
    """Format system telemetry and user intelligence statistics."""
    lines = [
        "*Platform Statistics*\n",
        "*Global Platform Scope*",
        f"- Indexed articles and papers: {stats.get('total_articles', 0):,}",
        f"- Active sources: {stats.get('active_sources', 0)}",
        f"- Monitored categories: {stats.get('stem_categories', 0)}",
        f"- Notifications delivered: {stats.get('total_notifications_sent', 0):,}\n",
    ]

    if "user_saved_articles" in stats:
        lines.extend(
            [
                "*Personal Intelligence Activity*",
                f"- Saved items: {stats.get('user_saved_articles', 0)} (`/saved`)",
                f"- Watchlist keywords: {stats.get('user_watchlist_keywords', 0)} (`/watchlist`)",
                f"- Notifications received: {stats.get('user_notifications_received', 0)}",
                f"- Quizzes completed: {stats.get('user_quizzes_taken', 0)} (`/progress`)",
            ]
        )

    return "\n".join(lines)


def format_tech_radar(
    horizon: str = "all",
    scored_articles: Optional[list] = None,
    domain_velocities: Optional[dict] = None,
) -> str:
    """Format interactive Technology Radar across 4 adoption horizons."""
    clean_horizon = (horizon or "all").lower().strip()

    if clean_horizon == "adopt":
        content = (
            "*STEM Technology Radar — ADOPT*\n\n"
            "Technologies with proven production stability and broad engineering support.\n\n"
            "1. *LLM Orchestration & Vector RAG*\n"
            "   Tools: Qdrant, Chroma, LlamaIndex, pgvector\n"
            "   Note: Standard approach for grounding language models on verified documents.\n\n"
            "2. *PyTorch 2.x & Graph Compilation*\n"
            "   Tools: TorchDynamo, TorchInductor, Triton kernels\n"
            "   Note: Standard runtime for training and inference.\n\n"
            "3. *FlashAttention-2 & Memory-Efficient Attention*\n"
            "   Tools: Tiling algorithms, fused CUDA kernels\n"
            "   Note: Baseline requirement for long-context sequence modeling.\n\n"
            "4. *Rust for Systems & Embedded Firmware*\n"
            "   Focus: Memory safety without garbage-collection latency\n"
            "   Note: Strong choice for high-concurrency services, robotics controllers, and WASM."
        )
    elif clean_horizon == "trial":
        content = (
            "*STEM Technology Radar — TRIAL*\n\n"
            "Technologies validated in labs or pilots, ready for controlled evaluation.\n\n"
            "1. *Vision-Language-Action (VLA) Robotics Models*\n"
            "   Examples: RT-2, OpenVLA, Octo\n"
            "   Focus: Tokenized control of robotic end-effectors from visual inputs.\n\n"
            "2. *Sim-to-Real Reinforcement Learning Locomotion*\n"
            "   Examples: Isaac Gym, domain randomization, humanoid walk policies\n"
            "   Focus: Dynamic balance recovery beyond classical inverse kinematics.\n\n"
            "3. *On-Device Small Language Models (SLMs)*\n"
            "   Examples: 1B-4B quantized architectures (GGUF, AWQ, EXL2)\n"
            "   Focus: Offline, low-latency inference on edge hardware.\n\n"
            "4. *Neuromorphic Event-Based Sensors*\n"
            "   Examples: Dynamic Vision Sensors (DVS), Spiking Neural Networks\n"
            "   Focus: Low-power sensing with microsecond temporal resolution."
        )
    elif clean_horizon == "assess":
        content = (
            "*STEM Technology Radar — ASSESS*\n\n"
            "Emerging research directions worth tracking and experimental prototyping.\n\n"
            "1. *Quantum Error Mitigation & Logical Qubits*\n"
            "   Examples: Surface codes, neutral-atom lattices, fault-tolerant gates\n"
            "   Status: Transitioning from NISQ devices toward error suppression.\n\n"
            "2. *High-Temperature Superconductivity*\n"
            "   Examples: Hydrides under compression, nickelate thin films\n"
            "   Status: Active laboratory replication and peer review.\n\n"
            "3. *Non-Invasive Brain-Computer Interfaces (BCI)*\n"
            "   Examples: High-density EEG, neural speech decoders\n"
            "   Status: Clinical trials and assistive communication systems.\n\n"
            "4. *Automated Synthetic Biology Foundries*\n"
            "   Examples: High-throughput DNA synthesis, enzymatic optimization\n"
            "   Status: Pilot biomanufacturing scale-up."
        )
    elif clean_horizon == "hold":
        content = (
            "*STEM Technology Radar — HOLD*\n\n"
            "Deprecated architectures, lock-in risks, or unverified claims to avoid for new systems.\n\n"
            "1. *Monolithic RNNs / LSTMs for Long Context*\n"
            "   Reason: Sequential bottlenecks limit GPU scaling compared to Transformers and SSMs.\n\n"
            "2. *Proprietary Closed Formats without Export*\n"
            "   Reason: Creates vendor lock-in and blocks independent evaluation.\n\n"
            "3. *Unquantized Large Models on Edge Devices*\n"
            "   Reason: Causes memory saturation, battery drain, and thermal throttling.\n\n"
            "4. *Unverified Claims without Code or Peer Review*\n"
            "   Reason: High risk of non-reproducible results."
        )
    else:
        content = (
            "*STEM Technology Radar (Q4 2026)*\n\n"
            "Technologies grouped into four adoption stages:\n\n"
            "*ADOPT:* LLM RAG Pipelines, PyTorch 2.x, FlashAttention-2, Rust Systems\n"
            "*TRIAL:* Vision-Language-Action (VLA), Humanoid RL, On-Device SLMs, Neuromorphic Chips\n"
            "*ASSESS:* Quantum Error Mitigation, High-Temp Superconductors, Non-Invasive BCI, SynBio\n"
            "*HOLD:* Monolithic RNNs, Closed Lock-in Formats, Unquantized Edge Models, Unverified Claims"
        )

    lines = [content]
    if domain_velocities:
        lines.append("\n*Empirical Domain Velocity*")
        for slug, d in list(domain_velocities.items())[:4]:
            lines.append(
                f"- *{sanitize_markdown(d.get('name', slug.title()))}*: {d.get('momentum', 'Stable')} "
                f"({d.get('count', 0)} articles, {d.get('paper_count', 0)} papers)"
            )
    elif scored_articles:
        lines.append("\n*Recent High-Signal Items*")
        for idx, item in enumerate(scored_articles[:3], 1):
            art = item[0] if isinstance(item, (tuple, list)) else item
            score = item[1] if isinstance(item, (tuple, list)) else 80.0
            lines.append(f"{idx}. {sanitize_markdown(art.title[:65])} (Score: {score:.1f})")

    lines.append("\nSelect a horizon below to filter.")
    return "\n".join(lines)


def format_trend_velocity(domain_velocities: dict) -> str:
    """Format evidence-based STEM trend velocity and momentum report."""
    if not domain_velocities:
        return "No trend momentum data calculated yet. Run `/collect` first."

    lines = [
        "*STEM Domain Velocity*\n",
        "Measured from recent publication volume, recency, and ranking scores:\n",
    ]

    for slug, d in domain_velocities.items():
        name = sanitize_markdown(d.get("name", slug.title()))
        momentum = d.get("momentum", "Stable")
        count = d.get("count", 0)
        papers = d.get("paper_count", 0)
        avg_score = d.get("avg_score", 0.0)
        top = d.get("top_headline", "")

        lines.append(
            f"*{name}*\n"
            f"Momentum: {momentum} · Articles: {count} (Papers: {papers}) · Avg score: {avg_score:.1f}/100\n"
            f"Top headline: {sanitize_markdown(top[:80])}\n"
        )

    lines.append("_Indicators reflect indexed database records and research activity._")
    return "\n".join(lines)
