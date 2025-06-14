from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""
    
    # Google Cloud settings
    google_application_credentials: Optional[str] = Field(
        default=None, validation_alias="GOOGLE_APPLICATION_CREDENTIALS"
    )
    google_cloud_project: Optional[str] = Field(default=None, validation_alias="GOOGLE_CLOUD_PROJECT")
    vertex_ai_location: str = Field(default="us-central1", validation_alias="VERTEX_AI_LOCATION")
    
    # Gemini API settings
    gemini_api_key: Optional[str] = Field(default=None, validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", validation_alias="GEMINI_MODEL")
    
    # Vector database settings
    qdrant_url: str = Field(default="http://localhost:6333", validation_alias="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(default=None, validation_alias="QDRANT_API_KEY")
    qdrant_collection_name: str = Field(default="agent_documents", validation_alias="QDRANT_COLLECTION_NAME")
    chroma_host: Optional[str] = Field(default=None, validation_alias="CHROMA_HOST")
    chroma_port: Optional[int] = Field(default=None, validation_alias="CHROMA_PORT")
    chroma_persist_directory: str = Field(default="./data/chroma", validation_alias="CHROMA_PERSIST_DIRECTORY")
    chroma_collection_name: str = Field(default="agent_documents", validation_alias="CHROMA_COLLECTION_NAME")
    vector_db_type: str = Field(default="qdrant", validation_alias="VECTOR_DB_TYPE")
    
    # Database settings
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/app.db", validation_alias="DATABASE_URL"
    )
    database_echo: bool = Field(default=False, validation_alias="DATABASE_ECHO")
    
    # Server settings
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    reload: bool = Field(default=False, validation_alias="RELOAD")
    
    # Security settings
    secret_key: str = Field(default="your-secret-key-here", validation_alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", validation_alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Logging settings
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(default="json", validation_alias="LOG_FORMAT")
    log_file: str = Field(default="./logs/app.log", validation_alias="LOG_FILE")
    
    # External API keys
    openai_api_key: Optional[str] = Field(default=None, validation_alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    
    # Agent settings
    max_agents: int = Field(default=10, validation_alias="MAX_AGENTS")
    agent_timeout: int = Field(default=300, validation_alias="AGENT_TIMEOUT")
    workflow_max_iterations: int = Field(default=50, validation_alias="WORKFLOW_MAX_ITERATIONS")
    
    # Cache settings
    redis_url: str = Field(default="redis://localhost:6379", validation_alias="REDIS_URL")
    cache_ttl: int = Field(default=3600, validation_alias="CACHE_TTL")
    
    # Monitoring settings
    enable_metrics: bool = Field(default=True, validation_alias="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, validation_alias="METRICS_PORT")
    
    # CORS settings
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"], 
        validation_alias="ALLOWED_ORIGINS"
    )
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        directories = [
            Path(self.log_file).parent,
            Path(self.chroma_persist_directory),
            Path("./data"),
            Path("./logs"),
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()


def get_config() -> Settings:
    """전역 설정 인스턴스 반환"""
    return settings

def load_config(config_path: Optional[str] = None) -> Settings:
    """설정 파일 로드 및 설정 인스턴스 반환"""
    global settings
    if config_path:
        settings = Settings(_env_file=config_path)
    else:
        settings = Settings()
    return settings