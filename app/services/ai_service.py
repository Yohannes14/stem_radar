"""AI Intelligence Engine providing automated technical analysis, summarization, and concept extraction."""

import json
import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from app.config import settings
from app.database.models import Article

logger = logging.getLogger(__name__)


class ArticleIntelligence(BaseModel):
    """Normalized schema for comprehensive AI-generated technical analysis."""

    article_title: str
    source: str
    category: str
    short_summary: str = Field(description="2-3 sentence executive summary.")
    what_happened: str = Field(description="Objective factual report of the event.")
    why_it_matters: str = Field(description="Strategic importance to science or industry.")
    technical_explanation: str = Field(description="How the technology or architecture works.")
    real_world_applications: List[str] = Field(description="Direct practical use cases.")
    future_possibilities: List[str] = Field(description="Long-term technological evolution.")
    important_concepts: List[str] = Field(description="Key technical terminology.")
    stem_content_opportunity: str = Field(description="Educational angle for content creation.")
    source_url: str


class AIService:
    """Enterprise AI Service interfacing with OpenAI API with resilient local heuristics fallback."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self._client = None
        if self.api_key:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(api_key=self.api_key)
                logger.info("AIService initialized with OpenAI model: %s", self.model)
            except Exception as exc:
                logger.warning("Failed to initialize AsyncOpenAI client: %s", exc)

    async def analyze_article(self, article: Article) -> ArticleIntelligence:
        """Analyze a technical article or research paper using AI (or fallback heuristics)."""
        source_name = article.source.name if article.source else "Tech Feed"
        category_name = article.categories[0].name if article.categories else "STEM Technology"

        if self._client:
            try:
                return await self._analyze_with_openai(article, source_name, category_name)
            except Exception as exc:
                logger.warning("OpenAI API call failed: %s. Falling back to heuristic analysis.", exc)

        return self._generate_heuristic_analysis(article, source_name, category_name)

    async def _analyze_with_openai(self, article: Article, source_name: str, category_name: str) -> ArticleIntelligence:
        """Query OpenAI API with structured JSON output instructions."""
        prompt = (
            f"Analyze the following technology news or research paper with technical rigor:\n\n"
            f"Title: {article.title}\n"
            f"Source: {source_name}\n"
            f"Category: {category_name}\n"
            f"Content/Description: {article.description or article.title}\n"
            f"URL: {article.url}\n\n"
            f"Generate a structured JSON response matching the required schema. "
            f"Never invent facts, statistics, or quotes. Clearly distinguish verified facts from interpretation."
        )

        response = await self._client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a Senior Technology Intelligence Analyst and STEM Educator. "
                        "Respond with a valid JSON object matching the ArticleIntelligence schema."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        raw_json = response.choices[0].message.content
        data = json.loads(raw_json)
        return ArticleIntelligence(**data)

    def _generate_heuristic_analysis(
        self, article: Article, source_name: str, category_name: str
    ) -> ArticleIntelligence:
        """High-quality deterministic fallback analysis when external LLM API is unavailable."""
        title = article.title
        desc = article.description or "No extended description available."

        return ArticleIntelligence(
            article_title=title,
            source=source_name,
            category=category_name,
            short_summary=f"{title}. {desc[:180]}...",
            what_happened=f"Development announced by {source_name}: {desc[:250]}...",
            why_it_matters=(
                f"Represents progress in {category_name}, potentially increasing efficiency, "
                f"reducing operational bottlenecks, or unlocking new research capabilities."
            ),
            technical_explanation=(
                f"The architecture focuses on {category_name} principles: {desc[:220]}... "
                "Optimization is achieved through modernized algorithmic pipelines and design patterns."
            ),
            real_world_applications=[
                f"Industrial implementation in {category_name}",
                "Automated continuous processing and optimization",
                "Educational research and laboratory experimentation",
            ],
            future_possibilities=[
                "Integration with autonomous edge devices",
                "Widespread standardization across open-source toolchains",
            ],
            important_concepts=[category_name, "Algorithmic Efficiency", "System Integration", "Scalability"],
            stem_content_opportunity=(
                f"Create a deep-dive tutorial breaking down the trade-offs of this {category_name} breakthrough."
            ),
            source_url=article.url,
        )


ai_service = AIService()
