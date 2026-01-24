"""Image Generation Handlers"""

from .base_image_handler import (
    BaseImageHandler,
    HandlerError,
    ValidationError,
    ProcessingError,
    OutputError,
)

from .generic_image_handler import (
    SingleImageHandler,
    BatchImageHandler,
)

from .illustration_handler import (
    IllustrationGenerationHandler,
)

__all__ = [
    # Base classes
    'BaseImageHandler',
    'HandlerError',
    'ValidationError',
    'ProcessingError',
    'OutputError',
    # Generic handlers
    'SingleImageHandler',
    'BatchImageHandler',
    # Specialized handlers
    'IllustrationGenerationHandler',
]