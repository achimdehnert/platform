"""Image Generation Configuration"""

from .config_loader import (
    get_config,
    ConfigLoader,
    DjangoImageGenerationConfig,
    ImageGenerationConfig,  # Alias for ConfigLoader
)

__all__ = [
    'get_config',
    'ConfigLoader',
    'ImageGenerationConfig',  # Backward compatibility
    'DjangoImageGenerationConfig',
]