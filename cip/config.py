"""Configuration management for CIP v2.

This module defines the application settings using Pydantic. All configuration
values are loaded from environment variables or a `.env` file. See
`.env.example` in the project root for the list of supported variables.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    openrouter_api_key: Optional[str] = Field(default=None, env="OPENROUTER_API_KEY")
    google_ai_api_key: Optional[str] = Field(default=None, env="GOOGLE_AI_API_KEY")
    groq_api_key: Optional[str] = Field(default=None, env="GROQ_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    admin_password: str = Field(..., env="ADMIN_PASSWORD")
    facilitator_password: str = Field(..., env="FACILITATOR_PASSWORD")
    max_users: int = Field(default=30, env="MAX_USERS")
    dev_mode: bool = Field(default=True, env="DEV_MODE")
    proto_mode: bool = Field(default=True, env="PROTO_MODE")
    pilot_mode: bool = Field(default=True, env="PILOT_MODE")
    log_level: str = Field(default="DEBUG", env="LOG_LEVEL")

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of the application settings."""
    return Settings()


settings = get_settings()