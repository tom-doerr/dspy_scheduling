"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings
from pydantic import field_validator, ConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    openrouter_api_key: str

    # Database
    database_url: str = "sqlite:///tasks.db"

    # DSPy Configuration
    dspy_model: str = "openrouter/deepseek/deepseek-v3.2-exp"

    # Background Scheduler
    scheduler_interval_seconds: int = 5
    scheduler_enabled: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 5000

    # Logging
    log_level: str = "INFO"
    log_format: str = "standard"  # "json" or "standard"

    # Fallback Scheduling (when DSPy fails)
    fallback_start_hour: int = 9
    fallback_duration_hours: int = 1

    @field_validator('openrouter_api_key')
    @classmethod
    def validate_api_key(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('openrouter_api_key must not be empty')
        return v

    @field_validator('dspy_model')
    @classmethod
    def validate_dspy_model(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('dspy_model must not be empty')
        if '/' not in v:
            raise ValueError('dspy_model must be in format "provider/model" (e.g., "openrouter/deepseek/deepseek-v3.2-exp")')
        return v

    @field_validator('scheduler_interval_seconds')
    @classmethod
    def validate_scheduler_interval(cls, v):
        if v <= 0:
            raise ValueError('scheduler_interval_seconds must be positive')
        if v > 3600:
            raise ValueError('scheduler_interval_seconds must not exceed 3600 (1 hour)')
        return v

    @field_validator('fallback_start_hour')
    @classmethod
    def validate_fallback_start_hour(cls, v):
        if v < 0 or v > 23:
            raise ValueError('fallback_start_hour must be between 0 and 23')
        return v

    @field_validator('fallback_duration_hours')
    @classmethod
    def validate_fallback_duration(cls, v):
        if v <= 0:
            raise ValueError('fallback_duration_hours must be positive')
        return v

    @field_validator('log_format')
    @classmethod
    def validate_log_format(cls, v):
        valid_formats = ['json', 'standard']
        if v.lower() not in valid_formats:
            raise ValueError(f'log_format must be one of {valid_formats}')
        return v.lower()

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Global settings instance
settings = Settings()
