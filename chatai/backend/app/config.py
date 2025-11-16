from __future__ import annotations

"""Centralized application settings."""
# @tag:backend,config

# --- Imports -----------------------------------------------------------------
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# --- Constants ----------------------------------------------------------------
_ENV_LAB_ROOT = os.environ.get("LAB_ROOT")
PROJECT_ROOT = Path(_ENV_LAB_ROOT).expanduser().resolve() if _ENV_LAB_ROOT else Path(__file__).resolve().parents[3]
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
    cosmos_endpoint: Optional[str] = Field(default=None, alias="COSMOS_ENDPOINT")
    cosmos_database: Optional[str] = Field(default=None, alias="COSMOS_DATABASE")
    cosmos_graph_container: str = Field(default="element-graphs", alias="COSMOS_GRAPH_CONTAINER")
    cosmos_run_container: str = Field(default="element-runs", alias="COSMOS_RUN_CONTAINER")
    cosmos_prefer_managed_identity: bool = Field(default=True, alias="COSMOS_USE_MANAGED_IDENTITY")
    cosmos_key: Optional[str] = Field(default=None, alias="COSMOS_KEY")
    cosmos_consistency: Literal["Session", "Eventual", "Strong", "ConsistentPrefix"] = Field(
        default="Session", alias="COSMOS_CONSISTENCY"
    )
    elements_max_active_runs: int = Field(
        default=3,
        alias="ELEMENTS_MAX_ACTIVE_RUNS",
        description="Guardrail limiting concurrent queued/running graph executions per workspace",
        ge=1,
        le=20,
    )

    @property
    def cosmos_enabled(self) -> bool:
        return bool(self.cosmos_endpoint and self.cosmos_database)


# --- Accessors ----------------------------------------------------------------
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a memoized settings object for the process lifetime."""

    return Settings()
