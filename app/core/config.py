"""
Core configuration module.

Loads environment variables from .env and provides typed settings
via Pydantic BaseSettings.
"""

from functools import lru_cache

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

    # --- Deployment ---
    environment: str = "development"  # "development" | "production"
    frontend_url: str = "http://localhost:5173"  # Vercel URL in production

    # --- Authentication ---
    admin_username: str = ""
    admin_password_hash: str = ""
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # --- LLM (Gemini) — primary provider ---
    gemini_api_key: str = ""
    gemini_api_keys: str = ""  # Comma-separated list
    gemini_model: str = "gemini-2.5-flash"

    # --- LLM (Groq) — fallback provider ---
    groq_api_key: str = ""
    groq_api_keys: str = ""  # Comma-separated list
    groq_model: str = "llama-3.1-8b-instant"

    # --- News Sources ---

    # NewsData.io
    newsdata_api_key: str = ""
    newsdata_api_keys: str = ""  # Comma-separated for round-robin

    # NewsAPI.ai (EventRegistry)
    newsapi_key: str = ""

    # ApiTube
    apitube_api_key: str = ""

    # GNews.io
    gnews_api_key: str = ""

    # Tavily — live search fallback only (NOT used for scheduled ingestion)
    tavily_api_key: str = ""
    tavily_api_keys: str = ""  # Comma-separated list for round-robin

    # Reddit / PRAW (not needed — using RSS)
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
    # In development: ./data/chroma_db (local)
    # In production (Render): /opt/render/project/src/data/vector_db (persistent disk)
    chroma_persist_dir: str = "./data/chroma_db"
    chromadb_path: str = "./data/chroma_db"  # Overridden by CHROMADB_PATH env var

    @property
    def resolved_chroma_path(self) -> str:
        """Return CHROMADB_PATH env var if explicitly overridden, else fall back to chroma_persist_dir."""
        if self.chromadb_path != "./data/chroma_db":
            return self.chromadb_path
        return self.chroma_persist_dir

    # --- Ingestion ---
    ingestion_interval_hours: int = 3

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # ---- Gemini keys -------------------------------------------------------

    @property
    def all_gemini_keys(self) -> list[str]:
        """All configured Gemini API keys (deduped)."""
        keys: list[str] = []
        if self.gemini_api_key:
            keys.append(self.gemini_api_key.strip())
        if self.gemini_api_keys:
            keys.extend([k.strip() for k in self.gemini_api_keys.split(",") if k.strip()])
        return list(dict.fromkeys(keys))  # dedupe, preserve order

    @property
    def is_llm_enabled(self) -> bool:
        """True if any LLM provider is configured."""
        return bool(self.all_gemini_keys or self.all_groq_keys)

    # ---- Groq keys ---------------------------------------------------------

    @property
    def all_groq_keys(self) -> list[str]:
        """All configured Groq API keys (deduped)."""
        keys: list[str] = []
        if self.groq_api_key:
            keys.append(self.groq_api_key.strip())
        if self.groq_api_keys:
            keys.extend([k.strip() for k in self.groq_api_keys.split(",") if k.strip()])
        return list(dict.fromkeys(keys))

    @property
    def is_groq_enabled(self) -> bool:
        return len(self.all_groq_keys) > 0

    # ---- Tavily keys -------------------------------------------------------

    @property
    def all_tavily_keys(self) -> list[str]:
        """All configured Tavily API keys (deduped)."""
        keys: list[str] = []
        if self.tavily_api_key:
            keys.append(self.tavily_api_key.strip())
        if self.tavily_api_keys:
            keys.extend([k.strip() for k in self.tavily_api_keys.split(",") if k.strip()])
        return list(dict.fromkeys(keys))

    @property
    def is_tavily_enabled(self) -> bool:
        return len(self.all_tavily_keys) > 0

    # ---- NewsData.io keys --------------------------------------------------

    @property
    def all_newsdata_keys(self) -> list[str]:
        """All configured NewsData.io API keys (deduped, for round-robin)."""
        keys: list[str] = []
        if self.newsdata_api_key:
            keys.append(self.newsdata_api_key.strip())
        if self.newsdata_api_keys:
            keys.extend([k.strip() for k in self.newsdata_api_keys.split(",") if k.strip()])
        return list(dict.fromkeys(keys))

    @property
    def is_newsdata_enabled(self) -> bool:
        return len(self.all_newsdata_keys) > 0

    # ---- Other sources -----------------------------------------------------

    @property
    def is_newsapi_enabled(self) -> bool:
        return bool(self.newsapi_key)

    @property
    def is_apitube_enabled(self) -> bool:
        return bool(self.apitube_api_key)

    @property
    def is_gnews_enabled(self) -> bool:
        return bool(self.gnews_api_key)

    @property
    def is_reddit_enabled(self) -> bool:
        # RSS feeds require no credentials — always enabled
        return True


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — loaded once on first call."""
    return Settings()
