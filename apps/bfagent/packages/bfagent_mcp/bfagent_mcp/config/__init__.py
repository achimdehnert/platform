"""
BF Agent MCP Server - Configuration
=====================================

Zentrale Konfiguration mit Environment-Variable Support.

Design-Prinzipien:
- 12-Factor App: Config aus Environment
- Pydantic Settings: Typsichere Konfiguration
- Hierarchie: Defaults → .env → Environment Variables
- Validation: Fail-Fast bei ungültiger Konfiguration
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# =============================================================================
# ENVIRONMENT DETECTION
# =============================================================================

def get_environment() -> str:
    """Detect current environment."""
    return os.getenv("BFAGENT_ENV", "development")


def is_production() -> bool:
    """Check if running in production."""
    return get_environment() == "production"


def is_development() -> bool:
    """Check if running in development."""
    return get_environment() == "development"


def is_testing() -> bool:
    """Check if running in test mode."""
    return os.getenv("TESTING", "").lower() in ("1", "true", "yes")


# =============================================================================
# BASE SETTINGS
# =============================================================================

class BaseConfig(BaseSettings):
    """Base configuration with common settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="BFAGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


# =============================================================================
# SERVER SETTINGS
# =============================================================================

class ServerSettings(BaseConfig):
    """MCP Server configuration."""
    
    # Server Identity
    server_name: str = Field(
        default="bfagent_mcp",
        description="MCP Server name"
    )
    server_version: str = Field(
        default="2.0.0",
        description="Server version"
    )
    
    # Transport
    transport: Literal["stdio", "http"] = Field(
        default="stdio",
        description="Transport protocol: stdio (local) or http (remote)"
    )
    http_host: str = Field(
        default="127.0.0.1",
        description="HTTP server host"
    )
    http_port: int = Field(
        default=8765,
        description="HTTP server port",
        ge=1024,
        le=65535
    )
    
    # Timeouts
    request_timeout_seconds: int = Field(
        default=30,
        description="Request timeout in seconds",
        ge=5,
        le=300
    )
    
    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    
    # Debug
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )


# =============================================================================
# DJANGO SETTINGS
# =============================================================================

class DjangoSettings(BaseConfig):
    """Django integration configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="",  # Django uses standard env vars
        extra="ignore",
    )
    
    # Django Settings Module
    django_settings_module: str = Field(
        default="config.settings",
        alias="DJANGO_SETTINGS_MODULE",
        description="Django settings module path"
    )
    
    # Database (when not using Django)
    database_url: Optional[str] = Field(
        default=None,
        alias="DATABASE_URL",
        description="Database URL for direct connection"
    )
    
    # Use Django ORM
    use_django: bool = Field(
        default=False,
        description="Use Django ORM instead of mock data"
    )
    
    # BF Agent Root Path
    bfagent_root: Optional[str] = Field(
        default=None,
        alias="BFAGENT_ROOT",
        description="BF Agent project root directory"
    )
    
    @field_validator('bfagent_root')
    @classmethod
    def validate_bfagent_root(cls, v: Optional[str]) -> Optional[str]:
        """Validate BF Agent root path exists."""
        if v:
            path = Path(v)
            if not path.exists():
                import warnings
                warnings.warn(f"BFAGENT_ROOT path does not exist: {v}")
        return v


# =============================================================================
# AI SETTINGS
# =============================================================================

class AISettings(BaseConfig):
    """AI service configuration."""
    
    # OpenAI
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    openai_model: str = Field(
        default="gpt-4",
        description="Default OpenAI model"
    )
    openai_max_tokens: int = Field(
        default=4000,
        description="Max tokens for OpenAI requests",
        ge=100,
        le=128000
    )
    
    # Anthropic
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key"
    )
    anthropic_model: str = Field(
        default="claude-3-sonnet-20240229",
        description="Default Anthropic model"
    )
    
    # Ollama (Local)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL"
    )
    ollama_model: str = Field(
        default="dolphin-mixtral",
        description="Default Ollama model"
    )
    
    # AI Enhancement
    enable_ai_enhancement: bool = Field(
        default=True,
        description="Enable AI-powered code enhancement"
    )
    ai_enhancement_provider: Literal["openai", "anthropic", "ollama"] = Field(
        default="openai",
        description="Provider for AI enhancement"
    )
    
    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)
    
    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)


# =============================================================================
# CACHE SETTINGS
# =============================================================================

class CacheSettings(BaseConfig):
    """Cache configuration."""
    
    enable_cache: bool = Field(default=True, description="Enable response caching")
    domain_cache_ttl: int = Field(default=300, ge=0)
    handler_cache_ttl: int = Field(default=300, ge=0)
    best_practice_cache_ttl: int = Field(default=3600, ge=0)
    max_cache_size: int = Field(default=1000, ge=100)


# =============================================================================
# FEATURE FLAGS
# =============================================================================

class FeatureFlags(BaseConfig):
    """Feature flags for gradual rollout."""
    
    model_config = SettingsConfigDict(
        env_prefix="BFAGENT_FEATURE_",
        extra="ignore",
    )
    
    enable_ai_code_generation: bool = Field(default=True)
    enable_semantic_search: bool = Field(default=False)
    enable_usage_statistics: bool = Field(default=False)
    enable_experimental: bool = Field(default=False)


# =============================================================================
# COMBINED SETTINGS
# =============================================================================

class Settings(BaseSettings):
    """Combined application settings."""
    
    model_config = SettingsConfigDict(env_prefix="BFAGENT_", extra="ignore")
    
    environment: str = Field(default_factory=get_environment)
    
    @property
    def server(self) -> ServerSettings:
        return get_server_settings()
    
    @property
    def django(self) -> DjangoSettings:
        return get_django_settings()
    
    @property
    def ai(self) -> AISettings:
        return get_ai_settings()
    
    @property
    def cache(self) -> CacheSettings:
        return get_cache_settings()
    
    @property
    def features(self) -> FeatureFlags:
        return get_feature_flags()
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "environment": self.environment,
            "server": self.server.model_dump(),
            "django": self.django.model_dump(),
            "ai": {
                **self.ai.model_dump(),
                "openai_api_key": "***" if self.ai.openai_api_key else None,
                "anthropic_api_key": "***" if self.ai.anthropic_api_key else None,
            },
            "cache": self.cache.model_dump(),
            "features": self.features.model_dump(),
        }


# =============================================================================
# CACHED GETTERS (Singleton Pattern)
# =============================================================================

@lru_cache()
def get_server_settings() -> ServerSettings:
    return ServerSettings()


@lru_cache()
def get_django_settings() -> DjangoSettings:
    return DjangoSettings()


@lru_cache()
def get_ai_settings() -> AISettings:
    return AISettings()


@lru_cache()
def get_cache_settings() -> CacheSettings:
    return CacheSettings()


@lru_cache()
def get_feature_flags() -> FeatureFlags:
    return FeatureFlags()


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache():
    """Clear all cached settings (for testing)."""
    get_server_settings.cache_clear()
    get_django_settings.cache_clear()
    get_ai_settings.cache_clear()
    get_cache_settings.cache_clear()
    get_feature_flags.cache_clear()
    get_settings.cache_clear()


# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging():
    """Configure logging based on settings."""
    import logging
    import sys
    
    settings = get_server_settings()
    
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=settings.log_format,
        handlers=[logging.StreamHandler(sys.stderr)]
    )
    
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    return logging.getLogger("bfagent_mcp")


__all__ = [
    "ServerSettings", "DjangoSettings", "AISettings", "CacheSettings",
    "FeatureFlags", "Settings",
    "get_server_settings", "get_django_settings", "get_ai_settings",
    "get_cache_settings", "get_feature_flags", "get_settings",
    "clear_settings_cache", "setup_logging",
    "get_environment", "is_production", "is_development", "is_testing",
]
