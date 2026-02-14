"""Core module with base classes, LLM client, registry, and contexts."""

from creative_services.core.base_handler import BaseHandler
from creative_services.core.llm_client import (
    CompletionResponse,
    LLMClient,
    LLMConfig,
    LLMProvider,
    LLMResponse,
    ToolCall,
)
from creative_services.core.llm_registry import (
    LLMTier,
    LLMEntry,
    LLMRegistry,
    DictRegistry,
    DynamicLLMClient,
)
from creative_services.core.usage_tracker import (
    UsageRecord,
    UsageStats,
    UsageTracker,
    InMemoryTracker,
    calculate_cost,
)
from creative_services.core.context import BaseContext

__all__ = [
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
