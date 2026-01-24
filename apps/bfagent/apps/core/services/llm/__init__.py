"""
Core LLM Service - Unified LLM Client System
=============================================

Consolidated LLM service providing a unified interface for all
LLM providers (OpenAI, Anthropic, Google, etc.).

This module consolidates implementations from:
- apps/bfagent/domains/book_writing/services/llm_service.py
- apps/bfagent/agents/handler_generator/llm_client.py
- apps/bfagent/services/llm_client.py
- apps/bfagent/services/handlers/processing/llm_processor.py

Quick Start:
    from apps.core.services.llm import get_client

    # Auto-detect provider from settings
    client = get_client()
    response = client.generate("Hello, world!")

    # Specific provider
    client = get_client("openai", api_key="sk-...")
    response = client.generate("Tell me a joke")

    # Structured output
    from pydantic import BaseModel

    class BookInfo(BaseModel):
        title: str
        author: str

    book = client.generate_structured(
        prompt="Parse: 1984 by George Orwell",
        response_model=BookInfo
    )

Components:
    - OpenAIClient: OpenAI API client (GPT-4, etc.)
    - AnthropicClient: Anthropic API client (Claude)
    - CostTracker: Usage and cost tracking
    - Token utilities: Estimation, truncation
"""

from typing import Optional

from .anthropic_client import AnthropicClient

# ==================== Base ====================
from .base import BaseLLMClient

# ==================== Exceptions ====================
from .exceptions import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMContentFilterError,
    LLMContextLengthError,
    LLMException,
    LLMModelNotFoundError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMValidationError,
)

# ==================== Models ====================
from .models import (
    LLM_PRICING,
    LLMConfig,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ResponseFormat,
    TokenUsage,
)

# ==================== Clients ====================
from .openai_client import OpenAIClient

# ==================== Utilities ====================
from .utils import (
    CostTracker,
    UsageRecord,
    build_few_shot_prompt,
    count_messages_tokens,
    estimate_tokens,
    format_system_prompt,
    truncate_to_tokens,
)

# ==================== Factory ====================


def get_client(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs,
) -> BaseLLMClient:
    """
    Get an LLM client instance.

    Factory function that returns the appropriate client based on
    provider. If provider is not specified, attempts to auto-detect
    from Django settings.

    Args:
        provider: Provider name ("openai", "anthropic", etc.)
        api_key: API key (uses settings if not provided)
        model: Model name
        **kwargs: Additional client configuration

    Returns:
        Configured LLM client instance

    Example:
        # Auto-detect from settings
        client = get_client()

        # Specific provider
        client = get_client("openai", model="gpt-4")

        # With API key
        client = get_client("anthropic", api_key="sk-ant-...")
    """
    # Try to get defaults from Django settings
    if provider is None or api_key is None:
        try:
            from django.conf import settings

            if provider is None:
                provider = getattr(settings, "LLM_PROVIDER", "openai")

            if api_key is None:
                if provider == "openai":
                    api_key = getattr(settings, "OPENAI_API_KEY", None)
                elif provider == "anthropic":
                    api_key = getattr(settings, "ANTHROPIC_API_KEY", None)

        except Exception:
            provider = provider or "openai"

    provider = (provider or "openai").lower()

    if provider == "openai":
        return OpenAIClient(api_key=api_key, model=model, **kwargs)
    elif provider == "anthropic":
        return AnthropicClient(api_key=api_key, model=model, **kwargs)
    else:
        # Default to OpenAI-compatible
        return OpenAIClient(api_key=api_key, model=model, **kwargs)


def get_openai_client(
    api_key: Optional[str] = None, model: str = "gpt-4", **kwargs
) -> OpenAIClient:
    """
    Get an OpenAI client instance.

    Convenience function for OpenAI specifically.

    Args:
        api_key: OpenAI API key
        model: Model name (default: gpt-4)
        **kwargs: Additional configuration

    Returns:
        OpenAIClient instance
    """
    return OpenAIClient(api_key=api_key, model=model, **kwargs)


def get_anthropic_client(
    api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022", **kwargs
) -> AnthropicClient:
    """
    Get an Anthropic client instance.

    Convenience function for Anthropic specifically.

    Args:
        api_key: Anthropic API key
        model: Model name (default: claude-3-5-sonnet)
        **kwargs: Additional configuration

    Returns:
        AnthropicClient instance
    """
    return AnthropicClient(api_key=api_key, model=model, **kwargs)


# ==================== Quick Functions ====================


def generate(
    prompt: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    **kwargs,
) -> LLMResponse:
    """
    Quick generation function.

    Creates a temporary client and generates a response.
    For repeated calls, prefer creating a client instance.

    Args:
        prompt: User prompt
        provider: LLM provider
        model: Model name
        system_prompt: System prompt
        **kwargs: Additional generation parameters

    Returns:
        LLMResponse

    Example:
        response = generate("Write a haiku")
        print(response.content)
    """
    client = get_client(provider=provider, model=model)
    return client.generate(prompt, system_prompt=system_prompt, **kwargs)


# ==================== Public API ====================

__all__ = [
    # Factory
    "get_client",
    "get_openai_client",
    "get_anthropic_client",
    "generate",
    # Clients
    "BaseLLMClient",
    "OpenAIClient",
    "AnthropicClient",
    # Models
    "LLMProvider",
    "ResponseFormat",
    "TokenUsage",
    "LLMConfig",
    "LLMRequest",
    "LLMResponse",
    "LLM_PRICING",
    # Exceptions
    "LLMException",
    "LLMConnectionError",
    "LLMAuthenticationError",
    "LLMRateLimitError",
    "LLMQuotaExceededError",
    "LLMValidationError",
    "LLMContentFilterError",
    "LLMContextLengthError",
    "LLMModelNotFoundError",
    "LLMTimeoutError",
    "LLMConfigurationError",
    # Utilities
    "CostTracker",
    "UsageRecord",
    "estimate_tokens",
    "truncate_to_tokens",
    "count_messages_tokens",
    "format_system_prompt",
    "build_few_shot_prompt",
]

__version__ = "1.0.0"
