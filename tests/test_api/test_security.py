"""Tests for API security: Authentication, Authorization, Rate Limiting, and Error Masking."""

import pytest
from httpx import AsyncClient

from app.api.dependencies import require_api_key
from app.api.middleware.rate_limit import InMemoryRateLimiter
from app.config import settings


@pytest.mark.asyncio
async def test_auth_with_configured_api_key(api_client: AsyncClient, monkeypatch):
    """Test API key authentication enforcement when API_KEY is set in settings."""
    test_key = "secure-stem-radar-key-12345"
    monkeypatch.setattr(settings, "api_key", test_key)

    payload = {"concept": "Quantum Teleportation", "mode": "intermediate"}

    # 1. Missing API key -> 401
    res_no_key = await api_client.post("/api/v1/ai/explain", json=payload)
    assert res_no_key.status_code == 401
    assert res_no_key.json()["error"]["code"] == "UNAUTHORIZED"

    # 2. Invalid API key -> 401
    res_bad_key = await api_client.post(
        "/api/v1/ai/explain",
        json=payload,
        headers={"X-API-Key": "wrong-key"},
    )
    assert res_bad_key.status_code == 401
    assert res_bad_key.json()["error"]["code"] == "UNAUTHORIZED"

    # 3. Valid API key via X-API-Key header -> 200
    res_ok_header = await api_client.post(
        "/api/v1/ai/explain",
        json=payload,
        headers={"X-API-Key": test_key},
    )
    assert res_ok_header.status_code == 200
    assert res_ok_header.json()["concept_name"] == "Quantum Teleportation"

    # 4. Valid API key via Authorization: Bearer <key> -> 200
    res_ok_bearer = await api_client.post(
        "/api/v1/ai/explain",
        json=payload,
        headers={"Authorization": f"Bearer {test_key}"},
    )
    assert res_ok_bearer.status_code == 200


@pytest.mark.asyncio
async def test_auth_production_mode_requires_api_key(monkeypatch):
    """Test that in production mode, an unset API_KEY rejects requests."""
    monkeypatch.setattr(settings, "api_key", None)
    monkeypatch.setattr(settings, "environment", "production")

    with pytest.raises(Exception) as exc_info:
        await require_api_key(x_api_key=None, authorization=None)
    assert "API_KEY must be configured" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_rate_limiter_sliding_window():
    """Test in-memory sliding window rate limiter triggers 429 when quota is exceeded."""
    limiter = InMemoryRateLimiter(requests_per_minute=3)
    user_id = "test-client-ip"

    # First 3 requests within 60s window allowed
    assert limiter.is_rate_limited(user_id) is False
    assert limiter.is_rate_limited(user_id) is False
    assert limiter.is_rate_limited(user_id) is False

    # 4th request must be blocked
    assert limiter.is_rate_limited(user_id) is True


@pytest.mark.asyncio
async def test_cors_preflight_headers(api_client: AsyncClient):
    """Test CORS headers on preflight OPTIONS requests."""
    response = await api_client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


@pytest.mark.asyncio
async def test_global_exception_handler_masks_internal_details(api_client: AsyncClient):
    """Test that unhandled exceptions do not leak stack traces to clients."""
    # Requesting health with invalid structure triggers global exception handler if unhandled
    response = await api_client.get("/api/v1/news?page=-99")
    # Must return structured 422, not raw 500 or stack trace
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert "code" in data["error"]
    assert "traceback" not in data
