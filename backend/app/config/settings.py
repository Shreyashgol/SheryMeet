"""Application configuration.

All configuration is environment-driven (12-factor). No secret or environment
specific value is ever hardcoded; every field below can be overridden via an
environment variable or a `.env` file. This module is the single source of truth
for configuration and is imported wherever settings are needed (via `get_settings`).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings loaded from the environment.

    Grouped by concern. Every field has a sensible, non-secret default so the
    application can boot in local/dev mode; secrets (API keys) default to empty
    and are validated lazily by the providers that need them.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_name: str = "meeting-intelligence-pipeline"
    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_json: bool = True

    # ── API ───────────────────────────────────────────────────────────────────
    api_v1_prefix: str = "/api/v1"
    # NoDecode: accept a comma-separated env string; parsed by `_split_csv` below.
    cors_allow_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    # ── Uploads ────────────────────────────────────────────────────────────────
    max_upload_bytes: int = 200 * 1024 * 1024  # 200 MB
    allowed_audio_formats: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["wav", "mp3"]
    )

    # ── Storage ────────────────────────────────────────────────────────────────
    storage_backend: Literal["local"] = "local"
    storage_local_dir: str = "/data/audio"

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/meetings"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_pre_ping: bool = True

    # ── Redis / Celery ─────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = ""
    celery_result_backend: str = ""
    celery_task_soft_time_limit: int = 1800  # 30 min soft limit per task
    celery_task_time_limit: int = 2100       # 35 min hard limit per task
    # When true, the pipeline runs INLINE in the calling process (no broker/worker
    # needed). Intended for constrained hosts (e.g. Render free tier) where a
    # separate background worker isn't available. Keep false for real async ops.
    celery_task_always_eager: bool = False

    # ── ASR (Automatic Speech Recognition) ─────────────────────────────────────
    asr_provider: Literal["local_whisper", "openai_whisper", "groq_whisper", "mock"] = (
        "local_whisper"
    )
    asr_model: str = "base"                    # faster-whisper size (local_whisper)
    asr_language: str | None = None            # None → auto-detect
    asr_timeout_seconds: int = 1200
    asr_device: str = "cpu"
    asr_compute_type: str = "int8"
    # Groq-hosted Whisper model id (used when asr_provider=groq_whisper). Reuses
    # groq_api_key / groq_base_url from the LLM section below.
    groq_whisper_model: str = "whisper-large-v3-turbo"

    # ── LLM ────────────────────────────────────────────────────────────────────
    llm_provider: Literal["claude", "openai", "gemini", "groq", "mock"] = "claude"
    llm_model: str = "claude-opus-4-8"
    llm_timeout_seconds: int = 120
    llm_max_output_tokens: int = 4096
    llm_temperature: float = 0.2
    # Groq exposes an OpenAI-compatible API at this base URL.
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # ── Provider credentials (secrets — never hardcoded) ───────────────────────
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""

    # ── Resilience / retries ───────────────────────────────────────────────────
    retry_max_attempts: int = 3
    retry_backoff_base_seconds: float = 2.0
    retry_backoff_max_seconds: float = 30.0

    @field_validator("cors_allow_origins", "allowed_audio_formats", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """Allow comma-separated env values for list fields (e.g. CORS_ALLOW_ORIGINS)."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: object) -> object:
        """Validate and normalize the database URL.

        Fails with a clear message when unset, and auto-corrects the common
        Neon copy-paste mistake of using the bare `postgresql://` (or
        `postgres://`) scheme instead of the psycopg2 driver scheme.
        """
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "DATABASE_URL is not set. Paste your Neon connection string into "
                "backend/.env, e.g. "
                "postgresql+psycopg2://<user>:<password>@<host>/<db>?sslmode=require"
            )
        url = value.strip()
        if url.startswith("postgresql+"):
            return url
        if url.startswith("postgresql://"):
            return "postgresql+psycopg2://" + url[len("postgresql://") :]
        if url.startswith("postgres://"):
            return "postgresql+psycopg2://" + url[len("postgres://") :]
        return url

    @property
    def broker_url(self) -> str:
        """Celery broker URL, defaulting to the Redis URL when unset."""
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        """Celery result backend, defaulting to the Redis URL when unset."""
        return self.celery_result_backend or self.redis_url


@lru_cache
def get_settings() -> Settings:
    """Return a cached `Settings` instance.

    Cached so configuration is parsed once per process. Tests can clear the cache
    via `get_settings.cache_clear()` to inject overrides.
    """
    return Settings()
