"""Application configuration and environment settings.

Provides central configuration loaded from environment variables and .env file
with production-minded defaults and type safety.
"""

import os
from pathlib import Path
from typing import Optional

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
            case_sensitive=False,
        )

        APP_NAME: str = "Bulk Certificate Generator"
        APP_VERSION: str = "1.0.0"
        APP_ENV: str = "development"
        DEBUG: bool = True
        API_V1_PREFIX: str = "/api/v1"

        # Database Configuration (SQLite default)
        DATABASE_URL: str = "sqlite:///./certificates.db"

        # Storage Configuration
        CERTIFICATE_OUTPUT_DIR: str = "./generated_certificates"

        # Bulk Job Limits
        MAX_BATCH_SIZE: int = 500

except ImportError:
    # Fallback if pydantic-settings is loading or in minimal environment
    class Settings:  # type: ignore
        APP_NAME: str = os.getenv("APP_NAME", "Bulk Certificate Generator")
        APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
        APP_ENV: str = os.getenv("APP_ENV", "development")
        DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
        API_V1_PREFIX: str = os.getenv("API_V1_PREFIX", "/api/v1")
        DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./certificates.db")
        CERTIFICATE_OUTPUT_DIR: str = os.getenv("CERTIFICATE_OUTPUT_DIR", "./generated_certificates")
        MAX_BATCH_SIZE: int = int(os.getenv("MAX_BATCH_SIZE", "500"))


settings = Settings()
