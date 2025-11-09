"""
Configuration management using Pydantic Settings.
Centralizes all environment variable handling with validation and type safety.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Weaviate configuration
    weaviate_url: str = "http://weaviate:8080"
    
    # OpenAI configuration
    openai_apikey: str = ""
    
    # Storage configuration
    upload_dir: str = "uploads/resumes"
    
    # CORS configuration
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080"
    
    # Logging configuration
    log_level: str = "INFO"
    
    # File upload security
    max_upload_size: int = 10 * 1024 * 1024  # 10MB in bytes
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    @property
    def max_upload_size_mb(self) -> float:
        """Get max upload size in MB."""
        return self.max_upload_size / (1024 * 1024)


# Singleton settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the singleton settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset the singleton settings instance. Useful for testing."""
    global _settings
    _settings = None

