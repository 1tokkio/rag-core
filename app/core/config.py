"""Application settings loaded from environment variables and an optional .env file."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration. Values come from the environment, never from code."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "rag-core"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://rag:rag@localhost:5433/rag"
    db_connect_timeout_seconds: int = 3

    # Ingestion limits (phase 2). Sizes are in bytes; chunk sizes are in characters.
    max_upload_bytes: int = 10 * 1024 * 1024
    default_chunk_size: int = 800
    default_chunk_overlap: int = 120
    max_chunk_size: int = 4000

    # Optional at startup: only required once /query is called (phase 4).
    anthropic_api_key: SecretStr | None = None
    llm_model: str = "claude-haiku-5-5"

    embedding_model: str = "intfloat/multilingual-e5-small"


@lru_cache
def get_settings() -> Settings:
    return Settings()
