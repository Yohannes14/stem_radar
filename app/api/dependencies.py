"""FastAPI dependency injection providers."""

from typing import AsyncGenerator, Optional

from fastapi import Depends, Header, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.exceptions import UnauthorizedException
from app.config import settings
from app.database.database import get_session_factory
from app.database.repository import Repository
from app.services.ai.service import AIService, ai_service
from app.services.automation_service import AutomationService, automation_service
from app.services.news_service import NewsService

# Standard header extractor for API keys
api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an asynchronous SQLAlchemy session from the connection pool."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def get_repository(session: AsyncSession = Depends(get_db_session)) -> Repository:
    """Provide an instantiated database Repository scoped to current request."""
    return Repository(session)


def get_news_service() -> NewsService:
    """Provide the NewsService singleton/factory."""
    return NewsService()


def get_ai_service() -> AIService:
    """Provide the AIService instance."""
    return ai_service


def get_automation_service() -> AutomationService:
    """Provide the AutomationService instance."""
    return automation_service


async def require_api_key(
    x_api_key: Optional[str] = Security(api_key_header_scheme),
    authorization: Optional[str] = Header(default=None),
) -> str:
    """Validate API key authentication for protected endpoints.

    Accepts key via X-API-Key header or Authorization: Bearer <key>.
    In development, if no API_KEY is set in settings, access is allowed.
    """
    token = x_api_key
    if not token and authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    # In development mode, if no API key is configured, pass with fallback tag
    if not settings.api_key:
        if settings.is_production:
            raise UnauthorizedException(message="API_KEY must be configured in environment for production mode.")
        return token or "dev-unrestricted"

    if not token or token != settings.api_key:
        raise UnauthorizedException(message="Invalid or missing API key.")

    return token
