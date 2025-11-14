from __future__ import annotations

"""Centralized application settings."""
# @tag:backend,config

# --- Imports -----------------------------------------------------------------
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# --- Constants ----------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "interactions.db"


# --- Settings model -----------------------------------------------------------
class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["local", "development", "production"] = Field(
        default="local", alias="ENVIRONMENT"
    )
    database_path: Path = Field(default=DEFAULT_DB_PATH, alias="DATABASE_PATH")
    llm_provider: Literal["openai", "echo"] = Field(
        default="echo", alias="LLM_PROVIDER"
    )
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    max_response_tokens: int = Field(default=512, alias="MAX_RESPONSE_TOKENS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


# --- Accessors ----------------------------------------------------------------
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a memoized settings object for the process lifetime."""

    return Settings()
