"""
Creative Services - Shared AI-powered creative writing services.

This package provides modular, reusable creative AI services for:
- Character generation
- World building
- Story writing (outlines, chapters)
- Scene analysis
- Illustration configuration
- Quality review

Core Features:
- LLMClient: Unified client for OpenAI, Anthropic, Groq, Ollama
- LLMRegistry: DB-driven LLM configuration (no code changes to switch models)
- DynamicLLMClient: Tier-based LLM selection (economy/standard/premium)
- UsageTracker: Token and cost tracking
- Adapters: Django ORM integration, BFAgent compatibility layer
"""

__version__ = "0.2.0"

from creative_services.core import (
    # Base
    BaseHandler,
    BaseContext,
    # LLM Client
    LLMClient,
    LLMConfig,
    LLMProvider,
    LLMResponse,
    # Tool-Use (complete() API)
    ToolCall,
    CompletionResponse,
    # LLM Registry (DB-driven)
    LLMTier,
    LLMEntry,
    LLMRegistry,
    DictRegistry,
    DynamicLLMClient,
    # Usage Tracking
    UsageRecord,
    UsageStats,
    UsageTracker,
    InMemoryTracker,
    calculate_cost,
)

__all__ = [
    # Version
    "__version__",
    # Base
    "BaseHandler",
    "BaseContext",
    # LLM Client
    "LLMClient",
    "LLMConfig",
    "LLMProvider",
    "LLMResponse",
    # Tool-Use (complete() API)
    "ToolCall",
    "CompletionResponse",
    # LLM Registry (DB-driven)
    "LLMTier",
    "LLMEntry",
    "LLMRegistry",
    "DictRegistry",
    "DynamicLLMClient",
    # Usage Tracking
    "UsageRecord",
    "UsageStats",
    "UsageTracker",
    "InMemoryTracker",
    "calculate_cost",
]
