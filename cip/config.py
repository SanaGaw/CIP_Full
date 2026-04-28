"""Configuration management for CIP v2.

This module defines the application settings using Pydantic. All configuration
values are loaded from environment variables or a `.env` file. See
`.env.example` in the project root for the list of supported variables.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    openrouter_api_key: Optional[str] = Field(default=None)
    google_ai_api_key: Optional[str] = Field(default=None)
    groq_api_key: Optional[str] = Field(default=None)
    grok_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    admin_password: str = Field(...)
    facilitator_password: str = Field(...)
    max_users: int = Field(default=30)
    dev_mode: bool = Field(default=True)
    proto_mode: bool = Field(default=True)
    pilot_mode: bool = Field(default=True)
    log_level: str = Field(default="DEBUG")

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }

    @model_validator(mode="before")
    @classmethod
    def _normalize_groq_alias(cls, values):
        if values is None:
            return values

        groq_value = values.get("groq_api_key")
        grok_value = values.get("grok_api_key")
        if groq_value is None and grok_value is not None:
            values["groq_api_key"] = grok_value
        return values


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of the application settings."""
    return Settings()


settings = get_settings()