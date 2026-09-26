from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Nexus — Intelligent Multi-Model API Hub"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./ai_nexus.db"
    
    # AI Provider API Keys
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Gateway Security
    DEFAULT_ADMIN_API_KEY: str = "nexus-dev-master-key-2026"
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    
    # Environment
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
