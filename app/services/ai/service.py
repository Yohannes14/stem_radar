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
    ComparisonDimension,
    ConceptComparison,
    ConceptExplanation,
    ExplanationMode,
    InteractiveLesson,
    LearningRoadmap,
    NewsSummary,
    ProjectRecommendation,
    QuizPackage,
    QuizQuestion,
    ResearchPaperAnalysis,
    RoadmapStage,
    SlideOutline,
    STEMContentPackage,
    TechnologyImpactAnalysis,
    VideoScript,
    VocabularyGlossary,
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
                f"You are a Principal Intelligence & Science Analyst. "
                f"Summarize the following development with objective rigor and clarity for a {mode}-level audience. "
                f"For political, regional, or policy topics, maintain strict journalistic neutrality, "
                f"avoid editorial bias, and attribute claims clearly to the source. "
                f"Never invent facts, benchmarks, casualties, or quotes. "
                f"Clearly distinguish source facts from implications."
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
        """Deterministic, domain-aware research paper analysis fallback extracting insights from paper text."""
        desc = (article.description or "").strip()
        sentences = [s.strip() for s in desc.split(".") if len(s.strip()) > 15]

        # Extract problem, methodology, and findings from abstract sentences if available
        problem = f"Addressing key theoretical and computational challenges in: {article.title}."
        method = "Empirical experimentation and algorithmic modeling described in the preprint publication."
        findings = []

        for s in sentences:
            s_low = s.lower()
            if any(k in s_low for k in ["propose", "present", "introduce", "develop", "framework", "architecture"]):
                method = f"Proposed approach: {s}."
            elif any(k in s_low for k in ["show", "demonstrate", "achieve", "outperform", "improve", "results"]):
                findings.append(f"Empirical validation: {s}.")
            elif any(k in s_low for k in ["address", "problem", "challenge", "bottleneck", "focus"]):
                if article.title.lower() in s_low:
                    problem = f"Core investigation: {s}."
                else:
                    problem = f"Core investigation for {article.title}: {s}."

        if not findings:
            clean_desc = desc[:160] if desc else "Measurable improvement over baseline methods"
            findings = [
                f"Primary result: {clean_desc}.",
                "Demonstrates architectural efficiency and computational scaling advantages.",
            ]

        return ResearchPaperAnalysis(
            paper_title=article.title,
            research_problem=problem,
            methodology=method,
            main_findings=findings[:3],
            limitations=[
                "Evaluation scope bounded by the specific benchmarks and datasets evaluated in this study.",
                "Real-world generalization across non-stationary production environments requires further replication.",
            ],
            practical_applications=[
                "High-performance engineering pipelines and model inference optimization",
                "Reproducible baseline for adjacent STEM research programs and open-source tooling",
            ],
            further_research_questions=[
                "How does this methodology scale to orders-of-magnitude larger parameter regimes?",
                "Can these theoretical bounds be applied to real-time edge devices with tight power constraints?",
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
            analogy = "Analogous to distributed asynchronous message passing with fault-tolerant state replication."
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

        # Domain-aware contextual components and prerequisites
        c_low = concept_name.lower()
        if any(k in c_low for k in ["transformer", "llm", "neural", "attention", "gpt", "model"]):
            components = [
                "Multi-Head Self-Attention",
                "Query/Key/Value Projections",
                "Positional Embeddings",
                "LayerNorm & MLP",
            ]
            prereqs = ["Linear Algebra & Matrix Multiplication", "Gradient Descent", "Softmax Activation Function"]
            misconceptions = [
                (
                    f"Believing {concept_name} possesses internal biological reasoning "
                    "rather than statistical weight projection."
                ),
                "Assuming larger parameter count automatically cures hallucination without grounded retrieval.",
            ]
        elif any(k in c_low for k in ["robot", "actuator", "kinematics", "quadruped", "slam", "control"]):
            components = [
                "Forward/Inverse Kinematics",
                "Brushless Actuator Dynamics",
                "State Estimation (IMU/LiDAR)",
                "Feedback Control Loop (PID/MPC)",
            ]
            prereqs = ["Rigid Body Dynamics", "Coordinate Transformations", "Real-Time Embedded Systems"]
            misconceptions = [
                f"Assuming software simulation alone transfers directly to {concept_name} without the sim-to-real gap.",
                "Neglecting thermal dissipation and power density limits in continuous actuator operation.",
            ]
        elif any(k in c_low for k in ["quantum", "qubit", "superconductor"]):
            components = [
                "Superposition State Vectors",
                "Unitary Quantum Logic Gates",
                "Entangled Bell Pairs",
                "Measurement & Decoherence",
            ]
            prereqs = ["Complex Vector Spaces (Hilbert Space)", "Probability Amplitudes", "Linear Operators"]
            misconceptions = [
                f"Assuming {concept_name} simply runs classical algorithms simultaneously in parallel universes.",
                "Overlooking extreme cryogenic cooling and physical noise isolation requirements.",
            ]
        else:
            components = [
                "Core Algorithmic Formulation",
                "Data Pipeline & Representations",
                "State Management & Transitions",
                "Benchmark Evaluation Metric",
            ]
            prereqs = ["Data Structures & Algorithms", "Computational Complexity (Big-O)", "System Architecture"]
            misconceptions = [
                (
                    f"Assuming {concept_name} replaces core domain principles "
                    "rather than optimizing specific operational constraints."
                ),
                "Disregarding memory bandwidth bottlenecks and amortized computational overhead in production.",
            ]

        return ConceptExplanation(
            concept_name=concept_name,
            mode=mode,
            core_definition=definition,
            how_it_works=how_it_works,
            analogy_or_example=analogy,
            key_components=components,
            common_misconceptions=misconceptions,
            prerequisites_or_related=prereqs,
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

    # ------------------ Phase 4: STEM Education Capabilities ------------------

    async def generate_roadmap(self, topic: str) -> LearningRoadmap:
        """Generate a progressive 4-stage STEM curriculum roadmap from novice to mastery."""
        clean_topic = topic.strip()
        cached = ai_cache.get("roadmap", clean_topic.lower())
        if cached:
            return cached

        if self.provider:
            system_prompt = (
                "You are a Distinguished Professor of STEM Education and Principal Engineering Architect. "
                "Design a progressive, rigorous 4-stage learning roadmap taking a student from fundamentals to mastery."
            )
            prompt = (
                f"Topic: {clean_topic}\n\n"
                "Generate a structured LearningRoadmap JSON with 4 distinct progressive stages, "
                "prerequisites, milestones, mini-projects, and an estimated duration in weeks."
            )
            try:
                roadmap, _ = await self.provider.generate_structured(prompt, system_prompt, LearningRoadmap)
                ai_cache.set("roadmap", clean_topic.lower(), roadmap)
                return roadmap
            except Exception as exc:
                logger.warning("Provider call failed for generate_roadmap: %s. Using heuristic fallback.", exc)

        roadmap = self._heuristic_roadmap(clean_topic)
        ai_cache.set("roadmap", clean_topic.lower(), roadmap)
        return roadmap

    def _heuristic_roadmap(self, topic: str) -> LearningRoadmap:
        """Deterministic curriculum roadmap fallback."""
        stages = [
            RoadmapStage(
                stage_number=1,
                title="Phase 1: Foundations & Core Mathematical Intuition",
                description=f"Master the foundational mathematics, mental models, and base terminology of {topic}.",
                key_milestones=[
                    "Understand core definitions and governing principles",
                    "Set up the local developer environment and required toolchains",
                    "Implement a minimal Hello World baseline script",
                ],
                recommended_projects=[f"Build a standalone toy simulator or baseline script demonstrating {topic}"],
            ),
            RoadmapStage(
                stage_number=2,
                title="Phase 2: Core Engineering & Standard Architectures",
                description=(
                    f"Learn modern architectural patterns, industry-standard frameworks, and data flows in {topic}."
                ),
                key_milestones=[
                    "Master idiomatic algorithms and standard design patterns",
                    "Benchmark performance constraints: latency, throughput, memory",
                    "Integrate automated testing and error-handling pipelines",
                ],
                recommended_projects=[f"Develop a complete modular system implementing standard {topic} workflows"],
            ),
            RoadmapStage(
                stage_number=3,
                title="Phase 3: Advanced Optimization & Production Systems",
                description=f"Scale {topic} into distributed, high-performance, and resilient production environments.",
                key_milestones=[
                    "Profile bottlenecks and apply low-level algorithmic optimizations",
                    "Deploy hardware acceleration or asynchronous parallel processing",
                    "Establish monitoring, telemetry, and security hardening",
                ],
                recommended_projects=[f"Build an end-to-end production-grade service scaling {topic} workloads"],
            ),
            RoadmapStage(
                stage_number=4,
                title="Phase 4: Frontier Research & Real-World Domain Mastery",
                description=f"Contribute to open-source state-of-the-art tools and reproduce recent papers in {topic}.",
                key_milestones=[
                    "Read, dissect, and critique recent arXiv research papers",
                    "Design custom novel extensions to existing state-of-the-art architectures",
                    "Publish technical documentation or open-source tooling",
                ],
                recommended_projects=[f"Reproduce an empirical benchmark from a recent research paper on {topic}"],
            ),
        ]

        return LearningRoadmap(
            topic=topic,
            overview=(
                f"A comprehensive 4-stage engineering curriculum structured to guide learners from fundamental "
                f"principles through production-grade systems and novel research in {topic}."
            ),
            prerequisites=["Foundational Mathematics (Linear Algebra & Calculus)", "Data Structures & Python"],
            stages=stages,
            estimated_duration_weeks=16,
        )

    async def generate_lesson(
        self,
        topic: str,
        level: ExplanationMode = "intermediate",
    ) -> InteractiveLesson:
        """Generate a comprehensive interactive lesson with objective, core lesson, and practical exercise."""
        clean_topic = topic.strip()
        cached = ai_cache.get("lesson", clean_topic.lower(), mode=level)
        if cached:
            return cached

        if self.provider:
            system_prompt = (
                f"You are a World-Class STEM Professor and Lead Technical Instructor. "
                f"Create a comprehensive, technically accurate interactive lesson for a {level.upper()} learner. "
                f"Format the core_lesson in structured Markdown with headings, code or bullet examples."
            )
            prompt = (
                f"Topic: {clean_topic}\n"
                f"Difficulty Level: {level}\n\n"
                "Generate InteractiveLesson JSON with objective, core_lesson, key_takeaways, and practical_exercise."
            )
            try:
                lesson, _ = await self.provider.generate_structured(prompt, system_prompt, InteractiveLesson)
                ai_cache.set("lesson", clean_topic.lower(), lesson, mode=level)
                return lesson
            except Exception as exc:
                logger.warning("Provider call failed for generate_lesson: %s. Using heuristic fallback.", exc)

        lesson = self._heuristic_lesson(clean_topic, level)
        ai_cache.set("lesson", clean_topic.lower(), lesson, mode=level)
        return lesson

    def _heuristic_lesson(self, topic: str, level: ExplanationMode) -> InteractiveLesson:
        """Deterministic lesson generator fallback."""
        if level == "beginner":
            core = (
                f"### 1. What is {topic}?\n"
                f"{topic} is a transformative discipline in modern technology. Think of it as a set of rules "
                "and systems designed to automate complex work with precision.\n\n"
                "### 2. Everyday Analogy\n"
                "Imagine an automated kitchen where every chef has a single recipe card and specialized tools. "
                "When an order arrives, each station acts in harmony to produce the final meal.\n\n"
                "### 3. Key Concepts to Know\n"
                "• **Input Data**: The raw measurements or text supplied to the system.\n"
                "• **Processing Engine**: The core algorithm transforming inputs.\n"
                "• **Output / Prediction**: The validated result returned to the user."
            )
            exercise = (
                f"Write down 3 real-world devices or platforms you use daily that rely on {topic}. "
                "Identify what the input and output are for each device."
            )
        elif level == "advanced":
            core = (
                f"### 1. Formal Foundations of {topic}\n"
                f"{topic} is analyzed through the lens of algorithmic state transitions, formal optimization "
                "landscapes, and computational complexity constraints.\n\n"
                "### 2. Architectural Mechanisms\n"
                "• **Mathematical Modeling**: Formulated as constrained optimization over manifolds.\n"
                "• **Resource Budgets**: Constrained by cache locality, memory bandwidth, and SIMD/GPU execution.\n"
                "• **Failure Modes**: Handled via asynchronous consensus, rollback safeguards, and clipping.\n\n"
                "```python\n"
                f"# Pseudocode architecture for {topic}\n"
                "def execute_pipeline(state: State, tensor: Tensor) -> State:\n"
                "    optimized_weights = solve_convex_dual(tensor.gradient)\n"
                "    return state.apply_transformation(optimized_weights)\n"
                "```"
            )
            exercise = (
                f"Implement a profiling benchmark measuring memory allocations and FLOPs for {topic}. "
                "Identify cache miss ratios and optimize the inner execution loop using vectorization."
            )
        else:
            core = (
                f"### 1. Overview of {topic}\n"
                f"{topic} serves as a foundational building block in production engineering systems, "
                "balancing trade-offs between precision, execution latency, and development velocity.\n\n"
                "### 2. How the Architecture Functions\n"
                "1. **Data Ingestion**: Raw inputs are sanitized, normalized, and converted into structured schemas.\n"
                "2. **Algorithmic Transformation**: The core computational logic executes via validated pipelines.\n"
                "3. **Feedback & Telemetry**: Monitoring captures latency, accuracy, and error rates in real time.\n\n"
                "```python\n"
                f"# Core workflow pattern for {topic}\n"
                "class PipelineCoordinator:\n"
                "    def process(self, raw_input: dict) -> dict:\n"
                "        cleaned = self.sanitize(raw_input)\n"
                "        return self.engine.execute(cleaned)\n"
                "```"
            )
            exercise = (
                f"Create a Python script that instantiates a modular class representing {topic}. "
                "Include unit tests asserting correct edge-case handling for malformed inputs."
            )

        return InteractiveLesson(
            topic=topic,
            level=level,
            title=f"Mastering {topic}: From Principles to Practice",
            objective=f"Understand the mechanics, engineering trade-offs, and implementation patterns of {topic}.",
            core_lesson=core,
            key_takeaways=[
                f"{topic} relies on robust data representations and systematic error handling.",
                "Performance optimizations must always be grounded in empirical profiling rather than guesswork.",
                "Modular architectures allow isolating components for independent testing and maintenance.",
            ],
            practical_exercise=exercise,
            next_recommended_topic=f"Advanced Optimization & Scaling in {topic}",
        )

    async def generate_quiz(
        self,
        topic: str,
        difficulty: ExplanationMode = "intermediate",
    ) -> QuizPackage:
        """Generate interactive multiple-choice quiz testing technical comprehension."""
        clean_topic = topic.strip()
        cached = ai_cache.get("quiz", clean_topic.lower(), mode=difficulty)
        if cached:
            return cached

        if self.provider:
            system_prompt = (
                f"You are a Rigorous STEM Examiner. Create a 3-question multiple-choice technical quiz "
                f"on {clean_topic} for a {difficulty.upper()} learner. Each question must have exactly 4 choices, "
                f"a 0-based correct_option_index, and a detailed pedagogical explanation."
            )
            prompt = (
                f"Topic: {clean_topic}\n"
                f"Difficulty: {difficulty}\n\n"
                "Generate QuizPackage JSON with 3 technical questions."
            )
            try:
                quiz, _ = await self.provider.generate_structured(prompt, system_prompt, QuizPackage)
                ai_cache.set("quiz", clean_topic.lower(), quiz, mode=difficulty)
                return quiz
            except Exception as exc:
                logger.warning("Provider call failed for generate_quiz: %s. Using heuristic fallback.", exc)

        quiz = self._heuristic_quiz(clean_topic, difficulty)
        ai_cache.set("quiz", clean_topic.lower(), quiz, mode=difficulty)
        return quiz

    def _heuristic_quiz(self, topic: str, difficulty: ExplanationMode) -> QuizPackage:
        """Deterministic technical quiz fallback."""
        questions = [
            QuizQuestion(
                question_id=1,
                question=f"What is the primary engineering objective when designing a system around {topic}?",
                options=[
                    "A) Maximizing computational throughput while maintaining bounded latency and correctness",
                    "B) Eliminating the need for testing and software verification",
                    "C) Restricting execution exclusively to single-threaded sequential hardware",
                    "D) Using unvalidated heuristics without formal bounds",
                ],
                correct_option_index=0,
                explanation=(
                    f"Option A is correct: {topic} systems prioritize balancing throughput, latency, and correctness. "
                    "Options B, C, and D reflect anti-patterns and misunderstandings of engineering rigor."
                ),
            ),
            QuizQuestion(
                question_id=2,
                question=f"When scaling {topic} to high volume, which bottleneck is most critical to profile first?",
                options=[
                    "A) Memory bandwidth, cache locality, and I/O serialization bottlenecks",
                    "B) The color scheme of the developer documentation website",
                    "C) Converting all synchronous code into busy-wait polling loops",
                    "D) Disabling garbage collection permanently without heap tracking",
                ],
                correct_option_index=0,
                explanation=(
                    "Option A is correct: Memory bandwidth and I/O serialization are the primary performance "
                    "limiting factors when scaling modern technical pipelines."
                ),
            ),
            QuizQuestion(
                question_id=3,
                question=f"What is the best practice for ensuring architectural reliability in {topic} deployments?",
                options=[
                    "A) Deploying automated telemetry, structured logging, and health probe circuit breakers",
                    "B) Ignoring transient network timeouts and disabling retry policies",
                    "C) Storing credentials and secret keys unencrypted in source control",
                    "D) Bypassing schema validation on external data payloads",
                ],
                correct_option_index=0,
                explanation=(
                    "Option A is correct: Resilient systems require observable telemetry, health probes, "
                    "and automated circuit breakers to isolate partial failures gracefully."
                ),
            ),
        ]

        return QuizPackage(
            topic=topic,
            difficulty=difficulty,
            title=f"Technical Comprehension Check: {topic}",
            questions=questions,
        )

    async def compare_concepts(self, concept_a: str, concept_b: str) -> ConceptComparison:
        """Perform a multi-dimensional architectural comparison between two STEM technologies."""
        key = f"{concept_a.strip().lower()}_vs_{concept_b.strip().lower()}"
        cached = ai_cache.get("comparison", key)
        if cached:
            return cached

        if self.provider:
            system_prompt = (
                "You are a Principal Systems Architect. Conduct an objective, multi-dimensional technical comparison "
                "between two technologies. Evaluate them across concrete dimensions such as latency, complexity, "
                "scalability, and provide definitive use-case guidelines."
            )
            prompt = (
                f"Compare Concept A: {concept_a}\nAgainst Concept B: {concept_b}\n\nGenerate ConceptComparison JSON."
            )
            try:
                comp, _ = await self.provider.generate_structured(prompt, system_prompt, ConceptComparison)
                ai_cache.set("comparison", key, comp)
                return comp
            except Exception as exc:
                logger.warning("Provider call failed for compare_concepts: %s. Using heuristic fallback.", exc)

        comp = self._heuristic_comparison(concept_a, concept_b)
        ai_cache.set("comparison", key, comp)
        return comp

    def _heuristic_comparison(self, concept_a: str, concept_b: str) -> ConceptComparison:
        """Deterministic concept comparison fallback."""
        dims = [
            ComparisonDimension(
                dimension="Computational Complexity & Overhead",
                concept_a_value=f"Optimized for deterministic performance with bounded memory overhead in {concept_a}.",
                concept_b_value=(f"Higher dynamic flexibility at the expense of runtime overhead in {concept_b}."),
            ),
            ComparisonDimension(
                dimension="Ease of Implementation & Tooling",
                concept_a_value="Established toolchain with widespread documentation and mature libraries.",
                concept_b_value="Modern emergent paradigm requiring specialized tooling or custom configurations.",
            ),
            ComparisonDimension(
                dimension="Scalability & Concurrency",
                concept_a_value="Scales vertically with high cache efficiency and predictable hardware utilization.",
                concept_b_value="Scales horizontally across distributed nodes with asynchronous message passing.",
            ),
        ]

        return ConceptComparison(
            concept_a=concept_a,
            concept_b=concept_b,
            overview=(
                f"Both {concept_a} and {concept_b} address overlapping engineering challenges, "
                "but choose different trade-offs along the spectrum of complexity, performance, and flexibility."
            ),
            key_differences=dims,
            when_to_use_a=[
                "When deterministic latency and minimal resource consumption are strict requirements.",
                "In legacy or established codebases where mature ecosystem support is essential.",
            ],
            when_to_use_b=[
                "When dynamic flexibility and distributed scaling outweigh low-level raw performance.",
                "For greenfield architectures requiring rapid iteration and asynchronous integration.",
            ],
            summary_verdict=(
                f"Choose {concept_a} for mission-critical core efficiency and deterministic bounds; "
                f"choose {concept_b} when horizontal agility and distributed flexibility are the primary drivers."
            ),
        )

    async def recommend_project(
        self,
        topic: str,
        difficulty: ExplanationMode = "intermediate",
    ) -> ProjectRecommendation:
        """Generate practical portfolio-worthy engineering project recommendation."""
        clean_topic = topic.strip()
        cached = ai_cache.get("project", clean_topic.lower(), mode=difficulty)
        if cached:
            return cached

        if self.provider:
            system_prompt = (
                f"You are a Staff Software Engineer and Technical Recruiter. "
                f"Design an impactful portfolio project for a {difficulty.upper()} developer in {clean_topic}. "
                f"Focus on practical problem solving, realistic architecture, tech stack, and hiring impact."
            )
            prompt = f"Topic: {clean_topic}\nDifficulty: {difficulty}\n\nGenerate ProjectRecommendation JSON."
            try:
                proj, _ = await self.provider.generate_structured(prompt, system_prompt, ProjectRecommendation)
                ai_cache.set("project", clean_topic.lower(), proj, mode=difficulty)
                return proj
            except Exception as exc:
                logger.warning("Provider call failed for recommend_project: %s. Using heuristic fallback.", exc)

        proj = self._heuristic_project(clean_topic, difficulty)
        ai_cache.set("project", clean_topic.lower(), proj, mode=difficulty)
        return proj

    def _heuristic_project(self, topic: str, difficulty: ExplanationMode) -> ProjectRecommendation:
        """Deterministic project recommendation fallback."""
        t_low = topic.lower()
        if any(k in t_low for k in ["robot", "kinematics", "quadruped", "actuator"]):
            skills = ["Python & C++", "ROS 2 / Gazebo", "Forward & Inverse Kinematics", "PID / State Estimation"]
            materials = [
                "Linux Workstation (Ubuntu 22.04 LTS)",
                "ROS 2 Humble / Gazebo Physics Simulator",
                "Optional: ESP32 Microcontroller & 3x Servo Motors",
            ]
            cost = "$0 using Gazebo simulation ($35 if assembling physical ESP32 prototype)"
        elif any(k in t_low for k in ["quantum", "qubit"]):
            skills = ["Linear Algebra", "Qiskit / Cirq SDK", "Quantum Circuit Design", "Error Mitigation"]
            materials = [
                "Python 3.12+ Scientific Environment",
                "IBM Quantum Platform / Rigetti Cloud Account (Free Tier)",
                "JupyterLab / NumPy / Qiskit Aer Simulator",
            ]
            cost = "$0 (Runs on local Qiskit Aer simulator & free IBM Quantum Cloud credits)"
        elif any(k in t_low for k in ["cyber", "security", "crypto"]):
            skills = ["Network Protocols (TCP/IP, TLS 1.3)", "Packet Analysis (Scapy)", "Linux Systems", "Cryptography"]
            materials = [
                "Linux / macOS Workstation",
                "Wireshark / Scapy / Docker Sandboxing",
                "Public Vulnerability Feeds (CVE / NVD APIs)",
            ]
            cost = "$0 (Free & open-source security tools in isolated containers)"
        else:
            skills = [
                "Python 3.12+",
                "AsyncIO & Event-Driven Architecture",
                "Pydantic V2 & SQL",
                "Unit Testing & CI/CD",
            ]
            materials = [
                "Development Workstation (macOS / Linux / WSL2)",
                "Docker Desktop & Python Virtualenv",
                "Public Open-Source Libraries & Free REST/gRPC APIs",
            ]
            cost = "$0 (Uses local developer workstation and open-source software)"

        return ProjectRecommendation(
            topic=topic,
            difficulty=difficulty,
            project_title=f"Autonomous Intelligence & Telemetry Engine for {topic}",
            problem_statement=(
                f"Real-world deployments of {topic} frequently suffer from unmonitored failures, "
                "opaque latency spikes, and lack of reproducible benchmarking data."
            ),
            system_architecture=(
                "A modular pipeline comprising: (1) Data ingest worker, (2) Core processing engine, "
                "(3) Asynchronous message broker, (4) Time-series telemetry database, and (5) Alert dashboard."
            ),
            tech_stack=["Python 3.12+", "AsyncIO", "Pydantic V2", "SQLAlchemy Async", "FastAPI / Docker"],
            required_skills=skills,
            components_and_materials=materials,
            estimated_cost=cost,
            step_by_step_milestones=[
                "Phase 1: Build the data ingestion client with resilient exponential retry policies",
                "Phase 2: Implement the core transformation algorithm with unit test coverage >90%",
                "Phase 3: Connect the database layer with ACID transactions and foreign key validation",
                "Phase 4: Integrate real-time Prometheus / structured metrics export",
            ],
            stretch_goals=[
                "Add automated load testing with Locust or k6 simulating 10,000 requests/second",
                "Implement distributed tracing with OpenTelemetry and Jaeger",
            ],
            portfolio_impact=(
                f"Demonstrates to hiring managers that you understand full-lifecycle production systems in {topic}, "
                "prioritizing resilience, clean architecture, and observable software design."
            ),
        )

    async def generate_vocabulary(self, topic: str) -> VocabularyGlossary:
        """Generate a curated glossary of essential technical terminology for a STEM topic."""
        clean_topic = topic.strip()
        cached = ai_cache.get("vocabulary", clean_topic.lower())
        if cached:
            return cached

        if self.provider:
            system_prompt = (
                "You are a Technical Lexicographer and STEM Educator. "
                f"Curate 6 essential technical terms defining the discipline of {clean_topic}."
            )
            prompt = f"Topic: {clean_topic}\n\nGenerate VocabularyGlossary JSON."
            try:
                vocab, _ = await self.provider.generate_structured(prompt, system_prompt, VocabularyGlossary)
                ai_cache.set("vocabulary", clean_topic.lower(), vocab)
                return vocab
            except Exception as exc:
                logger.warning("Provider call failed for generate_vocabulary: %s. Using heuristic fallback.", exc)

        vocab = self._heuristic_vocabulary(clean_topic)
        ai_cache.set("vocabulary", clean_topic.lower(), vocab)
        return vocab

    def _heuristic_vocabulary(self, topic: str) -> VocabularyGlossary:
        """Deterministic vocabulary glossary fallback."""
        terms = [
            VocabularyTerm(
                term=f"{topic} Architecture",
                definition=f"Structural organization, boundaries, and interfaces defining a {topic} system.",
            ),
            VocabularyTerm(
                term="Algorithmic Complexity",
                definition="Theoretical consumption of time and memory resources as input size approaches infinity.",
            ),
            VocabularyTerm(
                term="Throughput",
                definition="Quantified volume of successful units of work processed over a continuous time interval.",
            ),
            VocabularyTerm(
                term="Latency (p99)",
                definition="The response time threshold under which 99% of all requests are successfully serviced.",
            ),
            VocabularyTerm(
                term="Fault Tolerance",
                definition="System capability to sustain uninterrupted operation despite component failures.",
            ),
            VocabularyTerm(
                term="Telemetry",
                definition="The automated remote recording and transmission of operational performance metrics.",
            ),
        ]
        return VocabularyGlossary(topic=topic, terms=terms)

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
