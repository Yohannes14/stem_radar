"""Pydantic request and response schemas for AI intelligence endpoints."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.ai.schemas import ExplanationMode


class AISummarizeRequest(BaseModel):
    """Payload for summarizing an article or raw text."""

    article_id: Optional[int] = Field(default=None, description="ID of an existing stored article to summarize")
    title: Optional[str] = Field(default=None, min_length=3, max_length=500, description="Title if passing raw text")
    content: Optional[str] = Field(
        default=None, min_length=10, max_length=20000, description="Body content if passing raw text"
    )
    url: Optional[str] = Field(default=None, description="Optional original URL for raw text")
    mode: ExplanationMode = Field(
        default="intermediate", description="Explanation complexity: 'beginner', 'intermediate', or 'advanced'"
    )

    @model_validator(mode="after")
    def validate_article_or_content(self) -> "AISummarizeRequest":
        """Verify that either article_id or title+content is provided."""
        if self.article_id is None:
            if not self.title or not self.content:
                raise ValueError("Must provide either 'article_id' or both 'title' and 'content'.")
        return self


class AISummarizeResponse(BaseModel):
    """Structured AI executive technical summary."""

    headline: str = Field(..., description="Crisp technical headline")
    short_summary: str = Field(..., description="Executive 2-3 sentence summary")
    key_facts: List[str] = Field(..., description="Objective facts extracted from source")
    why_it_matters: str = Field(..., description="Strategic significance")
    potential_applications: List[str] = Field(..., description="Practical real-world use cases")
    technical_difficulty: str = Field(..., description="Assessed technical depth")
    original_source: str = Field(..., description="Reporting source name")
    source_url: str = Field(..., description="Direct link to source document")

    model_config = ConfigDict(from_attributes=True)


class AIExplainRequest(BaseModel):
    """Payload for requesting multi-tiered concept explanation."""

    concept: str = Field(..., min_length=2, max_length=150, description="Technical concept or algorithm name")
    mode: ExplanationMode = Field(
        default="intermediate", description="Target complexity: 'beginner', 'intermediate', or 'advanced'"
    )
    context: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional engineering domain context (e.g. 'robotics', 'distributed systems')",
    )


class AIExplainResponse(BaseModel):
    """Structured conceptual breakdown tailored to user depth level."""

    concept_name: str = Field(..., description="Target technical concept")
    mode: str = Field(..., description="Explanation depth level")
    core_definition: str = Field(..., description="Level-appropriate definition")
    how_it_works: str = Field(..., description="Mechanics and principles breakdown")
    analogy_or_example: str = Field(..., description="Concrete analogy or code/architecture example")
    key_components: List[str] = Field(..., description="Key building blocks or equations")
    common_misconceptions: List[str] = Field(..., description="Pitfalls and misconceptions")
    prerequisites_or_related: List[str] = Field(..., description="Related foundational concepts")

    model_config = ConfigDict(from_attributes=True)
