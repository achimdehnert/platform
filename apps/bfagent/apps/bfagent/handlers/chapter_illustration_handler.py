"""
Auto-Illustration Handler - MVP Version
Automatically illustrates chapters using LLM analysis + Image Generation

Based on Handler Framework v2.0 with Pydantic validation
"""
import structlog
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator
from pathlib import Path

from .illustration_handler import ImageGenerationHandler, PromptEnhancer

logger = structlog.get_logger(__name__)


class IllustrationPosition(BaseModel):
    """Position where an illustration should be placed"""
    paragraph_index: int = Field(..., ge=0, description="0-based paragraph index")
    scene_description: str = Field(..., min_length=10, max_length=500)
    illustration_type: str = Field(default="scene_illustration")
    priority: int = Field(default=5, ge=1, le=10, description="1=low, 10=high")
    
    @validator('illustration_type')
    def validate_illustration_type(cls, v):
        allowed_types = ['scene_illustration', 'character_portrait', 'location', 'action_scene']
        if v not in allowed_types:
            raise ValueError(f"illustration_type must be one of {allowed_types}")
        return v


class AutoIllustrationResult(BaseModel):
    """Result of auto-illustration process"""
    chapter_id: int
    total_positions_found: int = 0
    images_generated: int = 0
    total_cost_usd: float = 0.0
    duration_seconds: float = 0.0
    positions: List[IllustrationPosition] = Field(default_factory=list)
    generated_images: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class ChapterIllustrationHandler:
    """
    MVP Auto-Illustration Handler
    
    Phase 1: Analyze chapter → find illustration positions
    Phase 2: Generate prompts for each position
    Phase 3: Generate images (parallel in future)
    """
    
    def __init__(self, mock_mode: bool = False):
        """
        Initialize handler
        
        Args:
            mock_mode: If True, use mock images (no API calls, no cost)
        """
        self.mock_mode = mock_mode
        self.image_handler = ImageGenerationHandler(mock_mode=mock_mode)
        self.prompt_enhancer = PromptEnhancer()
        self.log = logger.bind(handler="ChapterIllustrationHandler", mock_mode=mock_mode)
    
    def analyze_chapter(
        self,
        chapter_text: str,
        max_illustrations: int = 3
    ) -> List[IllustrationPosition]:
        """
        Phase 1: Analyze chapter to find illustration positions
        
        In MVP: Simple heuristic-based approach
        In Production: Use LLM (GPT-4o-mini or Claude Haiku)
        
        Args:
            chapter_text: Full chapter text
            max_illustrations: Maximum number of illustrations to suggest
            
        Returns:
            List of illustration positions
        """
        self.log.info("chapter_analysis_start", text_length=len(chapter_text), max_illustrations=max_illustrations)
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in chapter_text.split('\n\n') if p.strip()]
        
        if len(paragraphs) == 0:
            self.log.warning("no_paragraphs_found")
            # In mock mode, generate test positions even without text
            if self.mock_mode:
                self.log.info("mock_mode_generating_test_positions", count=max_illustrations)
                return [
                    IllustrationPosition(
                        paragraph_index=i,
                        scene_description=f"test, highly detailed, professional illustration",
                        illustration_type="scene_illustration",
                        priority=10 - i
                    )
                    for i in range(min(max_illustrations, 3))
                ]
            return []
        
        # MVP: Simple heuristic - place illustrations at key positions
        positions = []
        
        # Opening scene (first paragraph)
        if len(paragraphs) >= 1:
            positions.append(IllustrationPosition(
                paragraph_index=0,
                scene_description=self._extract_scene_description(paragraphs[0]),
                illustration_type="scene_illustration",
                priority=10
            ))
        
        # Middle scene (if chapter is long enough)
        if len(paragraphs) >= 5:
            mid_index = len(paragraphs) // 2
            positions.append(IllustrationPosition(
                paragraph_index=mid_index,
                scene_description=self._extract_scene_description(paragraphs[mid_index]),
                illustration_type="scene_illustration",
                priority=7
            ))
        
        # Climax scene (near end, if enough paragraphs)
        if len(paragraphs) >= 8:
            climax_index = int(len(paragraphs) * 0.75)
            positions.append(IllustrationPosition(
                paragraph_index=climax_index,
                scene_description=self._extract_scene_description(paragraphs[climax_index]),
                illustration_type="action_scene",
                priority=9
            ))
        
        # Limit to max_illustrations
        positions = sorted(positions, key=lambda x: x.priority, reverse=True)[:max_illustrations]
        
        self.log.info("chapter_analysis_complete", positions_found=len(positions))
        return positions
    
    def _extract_scene_description(self, paragraph: str, max_length: int = 200) -> str:
        """Extract scene description from paragraph"""
        # MVP: Just use first sentence or truncate
        sentences = paragraph.split('.')
        description = sentences[0] if sentences else paragraph
        
        if len(description) > max_length:
            description = description[:max_length] + "..."
        
        return description.strip()
    
    async def generate_prompts(
        self,
        positions: List[IllustrationPosition],
        style_profile: Optional[str] = None,
        book_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """
        Phase 2: Generate image prompts for each position
        
        Args:
            positions: List of illustration positions
            style_profile: Optional style guide (e.g., "watercolor, fantasy style")
            book_context: Optional book metadata (genre, setting, characters)
            
        Returns:
            List of dicts with 'prompt' and 'negative_prompt'
        """
        self.log.info("prompt_generation_start", positions_count=len(positions))
        
        prompts = []
        
        for position in positions:
            # Build base prompt from scene description
            base_prompt = position.scene_description
            
            # Enhance with style profile
            enhanced_prompt = self.prompt_enhancer.enhance_prompt(
                base_prompt=base_prompt,
                style_profile_prompt=style_profile,
                image_type=position.illustration_type,
                enhance=True
            )
            
            # Build negative prompt
            negative_prompt = self.prompt_enhancer.build_negative_prompt(
                image_type=position.illustration_type
            )
            
            prompts.append({
                'prompt': enhanced_prompt,
                'negative_prompt': negative_prompt,
                'position': position.dict()
            })
        
        self.log.info("prompt_generation_complete", prompts_count=len(prompts))
        return prompts
    
    async def generate_images(
        self,
        prompts: List[Dict[str, str]],
        provider: str = 'dalle3',
        quality: str = 'standard',
        size: str = '1024x1024'
    ) -> List[Dict[str, Any]]:
        """
        Phase 3: Generate images for all prompts
        
        Args:
            prompts: List of prompt dicts from generate_prompts()
            provider: Image provider ('dalle3' or 'stable_diffusion')
            quality: Image quality ('standard' or 'hd')
            size: Image size (e.g., '1024x1024')
            
        Returns:
            List of generated image results
        """
        self.log.info("image_generation_start", prompts_count=len(prompts), provider=provider)
        
        results = []
        
        # MVP: Sequential generation
        # TODO: Make parallel in production (Celery tasks)
        for prompt_data in prompts:
            try:
                images = await self.image_handler.generate_image(
                    prompt=prompt_data['prompt'],
                    provider=provider,
                    quality=quality,
                    size=size,
                    negative_prompt=prompt_data.get('negative_prompt'),
                    num_images=1
                )
                
                # Add position info to result
                for img in images:
                    img['position'] = prompt_data['position']
                    results.extend([img])
                
            except Exception as e:
                self.log.error("image_generation_failed_for_prompt", 
                              prompt=prompt_data['prompt'][:100], 
                              error=str(e))
                # Continue with other images
                continue
        
        self.log.info("image_generation_complete", images_generated=len(results))
        return results
    
    async def auto_illustrate_chapter(
        self,
        chapter_id: int,
        chapter_text: str,
        max_illustrations: int = 3,
        style_profile: Optional[str] = None,
        provider: str = 'dalle3',
        quality: str = 'standard'
    ) -> AutoIllustrationResult:
        """
        Complete auto-illustration workflow
        
        Args:
            chapter_id: Chapter ID
            chapter_text: Full chapter text
            max_illustrations: Maximum number of illustrations
            style_profile: Optional style guide
            provider: Image provider
            quality: Image quality
            
        Returns:
            AutoIllustrationResult with all generated images
        """
        import time
        start_time = time.time()
        
        result = AutoIllustrationResult(chapter_id=chapter_id)
        
        try:
            # Phase 1: Analyze
            self.log.info("auto_illustrate_start", chapter_id=chapter_id, max_illustrations=max_illustrations)
            positions = self.analyze_chapter(chapter_text, max_illustrations)
            result.positions = positions
            result.total_positions_found = len(positions)
            
            if not positions:
                self.log.warning("no_positions_found", chapter_id=chapter_id)
                return result
            
            # Phase 2: Generate Prompts
            prompts = await self.generate_prompts(
                positions=positions,
                style_profile=style_profile
            )
            
            # Phase 3: Generate Images
            images = await self.generate_images(
                prompts=prompts,
                provider=provider,
                quality=quality
            )
            
            result.generated_images = images
            result.images_generated = len(images)
            result.total_cost_usd = sum(img.get('cost_usd', 0.0) for img in images)
            
        except Exception as e:
            self.log.error("auto_illustrate_failed", chapter_id=chapter_id, error=str(e))
            result.errors.append(str(e))
        
        finally:
            result.duration_seconds = time.time() - start_time
            self.log.info("auto_illustrate_complete", 
                         chapter_id=chapter_id,
                         images_generated=result.images_generated,
                         cost_usd=result.total_cost_usd,
                         duration=result.duration_seconds)
        
        return result
