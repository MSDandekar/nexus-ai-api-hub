from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path
import os
from dotenv import load_dotenv

# Resolve project root directory and .env absolute path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = ROOT_DIR / ".env"

# Explicitly load .env with override so environment is ready before settings instantiation
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH, override=True)
else:
    load_dotenv(override=True)

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
        env_file=str(ENV_PATH) if ENV_PATH.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

def _sanitize_key(key: Optional[str]) -> Optional[str]:
    if not key:
        return None
    cleaned = key.strip().strip('"').strip("'")
    return cleaned if cleaned else None

def get_gemini_api_key() -> Optional[str]:
    """Dynamically retrieves GEMINI_API_KEY from settings or os.environ, reloading .env if needed."""
    key = _sanitize_key(settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY"))
    if not key and ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH, override=True)
        key = _sanitize_key(os.environ.get("GEMINI_API_KEY"))
    return key

def get_openai_api_key() -> Optional[str]:
    """Dynamically retrieves OPENAI_API_KEY from settings or os.environ, reloading .env if needed."""
    key = _sanitize_key(settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY"))
    if not key and ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH, override=True)
        key = _sanitize_key(os.environ.get("OPENAI_API_KEY"))
    return key

def get_groq_api_key() -> Optional[str]:
    """Dynamically retrieves GROQ_API_KEY from settings or os.environ, reloading .env if needed."""
    key = _sanitize_key(settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY"))
    if not key and ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH, override=True)
        key = _sanitize_key(os.environ.get("GROQ_API_KEY"))
    return key

