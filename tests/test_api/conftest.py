"""FastAPI test fixtures and client configuration."""

from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_db_session
from app.api.main import app


@pytest_asyncio.fixture
async def api_client(test_session_factory) -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous HTTP test client mapped to in-memory test database."""

    async def override_get_db_session():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
