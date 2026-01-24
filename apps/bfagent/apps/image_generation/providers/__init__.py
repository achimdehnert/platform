"""
Image Generation Providers
===========================

Collection of image generation providers with unified interface.

Available Providers:
- OpenAIProvider: DALL-E 3
- StabilityAIProvider: Stable Diffusion 3

Author: BF Agent Team
Version: 1.0.0
"""

from .base_provider import (
    BaseImageProvider,
    ProviderConfig,
    ImageGenerationResult,
    ProviderStatus,
    ProviderError,
    RateLimitError,
    AuthenticationError,
    InvalidParameterError
)

from .openai_provider import OpenAIProvider
from .stability_provider import StabilityAIProvider
from .provider_manager import ProviderManager, SelectionStrategy, ProviderMetrics

__all__ = [
    # Base classes
    'BaseImageProvider',
    'ProviderConfig',
    'ImageGenerationResult',
    'ProviderStatus',
    
    # Exceptions
    'ProviderError',
    'RateLimitError',
    'AuthenticationError',
    'InvalidParameterError',
    
    # Providers
    'OpenAIProvider',
    'StabilityAIProvider',
    
    # Manager
    'ProviderManager',
    'SelectionStrategy',
    'ProviderMetrics',
]
