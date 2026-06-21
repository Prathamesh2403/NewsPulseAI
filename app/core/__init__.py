"""
Core configuration module.

Loads environment variables from .env and provides typed settings
via Pydantic BaseSettings.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # --- LLM (Gemini) ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # --- News Sources ---
    nyt_api_key: str = ""
    tavily_api_key: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "news_bot:v1.0"

    # --- Embedding ---
    embedding_model: str = "all-MiniLM-L6-v2"

    # --- Database ---
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/newsbot"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/newsbot"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- ChromaDB ---
    chroma_persist_dir: str = "./data/chroma_db"

    # --- Ingestion ---
    ingestion_interval_hours: int = 3

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_nyt_enabled(self) -> bool:
        return bool(self.nyt_api_key)

    @property
    def is_tavily_enabled(self) -> bool:
        return bool(self.tavily_api_key)

    @property
    def is_reddit_enabled(self) -> bool:
        return bool(self.reddit_client_id and self.reddit_client_secret)

    @property
    def is_llm_enabled(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — loaded once on first call."""
    return Settings()
