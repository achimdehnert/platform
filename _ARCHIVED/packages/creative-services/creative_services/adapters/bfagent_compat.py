"""
BFAgent Compatibility Layer.

This module provides backward-compatible wrappers that allow BFAgent's
existing code to continue working while using the new creative-services
infrastructure under the hood.

IMPORTANT: This is a BRIDGE module. BFAgent code can continue to use
its existing imports and patterns. Over time, code can be migrated
to use creative-services directly.

Usage in BFAgent (no code changes needed):
    # Existing BFAgent code continues to work:
    from apps.bfagent.services.llm_client import generate_text
    result = generate_text(prompt, system_prompt)
    
    # New code can use creative-services directly:
    from creative_services.core import DynamicLLMClient, LLMTier
    client = DynamicLLMClient(registry)
    response = await client.generate(prompt, tier=LLMTier.STANDARD)

Migration Path:
1. Install creative-services in BFAgent
2. Create adapter in apps/core/llm_adapters.py
3. Existing code continues to work
4. New code uses creative-services directly
5. Gradually migrate old code
"""

import asyncio
from typing import Optional, Any
from functools import wraps

from creative_services.core.llm_registry import (
    LLMTier,
    LLMEntry,
    DictRegistry,
    DynamicLLMClient,
)
from creative_services.core.llm_client import LLMResponse


def sync_wrapper(async_func):
    """Wrap async function to be callable synchronously."""
    @wraps(async_func)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, create a new loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, async_func(*args, **kwargs)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(async_func(*args, **kwargs))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(async_func(*args, **kwargs))
    return wrapper


class BFAgentLLMBridge:
    """
    Bridge class that provides BFAgent-compatible interface using creative-services.
    
    This allows existing BFAgent code to work without changes while
    using the new infrastructure.
    
    Usage:
        bridge = BFAgentLLMBridge()
        
        # Sync call (like existing BFAgent)
        result = bridge.generate_text(prompt, system_prompt)
        
        # With tier selection
        result = bridge.generate_text(prompt, tier="premium")
    """
    
    _instance: Optional["BFAgentLLMBridge"] = None
    
    def __init__(self, registry=None):
        self._registry = registry or DictRegistry.from_env()
        self._client = DynamicLLMClient(self._registry)
    
    @classmethod
    def get_instance(cls) -> "BFAgentLLMBridge":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def with_django_registry(cls, llms_model_class: Any) -> "BFAgentLLMBridge":
        """Create bridge with Django-backed registry."""
        from creative_services.adapters.django_adapter import DjangoLLMRegistry
        registry = DjangoLLMRegistry(llms_model_class)
        return cls(registry)
    
    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        llm_id: Optional[int] = None,
        tier: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Generate text synchronously (BFAgent-compatible).
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            llm_id: Specific LLM ID from database
            tier: Tier name ("economy", "standard", "premium")
            **kwargs: Additional LLM parameters
        
        Returns:
            Generated text content
        """
        tier_enum = None
        if tier:
            tier_map = {
                "economy": LLMTier.ECONOMY,
                "standard": LLMTier.STANDARD,
                "premium": LLMTier.PREMIUM,
                "local": LLMTier.LOCAL,
            }
            tier_enum = tier_map.get(tier.lower())
        
        response = self._generate_sync(
            prompt=prompt,
            system_prompt=system_prompt,
            llm_id=llm_id,
            tier=tier_enum,
            **kwargs,
        )
        return response.content
    
    @sync_wrapper
    async def _generate_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        llm_id: Optional[int] = None,
        tier: Optional[LLMTier] = None,
        **kwargs,
    ) -> LLMResponse:
        """Internal async generation."""
        return await self._client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            llm_id=llm_id,
            tier=tier,
            **kwargs,
        )
    
    async def generate_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        llm_id: Optional[int] = None,
        tier: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate text asynchronously."""
        tier_enum = None
        if tier:
            tier_map = {
                "economy": LLMTier.ECONOMY,
                "standard": LLMTier.STANDARD,
                "premium": LLMTier.PREMIUM,
                "local": LLMTier.LOCAL,
            }
            tier_enum = tier_map.get(tier.lower())
        
        return await self._client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            llm_id=llm_id,
            tier=tier_enum,
            **kwargs,
        )
    
    def get_available_llms(self) -> list[dict]:
        """Get list of available LLMs (for UI dropdowns)."""
        entries = self._registry.list_active()
        return [
            {
                "id": e.id,
                "name": e.name,
                "provider": e.provider,
                "model": e.model,
                "tier": e.tier.value,
            }
            for e in entries
        ]
    
    def get_llm_for_tier(self, tier: str) -> Optional[dict]:
        """Get the LLM that would be used for a tier."""
        tier_map = {
            "economy": LLMTier.ECONOMY,
            "standard": LLMTier.STANDARD,
            "premium": LLMTier.PREMIUM,
            "local": LLMTier.LOCAL,
        }
        tier_enum = tier_map.get(tier.lower())
        if not tier_enum:
            return None
        
        entry = self._registry.get_by_tier(tier_enum)
        if not entry:
            return None
        
        return {
            "id": entry.id,
            "name": entry.name,
            "provider": entry.provider,
            "model": entry.model,
            "tier": entry.tier.value,
        }


# Convenience functions for drop-in replacement
def generate_text(
    prompt: str,
    system_prompt: Optional[str] = None,
    llm_id: Optional[int] = None,
    tier: str = "standard",
    **kwargs,
) -> str:
    """
    Drop-in replacement for BFAgent's generate_text function.
    
    Usage:
        from creative_services.adapters.bfagent_compat import generate_text
        result = generate_text("Hello", tier="premium")
    """
    bridge = BFAgentLLMBridge.get_instance()
    return bridge.generate_text(
        prompt=prompt,
        system_prompt=system_prompt,
        llm_id=llm_id,
        tier=tier,
        **kwargs,
    )


async def generate_text_async(
    prompt: str,
    system_prompt: Optional[str] = None,
    llm_id: Optional[int] = None,
    tier: str = "standard",
    **kwargs,
) -> LLMResponse:
    """
    Async version of generate_text.
    
    Usage:
        from creative_services.adapters.bfagent_compat import generate_text_async
        response = await generate_text_async("Hello", tier="premium")
    """
    bridge = BFAgentLLMBridge.get_instance()
    return await bridge.generate_async(
        prompt=prompt,
        system_prompt=system_prompt,
        llm_id=llm_id,
        tier=tier,
        **kwargs,
    )
