"""Structured request logging middleware."""

import logging
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("stem_radar.api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs incoming HTTP requests, process time, status codes, and path metadata."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"

            # Skip logging noise for frequent health checks in debug mode
            if path == "/api/v1/health":
                logger.debug("%s %s -> %d (%0.2f ms)", method, path, response.status_code, duration_ms)
            else:
                logger.info("%s %s -> %d (%0.2f ms)", method, path, response.status_code, duration_ms)

            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error("%s %s -> FAILED (%0.2f ms): %s", method, path, duration_ms, exc)
            raise

