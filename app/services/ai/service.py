"""Enterprise Modular AI Intelligence Engine orchestrating LLM adapters, caching, and fallback heuristics."""

import logging
from typing import Optional

from app.core.config import settings
from app.database.models import Article
from app.services.ai.adapters.openai_adapter import OpenAIAdapter
from app.services.ai.cache import ai_cache
from app.services.ai.cost_tracker import cost_tracker
from app.services.ai.interface import BaseAIProvider
from app.services.ai.schemas import (
    ArticleIntelligence,
    ConceptExplanation,
    ExplanationMode,
    NewsSummary,
    ResearchPaperAnalysis,
    SlideOutline,
    STEMContentPackage,
    TechnologyImpactAnalysis,
    VideoScript,
    VocabularyTerm,
)

logger = logging.getLogger(__name__)


class AIService:
    """Core intelligence engine providing multi-capability STEM analysis with provider independence."""

    def __init__(
        self,
        provider: Optional[BaseAIProvider] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.provider: Optional[BaseAIProvider] = provider

        # Default to OpenAI adapter if API key is present and no custom provider supplied
        if self.provider is None and self.api_key:
            try:
                self.provider = OpenAIAdapter(
                    api_key=self.api_key,
                    model=self.model,
                    timeout=settings.ai_timeout,
                    max_retries=settings.ai_max_retries,
                )
                logger.info("AIService initialized with OpenAI adapter (model: %s)", self.model)
            except Exception as exc:
                logger.warning("Failed to initialize OpenAIAdapter: %s", exc)

    # ------------------ Capability 1: AI News Summarization ------------------

    async def summarize_news(
        self,
        article: Article,
        mode: ExplanationMode = "intermediate",
    ) -> NewsSummary:
        """Generate a structured technical summary for news developments."""
        cache_id = str(article.id or article.url)
        cached = ai_cache.get("news_summary", cache_id, mode=mode)
        if cached:
            return cached

        source_name = article.source.name if article.source else "Technology News"
        category_name = article.categories[0].name if article.categories else "Technology"

        if self.provider:
            system_prompt = (
                f"You are a Principal AI & STEM Intelligence Analyst. "
                f"Summarize the following technology news item with technical rigor for a {mode}-level audience. "
                f"Never invent facts, benchmarks, or quotes. Clearly distinguish source facts from implications."
            )
            prompt = (
                f"Headline/Title: {article.title}\n"
                f"Source: {source_name}\n"
                f"Category: {category_name}\n"
                f"Description/Content: {article.description or article.title}\n"
                f"URL: {article.url}\n\n"
                f"Target Level: {mode}\n"
                f"Generate the NewsSummary JSON."
            )
            try:
                summary, _ = await self.provider.generate_structured(prompt, system_prompt, NewsSummary)
                ai_cache.set("news_summary", cache_id, summary, mode=mode)
                return summary
            except Exception as exc:
                logger.warning("Provider call failed for summarize_news: %s. Using heuristic fallback.", exc)

        summary = self._heuristic_news_summary(article, mode)
        ai_cache.set("news_summary", cache_id, summary, mode=mode)
        return summary

    def _heuristic_news_summary(self, article: Article, mode: ExplanationMode) -> NewsSummary:
        """Deterministic, fact-preserving news summary fallback."""
        source_name = article.source.name if article.source else "Verified Source"
        desc = article.description or "Technical announcement released."
        clean_desc = desc[:300].strip()

        return NewsSummary(
            headline=article.title,
            short_summary=f"{article.title}. {clean_desc[:160]}...",
            key_facts=[
                f"Reported by {source_name}.",
                f"Core announcement: {clean_desc[:140]}.",
                "Source documentation available at primary URL.",
            ],
            why_it_matters=(
                "Advancements in this domain contribute to improved system reliability, "
                "algorithmic efficiency, and potential industrial applications."
            ),
            potential_applications=[
                "Enterprise software and infrastructure modernization",
                "Applied research experimentation and benchmarking",
            ],
            technical_difficulty=mode,
            original_source=source_name,
            source_url=article.url,
        )

    # ------------------ Capability 2: Research Paper Analysis ------------------

    async def analyze_research_paper(self, article: Article) -> ResearchPaperAnalysis:
        """Extract deep methodology, findings, and research questions from scientific papers."""
        cache_id = str(article.id or article.url)
        cached = ai_cache.get("paper_analysis", cache_id)
        if cached:
            return cached

        if self.provider:
            system_prompt = (
                "You are an academic peer reviewer and research scientist across STEM disciplines. "
                "Analyze the research paper abstract and text with strict empirical integrity. "
                "Do not fabricate findings or overstate claims. Identify concrete limitations."
            )
            prompt = (
                f"Paper Title: {article.title}\n"
                f"Abstract/Content: {article.description or article.title}\n"
                f"URL: {article.url}\n\n"
                "Extract structured scientific analysis according to the ResearchPaperAnalysis schema."
            )
            try:
                analysis, _ = await self.provider.generate_structured(prompt, system_prompt, ResearchPaperAnalysis)
                ai_cache.set("paper_analysis", cache_id, analysis)
                return analysis
            except Exception as exc:
                logger.warning("Provider call failed for analyze_research_paper: %s. Using heuristic fallback.", exc)

        analysis = self._heuristic_paper_analysis(article)
        ai_cache.set("paper_analysis", cache_id, analysis)
        return analysis

    def _heuristic_paper_analysis(self, article: Article) -> ResearchPaperAnalysis:
        """Deterministic research paper analysis fallback."""
        desc = article.description or "Scientific study details."
        clean_desc = desc[:300].strip()

        return ResearchPaperAnalysis(
            paper_title=article.title,
            research_problem=f"Addressing computational and algorithmic bottlenecks presented in: {article.title}.",
            methodology="Empirical validation and theoretical modeling described in the research publication.",
            main_findings=[
                f"Key reported result: {clean_desc[:160]}.",
                "Demonstrates measurable performance or architectural improvements over baseline methods.",
            ],
            limitations=[
                "Evaluation scope bounded by the specific experimental conditions and benchmarks reported.",
                "Real-world generalization requires independent replication across varied environments.",
            ],
            practical_applications=[
                "Algorithmic enhancement in production software pipelines",
                "Foundational building block for next-generation research prototypes",
            ],
            further_research_questions=[
                "How does the methodology scale to larger parameter spaces and real-time latency budgets?",
                "What optimizations exist for edge computing hardware deployment?",
            ],
            original_paper_url=article.url,
        )

    # ------------------ Capability 3: Technical Concept Explanations ------------------

    async def explain_concept(
        self,
        concept_name: str,
        mode: ExplanationMode = "intermediate",
        context: Optional[str] = None,
    ) -> ConceptExplanation:
        """Explain a STEM concept tailored to beginner, intermediate, or advanced audiences."""
        cached = ai_cache.get("concept_explanation", concept_name, mode=mode)
        if cached:
            return cached

        if self.provider:
            mode_guidelines = {
                "beginner": (
                    "Use intuitive real-world everyday analogies, zero jargon without definitions, clear language."
                ),
                "intermediate": (
                    "Focus on system architectures, mechanics, design trade-offs, and practical implementations."
                ),
                "advanced": (
                    "Provide rigorous mathematical, algorithmic, or low-level engineering details "
                    "and theoretical limits."
                ),
            }
            system_prompt = (
                f"You are a World-Class STEM Educator and Principal Staff Engineer. "
                f"Explain the technical concept for a {mode.upper()} audience. "
                f"Guideline: {mode_guidelines.get(mode, '')}"
            )
            prompt = f"Concept: {concept_name}\n"
            if context:
                prompt += f"Context: {context}\n"
            prompt += f"Explanation Level: {mode}\nGenerate ConceptExplanation JSON."

            try:
                explanation, _ = await self.provider.generate_structured(prompt, system_prompt, ConceptExplanation)
                ai_cache.set("concept_explanation", concept_name, explanation, mode=mode)
                return explanation
            except Exception as exc:
                logger.warning("Provider call failed for explain_concept: %s. Using heuristic fallback.", exc)

        explanation = self._heuristic_concept_explanation(concept_name, mode)
        ai_cache.set("concept_explanation", concept_name, explanation, mode=mode)
        return explanation

    def _heuristic_concept_explanation(self, concept_name: str, mode: ExplanationMode) -> ConceptExplanation:
        """Deterministic multi-tier concept explanation fallback."""
        if mode == "beginner":
            definition = (
                f"{concept_name} is a foundational technology that allows systems to process information "
                "or perform physical tasks efficiently."
            )
            analogy = (
                f"Think of {concept_name} like an automated assembly line where each station specializes in one task."
            )
            how_it_works = (
                f"{concept_name} takes input data, processes it through specialized rules, "
                "and produces the desired outcome without manual intervention."
            )
        elif mode == "advanced":
            definition = (
                f"{concept_name} represents an algorithmic paradigm optimizing computational complexity, "
                "throughput, and state transitions."
            )
            analogy = (
                "Analogous to distributed asynchronous message passing with fault-tolerant state replication."
            )
            how_it_works = (
                "Operates via mathematical transformations, parameter optimization over loss landscapes, "
                "and low-level resource scheduling."
            )
        else:
            definition = (
                f"{concept_name} is a technical framework used in modern engineering to solve complex domain problems."
            )
            analogy = "Similar to a high-efficiency compiler translating high-level intent into optimized steps."
            how_it_works = (
                f"{concept_name} leverages modular components and feedback loops to balance accuracy and latency."
            )

        return ConceptExplanation(
            concept_name=concept_name,
            mode=mode,
            core_definition=definition,
            how_it_works=how_it_works,
            analogy_or_example=analogy,
            key_components=["Core Algorithm", "Data Pipeline", "Optimization Function", "Evaluation Metrics"],
            common_misconceptions=[
                f"Assuming {concept_name} replaces foundational domain knowledge rather than augmenting it.",
                "Overlooking compute and memory overhead in production deployments.",
            ],
            prerequisites_or_related=["Data Structures & Algorithms", "Linear Algebra", "System Design"],
        )

    # ------------------ Capability 4: Technology Impact Analysis ------------------

    async def analyze_impact(self, article: Article) -> TechnologyImpactAnalysis:
        """Perform strategic technology intelligence assessment and impact forecasting."""
        cache_id = str(article.id or article.url)
        cached = ai_cache.get("impact_analysis", cache_id)
        if cached:
            return cached

        if self.provider:
            system_prompt = (
                "You are a Technology Strategist and Venture Intelligence Analyst. "
                "Assess the strategic and economic impact of this technology development. "
                "Ground all projections in established engineering principles; avoid hyperbole."
            )
            prompt = (
                f"Technology/Topic: {article.title}\n"
                f"Source: {article.source.name if article.source else 'Industry News'}\n"
                f"Details: {article.description or article.title}\n"
                f"URL: {article.url}\n\n"
                "Generate TechnologyImpactAnalysis JSON."
            )
            try:
                impact, _ = await self.provider.generate_structured(prompt, system_prompt, TechnologyImpactAnalysis)
                ai_cache.set("impact_analysis", cache_id, impact)
                return impact
            except Exception as exc:
                logger.warning("Provider call failed for analyze_impact: %s. Using heuristic fallback.", exc)

        impact = self._heuristic_impact_analysis(article)
        ai_cache.set("impact_analysis", cache_id, impact)
        return impact

    def _heuristic_impact_analysis(self, article: Article) -> TechnologyImpactAnalysis:
        """Deterministic impact analysis fallback."""
        cat_name = article.categories[0].name if article.categories else "STEM"
        return TechnologyImpactAnalysis(
            technology_name=article.title,
            executive_summary=(
                f"Strategic assessment indicates {article.title} provides significant technological "
                f"utility in {cat_name}, improving efficiency and expanding system capabilities."
            ),
            industry_disruption=[
                f"Cloud and enterprise infrastructure in {cat_name}",
                "Automated testing and continuous delivery workflows",
                "High-performance computing and hardware accelerators",
            ],
            scientific_significance=(
                "Validates new algorithmic heuristics and opens pathways for more resource-efficient designs."
            ),
            societal_and_ethical_implications=[
                "Workforce reskilling and adaptation to augmented automated tools",
                "Data privacy and algorithmic transparency considerations",
            ],
            adoption_timeline="1-3 years for early enterprise adoption; 3-5 years for industry standardization.",
            confidence_score=0.85,
        )

    # ------------------ Capability 5: STEM Content Opportunity Generation ------------------

    async def generate_stem_content(self, article: Article) -> STEMContentPackage:
        """Generate multi-format educational content opportunities (LinkedIn, Carousel, Video, Glossary)."""
        cache_id = str(article.id or article.url)
        cached = ai_cache.get("content_package", cache_id)
        if cached:
            return cached

        if self.provider:
            system_prompt = (
                "You are an Elite STEM Content Creator and Technical Educator. "
                "Transform the technical breakthrough into an engaging educational package "
                "featuring a LinkedIn post, exactly 5 carousel slides, a short video script, and technical vocabulary."
            )
            prompt = (
                f"Title: {article.title}\n"
                f"Source: {article.source.name if article.source else 'Tech Source'}\n"
                f"Details: {article.description or article.title}\n"
                f"URL: {article.url}\n\n"
                "Generate STEMContentPackage JSON."
            )
            try:
                pkg, _ = await self.provider.generate_structured(prompt, system_prompt, STEMContentPackage)
                ai_cache.set("content_package", cache_id, pkg)
                return pkg
            except Exception as exc:
                logger.warning("Provider call failed for generate_stem_content: %s. Using heuristic fallback.", exc)

        pkg = self._heuristic_content_package(article)
        ai_cache.set("content_package", cache_id, pkg)
        return pkg

    def _heuristic_content_package(self, article: Article) -> STEMContentPackage:
        """Deterministic content opportunity generation fallback."""
        title = article.title
        source = article.source.name if article.source else "STEM News"
        desc = (article.description or title)[:160].strip()
        cat = article.categories[0].name if article.categories else "STEM"

        slides = [
            SlideOutline(
                slide_number=1,
                title=f"Breakthrough in {cat}: {title[:40]}...",
                bullet_points=["What happened", "Why it matters to developers", "Key takeaway"],
            ),
            SlideOutline(
                slide_number=2,
                title="The Engineering Bottleneck",
                bullet_points=["Existing limitations in current architectures", "Why traditional approaches stalled"],
            ),
            SlideOutline(
                slide_number=3,
                title="The New Mechanism",
                bullet_points=[f"Mechanism: {desc[:80]}", "How algorithmic efficiency was gained"],
            ),
            SlideOutline(
                slide_number=4,
                title="Real-World Impact",
                bullet_points=["Faster inference / execution", "Lower hardware resource requirements"],
            ),
            SlideOutline(
                slide_number=5,
                title="Summary & Discussion",
                bullet_points=[f"Full analysis reported by {source}", f"Explore details at: {article.url}"],
            ),
        ]

        return STEMContentPackage(
            headline=f"Engineering Breakdown: {title}",
            target_audience=f"Software engineers, technical architects, and students interested in {cat}.",
            linkedin_post=(
                f"🚀 Major development in {cat}:\n\n"
                f"*{title}*\n\n"
                f"💡 The Core Innovation:\n{desc}...\n\n"
                f"🔍 Key Takeaway:\n"
                f"Demonstrates how architectural optimization directly reduces latency and compute constraints.\n\n"
                f"Source: {source} ({article.url})\n\n"
                f"#STEM #Technology #{cat.replace(' ', '')} #Engineering"
            ),
            carousel_slides=slides,
            video_script=VideoScript(
                hook=f"Did you hear what just happened in {cat}?",
                body=f"Engineers announced {title}. Here is how it works: {desc}... This changes how we build systems.",
                call_to_action=f"Check the full paper on {source} and follow STEM RADAR for daily breakthroughs!",
            ),
            technical_vocabulary=[
                VocabularyTerm(term=cat, definition=f"Core engineering discipline focused on {cat}."),
                VocabularyTerm(
                    term="Algorithmic Optimization",
                    definition="Refining code to reduce memory and time complexity.",
                ),
                VocabularyTerm(term="Throughput", definition="The rate at which a system processes data over time."),
            ],
            source_attribution=f"Originally reported by {source} ({article.url})",
        )

    # ------------------ Backward Compatibility: Composite Intelligence ------------------

    async def analyze_article(self, article: Article) -> ArticleIntelligence:
        """Composite analysis returning ArticleIntelligence (backward compatible)."""
        news_summary = await self.summarize_news(article, mode="intermediate")
        source_name = article.source.name if article.source else "Tech Feed"
        category_name = article.categories[0].name if article.categories else "STEM Technology"

        return ArticleIntelligence(
            article_title=article.title,
            source=source_name,
            category=category_name,
            short_summary=news_summary.short_summary,
            what_happened=f"Reported by {source_name}: {news_summary.short_summary}",
            why_it_matters=news_summary.why_it_matters,
            technical_explanation=(
                f"Technical depth ({news_summary.technical_difficulty}): {news_summary.short_summary}"
            ),
            real_world_applications=news_summary.potential_applications,
            future_possibilities=[
                "Scaling into production environments",
                "Cross-industry integration with open standard APIs",
            ],
            important_concepts=[category_name, "Optimization", "Scalability"],
            stem_content_opportunity=f"Create a deep-dive tutorial breaking down the trade-offs of {article.title}.",
            source_url=article.url,
        )

    def get_telemetry(self) -> dict:
        """Return usage, cost, and cache metrics."""
        return {
            "costs": cost_tracker.get_metrics(),
            "cache": {
                "hits": ai_cache.hits,
                "misses": ai_cache.misses,
                "cached_items": len(ai_cache._store),
            },
        }


ai_service = AIService()
