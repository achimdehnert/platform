"""
Output Schemas for Image Generation
====================================

Pydantic models for handler output validation.
Ensures consistent return values across all image generation handlers.

Author: BF Agent Team
Version: 1.0.0
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class GenerationStatus(str, Enum):
    """Status of image generation"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    PENDING = "pending"


class ImageOutput(BaseModel):
    """
    Output for a single generated image.
    """
    
    success: bool = Field(
        ...,
        description="Whether generation was successful"
    )
    
    image_id: Optional[int] = Field(
        default=None,
        description="Database ID of saved image"
    )
    
    url: Optional[str] = Field(
        default=None,
        description="URL of generated image (from provider)"
    )
    
    local_path: Optional[str] = Field(
        default=None,
        description="Local filesystem path to saved image"
    )
    
    prompt_used: str = Field(
        ...,
        description="Actual prompt used for generation"
    )
    
    revised_prompt: Optional[str] = Field(
        default=None,
        description="Provider-revised prompt (if applicable)"
    )
    
    provider: str = Field(
        ...,
        description="Provider that generated the image"
    )
    
    model: Optional[str] = Field(
        default=None,
        description="Specific model used"
    )
    
    generation_time_seconds: float = Field(
        ...,
        ge=0,
        description="Time taken to generate"
    )
    
    cost_cents: float = Field(
        ...,
        ge=0,
        description="Cost in cents"
    )
    
    size: Optional[str] = Field(
        default=None,
        description="Image dimensions"
    )
    
    file_size_bytes: Optional[int] = Field(
        default=None,
        description="File size in bytes"
    )
    
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="Generation timestamp"
    )
    
    class Config:
        use_enum_values = True


class SingleImageGenerationOutput(BaseModel):
    """
    Output from single image generation handler.
    """
    
    status: GenerationStatus = Field(
        ...,
        description="Overall generation status"
    )
    
    image: ImageOutput = Field(
        ...,
        description="Generated image details"
    )
    
    total_cost_cents: float = Field(
        ...,
        ge=0,
        description="Total cost"
    )
    
    total_time_seconds: float = Field(
        ...,
        ge=0,
        description="Total processing time"
    )
    
    handler_version: str = Field(
        default="1.0.0",
        description="Handler version used"
    )
    
    class Config:
        use_enum_values = True


class BatchImageGenerationOutput(BaseModel):
    """
    Output from batch image generation handler.
    """
    
    status: GenerationStatus = Field(
        ...,
        description="Overall batch status"
    )
    
    images: List[ImageOutput] = Field(
        ...,
        description="List of generated images"
    )
    
    total_requested: int = Field(
        ...,
        ge=1,
        description="Total images requested"
    )
    
    total_successful: int = Field(
        ...,
        ge=0,
        description="Successfully generated images"
    )
    
    total_failed: int = Field(
        ...,
        ge=0,
        description="Failed generations"
    )
    
    success_rate: float = Field(
        ...,
        ge=0,
        le=100,
        description="Success rate percentage"
    )
    
    total_cost_cents: float = Field(
        ...,
        ge=0,
        description="Total cost for all images"
    )
    
    total_time_seconds: float = Field(
        ...,
        ge=0,
        description="Total processing time"
    )
    
    average_time_per_image: float = Field(
        ...,
        ge=0,
        description="Average generation time per image"
    )
    
    provider_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Number of images per provider"
    )
    
    handler_version: str = Field(
        default="1.0.0",
        description="Handler version"
    )
    
    class Config:
        use_enum_values = True


class IllustrationGenerationOutput(BaseModel):
    """
    Output from illustration generation handler.
    
    Specialized for book/document illustration workflows.
    """
    
    status: GenerationStatus = Field(
        ...,
        description="Overall generation status"
    )
    
    book_id: Optional[int] = Field(
        default=None,
        description="Related book ID"
    )
    
    chapter_id: Optional[int] = Field(
        default=None,
        description="Related chapter ID"
    )
    
    illustrations: List[ImageOutput] = Field(
        ...,
        description="Generated illustrations"
    )
    
    total_scenes: int = Field(
        ...,
        ge=1,
        description="Total scenes illustrated"
    )
    
    successful_illustrations: int = Field(
        ...,
        ge=0,
        description="Successfully generated"
    )
    
    failed_illustrations: int = Field(
        ...,
        ge=0,
        description="Failed generations"
    )
    
    illustration_directory: str = Field(
        ...,
        description="Directory containing illustrations"
    )
    
    style_consistency_score: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Style consistency score (if calculated)"
    )
    
    total_cost_cents: float = Field(
        ...,
        ge=0,
        description="Total cost"
    )
    
    total_time_seconds: float = Field(
        ...,
        ge=0,
        description="Total time"
    )
    
    handler_version: str = Field(
        default="1.0.0",
        description="Handler version"
    )
    
    class Config:
        use_enum_values = True


class ProviderHealthOutput(BaseModel):
    """
    Output from provider health check.
    """
    
    provider: str = Field(
        ...,
        description="Provider name"
    )
    
    status: str = Field(
        ...,
        description="Current status"
    )
    
    available: bool = Field(
        ...,
        description="Is provider available"
    )
    
    response_time_ms: Optional[float] = Field(
        default=None,
        description="Health check response time"
    )
    
    last_check: datetime = Field(
        default_factory=datetime.now,
        description="Last health check time"
    )
    
    error: Optional[str] = Field(
        default=None,
        description="Error message if unavailable"
    )


class ProviderMetricsOutput(BaseModel):
    """
    Output for provider metrics and statistics.
    """
    
    provider: str = Field(
        ...,
        description="Provider name"
    )
    
    total_requests: int = Field(
        default=0,
        ge=0,
        description="Total requests made"
    )
    
    successful_requests: int = Field(
        default=0,
        ge=0,
        description="Successful generations"
    )
    
    failed_requests: int = Field(
        default=0,
        ge=0,
        description="Failed generations"
    )
    
    success_rate: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Success rate percentage"
    )
    
    total_cost_cents: float = Field(
        default=0.0,
        ge=0,
        description="Total cost incurred"
    )
    
    average_generation_time: float = Field(
        default=0.0,
        ge=0,
        description="Average generation time"
    )
    
    last_used: Optional[datetime] = Field(
        default=None,
        description="Last time provider was used"
    )


class CostEstimationOutput(BaseModel):
    """
    Output for cost estimation requests.
    """
    
    num_images: int = Field(
        ...,
        ge=1,
        description="Number of images"
    )
    
    estimated_cost_cents: float = Field(
        ...,
        ge=0,
        description="Estimated cost in cents"
    )
    
    estimated_cost_usd: float = Field(
        ...,
        ge=0,
        description="Estimated cost in USD"
    )
    
    provider: str = Field(
        ...,
        description="Provider for estimate"
    )
    
    breakdown: Dict[str, Any] = Field(
        default_factory=dict,
        description="Cost breakdown by parameters"
    )
    
    @property
    def cost_per_image_cents(self) -> float:
        """Calculate cost per image"""
        return self.estimated_cost_cents / self.num_images
    
    @property
    def cost_per_image_usd(self) -> float:
        """Calculate cost per image in USD"""
        return self.estimated_cost_usd / self.num_images


# Example usage
if __name__ == "__main__":
    # Test single image output
    single_output = SingleImageGenerationOutput(
        status=GenerationStatus.SUCCESS,
        image=ImageOutput(
            success=True,
            prompt_used="A cute cat",
            provider="OpenAI",
            generation_time_seconds=15.5,
            cost_cents=4.0,
            url="https://example.com/image.png"
        ),
        total_cost_cents=4.0,
        total_time_seconds=15.5
    )
    print("Single output valid:", single_output.dict())
    
    # Test batch output
    batch_output = BatchImageGenerationOutput(
        status=GenerationStatus.SUCCESS,
        images=[
            ImageOutput(
                success=True,
                prompt_used=f"Image {i}",
                provider="OpenAI",
                generation_time_seconds=10.0,
                cost_cents=4.0
            )
            for i in range(3)
        ],
        total_requested=3,
        total_successful=3,
        total_failed=0,
        success_rate=100.0,
        total_cost_cents=12.0,
        total_time_seconds=30.0,
        average_time_per_image=10.0,
        provider_distribution={"OpenAI": 3}
    )
    print("Batch output valid:", batch_output.dict())
    
    # Test cost estimation
    cost_estimate = CostEstimationOutput(
        num_images=10,
        estimated_cost_cents=40.0,
        estimated_cost_usd=0.40,
        provider="OpenAI"
    )
    print(f"Cost per image: ${cost_estimate.cost_per_image_usd:.3f}")
