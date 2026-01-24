"""
Generic Image Generation Handler
==================================

General-purpose handler for single or batch image generation.
Can be used for any domain, not just books.

Author: BF Agent Team
Version: 1.0.0
"""

from typing import Dict, Any
from pathlib import Path
import time
import structlog

from .base_image_handler import (
    BaseImageHandler,
    ValidationError,
    ProcessingError
)
from ..schemas.input_schemas import (
    SingleImageGenerationInput,
    BatchImageGenerationInput
)
from ..schemas.output_schemas import (
    SingleImageGenerationOutput,
    BatchImageGenerationOutput,
    ImageOutput,
    GenerationStatus
)
from ..providers import ProviderManager

logger = structlog.get_logger(__name__)


class SingleImageHandler(BaseImageHandler):
    """Handler for generating a single image"""
    
    HANDLER_NAME = "SingleImageHandler"
    HANDLER_VERSION = "1.0.0"
    HANDLER_DESCRIPTION = "Generates a single image from a text prompt"
    
    INPUT_SCHEMA = SingleImageGenerationInput
    OUTPUT_SCHEMA = SingleImageGenerationOutput
    
    def __init__(self, provider_manager: ProviderManager, config: Dict[str, Any] = None):
        super().__init__(config)
        self.provider_manager = provider_manager
    
    def _validate_input(self, data: Dict[str, Any]) -> SingleImageGenerationInput:
        """Validate input"""
        return SingleImageGenerationInput(**data)
    
    def _process(
        self,
        validated_input: SingleImageGenerationInput,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate single image"""
        start_time = time.time()
        
        logger.info(
            "Generating single image",
            prompt=validated_input.prompt[:100],
            provider=validated_input.provider
        )
        
        # Generate image
        result = self.provider_manager.generate_image(
            prompt=validated_input.prompt,
            preferred_provider=validated_input.provider if validated_input.provider != "auto" else None,
            size=validated_input.size,
            quality=validated_input.quality,
            style=validated_input.style if validated_input.style else None,
            negative_prompt=validated_input.negative_prompt,
            seed=validated_input.seed
        )
        
        # Save if requested
        if result.success and validated_input.save_to_path:
            save_path = Path(validated_input.save_to_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                self._download_image(result.image_url, save_path)
                result.local_path = save_path
                self._register_resource(save_path)
            except Exception as e:
                logger.error(f"Failed to save image: {e}")
        
        total_time = time.time() - start_time
        
        return {
            'image': result,
            'total_time': total_time
        }
    
    def _format_output(self, processing_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format output"""
        result = processing_result['image']
        
        status = GenerationStatus.SUCCESS if result.success else GenerationStatus.FAILED
        
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
            metadata=result.metadata
        )
        
        return {
            'status': status,
            'image': image_output,
            'total_cost_cents': result.cost_cents,
            'total_time_seconds': processing_result['total_time']
        }
    
    def _download_image(self, url: str, save_path: Path):
        """Download and save image"""
        import requests
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)


class BatchImageHandler(BaseImageHandler):
    """Handler for generating multiple images"""
    
    HANDLER_NAME = "BatchImageHandler"
    HANDLER_VERSION = "1.0.0"
    HANDLER_DESCRIPTION = "Generates multiple images from text prompts"
    
    INPUT_SCHEMA = BatchImageGenerationInput
    OUTPUT_SCHEMA = BatchImageGenerationOutput
    
    def __init__(self, provider_manager: ProviderManager, config: Dict[str, Any] = None):
        super().__init__(config)
        self.provider_manager = provider_manager
    
    def _validate_input(self, data: Dict[str, Any]) -> BatchImageGenerationInput:
        """Validate input"""
        return BatchImageGenerationInput(**data)
    
    def _process(
        self,
        validated_input: BatchImageGenerationInput,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate multiple images"""
        start_time = time.time()
        
        logger.info(
            "Starting batch image generation",
            num_images=len(validated_input.prompts),
            distribute=validated_input.distribute_load
        )
        
        # Generate images
        results = self.provider_manager.batch_generate(
            prompts=validated_input.prompts,
            distribute=validated_input.distribute_load,
            size=validated_input.size,
            quality=validated_input.quality,
            style=validated_input.style if validated_input.style else None
        )
        
        # Save images if directory specified
        if validated_input.save_to_directory:
            save_dir = Path(validated_input.save_to_directory)
            save_dir.mkdir(parents=True, exist_ok=True)
            
            for i, result in enumerate(results):
                if result.success and result.image_url:
                    filename = validated_input.naming_pattern.format(
                        index=i,
                        timestamp=int(time.time())
                    )
                    save_path = save_dir / filename
                    
                    try:
                        self._download_image(result.image_url, save_path)
                        result.local_path = save_path
                        self._register_resource(save_path)
                    except Exception as e:
                        logger.error(f"Failed to save image {i}: {e}")
        
        # Calculate metrics
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_cost = sum(r.cost_cents for r in results if r.success)
        total_time = time.time() - start_time
        avg_time = total_time / len(results) if results else 0
        
        # Provider distribution
        provider_dist = {}
        for r in results:
            if r.success:
                provider_dist[r.provider] = provider_dist.get(r.provider, 0) + 1
        
        return {
            'results': results,
            'total_requested': len(validated_input.prompts),
            'successful': successful,
            'failed': failed,
            'total_cost': total_cost,
            'total_time': total_time,
            'avg_time': avg_time,
            'provider_distribution': provider_dist
        }
    
    def _format_output(self, processing_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format output"""
        successful = processing_result['successful']
        total = processing_result['total_requested']
        
        if successful == total:
            status = GenerationStatus.SUCCESS
        elif successful > 0:
            status = GenerationStatus.PARTIAL_SUCCESS
        else:
            status = GenerationStatus.FAILED
        
        success_rate = (successful / total * 100) if total > 0 else 0
        
        # Convert results to ImageOutput
        images = []
        for result in processing_result['results']:
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
                metadata=result.metadata
            )
            images.append(image_output)
        
        return {
            'status': status,
            'images': images,
            'total_requested': total,
            'total_successful': successful,
            'total_failed': processing_result['failed'],
            'success_rate': success_rate,
            'total_cost_cents': processing_result['total_cost'],
            'total_time_seconds': processing_result['total_time'],
            'average_time_per_image': processing_result['avg_time'],
            'provider_distribution': processing_result['provider_distribution']
        }
    
    def _download_image(self, url: str, save_path: Path):
        """Download and save image"""
        import requests
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)


# Example usage
if __name__ == "__main__":
    from ..providers import OpenAIProvider, ProviderConfig, ProviderManager
    
    # Setup
    config = ProviderConfig(api_key="sk-test", model="dall-e-3")
    provider = OpenAIProvider(config)
    manager = ProviderManager(providers=[provider])
    
    # Single image
    single_handler = SingleImageHandler(provider_manager=manager)
    single_input = {
        'prompt': 'A beautiful sunset over mountains',
        'provider': 'openai',
        'size': '1024x1024'
    }
    # result = single_handler.handle(single_input)
    
    # Batch images
    batch_handler = BatchImageHandler(provider_manager=manager)
    batch_input = {
        'prompts': [
            'A cat',
            'A dog',
            'A bird'
        ],
        'distribute_load': True
    }
    # result = batch_handler.handle(batch_input)
