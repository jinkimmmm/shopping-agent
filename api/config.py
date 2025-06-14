"""Configuration settings for the Shopping Agent API"""

import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # Database Settings
    database_url: str = "sqlite:///./shopping_agent.db"
    
    # AI Model Settings
    openai_api_key: str = ""
    model_name: str = "gpt-3.5-turbo"
    max_tokens: int = 1000
    temperature: float = 0.7
    
    # Shopping Settings
    max_results: int = 10
    search_timeout: int = 30
    
    # Logging Settings
    log_level: str = "INFO"
    log_file: str = "shopping_agent.log"
    
    class Config:
        env_file = ".env"
        extra = "allow"

# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get application settings"""
    return settings

# Environment-specific configurations
def get_cors_origins() -> List[str]:
    """Get CORS origins from environment or use defaults"""
    origins_env = os.getenv("SHOPPING_AGENT_CORS_ORIGINS")
    if origins_env:
        return [origin.strip() for origin in origins_env.split(",")]
    return settings.cors_origins

def is_development() -> bool:
    """Check if running in development mode"""
    return os.getenv("SHOPPING_AGENT_ENV", "development").lower() == "development"

def is_production() -> bool:
    """Check if running in production mode"""
    return os.getenv("SHOPPING_AGENT_ENV", "development").lower() == "production"