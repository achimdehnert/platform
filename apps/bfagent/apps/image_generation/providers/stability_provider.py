"""
Stability AI Provider
=====================

Implementation of BaseImageProvider for Stability AI's Stable Diffusion 3.

Features:
- Cost-effective image generation
- Multiple aspect ratios
- Style presets
- Negative prompts
- Seed control for reproducibility

Author: BF Agent Team
Version: 1.0.0
"""

import requests
import time
from typing import Optional, Dict, Any
from pathlib import Path
import structlog

from .base_provider import (
    BaseImageProvider,
    ProviderConfig,
    ImageGenerationResult,
    ProviderStatus,
    ProviderError,
    AuthenticationError,
    InvalidParameterError,
    RateLimitError
)

logger = structlog.get_logger(__name__)


class StabilityAIProvider(BaseImageProvider):
    """
    Stability AI Stable Diffusion 3 provider.
    
    Supported aspect ratios: 16:9, 1:1, 21:9, 2:3, 3:2, 4:5, 5:4, 9:16, 9:21
    Supports negative prompts for better control
    """
    
    API_URL = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
    
    SUPPORTED_ASPECT_RATIOS = [
        "16:9", "1:1", "21:9", "2:3", "3:2", 
        "4:5", "5:4", "9:16", "9:21"
    ]
    
    SUPPORTED_MODELS = [
        "sd3",
        "sd3-turbo"
    ]
    
    STYLE_PRESETS = [
        "3d-model", "analog-film", "anime", "cinematic", "comic-book",
        "digital-art", "enhance", "fantasy-art", "isometric", "line-art",
        "low-poly", "modeling-compound", "neon-punk", "origami", "photographic",
        "pixel-art", "tile-texture"
    ]
    
    # Pricing (in cents) - Stability AI is generally cheaper than DALL-E
    PRICING = {
        "sd3": 3.5,  # per image
        "sd3-turbo": 2.0  # faster, cheaper
    }
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        # Set default model
        if not config.model:
            config.model = "sd3"
        
        # Validate API key format
        if not config.api_key or not config.api_key.startswith("sk-"):
            raise AuthenticationError("Invalid Stability AI API key format")
    
    def generate_image(
        self,
        prompt: str,
        aspect_ratio: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        style_preset: Optional[str] = None,
        seed: Optional[int] = None,
        output_format: str = "png",
        **kwargs
    ) -> ImageGenerationResult:
        """
        Generate image using Stable Diffusion 3.
        
        Args:
            prompt: Text description of desired image
            aspect_ratio: Image aspect ratio (e.g., "16:9", "1:1")
            negative_prompt: What to avoid in the image
            style_preset: Art style preset
            seed: Random seed for reproducibility
            output_format: "png" or "webp"
            
        Returns:
            ImageGenerationResult
        """
        start_time = time.time()
        
        # Apply rate limiting
        self._apply_rate_limit()
        
        # Set defaults
        aspect_ratio = aspect_ratio or "1:1"
        
        # Validate parameters
        if aspect_ratio not in self.SUPPORTED_ASPECT_RATIOS:
            return ImageGenerationResult(
                success=False,
                provider=self.provider_name,
                error_message=f"Invalid aspect ratio {aspect_ratio}. Supported: {self.SUPPORTED_ASPECT_RATIOS}"
            )
        
        if style_preset and style_preset not in self.STYLE_PRESETS:
            logger.warning(f"Invalid style preset {style_preset}, ignoring")
            style_preset = None
        
        # Prepare request headers
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Accept": "image/*"  # or application/json
        }
        
        # Prepare form data
        data = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "model": self.config.model,
            "output_format": output_format
        }
        
        if negative_prompt:
            data["negative_prompt"] = negative_prompt
        
        if style_preset:
            data["style_preset"] = style_preset
        
        if seed is not None:
            data["seed"] = seed
        
        # Add extra parameters from config
        data.update(self.config.extra_params)
        
        logger.info(
            "Generating image with Stable Diffusion 3",
            prompt=prompt[:100],
            aspect_ratio=aspect_ratio,
            model=self.config.model,
            style_preset=style_preset
        )
        
        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                files={"none": ''},  # multipart/form-data
                data=data,
                timeout=self.config.timeout_seconds
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                self.set_status(ProviderStatus.RATE_LIMITED)
                raise RateLimitError("Stability AI rate limit exceeded")
            
            # Handle authentication errors
            if response.status_code == 401 or response.status_code == 403:
                self.set_status(ProviderStatus.ERROR)
                raise AuthenticationError("Invalid Stability AI API key")
            
            # Handle other errors
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", "Unknown error")
                except:
                    error_msg = f"HTTP {response.status_code}"
                raise ProviderError(f"Stability AI API error: {error_msg}")
            
            # Response is the image binary data
            generation_time = time.time() - start_time
            cost = self.PRICING.get(self.config.model, 3.5)
            
            # In a real implementation, you would save the image here
            # For now, we'll just indicate success
            result = ImageGenerationResult(
                success=True,
                image_url=None,  # Would be set after saving
                prompt_used=prompt,
                provider=self.provider_name,
                generation_time_seconds=generation_time,
                cost_cents=cost,
                metadata={
                    "model": self.config.model,
                    "aspect_ratio": aspect_ratio,
                    "style_preset": style_preset,
                    "seed": seed,
                    "negative_prompt": negative_prompt,
                    "output_format": output_format,
                    "image_size_bytes": len(response.content)
                }
            )
            
            self.set_status(ProviderStatus.AVAILABLE)
            
            logger.info(
                "Image generated successfully",
                generation_time=generation_time,
                cost_cents=cost,
                size_bytes=len(response.content)
            )
            
            return result
            
        except requests.exceptions.Timeout:
            self.set_status(ProviderStatus.ERROR)
            return ImageGenerationResult(
                success=False,
                provider=self.provider_name,
                prompt_used=prompt,
                generation_time_seconds=time.time() - start_time,
                error_message=f"Request timeout after {self.config.timeout_seconds}s"
            )
            
        except (RateLimitError, AuthenticationError, ProviderError) as e:
            return ImageGenerationResult(
                success=False,
                provider=self.provider_name,
                prompt_used=prompt,
                generation_time_seconds=time.time() - start_time,
                error_message=str(e)
            )
            
        except Exception as e:
            self.set_status(ProviderStatus.ERROR)
            logger.error("Unexpected error in Stability AI generation", error=str(e))
            return ImageGenerationResult(
                success=False,
                provider=self.provider_name,
                prompt_used=prompt,
                generation_time_seconds=time.time() - start_time,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def check_status(self) -> ProviderStatus:
        """Check Stability AI API availability"""
        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}"
            }
            
            # Check account balance endpoint
            response = requests.get(
                "https://api.stability.ai/v1/user/balance",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                self.set_status(ProviderStatus.AVAILABLE)
            elif response.status_code == 429:
                self.set_status(ProviderStatus.RATE_LIMITED)
            else:
                self.set_status(ProviderStatus.ERROR)
                
        except Exception as e:
            logger.warning("Stability AI status check failed", error=str(e))
            self.set_status(ProviderStatus.UNAVAILABLE)
        
        return self._status
    
    def estimate_cost(
        self,
        num_images: int = 1,
        model: Optional[str] = None
    ) -> float:
        """
        Estimate cost for generating images.
        
        Returns:
            Cost in cents
        """
        model = model or self.config.model
        cost_per_image = self.PRICING.get(model, 3.5)
        return cost_per_image * num_images
    
    def get_supported_aspect_ratios(self) -> list:
        """Get list of supported aspect ratios"""
        return self.SUPPORTED_ASPECT_RATIOS.copy()
    
    def get_style_presets(self) -> list:
        """Get list of available style presets"""
        return self.STYLE_PRESETS.copy()
    
    def validate_aspect_ratio(self, aspect_ratio: str) -> bool:
        """Validate if aspect ratio is supported"""
        return aspect_ratio in self.SUPPORTED_ASPECT_RATIOS


# Example usage
if __name__ == "__main__":
    # Test configuration
    config = ProviderConfig(
        api_key="sk-test-key",
        model="sd3",
        default_size="1:1"
    )
    
    provider = StabilityAIProvider(config)
    
    # Check status
    status = provider.check_status()
    print(f"Provider status: {status}")
    
    # Estimate cost
    cost = provider.estimate_cost(num_images=10)
    print(f"Estimated cost for 10 images: ${cost/100:.2f}")
    
    # Show capabilities
    print(f"Supported aspect ratios: {provider.get_supported_aspect_ratios()}")
    print(f"Available style presets: {provider.get_style_presets()[:5]}...")
