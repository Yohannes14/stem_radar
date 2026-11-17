"""FastAPI application factory, lifespan context, and router mounting."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.exceptions import (
    APIException,
    api_exception_handler,
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.api.middleware.logging import RequestLoggingMiddleware
from app.api.v1.router import v1_router
from app.config import settings, setup_logging
from app.database.database import get_engine, init_db

logger = logging.getLogger("stem_radar.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Asynchronous lifespan manager handling startup and shutdown hooks."""
    setup_logging()
    logger.info("Initializing STEM RADAR API application...")

    # Ensure database schema is ready
    await init_db()
    logger.info("Database connection validated and initialized.")

    yield

    # Graceful shutdown: close async database engine pool
    logger.info("Shutting down STEM RADAR API application. Disposing database engine...")
    engine = get_engine()
    await engine.dispose()
    logger.info("Database engine disposed cleanly.")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    app = FastAPI(
        title="STEM RADAR Intelligence API",
        version="0.1.0",
        description=(
            "AI-powered multi-source technology and STEM intelligence platform REST API. "
            "Delivers real-time technology news, arXiv research insights, trending developments, "
            "and multi-tier AI summaries and conceptual explanations."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Structured Request Logging Middleware
    app.add_middleware(RequestLoggingMiddleware)

    # 3. Centralized Exception Handlers
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)

    # 4. Mount API v1 Router
    app.include_router(v1_router)

    return app


app = create_app()
