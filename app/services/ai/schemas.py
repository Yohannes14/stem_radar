"""Pydantic structured output models for STEM RADAR AI intelligence capabilities."""

from typing import List, Literal

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
