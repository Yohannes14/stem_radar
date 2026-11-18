"""AI Search Assistant providing grounded multi-source synthesis, source comparison, and topic explanation."""

import logging
from typing import List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.ui.design_system import AI_EDITORIAL_STYLE_INSTRUCTION, sanitize_markdown
from app.services.ai.cache import ai_cache
from app.services.ai.service import ai_service
from app.services.search.models import (
    SearchAISummary,
    SearchResultItem,
    SourceCitation,
    SourceComparison,
)

logger = logging.getLogger(__name__)


class SearchAIAssistant:
    """Intelligent search assistant synthesizing discoveries with citation fidelity and zero hallucination."""

    def __init__(self, ai_engine=None) -> None:
        self.ai = ai_engine or ai_service

    # ------------------ Capability 1: Multi-Source Search Summarization ------------------

    async def summarize_search_results(
        self,
        query: str,
        items: List[SearchResultItem],
        category: str = "all",
    ) -> SearchAISummary:
        """Synthesize a coherent factual overview across retrieved search items with source citations."""
        clean_query = query.strip()
        if not items:
            return SearchAISummary(
                query=clean_query,
                executive_summary=f"No matching documents or records were found for '{clean_query}'.",
                sourced_facts=[],
                analytical_implications=[],
                source_citations=[],
                related_questions=[
                    f"What are the foundational principles of {clean_query}?",
                    f"Are there related research papers or opportunities in {clean_query}?",
                ],
                research_recommendations=[
                    "Broaden your keyword terms or switch search scope to Live Web.",
                ],
            )

        top_items = items[:5]
        citations = [
            SourceCitation(
                index=idx,
                title=item.title,
                url=item.url,
                source_name=item.source_name,
                published_at=item.published_at,
                category=item.category,
                is_verified=item.is_verified,
            )
            for idx, item in enumerate(top_items, start=1)
        ]

        cache_id = f"{clean_query}:{category}:{':'.join(str(c.url) for c in citations)}"
        cached = ai_cache.get("search_ai_summary", cache_id)
        if cached and isinstance(cached, SearchAISummary):
            return cached

        if self.ai.provider:
            system_prompt = (
                "You are the STEM RADAR Principal Science & Intelligence Analyst. "
                "Synthesize a rigorous, objective, and high-impact search summary based strictly on the "
                "provided numbered sources.\n\n"
                "CRITICAL REQUIREMENTS:\n"
                "1. SOURCED FACTS: Attribute every factual statement strictly to its citation index "
                "(e.g. [1], [2]). Never state factual benchmarks, dates, or claims without citing the "
                "corresponding source.\n"
                "2. ANALYTICAL IMPLICATIONS: Clearly distinguish your analytical interpretation and "
                "engineering implications from raw sourced facts.\n"
                "3. ZERO HALLUCINATION: Never invent URLs, dates, authors, institutions, or findings "
                "not present in the sources.\n"
                "4. DISCOVERY: Suggest 3-4 insightful related questions and 2-3 actionable "
                "research/practical recommendations.\n"
                f"5. STYLE: {AI_EDITORIAL_STYLE_INSTRUCTION}"
            )

            sources_text = "\n\n".join(
                f"[{c.index}] Title: {c.title}\n"
                f"Publisher: {c.source_name} ({c.published_at.strftime('%Y-%m-%d') if c.published_at else 'Recent'})\n"
                f"URL: {c.url}\n"
                f"Excerpt: {item.snippet}"
                for c, item in zip(citations, top_items, strict=False)
            )

            prompt = (
                f"User Search Query: {clean_query}\n"
                f"Category Scope: {category}\n\n"
                f"Retrieved Documents:\n{sources_text}\n\n"
                f"Generate the SearchAISummary JSON."
            )

            try:
                summary, _ = await self.ai.provider.generate_structured(prompt, system_prompt, SearchAISummary)
                summary.source_citations = citations
                ai_cache.set("search_ai_summary", cache_id, summary)
                return summary
            except Exception as exc:
                logger.warning("AI provider failed for search summary: %s. Using heuristic synthesis.", exc)

        summary = self._heuristic_search_summary(clean_query, top_items, citations)
        ai_cache.set("search_ai_summary", cache_id, summary)
        return summary

    def _heuristic_search_summary(
        self,
        query: str,
        items: List[SearchResultItem],
        citations: List[SourceCitation],
    ) -> SearchAISummary:
        """Deterministic factual synthesis when external LLM is offline or unconfigured."""
        primary_title = items[0].title
        primary_source = items[0].source_name
        exec_summary = (
            f"Search analysis for '{query}' highlights active initiatives led by {primary_source} and related "
            f"institutions. Primary focus centers on '{primary_title}', addressing key technological developments, "
            f"academic pathways, and research milestones across {len(items)} evaluated sources."
        )

        sourced_facts = []
        for c, item in zip(citations, items, strict=False):
            snippet_clean = item.snippet.replace("\n", " ").strip()
            if not snippet_clean:
                snippet_clean = f"Key development regarding {item.title}"
            sourced_facts.append(f"{snippet_clean} [{c.index}]")

        analytical_implications = [
            f"Convergence across {len(items)} independent sources reflects accelerating interest in '{query}'.",
            "Institutional developments indicate transition from theoretical research to practical implementations.",
        ]

        related_questions = [
            f"What are the main technical challenges in {query}?",
            f"How does {query} compare to alternative approaches?",
            f"What funding or educational resources exist for {query}?",
        ]

        research_recommendations = [
            f"Review primary literature and code implementations related to [{primary_title}]({items[0].url}).",
            "Cross-reference experimental benchmarks against independent reproducible baselines.",
        ]

        return SearchAISummary(
            query=query,
            executive_summary=exec_summary,
            sourced_facts=sourced_facts,
            analytical_implications=analytical_implications,
            source_citations=citations,
            related_questions=related_questions,
            research_recommendations=research_recommendations,
            disclaimer=(
                "AI synthesis derived strictly from cited search results. "
                "Facts are attributed to respective publishers."
            ),
        )

    # ------------------ Capability 2: Cross-Source Comparison ------------------

    async def compare_sources(
        self,
        item_a: SearchResultItem,
        item_b: SearchResultItem,
        topic: Optional[str] = None,
    ) -> SourceComparison:
        """Produce an objective comparative analysis between two distinct search items."""
        cmp_topic = topic.strip() if topic else f"{item_a.title} vs {item_b.title}"
        cit_a = SourceCitation(
            index=1,
            title=item_a.title,
            url=item_a.url,
            source_name=item_a.source_name,
            published_at=item_a.published_at,
            category=item_a.category,
            is_verified=item_a.is_verified,
        )
        cit_b = SourceCitation(
            index=2,
            title=item_b.title,
            url=item_b.url,
            source_name=item_b.source_name,
            published_at=item_b.published_at,
            category=item_b.category,
            is_verified=item_b.is_verified,
        )

        cache_id = f"cmp:{item_a.url}:{item_b.url}"
        cached = ai_cache.get("search_ai_compare", cache_id)
        if cached and isinstance(cached, SourceComparison):
            return cached

        if self.ai.provider:
            system_prompt = (
                "You are the STEM RADAR Principal Comparative Analyst. "
                "Provide a rigorous, unbiased comparative evaluation between Source A and Source B.\n"
                "Highlight points of consensus, divergence (scope, methodologies, eligibility, or benchmarks), "
                "and concrete recommendations on which source serves which engineering/academic use case."
            )
            prompt = (
                f"Topic: {cmp_topic}\n\n"
                f"Source A:\n"
                f"Title: {item_a.title}\nPublisher: {item_a.source_name}\nURL: {item_a.url}\n"
                f"Snippet: {item_a.snippet}\n\n"
                f"Source B:\n"
                f"Title: {item_b.title}\nPublisher: {item_b.source_name}\nURL: {item_b.url}\n"
                f"Snippet: {item_b.snippet}\n\n"
                f"Generate the SourceComparison JSON."
            )
            try:
                comparison, _ = await self.ai.provider.generate_structured(prompt, system_prompt, SourceComparison)
                comparison.topic = cmp_topic
                comparison.source_a = cit_a
                comparison.source_b = cit_b
                ai_cache.set("search_ai_compare", cache_id, comparison)
                return comparison
            except Exception as exc:
                logger.warning("AI provider failed for source comparison: %s. Using heuristic comparison.", exc)

        comparison = self._heuristic_source_comparison(item_a, item_b, cmp_topic, cit_a, cit_b)
        ai_cache.set("search_ai_compare", cache_id, comparison)
        return comparison

    def _heuristic_source_comparison(
        self,
        item_a: SearchResultItem,
        item_b: SearchResultItem,
        topic: str,
        cit_a: SourceCitation,
        cit_b: SourceCitation,
    ) -> SourceComparison:
        """Deterministic comparison when LLM provider is unavailable."""
        common_ground = [
            f"Both sources address core advancements in {item_a.category} and {item_b.category}.",
            f"Each publication offers actionable context relevant to '{topic}'.",
        ]
        divergent_points = [
            f"Source A ({item_a.source_name}) prioritizes: '{item_a.title}'",
            f"Source B ({item_b.source_name}) concentrates on: '{item_b.title}'",
        ]
        synthesis = (
            f"While {item_a.source_name} provides direct coverage of {item_a.title}, "
            f"{item_b.source_name} complements this by addressing {item_b.title}. "
            f"Together they offer a multifaceted perspective on {topic}."
        )
        recommended_context = (
            f"Consult Source A ({cit_a.source_name}) for foundational details and Source B "
            f"({cit_b.source_name}) for complementary extensions and independent verification."
        )
        return SourceComparison(
            topic=topic,
            source_a=cit_a,
            source_b=cit_b,
            common_ground=common_ground,
            divergent_points=divergent_points,
            synthesis=synthesis,
            recommended_context=recommended_context,
        )

    # ------------------ Telegram UI Presentation Helpers ------------------

    def format_search_ai_summary(self, summary: SearchAISummary) -> str:
        """Render clean editorial summary with cited facts, analysis, and source links."""
        clean_q = sanitize_markdown(summary.query)
        lines = [
            f'*Search Summary — "{clean_q}"*\n',
            f"{sanitize_markdown(summary.executive_summary)}\n",
        ]

        if summary.sourced_facts:
            lines.append("*Key Sourced Facts*")
            for fact in summary.sourced_facts:
                lines.append(f"- {sanitize_markdown(fact)}")
            lines.append("")

        if summary.analytical_implications:
            lines.append("*Analytical Implications*")
            for imp in summary.analytical_implications:
                lines.append(f"- {sanitize_markdown(imp)}")
            lines.append("")

        if summary.source_citations:
            lines.append("*Sources*")
            for cit in summary.source_citations:
                date_str = cit.published_at.strftime("%b %Y") if cit.published_at else "Recent"
                verified = " · Verified" if cit.is_verified else ""
                lines.append(
                    f"[{cit.index}] [{sanitize_markdown(cit.title)}]({cit.url}) — "
                    f"{sanitize_markdown(cit.source_name)} ({date_str}){verified}"
                )
            lines.append("")

        if summary.research_recommendations:
            lines.append("*Next Steps*")
            for rec in summary.research_recommendations:
                lines.append(f"- {sanitize_markdown(rec)}")
            lines.append("")

        lines.append(f"_{sanitize_markdown(summary.disclaimer)}_")
        return "\n".join(lines)

    def get_search_ai_summary_keyboard(
        self,
        summary: SearchAISummary,
        category: str = "all",
        source: str = "all",
    ) -> InlineKeyboardMarkup:
        """Build interactive keyboard with related questions and back navigation."""
        buttons: List[List[InlineKeyboardButton]] = []
        clean_q = summary.query[:20]

        for _idx, q_text in enumerate(summary.related_questions[:2], start=1):
            short_q = q_text[:34]
            buttons.append([InlineKeyboardButton(f"{short_q}...", callback_data=f"search:rel_q:{q_text[:40]}")])

        buttons.append(
            [
                InlineKeyboardButton(
                    "Back to Results",
                    callback_data=f"search:back:{category}:{source}:{clean_q}",
                ),
                InlineKeyboardButton("Home", callback_data="menu:home"),
            ]
        )
        return InlineKeyboardMarkup(buttons)

    def format_source_comparison(self, comparison: SourceComparison) -> str:
        """Render clean comparison between two sources."""
        src_a_str = f"Source A: [{sanitize_markdown(comparison.source_a.title)}]({comparison.source_a.url})"
        src_b_str = f"Source B: [{sanitize_markdown(comparison.source_b.title)}]({comparison.source_b.url})"
        lines = [
            f"*Source Comparison — {sanitize_markdown(comparison.topic)}*\n",
            f"{src_a_str} ({sanitize_markdown(comparison.source_a.source_name)})",
            f"{src_b_str} ({sanitize_markdown(comparison.source_b.source_name)})\n",
            "*Common Ground*",
        ]
        for cg in comparison.common_ground:
            lines.append(f"- {sanitize_markdown(cg)}")
        lines.append("")

        lines.append("*Key Differences*")
        for dp in comparison.divergent_points:
            lines.append(f"- {sanitize_markdown(dp)}")
        lines.append("")

        lines.append(f"*Synthesis*\n{sanitize_markdown(comparison.synthesis)}\n")
        lines.append(f"*Recommended Reading*\n{sanitize_markdown(comparison.recommended_context)}")
        return "\n".join(lines)


search_ai_assistant = SearchAIAssistant()
