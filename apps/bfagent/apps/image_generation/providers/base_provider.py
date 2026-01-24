"""
Base Provider Interface for Image Generation
============================================

Abstract base class that defines the interface all image generation providers must implement.
Ensures consistency across different providers (OpenAI, Stability AI, etc.)

Author: BF Agent Team
Version: 1.0.0
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import time
from pathlib import Path


class ProviderStatus(Enum):
    """Provider availability status"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


@dataclass
class ImageGenerationResult:
    """Standardized result from image generation"""
    success: bool
    image_url: Optional[str] = None
    local_path: Optional[Path] = None
    prompt_used: str = ""
    revised_prompt: Optional[str] = None  # Some providers revise prompts
    provider: str = ""
    generation_time_seconds: float = 0.0
    cost_cents: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProviderConfig:
    """Configuration for a provider"""
    api_key: str
    model: str
    default_size: str = "1024x1024"
    default_quality: str = "standard"
    timeout_seconds: int = 60
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    rate_limit_per_minute: Optional[int] = None
    cost_per_image_cents: float = 0.0
    extra_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}


class BaseImageProvider(ABC):
    """
    Abstract base class for all image generation providers.
    
    All providers must implement:
    - generate_image(): Core generation method
    - check_status(): Health check
    - estimate_cost(): Cost calculation
    """
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.provider_name = self.__class__.__name__.replace("Provider", "")
        self._status = ProviderStatus.AVAILABLE
        self._last_request_time = 0.0
        self._request_count = 0
        
    # ==================== ABSTRACT METHODS ====================
    
    @abstractmethod
    def generate_image(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        style: Optional[str] = None,
        **kwargs
    ) -> ImageGenerationResult:
        """
        Generate an image from a text prompt.
        
        Args:
            prompt: Text description of the image to generate
            size: Image dimensions (e.g., "1024x1024")
            quality: Quality level (provider-specific)
            style: Art style (provider-specific)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            ImageGenerationResult with generated image details
            
        Raises:
            ProviderError: If generation fails
        """
        pass
    
    @abstractmethod
    def check_status(self) -> ProviderStatus:
        """
        Check if provider is available and healthy.
        
        Returns:
            ProviderStatus indicating current availability
        """
        pass
    
    @abstractmethod
    def estimate_cost(
        self,
        num_images: int = 1,
        size: Optional[str] = None,
        quality: Optional[str] = None
    ) -> float:
        """
        Estimate cost in cents for generating images.
        
        Args:
            num_images: Number of images to generate
            size: Image dimensions
            quality: Quality level
            
        Returns:
            Estimated cost in cents
        """
        pass
    
    # ==================== COMMON METHODS ====================
    
    def get_status(self) -> ProviderStatus:
        """Get current provider status"""
        return self._status
    
    def set_status(self, status: ProviderStatus):
        """Update provider status"""
        self._status = status
    
    def _apply_rate_limit(self):
        """Apply rate limiting if configured"""
        if not self.config.rate_limit_per_minute:
            return
            
        # Check if we need to wait
        time_since_last = time.time() - self._last_request_time
        min_interval = 60.0 / self.config.rate_limit_per_minute
        
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            time.sleep(wait_time)
        
        self._last_request_time = time.time()
        self._request_count += 1
    
    def _handle_retry(
        self,
        func,
        *args,
        **kwargs
    ) -> ImageGenerationResult:
        """
        Handle retries with exponential backoff.
        
        Args:
            func: Function to retry
            *args, **kwargs: Arguments for the function
            
        Returns:
            Result from successful execution
            
        Raises:
            Exception: If all retries fail
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.config.max_retries - 1:
                    # Exponential backoff
                    wait_time = self.config.retry_delay_seconds * (2 ** attempt)
                    time.sleep(wait_time)
                else:
                    # Last attempt failed
                    break
        
        # All retries failed
        return ImageGenerationResult(
            success=False,
            provider=self.provider_name,
            error_message=f"All {self.config.max_retries} retries failed: {str(last_exception)}"
        )
    
    def validate_size(self, size: str) -> bool:
        """
        Validate if size format is correct.
        Override in subclass for provider-specific validation.
        """
        try:
            width, height = size.lower().split('x')
            return width.isdigit() and height.isdigit()
        except:
            return False
    
    def get_supported_sizes(self) -> List[str]:
        """
        Get list of supported image sizes.
        Override in subclass for provider-specific sizes.
        """
        return ["1024x1024"]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get provider metrics"""
        return {
            "provider": self.provider_name,
            "status": self._status.value,
            "total_requests": self._request_count,
            "last_request_time": self._last_request_time,
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(status={self._status.value})"


class ProviderError(Exception):
    """Base exception for provider errors"""
    pass


class RateLimitError(ProviderError):
    """Raised when rate limit is exceeded"""
    pass


class AuthenticationError(ProviderError):
    """Raised when authentication fails"""
    pass


class InvalidParameterError(ProviderError):
    """Raised when parameters are invalid"""
    pass
