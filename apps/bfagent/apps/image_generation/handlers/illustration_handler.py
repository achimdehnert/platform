"""
Illustration Generation Handler
================================

Specialized handler for generating book illustrations in BF Agent Educational System.

Features:
- Batch generation of illustrations
- Style consistency across images
- Character consistency
- Integration with Book/Chapter models
- Automatic file organization
- Cost tracking

Author: BF Agent Team
Version: 1.0.0
"""

from typing import Dict, Any, List
from pathlib import Path
import time
from datetime import datetime
import structlog

from .base_image_handler import (
    BaseImageHandler,
    ValidationError,
    ProcessingError,
    OutputError
)
from ..schemas.input_schemas import IllustrationGenerationInput
from ..schemas.output_schemas import (
    IllustrationGenerationOutput,
    ImageOutput,
    GenerationStatus
)
from ..providers import ProviderManager, SelectionStrategy

logger = structlog.get_logger(__name__)


class IllustrationGenerationHandler(BaseImageHandler):
    """
    Handler for generating book/document illustrations.
    
    Integrates with BF Agent Educational Book System to generate
    consistent, high-quality illustrations for chapters.
    """
    
    HANDLER_NAME = "IllustrationGenerationHandler"
    HANDLER_VERSION = "1.0.0"
    HANDLER_DESCRIPTION = "Generates illustrations for educational books with style consistency"
    
    INPUT_SCHEMA = IllustrationGenerationInput
    OUTPUT_SCHEMA = IllustrationGenerationOutput
    
    def __init__(self, provider_manager: ProviderManager, config: Dict[str, Any] = None):
        """
        Initialize illustration handler.
        
        Args:
            provider_manager: Configured ProviderManager instance
            config: Handler configuration
        """
        super().__init__(config)
        self.provider_manager = provider_manager
        
        # Default config
        self.config.setdefault('max_parallel', 3)
        self.config.setdefault('save_images', True)
        self.config.setdefault('add_metadata', True)
        self.config.setdefault('quality', 'standard')
        
        logger.info(
            "IllustrationGenerationHandler initialized",
            config=self.config
        )
    
    def _validate_input(self, data: Dict[str, Any]) -> IllustrationGenerationInput:
        """
        Validate input using Pydantic schema.
        
        Ensures all required fields are present and valid.
        """
        try:
            validated = IllustrationGenerationInput(**data)
            
            # Additional business logic validation
            if validated.book_id and validated.book_id <= 0:
                raise ValueError("book_id must be positive")
            
            if validated.chapter_id and validated.chapter_id <= 0:
                raise ValueError("chapter_id must be positive")
            
            # Ensure output directory is valid
            output_dir = Path(validated.save_to_directory)
            if not output_dir.parent.exists():
                raise ValueError(f"Parent directory does not exist: {output_dir.parent}")
            
            logger.info(
                "Input validated successfully",
                num_scenes=len(validated.scene_descriptions),
                book_id=validated.book_id,
                chapter_id=validated.chapter_id
            )
            
            return validated
            
        except Exception as e:
            raise ValidationError(f"Input validation failed: {str(e)}") from e
    
    def _process(
        self,
        validated_input: IllustrationGenerationInput,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Core processing: Generate all illustrations.
        
        Steps:
        1. Prepare prompts with style consistency
        2. Generate images (batch or sequential)
        3. Save images to disk
        4. Track metrics
        """
        start_time = time.time()
        
        # Create output directory
        output_dir = Path(validated_input.save_to_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        self._register_resource(output_dir)  # For rollback
        
        logger.info(
            "Starting illustration generation",
            num_scenes=len(validated_input.scene_descriptions),
            output_dir=str(output_dir),
            style=validated_input.illustration_style
        )
        
        # Prepare prompts
        prompts = self._prepare_prompts(validated_input)
        
        # Generate illustrations
        illustrations = []
        successful = 0
        failed = 0
        total_cost = 0.0
        
        for i, (scene_desc, prompt) in enumerate(zip(validated_input.scene_descriptions, prompts)):
            logger.info(f"Generating illustration {i+1}/{len(prompts)}", scene=scene_desc[:50])
            
            # Generate image
            result = self.provider_manager.generate_image(
                prompt=prompt,
                preferred_provider=validated_input.provider,
                size=validated_input.aspect_ratio,
                quality=validated_input.quality
            )
            
            # Save image if successful
            if result.success and config.get('save_images', True):
                # Determine filename
                filename = self._get_filename(
                    pattern=validated_input.naming_pattern,
                    index=i,
                    chapter=validated_input.chapter_id,
                    scene=i
                )
                
                local_path = output_dir / filename
                
                # Download and save image
                if result.image_url:
                    try:
                        self._download_image(result.image_url, local_path)
                        result.local_path = local_path
                        self._register_resource(local_path)  # For rollback
                        logger.info(f"Saved illustration to {local_path}")
                    except Exception as e:
                        logger.error(f"Failed to save image: {e}")
                        result.success = False
                        result.error_message = f"Failed to save: {str(e)}"
            
            # Convert to ImageOutput
            image_output = ImageOutput(
                success=result.success,
                url=result.image_url,
                local_path=str(result.local_path) if result.local_path else None,
                prompt_used=result.prompt_used,
                revised_prompt=result.revised_prompt,
                provider=result.provider,
                generation_time_seconds=result.generation_time_seconds,
                cost_cents=result.cost_cents,
                error_message=result.error_message,
                metadata={
                    **result.metadata,
                    'scene_index': i,
                    'scene_description': scene_desc
                }
            )
            
            illustrations.append(image_output)
            
            if result.success:
                successful += 1
                total_cost += result.cost_cents
            else:
                failed += 1
        
        total_time = time.time() - start_time
        
        logger.info(
            "Illustration generation completed",
            total=len(illustrations),
            successful=successful,
            failed=failed,
            total_cost_cents=total_cost,
            total_time_seconds=total_time
        )
        
        return {
            'illustrations': illustrations,
            'total_scenes': len(validated_input.scene_descriptions),
            'successful': successful,
            'failed': failed,
            'total_cost_cents': total_cost,
            'total_time_seconds': total_time,
            'output_directory': str(output_dir),
            'book_id': validated_input.book_id,
            'chapter_id': validated_input.chapter_id
        }
    
    def _format_output(self, processing_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format output to match IllustrationGenerationOutput schema.
        """
        successful = processing_result['successful']
        total = processing_result['total_scenes']
        
        # Determine status
        if successful == total:
            status = GenerationStatus.SUCCESS
        elif successful > 0:
            status = GenerationStatus.PARTIAL_SUCCESS
        else:
            status = GenerationStatus.FAILED
        
        output = {
            'status': status,
            'book_id': processing_result['book_id'],
            'chapter_id': processing_result['chapter_id'],
            'illustrations': processing_result['illustrations'],
            'total_scenes': total,
            'successful_illustrations': successful,
            'failed_illustrations': processing_result['failed'],
            'illustration_directory': processing_result['output_directory'],
            'total_cost_cents': processing_result['total_cost_cents'],
            'total_time_seconds': processing_result['total_time_seconds'],
            'handler_version': self.HANDLER_VERSION
        }
        
        return output
    
    # ==================== HELPER METHODS ====================
    
    def _prepare_prompts(self, input_data: IllustrationGenerationInput) -> List[str]:
        """
        Prepare enhanced prompts with style consistency.
        
        Adds:
        - Illustration style prefix
        - Character descriptions (if provided)
        - Consistency keywords
        """
        prompts = []
        
        # Build style prefix
        style_prefix = f"{input_data.illustration_style} style, "
        
        if input_data.ensure_consistency:
            style_prefix += "consistent art style, same visual aesthetic, "
        
        # Build character context if provided
        character_context = ""
        if input_data.character_descriptions:
            char_desc_parts = [
                f"{name} is {desc}"
                for name, desc in input_data.character_descriptions.items()
            ]
            character_context = "Characters: " + ", ".join(char_desc_parts) + ". "
        
        # Generate prompts
        for scene_desc in input_data.scene_descriptions:
            prompt = style_prefix + character_context + scene_desc
            prompts.append(prompt)
        
        logger.debug(f"Prepared {len(prompts)} prompts with style consistency")
        
        return prompts
    
    def _get_filename(
        self,
        pattern: str,
        index: int,
        chapter: int = None,
        scene: int = None
    ) -> str:
        """
        Generate filename from pattern.
        
        Supports:
        - {index}: Scene index (0-based)
        - {chapter}: Chapter ID
        - {scene}: Scene number
        - {timestamp}: Current timestamp
        """
        filename = pattern
        
        replacements = {
            '{index}': f"{index:03d}",
            '{chapter}': str(chapter) if chapter else "00",
            '{scene}': f"{scene:02d}" if scene is not None else "00",
            '{timestamp}': datetime.now().strftime('%Y%m%d_%H%M%S')
        }
        
        for placeholder, value in replacements.items():
            filename = filename.replace(placeholder, value)
        
        # Ensure .png extension
        if not filename.endswith('.png'):
            filename += '.png'
        
        return filename
    
    def _download_image(self, url: str, save_path: Path):
        """
        Download image from URL and save to disk.
        
        Args:
            url: Image URL
            save_path: Path to save image
            
        Raises:
            Exception: If download fails
        """
        import requests
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            logger.debug(f"Downloaded image: {save_path}")
            
        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            raise
    
    def estimate_cost(self, num_illustrations: int) -> float:
        """
        Estimate cost for generating illustrations.
        
        Args:
            num_illustrations: Number of illustrations
            
        Returns:
            Estimated cost in cents
        """
        # Note: Don't pass size/quality kwargs as not all providers support them in estimate_cost
        return self.provider_manager.estimate_cost(
            num_images=num_illustrations
        )


# Example usage
if __name__ == "__main__":
    from ..providers import OpenAIProvider, ProviderConfig, ProviderManager
    
    # Setup provider
    openai_config = ProviderConfig(
        api_key="sk-test-key",
        model="dall-e-3"
    )
    provider = OpenAIProvider(openai_config)
    manager = ProviderManager(providers=[provider])
    
    # Create handler
    handler = IllustrationGenerationHandler(
        provider_manager=manager,
        config={'save_images': True}
    )
    
    # Example input
    input_data = {
        'book_id': 1,
        'chapter_id': 1,
        'scene_descriptions': [
            "Max and Mia arriving at the mysterious Brain Island",
            "The children solving a colorful puzzle together"
        ],
        'illustration_style': "watercolor children's book",
        'save_to_directory': '/tmp/test_illustrations',
        'provider': 'openai'
    }
    
    # Estimate cost
    cost = handler.estimate_cost(num_illustrations=2)
    print(f"Estimated cost: ${cost/100:.2f}")
    
    # Execute (would need valid API key)
    # result = handler.handle(input_data)
    # print(result)
