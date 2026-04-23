"""
Adapters for integrating creative-services with various frameworks.

Available adapters:
- django_adapter: Django ORM adapters for LLM Registry and Usage Tracking
- bfagent_compat: Backward-compatible wrappers for BFAgent
"""

from creative_services.adapters.django_adapter import (
    DjangoLLMRegistry,
    DjangoUsageTracker,
    TIER_MAPPING,
)
from creative_services.adapters.bfagent_compat import (
    BFAgentLLMBridge,
    generate_text,
    generate_text_async,
)

__all__ = [
    # Django adapters
    "DjangoLLMRegistry",
    "DjangoUsageTracker",
    "TIER_MAPPING",
    # BFAgent compatibility
    "BFAgentLLMBridge",
    "generate_text",
    "generate_text_async",
]
