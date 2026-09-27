import os
import urllib.parse
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Deployment Environment
    ENVIRONMENT: Literal["development", "production", "testing"] = "development"
    DATABASE_URL: str
    
    SECRET_KEY: str = "7a4f9b8c2d1e6f3a5b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60


    DEFAULT_LLM_PROVIDER: Literal["openai", "gemini", "anthropic", "mock"] = "mock"
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def encoded_database_url(self) -> str:
        url = self.DATABASE_URL
        if "@" in url:
            try:
                prefix, rest = url.split("://", 1)
                auth, host = rest.rsplit("@", 1)
                user, password = auth.split(":", 1)
                encoded_password = urllib.parse.quote_plus(password)
                return f"{prefix}://{user}:{encoded_password}@{host}"
            except ValueError:
                return url
        return url

settings = Settings()
