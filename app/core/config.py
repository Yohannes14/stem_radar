"""Application configuration management using Pydantic Settings."""

from pathlib import Path
from typing import List, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """Production-grade typed application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram Bot
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_proxy_url: Optional[str] = Field(default=None, alias="TELEGRAM_PROXY_URL")
    telegram_connect_timeout: float = Field(default=30.0, alias="TELEGRAM_CONNECT_TIMEOUT")
    telegram_read_timeout: float = Field(default=30.0, alias="TELEGRAM_READ_TIMEOUT")
    allowed_telegram_user_ids: str = Field(default="", alias="ALLOWED_TELEGRAM_USER_IDS")
    allowed_user_ids: List[int] = Field(default_factory=list)

    # Database
    database_url: str = Field(default=f"sqlite+aiosqlite:///{DATA_DIR}/stem_radar.db", alias="DATABASE_URL")

    # Environment & Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # AI Engine Settings
    ai_provider: str = Field(default="openai", alias="AI_PROVIDER")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    ai_timeout: float = Field(default=30.0, alias="AI_TIMEOUT")
    ai_max_retries: int = Field(default=2, alias="AI_MAX_RETRIES")
    ai_cache_ttl_seconds: int = Field(default=86400, alias="AI_CACHE_TTL_SECONDS")
    ai_cost_tracking_enabled: bool = Field(default=True, alias="AI_COST_TRACKING_ENABLED")

    # Social & Developer APIs (Optional)
    github_token: Optional[str] = Field(default=None, alias="GITHUB_TOKEN")
    x_api_bearer_token: Optional[str] = Field(default=None, alias="X_API_BEARER_TOKEN")
    linkedin_client_id: Optional[str] = Field(default=None, alias="LINKEDIN_CLIENT_ID")
    linkedin_client_secret: Optional[str] = Field(default=None, alias="LINKEDIN_CLIENT_SECRET")

    # FastAPI Server & Security Settings
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_key: Optional[str] = Field(default=None, alias="API_KEY")
    api_admin_key: Optional[str] = Field(default=None, alias="API_ADMIN_KEY")
    api_rate_limit_per_minute: int = Field(default=60, alias="API_RATE_LIMIT_PER_MINUTE")
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    @model_validator(mode="after")
    def parse_user_ids(self) -> "Settings":
        if self.allowed_telegram_user_ids and not self.allowed_user_ids:
            parsed = []
            for raw in self.allowed_telegram_user_ids.split(","):
                cleaned = raw.strip()
                if cleaned.isdigit() or (cleaned.startswith("-") and cleaned[1:].isdigit()):
                    parsed.append(int(cleaned))
            self.allowed_user_ids = parsed
        return self

    def is_user_allowed(self, user_id: int) -> bool:
        """Verify whether a Telegram user is authorized."""
        if not self.allowed_user_ids:
            # If no IDs are specified, allow access in development
            return True
        return user_id in self.allowed_user_ids

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ("production", "prod")


settings = Settings()
