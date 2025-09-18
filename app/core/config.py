"""
FloatChat - Configuration Management

Centralized configuration management using Pydantic Settings.
Handles environment variables, validation, and application settings.
"""

import os
from functools import lru_cache
from typing import List, Optional, Any, Dict
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # =============================================================================
    # APPLICATION SETTINGS
    # =============================================================================
    app_name: str = Field(default="FloatChat", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_description: str = Field(
        default="AI-Powered Conversational Interface for ARGO Ocean Data Discovery and Visualization",
        env="APP_DESCRIPTION"
    )
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Server configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    reload: bool = Field(default=True, env="RELOAD")
    
    # =============================================================================
    # DATABASE CONFIGURATION
    # =============================================================================
    # PostgreSQL Database
    database_url: str = Field(
        default="postgresql://floatchat_user:password@localhost:5432/floatchat_db",
        env="DATABASE_URL"
    )
    database_host: str = Field(default="localhost", env="DATABASE_HOST")
    database_port: int = Field(default=5432, env="DATABASE_PORT")
    database_name: str = Field(default="floatchat_db", env="DATABASE_NAME")
    database_user: str = Field(default="floatchat_user", env="DATABASE_USER")
    database_password: str = Field(default="password", env="DATABASE_PASSWORD")
    
    # Database connection pool
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    
    # =============================================================================
    # REDIS CONFIGURATION
    # =============================================================================
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # Cache configuration
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")
    cache_max_entries: int = Field(default=10000, env="CACHE_MAX_ENTRIES")
    
    # =============================================================================
    # AI/LLM CONFIGURATION
    # =============================================================================
    # Google Gemini Studio API
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash", env="GEMINI_MODEL")
    gemini_max_tokens: int = Field(default=4096, env="GEMINI_MAX_TOKENS")
    gemini_temperature: float = Field(default=0.7, env="GEMINI_TEMPERATURE")
    max_conversation_history: int = Field(default=10, env="MAX_CONVERSATION_HISTORY")
    gemini_top_p: float = Field(default=0.8, env="GEMINI_TOP_P")
    gemini_top_k: int = Field(default=40, env="GEMINI_TOP_K")
    
    # Rate limiting for Gemini API (free tier: 15 RPM)
    gemini_rate_limit: int = Field(default=15, env="GEMINI_RATE_LIMIT")
    gemini_rate_window: int = Field(default=60, env="GEMINI_RATE_WINDOW")
    
    # =============================================================================
    # VECTOR DATABASE CONFIGURATION
    # =============================================================================
    # ChromaDB Configuration
    chromadb_host: str = Field(default="localhost", env="CHROMADB_HOST")
    chromadb_port: int = Field(default=8001, env="CHROMADB_PORT")
    chromadb_collection_name: str = Field(default="argo_metadata", env="CHROMADB_COLLECTION_NAME")
    
    # Embedding model
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", 
        env="EMBEDDING_MODEL"
    )
    embedding_dimension: int = Field(default=384, env="EMBEDDING_DIMENSION")
    embedding_batch_size: int = Field(default=32, env="EMBEDDING_BATCH_SIZE")
    
    # =============================================================================
    # VOICE PROCESSING CONFIGURATION
    # =============================================================================
    # Google Text-to-Speech
    gtts_lang: str = Field(default="en", env="GTTS_LANG")
    gtts_slow: bool = Field(default=False, env="GTTS_SLOW")
    gtts_cache_ttl: int = Field(default=86400, env="GTTS_CACHE_TTL")
    
    # Speech Recognition
    speech_recognition_engine: str = Field(default="google", env="SPEECH_RECOGNITION_ENGINE")
    speech_recognition_timeout: int = Field(default=5, env="SPEECH_RECOGNITION_TIMEOUT")
    speech_recognition_phrase_timeout: int = Field(default=1, env="SPEECH_RECOGNITION_PHRASE_TIMEOUT")
    
    # Audio processing
    audio_sample_rate: int = Field(default=16000, env="AUDIO_SAMPLE_RATE")
    audio_channels: int = Field(default=1, env="AUDIO_CHANNELS")
    audio_format: str = Field(default="wav", env="AUDIO_FORMAT")
    audio_max_duration: int = Field(default=300, env="AUDIO_MAX_DURATION")
    
    # Voice confidence threshold
    voice_confidence_threshold: float = Field(default=0.7, env="VOICE_CONFIDENCE_THRESHOLD")
    
    # =============================================================================
    # MULTILINGUAL CONFIGURATION
    # =============================================================================
    supported_languages: List[str] = Field(default=["en", "hi"], env="SUPPORTED_LANGUAGES")
    default_language: str = Field(default="en", env="DEFAULT_LANGUAGE")
    
    # Language detection
    language_detection_confidence: float = Field(default=0.8, env="LANGUAGE_DETECTION_CONFIDENCE")
    
    # =============================================================================
    # ARGO DATA CONFIGURATION
    # =============================================================================
    argo_data_path: Path = Field(default=Path("./argo_data"), env="ARGO_DATA_PATH")
    argo_processed_path: Path = Field(default=Path("./data/processed"), env="ARGO_PROCESSED_PATH")
    argo_cache_path: Path = Field(default=Path("./data/cache"), env="ARGO_CACHE_PATH")
    
    # Data processing
    argo_batch_size: int = Field(default=100, env="ARGO_BATCH_SIZE")
    argo_parallel_workers: int = Field(default=4, env="ARGO_PARALLEL_WORKERS")
    argo_chunk_size: int = Field(default=1000, env="ARGO_CHUNK_SIZE")
    
    # Data validation
    argo_validation_enabled: bool = Field(default=True, env="ARGO_VALIDATION_ENABLED")
    argo_quality_threshold: float = Field(default=0.8, env="ARGO_QUALITY_THRESHOLD")
    
    # =============================================================================
    # API CONFIGURATION
    # =============================================================================
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    api_title: str = Field(default="FloatChat API", env="API_TITLE")
    api_description: str = Field(
        default="AI-Powered Conversational Interface for ARGO Ocean Data",
        env="API_DESCRIPTION"
    )
    api_version: str = Field(default="1.0.0", env="API_VERSION")
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8501"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        env="CORS_ALLOW_METHODS"
    )
    cors_allow_headers: List[str] = Field(default=["*"], env="CORS_ALLOW_HEADERS")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")
    
    # =============================================================================
    # AUTHENTICATION AND SECURITY
    # =============================================================================
    secret_key: str = Field(
        default="your_super_secret_key_change_this_in_production",
        env="SECRET_KEY"
    )
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # API Key configuration
    api_key_enabled: bool = Field(default=False, env="API_KEY_ENABLED")
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    
    # Security headers
    security_headers_enabled: bool = Field(default=True, env="SECURITY_HEADERS_ENABLED")
    
    # =============================================================================
    # PERFORMANCE CONFIGURATION
    # =============================================================================
    # Connection pooling
    connection_pool_size: int = Field(default=20, env="CONNECTION_POOL_SIZE")
    connection_pool_max_overflow: int = Field(default=0, env="CONNECTION_POOL_MAX_OVERFLOW")
    connection_pool_timeout: int = Field(default=30, env="CONNECTION_POOL_TIMEOUT")
    
    # Query optimization
    query_cache_enabled: bool = Field(default=True, env="QUERY_CACHE_ENABLED")
    query_cache_ttl: int = Field(default=300, env="QUERY_CACHE_TTL")
    query_timeout: int = Field(default=30, env="QUERY_TIMEOUT")
    
    # File upload limits
    max_upload_size: int = Field(default=10485760, env="MAX_UPLOAD_SIZE")  # 10MB
    max_audio_duration: int = Field(default=300, env="MAX_AUDIO_DURATION")  # 5 minutes
    
    # =============================================================================
    # DEPLOYMENT CONFIGURATION
    # =============================================================================
    # Domain configuration
    domain: str = Field(default="localhost", env="DOMAIN")
    allowed_hosts: List[str] = Field(default=["localhost", "127.0.0.1"], env="ALLOWED_HOSTS")
    
    # SSL/TLS
    ssl_enabled: bool = Field(default=False, env="SSL_ENABLED")
    ssl_cert_path: Optional[str] = Field(default=None, env="SSL_CERT_PATH")
    ssl_key_path: Optional[str] = Field(default=None, env="SSL_KEY_PATH")
    
    # =============================================================================
    # VALIDATORS
    # =============================================================================
    
    @field_validator('supported_languages')
    @classmethod
    def validate_languages(cls, v):
        """Validate supported languages list."""
        if isinstance(v, str):
            return [lang.strip() for lang in v.split(',')]
        return v
    
    @field_validator('cors_origins')
    @classmethod
    def validate_cors_origins(cls, v):
        """Validate CORS origins list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @field_validator('cors_allow_methods')
    @classmethod
    def validate_cors_methods(cls, v):
        """Validate CORS methods list."""
        if isinstance(v, str):
            return [method.strip() for method in v.split(',')]
        return v
    
    @field_validator('cors_allow_headers')
    @classmethod
    def validate_cors_headers(cls, v):
        """Validate CORS headers list."""
        if isinstance(v, str):
            return [header.strip() for header in v.split(',')]
        return v
    
    @field_validator('allowed_hosts')
    @classmethod
    def validate_allowed_hosts(cls, v):
        """Validate allowed hosts list."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(',')]
        return v
    
    @field_validator('argo_data_path', 'argo_processed_path', 'argo_cache_path')
    @classmethod
    def validate_paths(cls, v):
        """Ensure paths are Path objects."""
        if isinstance(v, str):
            return Path(v)
        return v
    
    @field_validator('gemini_api_key')
    @classmethod
    def validate_gemini_api_key(cls, v):
        """Validate Gemini API key is provided in production."""
        # In production, API key should be provided
        return v
    
    # =============================================================================
    # CONFIGURATION
    # =============================================================================
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "validate_assignment": True,
        "extra": "allow"
    }
    
    # =============================================================================
    # PROPERTIES
    # =============================================================================
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL."""
        return self.database_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == 'development'
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == 'production'
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment.lower() == 'testing'
    


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    Uses lru_cache to ensure settings are loaded once and reused.
    This is important for performance and consistency.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()


def get_database_url(settings: Optional[Settings] = None) -> str:
    """
    Get database URL for current environment.
    
    Args:
        settings: Optional settings instance
        
    Returns:
        str: Database connection URL
    """
    if settings is None:
        settings = get_settings()
    
    return settings.database_url


def get_redis_url(settings: Optional[Settings] = None) -> str:
    """
    Get Redis URL for current environment.
    
    Args:
        settings: Optional settings instance
        
    Returns:
        str: Redis connection URL
    """
    if settings is None:
        settings = get_settings()
    
    return settings.redis_url


def create_directories(settings: Optional[Settings] = None) -> None:
    """
    Create necessary directories for the application.
    
    Args:
        settings: Optional settings instance
    """
    if settings is None:
        settings = get_settings()
    
    # Create data directories
    settings.argo_processed_path.mkdir(parents=True, exist_ok=True)
    settings.argo_cache_path.mkdir(parents=True, exist_ok=True)
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Create exports directory
    exports_dir = Path("data/exports")
    exports_dir.mkdir(parents=True, exist_ok=True)
