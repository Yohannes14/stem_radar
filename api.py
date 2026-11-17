"""STEM RADAR FastAPI application launcher."""

import os

import uvicorn

from app.config import settings

if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.api_port))
    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=port,
        reload=not settings.is_production,
        log_level=settings.log_level.lower(),
    )
