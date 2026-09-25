import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Project metadata
    PROJECT_NAME: str = "AG004 — CI/CD Failure Triage & Flaky-Test Predictor"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Environment & Database
    ENV: str = "development"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ag004"
    POSTGRES_USER: str = "ag004"
    POSTGRES_PASSWORD: str = "changeme"
    DATABASE_URL: Optional[str] = None
    SQLITE_FALLBACK: bool = True
    SQLITE_PATH: str = "./ag004.db"

    # Security & Auth
    JWT_SECRET: str = "ag004-super-secure-production-ready-jwt-secret-key-replace-in-env-32bytes!"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ADMIN_BOOTSTRAP_PASSWORD: Optional[str] = None

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8000"
    ]

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 120

    # GitHub integration
    GITHUB_APP_ID: Optional[str] = None
    GITHUB_APP_PRIVATE_KEY_PATH: Optional[str] = "./secrets/github-app-private-key.pem"
    GITHUB_WEBHOOK_SECRET: str = "ag004-webhook-secret-token"
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_REPO_OWNER: Optional[str] = "example-org"
    GITHUB_REPO_NAME: Optional[str] = "demo-pipeline-repo"

    # Qdrant Vector Store
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "failure_embeddings"
    QDRANT_LOCAL_PATH: str = "./qdrant_storage"

    # LLM (Ollama / Local OpenAI-compatible)
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    LLM_MODEL: str = "llama3.1:8b"
    LLM_API_KEY: str = "local"
    LLM_TIMEOUT: int = 30
    LLM_FALLBACK_REASONER: bool = True

    # Cold-start evaluation rule
    MIN_REAL_SAMPLES: int = 200

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        # If postgres credentials provided and not sqlite fallback requested explicitly
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()
