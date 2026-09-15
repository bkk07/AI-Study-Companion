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
    jwt_expire_minutes: int = Field(default=60, alias="JWT_EXPIRE_MINUTES")

    # AI
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")

    # Background
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://redis:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://redis:6379/0", alias="CELERY_RESULT_BACKEND")

    # Storage
    upload_dir: str = Field(default="/data/uploads", alias="UPLOAD_DIR")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

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
