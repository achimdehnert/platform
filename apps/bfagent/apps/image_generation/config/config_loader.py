"""
Configuration Loader
====================

Loads and validates configuration from YAML files and environment variables.

Author: BF Agent Team
Version: 1.0.0
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class ConfigLoader:
    """
    Loads configuration from YAML and environment variables.
    
    Priority:
    1. Environment variables (highest)
    2. YAML configuration
    3. Defaults (lowest)
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize config loader.
        
        Args:
            config_path: Path to YAML config file
        """
        if config_path is None:
            config_path = Path(__file__).parent / "providers.yaml"
        
        self.config_path = config_path
        self.config = self._load_config()
        
        logger.info(
            "Configuration loaded",
            config_path=str(config_path),
            providers_enabled=len(self.get_enabled_providers())
        )
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific provider.
        
        Args:
            provider_name: Name of provider (e.g., 'openai', 'stability')
            
        Returns:
            Provider configuration dict
        """
        providers = self.config.get('providers', {})
        provider_config = providers.get(provider_name, {})
        
        # Get API key from environment if specified
        if 'api_key_env' in provider_config:
            env_var = provider_config['api_key_env']
            api_key = os.getenv(env_var)
            if api_key:
                provider_config['api_key'] = api_key
            else:
                logger.warning(
                    f"API key environment variable not set: {env_var}",
                    provider=provider_name
                )
        
        return provider_config
    
    def get_enabled_providers(self) -> list:
        """Get list of enabled provider names"""
        providers = self.config.get('providers', {})
        return [
            name for name, config in providers.items()
            if config.get('enabled', False)
        ]
    
    def get_manager_config(self) -> Dict[str, Any]:
        """Get ProviderManager configuration"""
        return self.config.get('manager', {})
    
    def get_handler_config(self, handler_name: str) -> Dict[str, Any]:
        """Get configuration for a specific handler"""
        handlers = self.config.get('handlers', {})
        return handlers.get(handler_name, {})
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration"""
        return self.config.get('storage', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.config.get('logging', {})
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return self.config.get('monitoring', {})
    
    def get_development_config(self) -> Dict[str, Any]:
        """Get development settings"""
        return self.config.get('development', {})
    
    def is_dry_run(self) -> bool:
        """Check if dry-run mode is enabled"""
        dev_config = self.get_development_config()
        return dev_config.get('dry_run', False)
    
    def get_cost_limit(self, limit_type: str = 'daily') -> float:
        """
        Get cost limit in cents.
        
        Args:
            limit_type: 'daily' or 'per_image'
            
        Returns:
            Cost limit in cents
        """
        monitoring = self.get_monitoring_config()
        alerts = monitoring.get('cost_alerts', {})
        
        if limit_type == 'daily':
            return alerts.get('daily_limit_cents', float('inf'))
        elif limit_type == 'per_image':
            return alerts.get('per_image_limit_cents', float('inf'))
        
        return float('inf')
    
    def reload(self):
        """Reload configuration from file"""
        self.config = self._load_config()
        logger.info("Configuration reloaded")


# Global config instance
_config_instance = None


def get_config(config_path: Optional[Path] = None) -> ConfigLoader:
    """
    Get global configuration instance.
    
    Args:
        config_path: Path to config file (only used on first call)
        
    Returns:
        ConfigLoader instance
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = ConfigLoader(config_path)
    
    return _config_instance


# Example usage
if __name__ == "__main__":
    # Load config
    config = get_config()
    
    # Get provider configs
    openai_config = config.get_provider_config('openai')
    print("OpenAI config:", openai_config.get('model'))
    
    stability_config = config.get_provider_config('stability')
    print("Stability config:", stability_config.get('model'))
    
    # Get enabled providers
    enabled = config.get_enabled_providers()
    print("Enabled providers:", enabled)
    
    # Get handler config
    illustration_config = config.get_handler_config('illustration')
    print("Illustration handler config:", illustration_config)
    
    # Get storage config
    storage = config.get_storage_config()
    print("Storage base directory:", storage.get('base_directory'))
    
    # Check dry run
    print("Dry run mode:", config.is_dry_run())


# Django Integration
def get_django_config():
    """Get configuration from Django settings if available"""
    try:
        from django.conf import settings
        
        if hasattr(settings, 'IMAGE_GENERATION'):
            return DjangoImageGenerationConfig()
    except (ImportError, Exception):
        pass
    
    return None


class DjangoImageGenerationConfig:
    """Configuration from Django settings"""
    
    def __init__(self):
        from django.conf import settings
        self.settings = settings.IMAGE_GENERATION
    
    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """Get provider config from Django settings"""
        providers = self.settings.get('PROVIDERS', {})
        provider_config = providers.get(provider_name.upper(), {})
        
        return {
            'api_key': provider_config.get('API_KEY', ''),
            'model': provider_config.get('MODEL', ''),
            'enabled': provider_config.get('ENABLED', False),
            'default_size': provider_config.get('DEFAULT_SIZE'),
            'default_quality': provider_config.get('DEFAULT_QUALITY'),
            'rate_limit_per_minute': provider_config.get('RATE_LIMIT_PER_MINUTE', 10),
        }
    
    def get_enabled_providers(self):
        """Get list of enabled providers"""
        providers = self.settings.get('PROVIDERS', {})
        return [name.lower() for name, config in providers.items() if config.get('ENABLED', False)]
    
    def get_manager_config(self) -> Dict[str, Any]:
        """Get manager configuration"""
        return self.settings.get('MANAGER', {})
    
    def get_handler_config(self, handler_name: str) -> Dict[str, Any]:
        """Get handler configuration"""
        handlers = self.settings.get('HANDLERS', {})
        return handlers.get(handler_name.upper(), {})
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration"""
        return {
            'base_directory': self.settings.get('OUTPUT_DIR', 'media/generated_images')
        }
    
    def is_dry_run(self) -> bool:
        """Check if in dry run mode"""
        return self.settings.get('DRY_RUN', False)


# Alias for backward compatibility
ImageGenerationConfig = ConfigLoader


# Smart get_config that tries Django first
_config_instance = None

def get_config():
    """Get configuration (Django-aware)"""
    global _config_instance
    
    if _config_instance is None:
        # Try Django first
        django_config = get_django_config()
        if django_config:
            _config_instance = django_config
            logger.info("Using Django settings for configuration")
        else:
            # Fallback to YAML
            _config_instance = ConfigLoader()
            logger.info("Using YAML configuration")
    
    return _config_instance
