"""Resilient async HTTP client manager with retry and timeout policies."""

import asyncio
import logging
import random
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20.0
DEFAULT_USER_AGENT = "StemRadar/1.0 (+https://github.com/stem-radar; research & intelligence platform)"


class ResilientHTTPClient:
    """Async HTTP client wrapper providing automatic retries, exponential backoff,
    and standardized headers.
    """

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.headers = headers or {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, application/json, */*",
        }

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Execute an asynchronous HTTP GET request with retry and exponential backoff."""
        req_headers = {**self.headers, **(headers or {})}

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers=req_headers,
        ) as client:
            last_exception: Optional[Exception] = None

            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await client.get(url, params=params)
                    # Return immediately on successful response
                    if response.status_code in (200, 201, 206):
                        return response

                    # Do not retry 404 or 401 client errors
                    if response.status_code in (401, 403, 404):
                        logger.warning("HTTP %d received for %s - skipping retries.", response.status_code, url)
                        return response

                    logger.warning(
                        "Attempt %d/%d for %s returned status %d",
                        attempt,
                        self.max_retries,
                        url,
                        response.status_code,
                    )
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    last_exception = exc
                    logger.warning("Attempt %d/%d failed for %s: %s", attempt, self.max_retries, url, exc)

                if attempt < self.max_retries:
                    # Exponential backoff with random jitter to prevent thundering herd
                    sleep_time = (self.backoff_factor**attempt) + random.uniform(0.1, 0.5)
                    await asyncio.sleep(sleep_time)

            if last_exception:
                raise last_exception

            return response
