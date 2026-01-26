"""
LLM Registry - DB-driven LLM configuration and selection.

Provides:
- LLMTier: Economy, Standard, Premium tiers for cost/quality tradeoffs
- LLMRegistry Protocol: Interface for LLM configuration storage
- DictRegistry: Simple in-memory registry for testing
- Adapters for Django ORM integration (in consuming apps)

Usage:
    # With dict registry (testing/simple use)
    registry = DictRegistry.from_env()
    client = DynamicLLMClient(registry)
    response = await client.generate("Hello", tier=LLMTier.STANDARD)
    
    # With Django registry (in BFAgent/TravelBeat)
    from apps.core.llm_adapters import DjangoLLMRegistry
    registry = DjangoLLMRegistry()
    client = DynamicLLMClient(registry)
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Protocol, runtime_checkable
from pydantic import BaseModel, Field

from .llm_client import LLMClient, LLMConfig, LLMProvider, LLMResponse


class LLMTier(str, Enum):
    """LLM Tiers for cost/quality tradeoffs."""
    ECONOMY = "economy"      # GPT-3.5, Claude Haiku, Groq Llama
    STANDARD = "standard"    # GPT-4o-mini, Claude Sonnet
    PREMIUM = "premium"      # GPT-4o, Claude Opus
    LOCAL = "local"          # Ollama, local models


@dataclass
class LLMEntry:
    """Single LLM configuration entry."""
    id: Optional[int] = None
    name: str = ""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    tier: LLMTier = LLMTier.STANDARD
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    cost_per_1k_input: float = 0.00015
    cost_per_1k_output: float = 0.0006
    is_active: bool = True
    capabilities: dict = field(default_factory=dict)
    
    def to_llm_config(self) -> LLMConfig:
        """Convert to LLMConfig for LLMClient."""
        provider_map = {
            "openai": LLMProvider.OPENAI,
            "anthropic": LLMProvider.ANTHROPIC,
            "groq": LLMProvider.GROQ,
            "ollama": LLMProvider.OLLAMA,
        }
        return LLMConfig(
            provider=provider_map.get(self.provider, LLMProvider.OPENAI),
            model=self.model,
            api_key=self.api_key,
            base_url=self.api_endpoint,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )


@runtime_checkable
class LLMRegistry(Protocol):
    """Protocol for LLM registry implementations."""
    
    def get_by_id(self, llm_id: int) -> Optional[LLMEntry]:
        """Get LLM by database ID."""
        ...
    
    def get_by_name(self, name: str) -> Optional[LLMEntry]:
        """Get LLM by name."""
        ...
    
    def get_by_tier(self, tier: LLMTier) -> Optional[LLMEntry]:
        """Get cheapest active LLM in tier."""
        ...
    
    def get_default(self) -> LLMEntry:
        """Get default LLM (cheapest active)."""
        ...
    
    def list_active(self) -> list[LLMEntry]:
        """List all active LLMs."""
        ...


class DictRegistry:
    """Simple in-memory LLM registry for testing and simple deployments."""
    
    # Default tier mappings
    TIER_MODELS = {
        LLMTier.ECONOMY: [
            ("openai", "gpt-3.5-turbo"),
            ("anthropic", "claude-3-haiku-20240307"),
            ("groq", "llama-3.3-70b-versatile"),
        ],
        LLMTier.STANDARD: [
            ("openai", "gpt-4o-mini"),
            ("anthropic", "claude-3-5-sonnet-20241022"),
        ],
        LLMTier.PREMIUM: [
            ("openai", "gpt-4o"),
            ("anthropic", "claude-3-opus-20240229"),
        ],
        LLMTier.LOCAL: [
            ("ollama", "llama3.2"),
            ("ollama", "mistral"),
        ],
    }
    
    def __init__(self, entries: Optional[list[LLMEntry]] = None):
        self._entries: list[LLMEntry] = entries or []
    
    @classmethod
    def from_env(cls) -> "DictRegistry":
        """Create registry from environment variables."""
        entries = []
        
        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            entries.extend([
                LLMEntry(
                    id=1, name="GPT-3.5 Turbo", provider="openai",
                    model="gpt-3.5-turbo", tier=LLMTier.ECONOMY,
                    api_key=os.getenv("OPENAI_API_KEY"),
                    cost_per_1k_input=0.0005, cost_per_1k_output=0.0015,
                ),
                LLMEntry(
                    id=2, name="GPT-4o-mini", provider="openai",
                    model="gpt-4o-mini", tier=LLMTier.STANDARD,
                    api_key=os.getenv("OPENAI_API_KEY"),
                    cost_per_1k_input=0.00015, cost_per_1k_output=0.0006,
                ),
                LLMEntry(
                    id=3, name="GPT-4o", provider="openai",
                    model="gpt-4o", tier=LLMTier.PREMIUM,
                    api_key=os.getenv("OPENAI_API_KEY"),
                    cost_per_1k_input=0.005, cost_per_1k_output=0.015,
                ),
            ])
        
        # Anthropic
        if os.getenv("ANTHROPIC_API_KEY"):
            entries.extend([
                LLMEntry(
                    id=10, name="Claude 3 Haiku", provider="anthropic",
                    model="claude-3-haiku-20240307", tier=LLMTier.ECONOMY,
                    api_key=os.getenv("ANTHROPIC_API_KEY"),
                    cost_per_1k_input=0.00025, cost_per_1k_output=0.00125,
                ),
                LLMEntry(
                    id=11, name="Claude 3.5 Sonnet", provider="anthropic",
                    model="claude-3-5-sonnet-20241022", tier=LLMTier.STANDARD,
                    api_key=os.getenv("ANTHROPIC_API_KEY"),
                    cost_per_1k_input=0.003, cost_per_1k_output=0.015,
                ),
                LLMEntry(
                    id=12, name="Claude 3 Opus", provider="anthropic",
                    model="claude-3-opus-20240229", tier=LLMTier.PREMIUM,
                    api_key=os.getenv("ANTHROPIC_API_KEY"),
                    cost_per_1k_input=0.015, cost_per_1k_output=0.075,
                ),
            ])
        
        # Groq (free tier)
        if os.getenv("GROQ_API_KEY"):
            entries.append(
                LLMEntry(
                    id=20, name="Groq Llama 3.3", provider="groq",
                    model="llama-3.3-70b-versatile", tier=LLMTier.ECONOMY,
                    api_key=os.getenv("GROQ_API_KEY"),
                    cost_per_1k_input=0.0, cost_per_1k_output=0.0,
                )
            )
        
        return cls(entries)
    
    def get_by_id(self, llm_id: int) -> Optional[LLMEntry]:
        for entry in self._entries:
            if entry.id == llm_id and entry.is_active:
                return entry
        return None
    
    def get_by_name(self, name: str) -> Optional[LLMEntry]:
        for entry in self._entries:
            if entry.name == name and entry.is_active:
                return entry
        return None
    
    def get_by_tier(self, tier: LLMTier) -> Optional[LLMEntry]:
        """Get cheapest active LLM in tier."""
        tier_entries = [e for e in self._entries if e.tier == tier and e.is_active]
        if not tier_entries:
            return None
        return min(tier_entries, key=lambda e: e.cost_per_1k_input + e.cost_per_1k_output)
    
    def get_default(self) -> LLMEntry:
        """Get default LLM (cheapest active, prefer STANDARD tier)."""
        # Try STANDARD first
        entry = self.get_by_tier(LLMTier.STANDARD)
        if entry:
            return entry
        # Fall back to any active
        active = self.list_active()
        if active:
            return min(active, key=lambda e: e.cost_per_1k_input + e.cost_per_1k_output)
        # Ultimate fallback
        return LLMEntry(
            name="Fallback GPT-4o-mini",
            provider="openai",
            model="gpt-4o-mini",
            tier=LLMTier.STANDARD,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    
    def list_active(self) -> list[LLMEntry]:
        return [e for e in self._entries if e.is_active]
    
    def add(self, entry: LLMEntry) -> None:
        """Add entry to registry."""
        self._entries.append(entry)


class DynamicLLMClient:
    """
    LLM Client with dynamic model selection via Registry.
    
    Supports:
    - Selection by ID (explicit)
    - Selection by name (explicit)
    - Selection by tier (automatic cost/quality tradeoff)
    - Fallback to default
    
    Usage:
        registry = DictRegistry.from_env()
        client = DynamicLLMClient(registry)
        
        # Use specific LLM
        response = await client.generate("Hello", llm_id=2)
        
        # Use tier-based selection
        response = await client.generate("Hello", tier=LLMTier.PREMIUM)
        
        # Use default
        response = await client.generate("Hello")
    """
    
    def __init__(self, registry: LLMRegistry):
        self.registry = registry
        self._clients: dict[int, LLMClient] = {}
    
    def _get_or_create_client(self, entry: LLMEntry) -> LLMClient:
        """Get cached client or create new one."""
        if entry.id not in self._clients:
            config = entry.to_llm_config()
            self._clients[entry.id] = LLMClient(config)
        return self._clients[entry.id]
    
    def _resolve_entry(
        self,
        llm_id: Optional[int] = None,
        llm_name: Optional[str] = None,
        tier: Optional[LLMTier] = None,
    ) -> LLMEntry:
        """Resolve LLM entry from parameters."""
        if llm_id:
            entry = self.registry.get_by_id(llm_id)
            if entry:
                return entry
        
        if llm_name:
            entry = self.registry.get_by_name(llm_name)
            if entry:
                return entry
        
        if tier:
            entry = self.registry.get_by_tier(tier)
            if entry:
                return entry
        
        return self.registry.get_default()
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        llm_id: Optional[int] = None,
        llm_name: Optional[str] = None,
        tier: Optional[LLMTier] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate text with dynamic LLM selection.
        
        Priority:
        1. llm_id (explicit)
        2. llm_name (explicit)
        3. tier (automatic selection)
        4. default (cheapest active)
        """
        entry = self._resolve_entry(llm_id, llm_name, tier)
        client = self._get_or_create_client(entry)
        
        response = await client.generate(prompt, system_prompt, **kwargs)
        
        # TODO: Track usage via UsageTracker
        # self._track_usage(entry, response)
        
        return response
    
    def get_entry_for_tier(self, tier: LLMTier) -> Optional[LLMEntry]:
        """Get the LLM entry that would be used for a tier."""
        return self.registry.get_by_tier(tier)
    
    def list_available(self) -> list[LLMEntry]:
        """List all available LLMs."""
        return self.registry.list_active()
