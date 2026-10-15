import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "LearnWhy AI"
    APP_ENV: str = "development"
    APP_VERSION: str = "1.0.0"

    # Default to local SQLite file if DATABASE_URL is not set in environment;
    # supports postgresql+psycopg2://... seamlessly for Docker/production.
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'learnwhy.db'}"

    JWT_SECRET_KEY: str = "learnwhy-local-dev-secret-override-via-env-var-in-prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Configurable learning model parameters (provisional baseline, not validated optimal weights)
    MASTERY_ALPHA: float = 0.20
    DEFAULT_PRIOR_MASTERY: float = 0.35
    REC_WEIGHT_GAP: float = 0.50
    REC_WEIGHT_PREREQ: float = 0.30
    REC_WEIGHT_DIFFICULTY: float = 0.20

    RULE_ENGINE_VERSION: str = "v1.0.0-rules"
    MASTERY_MODEL_VERSION: str = "v1.0.0-ema-alpha0.2"

    # Rate limits
    AUTH_RATE_LIMIT_PER_MINUTE: int = 45
    API_RATE_LIMIT_PER_MINUTE: int = 240

    # Optional LLM adapter settings (never exposed to browser)
    LLM_PROVIDER: str = "none"
    LLM_API_KEY: str = ""
    LLM_MODEL_NAME: str = ""
    LLM_TIMEOUT_SECONDS: int = 8

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
