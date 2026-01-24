"""
Provider Manager
================

Manages multiple image generation providers with:
- Load balancing
- Automatic fallback
- Cost optimization
- Health monitoring

Author: BF Agent Team
Version: 1.0.0
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import structlog
from dataclasses import dataclass

from .base_provider import (
    BaseImageProvider,
    ImageGenerationResult,
    ProviderStatus,
    ProviderConfig
)

logger = structlog.get_logger(__name__)


class SelectionStrategy(Enum):
    """Strategy for selecting provider"""
    CHEAPEST = "cheapest"  # Select cheapest available provider
    FASTEST = "fastest"  # Select historically fastest provider
    PRIORITY = "priority"  # Use configured priority order
    ROUND_ROBIN = "round_robin"  # Distribute load evenly
    RANDOM = "random"  # Random selection


@dataclass
class ProviderMetrics:
    """Metrics for a provider"""
    provider_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_cost_cents: float = 0.0
    total_generation_time: float = 0.0
    average_generation_time: float = 0.0
    success_rate: float = 0.0
    
    def update(self, result: ImageGenerationResult):
        """Update metrics with a new result"""
        self.total_requests += 1
        
        if result.success:
            self.successful_requests += 1
            self.total_cost_cents += result.cost_cents
            self.total_generation_time += result.generation_time_seconds
        else:
            self.failed_requests += 1
        
        # Recalculate averages
        if self.successful_requests > 0:
            self.average_generation_time = (
                self.total_generation_time / self.successful_requests
            )
        
        if self.total_requests > 0:
            self.success_rate = (
                self.successful_requests / self.total_requests * 100
            )


class ProviderManager:
    """
    Manages multiple image generation providers.
    
    Features:
    - Automatic provider selection
    - Failover to backup providers
    - Cost optimization
    - Health monitoring
    """
    
    def __init__(
        self,
        providers: List[BaseImageProvider],
        strategy: SelectionStrategy = SelectionStrategy.PRIORITY,
        enable_fallback: bool = True
    ):
        """
        Initialize provider manager.
        
        Args:
            providers: List of configured providers
            strategy: Selection strategy
            enable_fallback: Enable automatic fallback on failure
        """
        self.providers = providers
        self.strategy = strategy
        self.enable_fallback = enable_fallback
        
        # Metrics tracking
        self.metrics: Dict[str, ProviderMetrics] = {}
        for provider in providers:
            self.metrics[provider.provider_name] = ProviderMetrics(
                provider_name=provider.provider_name
            )
        
        # Round robin counter
        self._round_robin_index = 0
        
        logger.info(
            "Provider manager initialized",
            num_providers=len(providers),
            strategy=strategy.value,
            enable_fallback=enable_fallback
        )
    
    def generate_image(
        self,
        prompt: str,
        preferred_provider: Optional[str] = None,
        **kwargs
    ) -> ImageGenerationResult:
        """
        Generate image using best available provider.
        
        Args:
            prompt: Image description
            preferred_provider: Name of preferred provider (optional)
            **kwargs: Parameters passed to provider
            
        Returns:
            ImageGenerationResult
        """
        # Get provider order
        if preferred_provider:
            providers = self._get_provider_by_name(preferred_provider)
            if not providers:
                logger.warning(
                    f"Preferred provider '{preferred_provider}' not found, using strategy"
                )
                providers = self._select_providers()
        else:
            providers = self._select_providers()
        
        # Try providers in order
        last_result = None
        for provider in providers:
            logger.info(
                "Attempting image generation",
                provider=provider.provider_name,
                prompt=prompt[:100]
            )
            
            # Check provider status first
            if provider.get_status() == ProviderStatus.UNAVAILABLE:
                logger.warning(
                    f"Skipping unavailable provider: {provider.provider_name}"
                )
                continue
            
            # Attempt generation
            result = provider.generate_image(prompt=prompt, **kwargs)
            
            # Update metrics
            self.metrics[provider.provider_name].update(result)
            
            if result.success:
                logger.info(
                    "Image generated successfully",
                    provider=provider.provider_name,
                    cost_cents=result.cost_cents,
                    generation_time=result.generation_time_seconds
                )
                return result
            
            last_result = result
            logger.warning(
                "Provider failed",
                provider=provider.provider_name,
                error=result.error_message
            )
            
            # If fallback disabled, stop here
            if not self.enable_fallback:
                break
        
        # All providers failed
        logger.error("All providers failed to generate image", prompt=prompt[:100])
        return last_result or ImageGenerationResult(
            success=False,
            provider="None",
            prompt_used=prompt,
            error_message="All providers failed"
        )
    
    def batch_generate(
        self,
        prompts: List[str],
        distribute: bool = True,
        **kwargs
    ) -> List[ImageGenerationResult]:
        """
        Generate multiple images.
        
        Args:
            prompts: List of image descriptions
            distribute: Distribute across providers for better load balancing
            **kwargs: Parameters passed to providers
            
        Returns:
            List of ImageGenerationResults
        """
        results = []
        
        if distribute and len(self.providers) > 1:
            # Distribute prompts across providers
            for i, prompt in enumerate(prompts):
                provider_index = i % len(self.providers)
                preferred = self.providers[provider_index].provider_name
                result = self.generate_image(
                    prompt=prompt,
                    preferred_provider=preferred,
                    **kwargs
                )
                results.append(result)
        else:
            # Use standard selection for each
            for prompt in prompts:
                result = self.generate_image(prompt=prompt, **kwargs)
                results.append(result)
        
        return results
    
    def _select_providers(self) -> List[BaseImageProvider]:
        """Select providers based on strategy"""
        available = [p for p in self.providers if p.get_status() != ProviderStatus.UNAVAILABLE]
        
        if not available:
            logger.error("No available providers!")
            return self.providers  # Return all as last resort
        
        if self.strategy == SelectionStrategy.PRIORITY:
            # Return in order (first = highest priority)
            return available
        
        elif self.strategy == SelectionStrategy.CHEAPEST:
            # Sort by estimated cost
            return sorted(
                available,
                key=lambda p: p.estimate_cost(num_images=1)
            )
        
        elif self.strategy == SelectionStrategy.FASTEST:
            # Sort by average generation time
            return sorted(
                available,
                key=lambda p: self.metrics[p.provider_name].average_generation_time or 999
            )
        
        elif self.strategy == SelectionStrategy.ROUND_ROBIN:
            # Rotate through providers
            provider = available[self._round_robin_index % len(available)]
            self._round_robin_index += 1
            # Return primary + fallbacks
            result = [provider]
            result.extend([p for p in available if p != provider])
            return result
        
        elif self.strategy == SelectionStrategy.RANDOM:
            import random
            shuffled = available.copy()
            random.shuffle(shuffled)
            return shuffled
        
        return available
    
    def _get_provider_by_name(self, name: str) -> List[BaseImageProvider]:
        """Get provider by name, with fallbacks"""
        # Find primary provider
        primary = None
        for provider in self.providers:
            if provider.provider_name.lower() == name.lower():
                primary = provider
                break
        
        if not primary:
            return []
        
        # Build list: primary + other available providers as fallback
        result = [primary]
        if self.enable_fallback:
            result.extend([p for p in self.providers if p != primary])
        
        return result
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics for all providers"""
        return {
            "total_requests": sum(m.total_requests for m in self.metrics.values()),
            "total_successful": sum(m.successful_requests for m in self.metrics.values()),
            "total_failed": sum(m.failed_requests for m in self.metrics.values()),
            "total_cost_cents": sum(m.total_cost_cents for m in self.metrics.values()),
            "providers": {
                name: {
                    "requests": metrics.total_requests,
                    "success_rate": round(metrics.success_rate, 2),
                    "avg_time": round(metrics.average_generation_time, 2),
                    "total_cost_cents": round(metrics.total_cost_cents, 2)
                }
                for name, metrics in self.metrics.items()
            }
        }
    
    def estimate_cost(
        self,
        num_images: int,
        provider_name: Optional[str] = None,
        **kwargs
    ) -> float:
        """
        Estimate cost for generating images.
        
        Args:
            num_images: Number of images
            provider_name: Specific provider (uses cheapest if None)
            **kwargs: Provider-specific parameters
            
        Returns:
            Estimated cost in cents
        """
        if provider_name:
            providers = self._get_provider_by_name(provider_name)
            if not providers:
                return 0.0
            return providers[0].estimate_cost(num_images=num_images, **kwargs)
        
        # Return cheapest option
        costs = [
            p.estimate_cost(num_images=num_images, **kwargs)
            for p in self.providers
        ]
        return min(costs) if costs else 0.0
    
    def health_check(self) -> Dict[str, ProviderStatus]:
        """Check status of all providers"""
        statuses = {}
        for provider in self.providers:
            status = provider.check_status()
            statuses[provider.provider_name] = status
            logger.info(
                "Provider health check",
                provider=provider.provider_name,
                status=status.value
            )
        return statuses
    
    def get_provider_capabilities(self) -> Dict[str, Any]:
        """Get capabilities of all providers"""
        capabilities = {}
        for provider in self.providers:
            capabilities[provider.provider_name] = {
                "supported_sizes": provider.get_supported_sizes(),
                "status": provider.get_status().value,
            }
        return capabilities


# Example usage
if __name__ == "__main__":
    from .openai_provider import OpenAIProvider
    from .stability_provider import StabilityAIProvider
    
    # Configure providers
    openai_config = ProviderConfig(
        api_key="sk-test-openai",
        model="dall-e-3"
    )
    
    stability_config = ProviderConfig(
        api_key="sk-test-stability",
        model="sd3"
    )
    
    # Create provider instances
    providers = [
        OpenAIProvider(openai_config),
        StabilityAIProvider(stability_config)
    ]
    
    # Create manager
    manager = ProviderManager(
        providers=providers,
        strategy=SelectionStrategy.CHEAPEST,
        enable_fallback=True
    )
    
    # Health check
    statuses = manager.health_check()
    print("Provider statuses:", statuses)
    
    # Estimate costs
    cost = manager.estimate_cost(num_images=10)
    print(f"Estimated cost for 10 images: ${cost/100:.2f}")
    
    # Get metrics
    metrics = manager.get_metrics()
    print("Metrics:", metrics)
