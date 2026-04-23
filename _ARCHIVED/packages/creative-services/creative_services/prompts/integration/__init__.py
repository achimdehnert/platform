"""
Integration module for connecting the Prompt Template System to external systems.

Provides ready-to-use integrations for:
- BFAgent (Django-based writing assistant)
- Generic LLM clients (OpenAI, Anthropic, etc.)
"""

from .bfagent import (
    BFAgentRegistry,
    BFAgentLLMClient,
    create_bfagent_executor,
)

from .llm_clients import (
    OpenAIClient,
    AnthropicClient,
    create_llm_client,
)

__all__ = [
    # BFAgent
    "BFAgentRegistry",
    "BFAgentLLMClient",
    "create_bfagent_executor",
    # LLM Clients
    "OpenAIClient",
    "AnthropicClient",
    "create_llm_client",
]
