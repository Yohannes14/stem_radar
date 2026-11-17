"""In-memory sliding window rate limiter for expensive endpoints."""

import time
from collections import defaultdict
from typing import Dict, List

from fastapi import Request

from app.api.exceptions import RateLimitExceededException


class InMemoryRateLimiter:
    """Sliding-window in-memory rate limiter keyed by API key or client IP."""

    def __init__(self, requests_per_minute: int = 30) -> None:
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60.0
        self._history: Dict[str, List[float]] = defaultdict(list)

    def is_rate_limited(self, identifier: str) -> bool:
        """Check whether the given identifier has exceeded its quota within the time window."""
        now = time.time()
        cutoff = now - self.window_seconds

        # Prune expired timestamps
        timestamps = [t for t in self._history[identifier] if t > cutoff]
        self._history[identifier] = timestamps

        if len(timestamps) >= self.requests_per_minute:
            return True

        self._history[identifier].append(now)
        return False

    async def __call__(self, request: Request) -> None:
        """FastAPI dependency evaluation enforcing rate limit."""
        api_key = request.headers.get("X-API-Key")
        client_host = request.client.host if request.client else "127.0.0.1"
        identifier = f"key:{api_key}" if api_key else f"ip:{client_host}"

        if self.is_rate_limited(identifier):
            raise RateLimitExceededException(
                message=f"Rate limit of {self.requests_per_minute} requests per minute exceeded. Please retry later."
            )


# Default rate limiter for expensive AI operations (e.g. 20 requests/minute)
ai_rate_limiter = InMemoryRateLimiter(requests_per_minute=20)

# Sliding window rate limiter for unified search queries (e.g. 60 requests/minute)
search_rate_limiter = InMemoryRateLimiter(requests_per_minute=60)
