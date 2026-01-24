"""Image Generation Schemas"""

from .input_schemas import (
    SingleImageGenerationInput,
    BatchImageGenerationInput,
    IllustrationGenerationInput,
    ImageProvider,
    ImageQuality,
    ImageStyle,
)

from .output_schemas import (
    ImageOutput,
    SingleImageGenerationOutput,
    BatchImageGenerationOutput,
    IllustrationGenerationOutput,
    GenerationStatus,
)

# Aliases for convenience and backward compatibility
SingleImageInput = SingleImageGenerationInput
BatchImageInput = BatchImageGenerationInput
SingleImageOutput = SingleImageGenerationOutput
BatchImageOutput = BatchImageGenerationOutput

__all__ = [
    # Input schemas (full names)
    'SingleImageGenerationInput',
    'BatchImageGenerationInput',
    'IllustrationGenerationInput',
    'ImageProvider',
    'ImageQuality',
    'ImageStyle',
    # Output schemas (full names)
    'ImageOutput',
    'SingleImageGenerationOutput',
    'BatchImageGenerationOutput',
    'IllustrationGenerationOutput',
    'GenerationStatus',
    # Aliases (short names)
    'SingleImageInput',
    'BatchImageInput',
    'SingleImageOutput',
    'BatchImageOutput',
]