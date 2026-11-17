"""Pydantic structured output models for STEM RADAR AI intelligence capabilities."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

ExplanationMode = Literal["beginner", "intermediate", "advanced"]


class NewsSummary(BaseModel):
    """Structured AI technical summary for technology and engineering news."""

    headline: str = Field(description="Crisp, informative news headline.")
    short_summary: str = Field(description="2-3 sentence executive technical summary.")
    key_facts: List[str] = Field(description="Bullet-pointed objective facts reported in the source.")
    why_it_matters: str = Field(description="Strategic importance to engineering, science, or industry.")
    potential_applications: List[str] = Field(description="Practical real-world use cases or deployments.")
    technical_difficulty: ExplanationMode = Field(description="Technical depth: beginner, intermediate, or advanced.")
    original_source: str = Field(description="Name of the reporting publication or platform.")
    source_url: str = Field(description="Direct URL to original source.")


class ResearchPaperAnalysis(BaseModel):
    """Rigorous scientific analysis schema for peer-reviewed and pre-print research papers."""

    paper_title: str = Field(description="Title of the research paper.")
    research_problem: str = Field(description="Core scientific or engineering question addressed.")
    methodology: str = Field(description="Experimental or theoretical approach, architecture, or dataset.")
    main_findings: List[str] = Field(description="Primary empirical or theoretical results achieved.")
    limitations: List[str] = Field(description="Explicitly stated or identified constraints and boundary conditions.")
    practical_applications: List[str] = Field(description="Translational impact for industry or software systems.")
    further_research_questions: List[str] = Field(description="Unresolved hypotheses and promising directions.")
    original_paper_url: str = Field(description="Direct URL to the paper or arXiv abstract.")
    code_repository_url: Optional[str] = Field(
        default=None,
        description="Direct URL to open source code, model weights, or replication repository if available.",
    )


class ConceptExplanation(BaseModel):
    """Multi-tiered technical concept explanation tailored to user experience level."""

    concept_name: str = Field(description="Name of the technical concept or algorithm.")
    mode: ExplanationMode = Field(description="Explanation depth: beginner, intermediate, or advanced.")
    core_definition: str = Field(description="Clear, accurate definition suited to the target level.")
    how_it_works: str = Field(description="Step-by-step breakdown of mechanisms and principles.")
    analogy_or_example: str = Field(description="Intuitive real-world analogy or concrete code/engineering example.")
    key_components: List[str] = Field(description="Essential building blocks or equations.")
    common_misconceptions: List[str] = Field(description="Pitfalls or incorrect assumptions to avoid.")
    prerequisites_or_related: List[str] = Field(description="Related foundational concepts to study.")


class TechnologyImpactAnalysis(BaseModel):
    """Strategic technology intelligence analyzing commercial and scientific impact."""

    technology_name: str = Field(description="Name of the technology or breakthrough.")
    executive_summary: str = Field(description="Synthesized strategic assessment.")
    industry_disruption: List[str] = Field(description="Sectors and industrial workflows likely to be transformed.")
    scientific_significance: str = Field(description="Value added to the broader scientific knowledge base.")
    societal_and_ethical_implications: List[str] = Field(description="Safety, regulatory, or workforce considerations.")
    adoption_timeline: str = Field(
        description="Expected time horizon for mainstream adoption (e.g. 1-3 yrs, 5-10 yrs)."
    )
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence in forecast based on empirical evidence.")


class SlideOutline(BaseModel):
    """Single slide in a multi-slide educational carousel."""

    slide_number: int = Field(ge=1, le=5)
    title: str = Field(description="Slide headline.")
    bullet_points: List[str] = Field(description="1-3 concise, visually digestable bullet points.")


class VideoScript(BaseModel):
    """Short-form educational video script (Shorts/Reels/TikTok)."""

    hook: str = Field(description="Attention-grabbing technical hook for seconds 0:00 - 0:03.")
    body: str = Field(description="Core explanation and demonstration for seconds 0:04 - 0:20.")
    call_to_action: str = Field(description="Closing takeaway and engagement prompt for seconds 0:21 - 0:30.")


class VocabularyTerm(BaseModel):
    """Key technical term and pedagogical definition."""

    term: str
    definition: str


class STEMContentPackage(BaseModel):
    """Multi-channel educational content package for STEM educators and creators."""

    headline: str = Field(description="Educational content headline.")
    target_audience: str = Field(description="Intended audience (e.g. junior developers, robotics researchers).")
    linkedin_post: str = Field(description="Engaging, professionally formatted LinkedIn post.")
    carousel_slides: List[SlideOutline] = Field(description="Exactly 5 slide outlines for Instagram/LinkedIn.")
    video_script: VideoScript = Field(description="Short-form video script with timestamp breakdown.")
    technical_vocabulary: List[VocabularyTerm] = Field(description="Curated glossary terms.")
    source_attribution: str = Field(description="Attribution referencing original publication.")


class ArticleIntelligence(BaseModel):
    """Comprehensive composite intelligence schema (backward compatibility)."""

    article_title: str
    source: str
    category: str
    short_summary: str
    what_happened: str
    why_it_matters: str
    technical_explanation: str
    real_world_applications: List[str]
    future_possibilities: List[str]
    important_concepts: List[str]
    stem_content_opportunity: str
    source_url: str


# ------------------ Phase 4: STEM Education Schemas ------------------


class RoadmapStage(BaseModel):
    """Specific learning phase within a structured educational roadmap."""

    stage_number: int = Field(ge=1, le=10)
    title: str = Field(description="Stage headline (e.g. Stage 1: Mathematical Foundations).")
    description: str = Field(description="Core concepts and competencies to acquire in this phase.")
    key_milestones: List[str] = Field(description="Actionable milestones to master.")
    recommended_projects: List[str] = Field(description="Hands-on mini-projects validating the stage.")


class LearningRoadmap(BaseModel):
    """End-to-end curriculum roadmap guiding learners from novice to mastery in any STEM domain."""

    topic: str = Field(description="Target STEM topic or engineering field.")
    overview: str = Field(description="Strategic executive summary of what this roadmap covers.")
    prerequisites: List[str] = Field(description="Foundational math or engineering prerequisites.")
    stages: List[RoadmapStage] = Field(description="Ordered progressive stages from beginner to mastery.")
    estimated_duration_weeks: int = Field(ge=1, description="Realistic timeline in weeks.")


class InteractiveLesson(BaseModel):
    """Deep-dive interactive technical lesson adapted to student difficulty level."""

    topic: str = Field(description="Subject matter.")
    level: ExplanationMode = Field(description="Instructional level: beginner, intermediate, or advanced.")
    title: str = Field(description="Engaging technical lesson title.")
    objective: str = Field(description="Clear learning outcome expected after completing the lesson.")
    core_lesson: str = Field(description="Thorough, technically accurate explanation with code or formulas.")
    key_takeaways: List[str] = Field(description="Bullet-pointed foundational takeaways.")
    practical_exercise: str = Field(description="Hands-on coding or architectural design exercise.")
    next_recommended_topic: str = Field(description="Logical sequential topic to explore next.")


class QuizQuestion(BaseModel):
    """Multiple choice technical quiz question."""

    question_id: int = Field(ge=1)
    question: str = Field(description="The technical question testing conceptual or practical understanding.")
    options: List[str] = Field(description="Exactly 4 distinct answers.")
    correct_option_index: int = Field(ge=0, le=3, description="0-based index of correct option in options list.")
    explanation: str = Field(description="Pedagogical explanation of why the correct answer is right and others wrong.")


class QuizPackage(BaseModel):
    """Interactive quiz bundle testing comprehension for a STEM topic."""

    topic: str = Field(description="Topic assessed.")
    difficulty: ExplanationMode = Field(description="Difficulty level of questions.")
    title: str = Field(description="Quiz title.")
    questions: List[QuizQuestion] = Field(description="Set of multiple-choice questions.")


class ComparisonDimension(BaseModel):
    """Specific metric or attribute comparing two technologies."""

    dimension: str = Field(description="Attribute compared (e.g. Latency, Memory Footprint, Throughput).")
    concept_a_value: str = Field(description="Performance or behavior of concept A.")
    concept_b_value: str = Field(description="Performance or behavior of concept B.")


class ConceptComparison(BaseModel):
    """Rigorous architectural comparison between two technologies, frameworks, or concepts."""

    concept_a: str
    concept_b: str
    overview: str = Field(description="High-level overview of the problem space and why they are compared.")
    key_differences: List[ComparisonDimension] = Field(description="Attribute-by-attribute comparison table.")
    when_to_use_a: List[str] = Field(description="Engineering scenarios where concept A is optimal.")
    when_to_use_b: List[str] = Field(description="Engineering scenarios where concept B is optimal.")
    summary_verdict: str = Field(description="Pragmatic engineering trade-off verdict.")


class ProjectRecommendation(BaseModel):
    """Practical hands-on engineering project recommendation building portfolio strength."""

    topic: str
    difficulty: ExplanationMode
    project_title: str = Field(description="Concrete real-world project title.")
    problem_statement: str = Field(description="The realistic problem the project solves.")
    system_architecture: str = Field(description="Component diagram and data flow description.")
    tech_stack: List[str] = Field(description="Recommended libraries, languages, and frameworks.")
    required_skills: List[str] = Field(default_factory=list, description="Required skills and prerequisites.")
    components_and_materials: List[str] = Field(
        default_factory=list, description="Hardware/software components, APIs, and materials."
    )
    estimated_cost: str = Field(
        default="Free / Open-Source (assumes workstation and public APIs)",
        description="Estimated cost with explicit assumptions.",
    )
    estimated_time: str = Field(
        default="1-2 weeks (~15-25 hours)",
        description="Estimated completion timeline for development and testing.",
    )
    learning_outcomes: List[str] = Field(
        default_factory=list,
        description="Core engineering principles and technical skills acquired upon completion.",
    )
    step_by_step_milestones: List[str] = Field(description="Phased implementation steps.")
    verification_steps: List[str] = Field(
        default_factory=list,
        description="Automated tests, physical validation, and benchmarking procedures.",
    )
    common_pitfalls: List[str] = Field(
        default_factory=list,
        description="Frequent architectural, hardware, or debugging mistakes to avoid.",
    )
    stretch_goals: List[str] = Field(description="Advanced extensions for top-tier portfolios.")
    portfolio_impact: str = Field(description="What this demonstrates to engineering hiring managers.")


class VocabularyGlossary(BaseModel):
    """Curated technical glossary covering a STEM topic."""

    topic: str
    terms: List[VocabularyTerm] = Field(description="Glossary terms paired with precise definitions.")
