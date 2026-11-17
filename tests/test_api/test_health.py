"""Tests for the /api/v1/health endpoint and application lifecycle."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_db_session
from app.api.main import app, lifespan


@pytest.mark.asyncio
async def test_health_endpoint_healthy(api_client: AsyncClient):
    """Test successful health check with connected database."""
    response = await api_client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data
    assert "details" in data
    assert "X-Process-Time" in response.headers


@pytest.mark.asyncio
async def test_health_endpoint_database_degraded(api_client: AsyncClient):
    """Test health check degradation when database connection fails."""

    async def broken_db_session():
        broken_session = AsyncMock()
        broken_session.execute.side_effect = RuntimeError("Database unreachable")
        yield broken_session

    app.dependency_overrides[get_db_session] = broken_db_session

    response = await api_client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"] == "disconnected"

    # Reset override
    app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_application_lifespan_lifecycle():
    """Verify application lifespan manager executes startup and shutdown safely."""
    with patch("app.api.main.init_db", new_callable=AsyncMock) as mock_init:
        with patch("app.api.main.get_engine") as mock_get_engine:
            mock_engine = AsyncMock()
            mock_get_engine.return_value = mock_engine

            async with lifespan(app):
                mock_init.assert_awaited_once()

            mock_engine.dispose.assert_awaited_once()

