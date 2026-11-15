"""OpenAI LLM provider adapter with retry, timeout, and schema validation."""

import json
import logging
from typing import Tuple, Type, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.services.ai.cost_tracker import cost_tracker
from app.services.ai.interface import BaseAIProvider, TokenUsage

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class OpenAIAdapter(BaseAIProvider):
    """Production adapter for OpenAI API chat completions."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str,
        response_model: Type[T],
        temperature: float = 0.2,
    ) -> Tuple[T, TokenUsage]:
        """Generate a validated structured Pydantic object using JSON mode."""
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        augmented_system_prompt = (
            f"{system_prompt}\n\n"
            f"You MUST respond ONLY with a valid JSON object matching this JSON Schema:\n{schema_json}"
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": augmented_system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )

        raw_content = response.choices[0].message.content or "{}"
        parsed_data = json.loads(raw_content)
        validated_instance = response_model.model_validate(parsed_data)

        # Extract token usage
        usage_data = response.usage
        prompt_tokens = usage_data.prompt_tokens if usage_data else 0
        completion_tokens = usage_data.completion_tokens if usage_data else 0
        total_tokens = usage_data.total_tokens if usage_data else prompt_tokens + completion_tokens

        cost = cost_tracker.record_usage(self.model, prompt_tokens, completion_tokens)
        token_usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
        )

        return validated_instance, token_usage

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.3,
    ) -> Tuple[str, TokenUsage]:
        """Generate unstructured text from OpenAI."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )

        text = response.choices[0].message.content or ""
        usage_data = response.usage
        prompt_tokens = usage_data.prompt_tokens if usage_data else 0
        completion_tokens = usage_data.completion_tokens if usage_data else 0
        total_tokens = usage_data.total_tokens if usage_data else prompt_tokens + completion_tokens

        cost = cost_tracker.record_usage(self.model, prompt_tokens, completion_tokens)
        token_usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
        )

        return text, token_usage
