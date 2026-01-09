"""
Configuration Management using Pydantic

Loads and validates environment variables. Fails fast on startup if config is invalid.

Usage:
    from bot.utils.config import settings
    print(settings.TELEGRAM_BOT_TOKEN)
"""

import json
from typing import Dict, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    TELEGRAM_BOT_TOKEN: str = Field(..., description="Telegram Bot API token")
    ADMIN_TELEGRAM_IDS: str = Field(..., description="Comma-separated admin IDs")

    LLM_PROVIDER: str = Field(default="openai", description="LLM provider: openai, claude, or gemini")
    OPENAI_API_KEY: str | None = Field(default=None)
    ANTHROPIC_API_KEY: str | None = Field(default=None)
    GOOGLE_API_KEY: str | None = Field(default=None)

    DATABASE_URL: str = Field(..., description="PostgreSQL connection URL")

    MENTOR_DOMAINS: str = Field(
        default='{"computer_vision": [], "research": [], "data_science": []}',
        description="JSON mapping of domains to mentor IDs"
    )

    LOG_LEVEL: str = Field(default="INFO")
    ENVIRONMENT: str = Field(default="development")

    MODERATION_CONFIDENCE_THRESHOLD: float = Field(default=0.7, ge=0.0, le=1.0)
    FAQ_SIMILARITY_THRESHOLD: float = Field(default=0.85, ge=0.0, le=1.0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @field_validator("LLM_PROVIDER")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Ensure LLM provider is valid"""
        allowed = ["openai", "claude", "gemini"]
        if v not in allowed:
            raise ValueError(f"LLM_PROVIDER must be one of {allowed}, got: {v}")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid"""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}, got: {v}")
        return v

    # Helper methods

    def get_admin_ids(self) -> List[int]:
        """Parse comma-separated admin IDs"""
        return [int(id_.strip()) for id_ in self.ADMIN_TELEGRAM_IDS.split(",")]

    def get_mentor_domains(self) -> Dict[str, List[int]]:
        """Parse JSON mentor domains"""
        return json.loads(self.MENTOR_DOMAINS)

    def get_llm_api_key(self) -> str:
        """Get API key for selected provider"""
        if self.LLM_PROVIDER == "openai":
            if not self.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
            return self.OPENAI_API_KEY
        elif self.LLM_PROVIDER == "claude":
            if not self.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=claude")
            return self.ANTHROPIC_API_KEY
        elif self.LLM_PROVIDER == "gemini":
            if not self.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY is required when LLM_PROVIDER=gemini")
            return self.GOOGLE_API_KEY
        else:
            raise ValueError(f"Unknown LLM provider: {self.LLM_PROVIDER}")

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"


settings = Settings()

try:
    settings.get_llm_api_key()
except ValueError as e:
    print(f"Configuration Error: {e}")
    raise
