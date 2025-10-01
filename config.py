"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings
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

    # Fallback Scheduling (when DSPy fails)
    fallback_start_hour: int = 9
    fallback_duration_hours: int = 1

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
