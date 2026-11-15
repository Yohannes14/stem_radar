"""Usage telemetry and real-time LLM cost estimation tracker."""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Pricing per 1,000,000 tokens in USD (Standard published rates)
MODEL_RATE_CARD: Dict[str, Dict[str, float]] = {
    "gpt-4o-mini": {
        "input_per_m": 0.15,
        "output_per_m": 0.60,
    },
    "gpt-4o": {
        "input_per_m": 2.50,
        "output_per_m": 10.00,
    },
    "gpt-4-turbo": {
        "input_per_m": 10.00,
        "output_per_m": 30.00,
    },
    "gpt-3.5-turbo": {
        "input_per_m": 0.50,
        "output_per_m": 1.50,
    },
    "default": {
        "input_per_m": 0.50,
        "output_per_m": 1.50,
    },
}


class AICostTracker:
    """Thread-safe usage accumulator tracking tokens and estimated financial costs."""

    def __init__(self) -> None:
        self.total_requests: int = 0
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_cost_usd: float = 0.0

    def compute_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate estimated USD cost for a single request based on model rate card."""
        rates = MODEL_RATE_CARD.get(model.lower(), MODEL_RATE_CARD["default"])
        input_cost = (prompt_tokens / 1_000_000) * rates["input_per_m"]
        output_cost = (completion_tokens / 1_000_000) * rates["output_per_m"]
        return round(input_cost + output_cost, 7)

    def record_usage(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Record usage metrics from a completed request and update cumulative telemetry."""
        cost = self.compute_cost(model, prompt_tokens, completion_tokens)
        self.total_requests += 1
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_cost_usd = round(self.total_cost_usd + cost, 6)

        logger.debug(
            "AI Request logged (%s): prompt=%d, completion=%d, cost=$%.6f | Cumulative: %d reqs, $%.4f",
            model,
            prompt_tokens,
            completion_tokens,
            cost,
            self.total_requests,
            self.total_cost_usd,
        )
        return cost

    def get_metrics(self) -> Dict[str, Any]:
        """Return cumulative telemetry snapshot."""
        return {
            "total_requests": self.total_requests,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
            "total_cost_usd": self.total_cost_usd,
        }

    def reset(self) -> None:
        """Reset counters for testing or billing cycles."""
        self.total_requests = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost_usd = 0.0


cost_tracker = AICostTracker()

