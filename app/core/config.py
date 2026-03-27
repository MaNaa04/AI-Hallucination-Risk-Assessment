"""
Settings and configuration management.
Loads environment variables from .env file.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""
    
    # API Configuration
    app_name: str = "AI Hallucination Detection Backend"
    app_version: str = "0.1.0"
    app_debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # LLM Configuration
    llm_provider: str = "gemini"  # "gemini" or "openai"
    llm_api_key: str = ""
    llm_model: str = "gemini-2.0-flash"  # or "gpt-4", "gpt-3.5-turbo"
    llm_api_base: str = ""
    
    # External API Keys
    serpapi_key: str = ""
    wikipedia_api_enabled: bool = True
    
    # Caching
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    
    # Evidence Configuration
    max_evidence_tokens: int = 800
    max_claims_per_request: int = 3
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
