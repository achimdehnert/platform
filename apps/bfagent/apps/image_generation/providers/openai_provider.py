"""
OpenAI DALL-E 3 Provider
========================

Implementation of BaseImageProvider for OpenAI's DALL-E 3 model.

Features:
- High-quality image generation
- Automatic prompt revision
- Support for different sizes and qualities
- Style control (vivid/natural)

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


class OpenAIProvider(BaseImageProvider):
    """
    OpenAI DALL-E 3 image generation provider.
    
    Supported sizes: 1024x1024, 1792x1024, 1024x1792
    Supported qualities: standard, hd
    Supported styles: vivid, natural
    """
    
    API_URL = "https://api.openai.com/v1/images/generations"
    
    SUPPORTED_SIZES = [
        "1024x1024",
        "1792x1024",
        "1024x1792"
    ]
    
    SUPPORTED_QUALITIES = ["standard", "hd"]
    SUPPORTED_STYLES = ["vivid", "natural"]
    
    # Pricing (in cents)
    PRICING = {
        "standard": {
            "1024x1024": 4.0,
            "1792x1024": 8.0,
            "1024x1792": 8.0
        },
        "hd": {
            "1024x1024": 8.0,
            "1792x1024": 12.0,
            "1024x1792": 12.0
        }
    }
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        # Set defaults for DALL-E 3
        if not config.model:
            config.model = "dall-e-3"
        
        # Validate API key
        if not config.api_key or not config.api_key.startswith("sk-"):
            raise AuthenticationError("Invalid OpenAI API key format")
    
    def generate_image(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        style: Optional[str] = None,
        n: int = 1,  # DALL-E 3 only supports n=1
        **kwargs
    ) -> ImageGenerationResult:
        """
        Generate image using DALL-E 3.
        
        Args:
            prompt: Text description
            size: Image size (1024x1024, 1792x1024, 1024x1792)
            quality: "standard" or "hd"
            style: "vivid" or "natural"
            n: Number of images (must be 1 for DALL-E 3)
            
        Returns:
            ImageGenerationResult
        """
        start_time = time.time()
        
        # Apply rate limiting
        self._apply_rate_limit()
        
        # Set defaults
        size = size or self.config.default_size
        quality = quality or self.config.default_quality
        style = style or "vivid"
        
        # Validate parameters
        if size not in self.SUPPORTED_SIZES:
            return ImageGenerationResult(
                success=False,
                provider=self.provider_name,
                error_message=f"Invalid size {size}. Supported: {self.SUPPORTED_SIZES}"
            )
        
        if quality not in self.SUPPORTED_QUALITIES:
            return ImageGenerationResult(
                success=False,
                provider=self.provider_name,
                error_message=f"Invalid quality {quality}. Supported: {self.SUPPORTED_QUALITIES}"
            )
        
        if style not in self.SUPPORTED_STYLES:
            logger.warning(f"Invalid style {style}, defaulting to 'vivid'")
            style = "vivid"
        
        if n != 1:
            logger.warning("DALL-E 3 only supports n=1, adjusting")
            n = 1
        
        # Prepare request
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "n": n,
            "size": size,
            "quality": quality,
            "style": style,
            "response_format": "url"  # Could also be "b64_json"
        }
        
        # Add extra parameters from config
        payload.update(self.config.extra_params)
        
        logger.info(
            "Generating image with DALL-E 3",
            prompt=prompt[:100],
            size=size,
            quality=quality,
            style=style
        )
        
        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=self.config.timeout_seconds
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                self.set_status(ProviderStatus.RATE_LIMITED)
                raise RateLimitError("OpenAI rate limit exceeded")
            
            # Handle authentication errors
            if response.status_code == 401:
                self.set_status(ProviderStatus.ERROR)
                raise AuthenticationError("Invalid OpenAI API key")
            
            # Handle other errors
            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                raise ProviderError(f"OpenAI API error: {error_msg}")
            
            # Parse response
            data = response.json()
            image_data = data["data"][0]
            
            generation_time = time.time() - start_time
            cost = self.PRICING[quality][size]
            
            result = ImageGenerationResult(
                success=True,
                image_url=image_data["url"],
                prompt_used=prompt,
                revised_prompt=image_data.get("revised_prompt"),
                provider=self.provider_name,
                generation_time_seconds=generation_time,
                cost_cents=cost,
                metadata={
                    "model": self.config.model,
                    "size": size,
                    "quality": quality,
                    "style": style,
                    "api_response": data
                }
            )
            
            self.set_status(ProviderStatus.AVAILABLE)
            
            logger.info(
                "Image generated successfully",
                generation_time=generation_time,
                cost_cents=cost,
                revised_prompt=image_data.get("revised_prompt") != prompt
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
            logger.error("Unexpected error in DALL-E 3 generation", error=str(e))
            return ImageGenerationResult(
                success=False,
                provider=self.provider_name,
                prompt_used=prompt,
                generation_time_seconds=time.time() - start_time,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def check_status(self) -> ProviderStatus:
        """Check OpenAI API availability with a simple request"""
        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}"
            }
            
            # Simple health check to models endpoint
            response = requests.get(
                "https://api.openai.com/v1/models/dall-e-3",
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
            logger.warning("OpenAI status check failed", error=str(e))
            self.set_status(ProviderStatus.UNAVAILABLE)
        
        return self._status
    
    def estimate_cost(
        self,
        num_images: int = 1,
        size: Optional[str] = None,
        quality: Optional[str] = None
    ) -> float:
        """
        Estimate cost for generating images.
        
        Returns:
            Cost in cents
        """
        size = size or self.config.default_size
        quality = quality or self.config.default_quality
        
        if size not in self.SUPPORTED_SIZES or quality not in self.SUPPORTED_QUALITIES:
            return 0.0
        
        return self.PRICING[quality][size] * num_images
    
    def get_supported_sizes(self) -> list:
        """Get list of supported sizes"""
        return self.SUPPORTED_SIZES.copy()
    
    def validate_size(self, size: str) -> bool:
        """Validate if size is supported"""
        return size in self.SUPPORTED_SIZES


# Example usage
if __name__ == "__main__":
    # Test configuration
    config = ProviderConfig(
        api_key="sk-test-key",
        model="dall-e-3",
        default_size="1024x1024",
        default_quality="standard"
    )
    
    provider = OpenAIProvider(config)
    
    # Check status
    status = provider.check_status()
    print(f"Provider status: {status}")
    
    # Estimate cost
    cost = provider.estimate_cost(num_images=5, quality="hd", size="1792x1024")
    print(f"Estimated cost for 5 HD images: ${cost/100:.2f}")
