"""Modular AI Intelligence Engine package."""

from app.services.ai.adapters.openai_adapter import OpenAIAdapter
from app.services.ai.cache import AICache, ai_cache
from app.services.ai.cost_tracker import AICostTracker, cost_tracker
from app.services.ai.interface import BaseAIProvider, TokenUsage
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
from app.services.ai.service import AIService, ai_service

__all__ = [
    "AIService",
    "ai_service",
    "BaseAIProvider",
    "TokenUsage",
    "OpenAIAdapter",
    "AICache",
    "ai_cache",
    "AICostTracker",
    "cost_tracker",
    "ExplanationMode",
    "NewsSummary",
    "ResearchPaperAnalysis",
    "ConceptExplanation",
    "TechnologyImpactAnalysis",
    "STEMContentPackage",
    "SlideOutline",
    "VideoScript",
    "VocabularyTerm",
    "ArticleIntelligence",
    "RoadmapStage",
    "LearningRoadmap",
    "InteractiveLesson",
    "QuizQuestion",
    "QuizPackage",
    "ComparisonDimension",
    "ConceptComparison",
    "ProjectRecommendation",
    "VocabularyGlossary",
]

