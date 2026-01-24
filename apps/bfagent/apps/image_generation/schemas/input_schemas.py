"""
Input Schemas for Image Generation
===================================

Pydantic models for validating input to image generation handlers.
Follows BF Agent Handler Framework patterns.

Author: BF Agent Team
Version: 1.0.0
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from enum import Enum


class ImageProvider(str, Enum):
    """Supported image generation providers"""
    OPENAI = "openai"
    STABILITY = "stability"
    AUTO = "auto"  # Automatic selection


class ImageQuality(str, Enum):
    """Image quality levels"""
    STANDARD = "standard"
    HD = "hd"
    HIGH = "high"


class ImageStyle(str, Enum):
    """Common image styles"""
    NATURAL = "natural"
    VIVID = "vivid"
    PHOTOGRAPHIC = "photographic"
    DIGITAL_ART = "digital-art"
    ANIME = "anime"
    CINEMATIC = "cinematic"
    FANTASY = "fantasy"


class SingleImageGenerationInput(BaseModel):
    """
    Input for generating a single image.
    
    Used by generic image generation handler.
    """
    
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Text description of the image to generate"
    )
    
    provider: ImageProvider = Field(
        default=ImageProvider.AUTO,
        description="Preferred image generation provider"
    )
    
    size: Optional[str] = Field(
        default="1024x1024",
        description="Image dimensions (e.g., '1024x1024', '16:9')"
    )
    
    quality: ImageQuality = Field(
        default=ImageQuality.STANDARD,
        description="Image quality level"
    )
    
    style: Optional[ImageStyle] = Field(
        default=None,
        description="Art style for the image"
    )
    
    negative_prompt: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="What to avoid in the image (Stability AI)"
    )
    
    seed: Optional[int] = Field(
        default=None,
        ge=0,
        description="Random seed for reproducibility"
    )
    
    save_to_path: Optional[str] = Field(
        default=None,
        description="Path to save the generated image"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata to track with image"
    )
    
    @validator('prompt')
    def prompt_not_empty(cls, v):
        """Ensure prompt is not just whitespace"""
        if not v.strip():
            raise ValueError("Prompt cannot be empty or whitespace")
        return v.strip()
    
    class Config:
        use_enum_values = True


class BatchImageGenerationInput(BaseModel):
    """
    Input for generating multiple images.
    
    Supports batch generation with optional distribution across providers.
    """
    
    prompts: List[str] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of image prompts"
    )
    
    provider: ImageProvider = Field(
        default=ImageProvider.AUTO,
        description="Preferred image generation provider"
    )
    
    size: Optional[str] = Field(
        default="1024x1024",
        description="Image dimensions for all images"
    )
    
    quality: ImageQuality = Field(
        default=ImageQuality.STANDARD,
        description="Image quality level"
    )
    
    style: Optional[ImageStyle] = Field(
        default=None,
        description="Art style for all images"
    )
    
    distribute_load: bool = Field(
        default=True,
        description="Distribute generation across multiple providers"
    )
    
    save_to_directory: Optional[str] = Field(
        default=None,
        description="Directory to save generated images"
    )
    
    naming_pattern: str = Field(
        default="image_{index:03d}.png",
        description="Filename pattern (supports {index}, {timestamp})"
    )
    
    @validator('prompts')
    def prompts_not_empty(cls, v):
        """Ensure all prompts are valid"""
        cleaned = [p.strip() for p in v if p.strip()]
        if not cleaned:
            raise ValueError("At least one non-empty prompt required")
        return cleaned
    
    class Config:
        use_enum_values = True


class IllustrationGenerationInput(BaseModel):
    """
    Input for generating book/document illustrations.
    
    Specialized for BF Agent Educational Book System integration.
    """
    
    book_id: Optional[int] = Field(
        default=None,
        description="Related book ID (if applicable)"
    )
    
    chapter_id: Optional[int] = Field(
        default=None,
        description="Related chapter ID (if applicable)"
    )
    
    scene_descriptions: List[str] = Field(
        ...,
        min_items=1,
        description="List of scene descriptions to illustrate"
    )
    
    illustration_style: str = Field(
        default="children's book watercolor",
        description="Overall illustration style for consistency"
    )
    
    character_descriptions: Optional[Dict[str, str]] = Field(
        default=None,
        description="Consistent character descriptions (name -> description)"
    )
    
    aspect_ratio: str = Field(
        default="16:9",
        description="Aspect ratio for illustrations"
    )
    
    provider: ImageProvider = Field(
        default=ImageProvider.OPENAI,
        description="Preferred provider (DALL-E recommended for illustrations)"
    )
    
    quality: ImageQuality = Field(
        default=ImageQuality.STANDARD,
        description="Image quality"
    )
    
    save_to_directory: str = Field(
        ...,
        description="Directory to save illustrations"
    )
    
    naming_pattern: str = Field(
        default="illustration_{chapter}_{scene:02d}.png",
        description="Filename pattern"
    )
    
    ensure_consistency: bool = Field(
        default=True,
        description="Add style consistency prompts"
    )
    
    @validator('scene_descriptions')
    def validate_scenes(cls, v):
        """Ensure scene descriptions are valid"""
        if not v:
            raise ValueError("At least one scene description required")
        cleaned = [s.strip() for s in v if s.strip()]
        if len(cleaned) != len(v):
            raise ValueError("All scene descriptions must be non-empty")
        return cleaned
    
    class Config:
        use_enum_values = True


class ImageRegenerationInput(BaseModel):
    """
    Input for regenerating/modifying an existing image.
    
    For iterations and improvements.
    """
    
    original_image_id: int = Field(
        ...,
        description="ID of original image to regenerate"
    )
    
    modification_prompt: str = Field(
        ...,
        min_length=1,
        description="How to modify the image"
    )
    
    keep_original_prompt: bool = Field(
        default=True,
        description="Append to original prompt vs replace"
    )
    
    provider: ImageProvider = Field(
        default=ImageProvider.AUTO,
        description="Provider to use"
    )
    
    seed: Optional[int] = Field(
        default=None,
        description="Seed for reproducibility"
    )
    
    class Config:
        use_enum_values = True


class ProviderConfigInput(BaseModel):
    """
    Input for configuring providers.
    
    Used for runtime provider configuration.
    """
    
    provider: ImageProvider = Field(
        ...,
        description="Provider to configure"
    )
    
    api_key: str = Field(
        ...,
        min_length=10,
        description="API key for the provider"
    )
    
    model: Optional[str] = Field(
        default=None,
        description="Model to use (provider-specific)"
    )
    
    default_size: Optional[str] = Field(
        default=None,
        description="Default image size"
    )
    
    default_quality: Optional[str] = Field(
        default=None,
        description="Default quality level"
    )
    
    rate_limit_per_minute: Optional[int] = Field(
        default=None,
        ge=1,
        le=100,
        description="Rate limit (requests per minute)"
    )
    
    timeout_seconds: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Request timeout"
    )
    
    @validator('api_key')
    def validate_api_key(cls, v):
        """Basic API key validation"""
        if not v.startswith(('sk-', 'api-')):
            raise ValueError("Invalid API key format")
        return v
    
    class Config:
        use_enum_values = True


# Example usage and validation
if __name__ == "__main__":
    # Test single image input
    single = SingleImageGenerationInput(
        prompt="A cute cat wearing a hat",
        provider="openai",
        size="1024x1024",
        quality="standard"
    )
    print("Single image input:", single.dict())
    
    # Test batch input
    batch = BatchImageGenerationInput(
        prompts=[
            "A sunset over mountains",
            "A futuristic city",
            "An underwater scene"
        ],
        distribute_load=True
    )
    print("Batch input valid:", batch.dict())
    
    # Test illustration input
    illustration = IllustrationGenerationInput(
        book_id=1,
        scene_descriptions=[
            "Max and Mia arriving at the brain island",
            "The children solving a puzzle together"
        ],
        illustration_style="children's book watercolor",
        save_to_directory="/output/illustrations"
    )
    print("Illustration input valid:", illustration.dict())
