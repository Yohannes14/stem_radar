"""Provider-independent AI service interfaces and token accounting schemas."""

import abc
from dataclasses import dataclass
from typing import Tuple, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass
class TokenUsage:
    """Usage accounting for a single LLM generation request."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class BaseAIProvider(abc.ABC):
    """Abstract interface that all concrete AI/LLM providers must implement."""

    @abc.abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str,
        response_model: Type[T],
        temperature: float = 0.2,
    ) -> Tuple[T, TokenUsage]:  # type: ignore[name-defined]
        """Generate structured output validated against a Pydantic schema."""
        pass

    @abc.abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.3,
    ) -> Tuple[str, TokenUsage]:  # type: ignore[name-defined]
        """Generate raw text response from the LLM provider."""
        pass
