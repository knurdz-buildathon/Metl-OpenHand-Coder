"""
Application configuration via pydantic-settings, loaded from environment / .env.
"""

from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Metl Agent API.

    Values are loaded from environment variables or a ``.env`` file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- Database (SQLite for MVP) -----------------------------------------
    DATABASE_URL: str = "sqlite+aiosqlite:///app/data/metl.db"

    # -- Control Panel integration -----------------------------------------
    CONTROL_PANEL_WEBHOOK_URL: str = ""

    # -- Docker images -----------------------------------------------------
    OPENHANDS_IMAGE: str = "ghcr.io/all-hands-ai/openhands:latest"
    PREVIEW_NGINX_IMAGE: str = "nginx:alpine"

    # -- Preview infrastructure --------------------------------------------
    PREVIEW_BASE_DOMAIN: str = "code.metl.run"
    PREVIEW_PORT_RANGE_START: int = 9000
    PREVIEW_PORT_RANGE_END: int = 9100

    # -- Artifacts storage -------------------------------------------------
    ARTIFACTS_DIR: str = "/tmp/metl-artifacts"

    # -- GitHub ------------------------------------------------------------
    GITHUB_TOKEN: Optional[str] = None

    # -- LLM API keys (individual provider keys) ----------------------------
    LLM_OPENAI_API_KEY: Optional[str] = None
    LLM_ANTHROPIC_API_KEY: Optional[str] = None
    LLM_GOOGLE_API_KEY: Optional[str] = None
    LLM_MISTRAL_API_KEY: Optional[str] = None

    # -- Azure AI Foundry (custom OpenAI-compatible endpoint) ---------------
    AZURE_AI_API_KEY: Optional[str] = None
    AZURE_AI_BASE_URL: Optional[str] = None
    AZURE_AI_MODEL: str = "gpt-4o"

    # -- Job execution ------------------------------------------------------
    JOB_EXECUTION_TIMEOUT: int = 3600  # seconds
    MAX_ITERATIONS: int = 10

    # -- v0 API (optional) -------------------------------------------------
    V0_API_URL: str = ""
    V0_API_KEY: Optional[str] = None


settings = Settings()