"""AI Service compatibility facade delegating to the modular app.services.ai engine."""

from app.services.ai.cache import AICache, ai_cache
from app.services.ai.cost_tracker import AICostTracker, cost_tracker
from app.services.ai.interface import BaseAIProvider, TokenUsage
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
from app.services.ai.service import AIService, ai_service

__all__ = [
    "AIService",
    "ai_service",
    "BaseAIProvider",
    "TokenUsage",
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
]
