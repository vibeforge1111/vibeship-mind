"""Configuration management for Mind v5."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MIND_",
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "mind"
    postgres_password: SecretStr = SecretStr("mind")
    postgres_db: str = "mind"

    @property
    def postgres_url(self) -> str:
        """Build PostgreSQL connection URL."""
        password = self.postgres_password.get_secret_value()
        return f"postgresql+asyncpg://{self.postgres_user}:{password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def postgres_url_sync(self) -> str:
        """Build synchronous PostgreSQL connection URL (for migrations)."""
        password = self.postgres_password.get_secret_value()
        return f"postgresql://{self.postgres_user}:{password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # NATS
    nats_url: str = "nats://localhost:4222"
    nats_user: str | None = None
    nats_password: SecretStr | None = None

    # Qdrant (optional, pgvector is default)
    qdrant_url: str | None = None
    qdrant_api_key: SecretStr | None = None

    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    openai_api_key: SecretStr | None = None

    # Temporal
    temporal_host: str = "localhost"
    temporal_port: int = 7233
    temporal_namespace: str = "default"

    # Observability
    otel_exporter_otlp_endpoint: str | None = None
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "console"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
