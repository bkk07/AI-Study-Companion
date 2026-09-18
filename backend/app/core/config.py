from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Centralized environment configuration — Phase 06.
    DATABASE_URL is the single relational source of truth (PostgreSQL + pgvector).
    All credentials are via env vars; never hardcoded. Mirrors backend/.env.example
    and docker-compose.yml service-name URLs (postgres/redis) vs host localhost.
    """

    # Database — SQLAlchemy URL with psycopg driver
    # Docker: postgresql+psycopg://postgres:postgres@postgres:5432/ai_study_companion
    # Host:   postgresql+psycopg://postgres:postgres@localhost:5432/ai_study_companion
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@postgres:5432/ai_study_companion",
        alias="DATABASE_URL",
    )

    # Auth
    jwt_secret: str = Field(default="change-me-to-a-long-random-string-at-least-32-chars", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=2880, alias="JWT_EXPIRE_MINUTES")

    # AI — LLM_PROVIDER selects the chat-completions backend ("groq" or "inception").
    # Mercury 2.5 only accepts temperature 0.5-1 (see groq_client clamp).
    llm_provider: str = Field(default="groq", alias="LLM_PROVIDER")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="openai/gpt-oss-20b", alias="GROQ_MODEL")
    inception_api_key: str = Field(default="", alias="INCEPTION_API_KEY")
    inception_model: str = Field(default="mercury-2.5", alias="INCEPTION_MODEL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_provider: str = Field(default="local", alias="EMBEDDING_PROVIDER")

    # Documents — hybrid PDF pipeline: PyMuPDF text + per-page Tesseract OCR
    # for scanned pages (worker only). Render DPI 300 is Tesseract's sweet spot.
    ocr_enabled: bool = Field(default=True, alias="OCR_ENABLED")
    ocr_language: str = Field(default="eng", alias="OCR_LANGUAGE")
    ocr_dpi: int = Field(default=300, alias="OCR_DPI")

    # Full extraction — structured tables + figure captions (worker only).
    # Tables use PyMuPDF find_tables (no new deps). Figures are cropped and
    # captioned via NaraRouter vision (OpenAI-compatible chat completions);
    # any vision failure falls back to cropped-OCR/placeholder, never failing
    # the document. Budgets bound cost/time on image-heavy PDFs.
    tables_enabled: bool = Field(default=True, alias="TABLES_ENABLED")
    vision_enabled: bool = Field(default=True, alias="VISION_ENABLED")
    vision_model: str = Field(
        default="stepfun-3.7-flash", alias="VISION_MODEL"
    )
    vision_max_images_per_doc: int = Field(default=12, alias="VISION_MAX_IMAGES_PER_DOC")
    vision_timeout_s: float = Field(default=20.0, alias="VISION_TIMEOUT_S")

    # NaraRouter vision provider (OpenAI-compatible).
    # Base URL: https://router.bynara.id/v1 → chat URL is {base}/chat/completions
    nararouter_api_key: str = Field(default="", alias="NARAROUTER_API_KEY")
    nararouter_base_url: str = Field(
        default="https://router.bynara.id/v1", alias="NARAROUTER_BASE_URL"
    )
    nararouter_model: str = Field(default="stepfun-3.7-flash", alias="NARAROUTER_MODEL")

    # Background
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://redis:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://redis:6379/0", alias="CELERY_RESULT_BACKEND")

    # Storage
    upload_dir: str = Field(default="/data/uploads", alias="UPLOAD_DIR")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:5175,http://127.0.0.1:5175",
        alias="CORS_ORIGINS",
    )

    # AI-cost protection (Phase 49): sliding-window budgets per LLM endpoint
    # scope, enforced per user and per project. Prototype defaults are generous;
    # tighten via env in production.
    rate_limit_llm_per_minute_user: int = Field(default=30, alias="RATE_LIMIT_LLM_PER_MINUTE_USER")
    rate_limit_llm_per_minute_project: int = Field(default=120, alias="RATE_LIMIT_LLM_PER_MINUTE_PROJECT")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
