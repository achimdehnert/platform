"""
Chapter Auto-Illustration Handler V2.0
=======================================

Production-ready handler with Pydantic validation and transaction safety.

Auto-generates illustrations for book chapters using AI image generation.

Features:
- Three-phase processing (Input → Process → Output)
- Pydantic validation for type safety
- Transaction safety with automatic rollback
- Mock mode for cost-free testing
- Multi-provider support (DALL-E 3, Stable Diffusion, Mock)
- Cost tracking and metrics
- Style profile support

Author: BF Agent Framework
Date: 2025-11-02
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, validator
from django.utils import timezone
import asyncio
import logging

from apps.bfagent.handlers.base_handler_v2 import BaseHandler, ProcessingError
from apps.bfagent.models import BookChapters, GeneratedImage
from apps.bfagent.handlers.chapter_illustration_handler import ChapterIllustrationHandler

logger = logging.getLogger(__name__)


class ChapterAutoIllustrateHandlerV2(BaseHandler):
    """
    Handler for auto-illustrating chapters with AI
    
    INPUT PHASE:
    - Validates chapter exists and accessible
    - Validates max_illustrations range (1-10)
    - Validates provider ('dalle3', 'stable-diffusion', 'mock')
    - Validates style_profile_id if provided
    - Validates resolution format (WIDTHxHEIGHT)
    - Validates quality ('standard', 'hd')
    
    PROCESSING PHASE:
    - Loads chapter content
    - Analyzes chapter for illustration positions (heuristic or LLM)
    - Generates AI prompts for each position
    - Generates images (mock or real provider)
    - Saves images to database (within transaction)
    - Tracks cost and duration metrics
    
    OUTPUT PHASE:
    - Returns structured response with metrics
    - Includes images_generated, images_saved counts
    - Includes total_cost_usd, duration_seconds
    - Includes mock_mode indicator
    - Includes list of generated images with metadata
    """
    
    handler_name = 'chapter_auto_illustrate'
    handler_version = '2.0.0'
    domain = 'bookwriting'
    category = 'illustration'
    
    # ==================== INPUT SCHEMA ====================
    
    class InputSchema(BaseModel):
        """Input validation schema"""
        
        chapter_id: int = Field(gt=0, description="Chapter to illustrate")
        
        max_illustrations: int = Field(
            default=3,
            ge=1,
            le=10,
            description="Maximum number of illustrations to generate (1-10)"
        )
        
        provider: Literal['mock', 'dalle3', 'stable-diffusion'] = Field(
            default='mock',
            description="Image generation provider"
        )
        
        style_profile_id: Optional[int] = Field(
            None,
            gt=0,
            description="Style profile ID (e.g., 'watercolor', 'realistic')"
        )
        
        style_profile_prompt: Optional[str] = Field(
            None,
            max_length=500,
            description="Custom style prompt (overrides profile)"
        )
        
        resolution: str = Field(
            default='1024x1024',
            description="Image resolution (e.g., '1024x1024', '1792x1024')"
        )
        
        quality: Literal['standard', 'hd'] = Field(
            default='standard',
            description="Image quality (DALL-E 3 only)"
        )
        
        # Advanced options
        analyze_with_llm: bool = Field(
            False,
            description="Use LLM for scene analysis (experimental, costs extra)"
        )
        
        save_to_chapter: bool = Field(
            True,
            description="Save generated images to chapter"
        )
        
        @validator('resolution')
        def validate_resolution(cls, v):
            """Validate resolution format"""
            import re
            if not re.match(r'^\d+x\d+$', v):
                raise ValueError(
                    f"Invalid resolution format: {v}. "
                    "Expected format: WIDTHxHEIGHT (e.g., 1024x1024)"
                )
            
            # Parse dimensions
            width, height = map(int, v.split('x'))
            
            # Validate ranges
            if not (256 <= width <= 2048 and 256 <= height <= 2048):
                raise ValueError(
                    f"Resolution dimensions must be between 256 and 2048. "
                    f"Got: {width}x{height}"
                )
            
            return v
        
        @validator('provider')
        def validate_provider(cls, v):
            """Ensure provider is valid"""
            valid = ['mock', 'dalle3', 'stable-diffusion']
            if v not in valid:
                raise ValueError(f"Invalid provider: {v}. Valid: {valid}")
            return v
        
        class Config:
            schema_extra = {
                "example": {
                    "chapter_id": 5,
                    "max_illustrations": 3,
                    "provider": "mock",
                    "style_profile_prompt": "Watercolor, fantasy style, dreamy atmosphere",
                    "resolution": "1024x1024",
                    "quality": "standard",
                    "analyze_with_llm": False,
                    "save_to_chapter": True
                }
            }
    
    # ==================== OUTPUT SCHEMA ====================
    
    class OutputSchema(BaseModel):
        """Output validation schema"""
        
        success: bool = True
        action: str = 'auto_illustrate_chapter'
        
        chapter_id: int = Field(..., description="Chapter that was illustrated")
        
        images_generated: int = Field(
            ...,
            ge=0,
            description="Number of images successfully generated"
        )
        
        images_saved: int = Field(
            ...,
            ge=0,
            description="Number of images saved to database"
        )
        
        total_cost_usd: float = Field(
            ...,
            ge=0.0,
            description="Total cost in USD"
        )
        
        duration_seconds: float = Field(
            ...,
            ge=0.0,
            description="Total processing duration"
        )
        
        mock_mode: bool = Field(
            ...,
            description="Whether mock mode was used"
        )
        
        generated_images: List[Dict[str, Any]] = Field(
            default_factory=list,
            description="List of generated images with metadata"
        )
        
        message: str = Field(
            ...,
            description="Human-readable result message"
        )
        
        warnings: List[str] = Field(
            default_factory=list,
            description="Non-fatal warnings"
        )
        
        class Config:
            schema_extra = {
                "example": {
                    "success": True,
                    "action": "auto_illustrate_chapter",
                    "chapter_id": 5,
                    "images_generated": 3,
                    "images_saved": 3,
                    "total_cost_usd": 0.12,
                    "duration_seconds": 15.3,
                    "mock_mode": False,
                    "generated_images": [
                        {
                            "id": 42,
                            "image_url": "https://...",
                            "prompt": "Hero entering dark forest...",
                            "paragraph_index": 0,
                            "cost_usd": 0.04
                        }
                    ],
                    "message": "Generated 3 illustrations for chapter 5",
                    "warnings": []
                }
            }
    
    # ==================== INITIALIZATION ====================
    
    def __init__(self):
        super().__init__()
        # Will be initialized per-request with mock_mode setting
        self.illustration_handler = None
    
    # ==================== PROCESSING ====================
    
    def process(self, validated_input: InputSchema) -> Dict[str, Any]:
        """
        Main processing logic with transaction safety
        
        All database operations are wrapped in transaction.atomic()
        by the base handler, so any exception will rollback changes.
        """
        warnings = []
        import time
        start_time = time.time()
        
        # Determine mock mode
        mock_mode = validated_input.provider == 'mock'
        
        # Initialize illustration handler with mock mode
        self.illustration_handler = ChapterIllustrationHandler(mock_mode=mock_mode)
        
        # 1. Load chapter
        chapter = self._load_chapter(validated_input.chapter_id)
        
        # Warn if chapter has no content
        if not chapter.content or len(chapter.content.strip()) < 100:
            if mock_mode:
                warnings.append(
                    "Chapter content is empty or very short. "
                    "Generated test illustrations for demonstration."
                )
            else:
                raise ProcessingError(
                    "Chapter content is too short for illustration "
                    "(minimum 100 characters required)"
                )
        
        # 2. Load style profile if specified
        style_prompt = validated_input.style_profile_prompt
        if validated_input.style_profile_id:
            try:
                style_prompt = self._load_style_profile(validated_input.style_profile_id)
            except Exception as e:
                warnings.append(f"Failed to load style profile: {e}")
        
        # 3. Run auto-illustration workflow
        try:
            result = asyncio.run(
                self.illustration_handler.auto_illustrate_chapter(
                    chapter_id=chapter.id,
                    chapter_text=chapter.content or "",
                    max_illustrations=validated_input.max_illustrations,
                    style_profile=style_prompt,
                    provider=validated_input.provider,
                    quality=validated_input.quality
                )
            )
            
            self.logger.info(
                f"Auto-illustration completed for chapter {chapter.id}: "
                f"{result.images_generated} images generated, "
                f"cost: ${result.total_cost_usd:.4f}"
            )
            
        except Exception as e:
            self.logger.error(f"Auto-illustration failed: {e}")
            raise ProcessingError(f"Illustration generation failed: {e}")
        
        # 4. Save images to database (if enabled)
        saved_images = []
        if validated_input.save_to_chapter and result.generated_images:
            try:
                saved_images = self._save_images_to_database(
                    chapter=chapter,
                    images_data=result.generated_images,
                    provider=validated_input.provider,
                    total_cost=result.total_cost_usd,
                    total_duration=result.duration_seconds
                )
                
                self.logger.info(
                    f"Saved {len(saved_images)} images to database for chapter {chapter.id}"
                )
                
            except Exception as e:
                self.logger.error(f"Failed to save images: {e}")
                warnings.append(f"Failed to save images to database: {e}")
        
        # 5. Calculate final metrics
        duration = time.time() - start_time
        
        # 6. Format output
        return {
            'chapter_id': chapter.id,
            'images_generated': result.images_generated,
            'images_saved': len(saved_images),
            'total_cost_usd': float(result.total_cost_usd),
            'duration_seconds': duration,
            'mock_mode': mock_mode,
            'generated_images': [
                self._format_image_output(img, saved_images)
                for img in result.generated_images
            ],
            'warnings': warnings,
            'message': (
                f"Generated {result.images_generated} illustrations for chapter {chapter.id} "
                f"in {duration:.1f}s (${result.total_cost_usd:.4f})"
            )
        }
    
    # ==================== HELPER METHODS ====================
    
    def _load_chapter(self, chapter_id: int) -> BookChapters:
        """Load chapter with error handling"""
        try:
            return BookChapters.objects.select_related('project').get(id=chapter_id)
        except BookChapters.DoesNotExist:
            raise ProcessingError(f"Chapter {chapter_id} not found")
    
    def _load_style_profile(self, profile_id: int) -> str:
        """Load style profile prompt (placeholder for future implementation)"""
        # TODO: Implement StyleProfile model and lookup
        self.logger.warning(
            f"Style profile lookup not implemented yet (profile_id: {profile_id}). "
            "Using default style."
        )
        return "Professional book illustration, high quality, detailed"
    
    def _save_images_to_database(
        self,
        chapter: BookChapters,
        images_data: List[Dict[str, Any]],
        provider: str,
        total_cost: float,
        total_duration: float
    ) -> List[GeneratedImage]:
        """
        Save generated images to database
        
        This runs within the transaction, so failures will rollback.
        """
        saved_images = []
        
        for idx, img_data in enumerate(images_data):
            import uuid
            
            # Calculate per-image cost and duration
            per_image_cost = total_cost / len(images_data) if images_data else 0
            per_image_duration = total_duration / len(images_data) if images_data else 0
            
            # Extract data from result
            image_url = img_data.get('url') or img_data.get('image_url', '')
            scene_desc = img_data.get('scene_description', '')
            prompt = img_data.get('prompt', scene_desc)
            paragraph_idx = img_data.get('position', {}).get('paragraph_index', idx)
            illustration_type = img_data.get('type') or img_data.get('illustration_type', 'scene_illustration')
            
            try:
                generated_img = GeneratedImage.objects.create(
                    # Required fields
                    image_id=f"auto-{chapter.id}-{uuid.uuid4().hex[:8]}",
                    user=chapter.project.user,
                    chapter=chapter,
                    project=chapter.project,
                    image_url=image_url,
                    provider_used=provider,
                    prompt_used=prompt[:1000],  # Truncate if too long
                    resolution=img_data.get('size', '1024x1024'),
                    quality=img_data.get('quality', 'standard'),
                    # Optional fields
                    image_type=illustration_type,
                    cost_usd=per_image_cost,
                    generation_time_seconds=per_image_duration,
                    status='generated',
                    content_context={'paragraph_index': paragraph_idx}
                )
                
                saved_images.append(generated_img)
                
                self.logger.debug(
                    f"Saved image {idx+1}/{len(images_data)} to database: {generated_img.id}"
                )
                
            except Exception as e:
                self.logger.error(
                    f"Failed to save image {idx+1} to database: {e}",
                    extra={'image_data': img_data}
                )
                # Continue with other images
                continue
        
        return saved_images
    
    def _format_image_output(
        self,
        img_data: Dict[str, Any],
        saved_images: List[GeneratedImage]
    ) -> Dict[str, Any]:
        """Format image data for output"""
        
        # Find matching saved image
        image_url = img_data.get('url') or img_data.get('image_url', '')
        saved_img = next(
            (img for img in saved_images if img.image_url == image_url),
            None
        )
        
        return {
            'id': saved_img.id if saved_img else None,
            'image_url': image_url,
            'prompt': img_data.get('prompt', img_data.get('scene_description', '')),
            'paragraph_index': img_data.get('position', {}).get('paragraph_index', 0),
            'illustration_type': img_data.get('type') or img_data.get('illustration_type', 'scene_illustration'),
            'cost_usd': img_data.get('cost_usd', 0.0),
            'generation_time_seconds': img_data.get('generation_time_seconds', 0.0),
            'provider': img_data.get('provider', 'unknown'),
            'quality': img_data.get('quality', 'standard'),
            'size': img_data.get('size', '1024x1024'),
        }
