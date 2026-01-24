"""
LLM Service Models & Types
==========================

Data models for LLM requests, responses, and configuration.

Usage:
    from apps.core.services.llm import (
        LLMRequest,
        LLMResponse,
        LLMConfig,
        TokenUsage
    )
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type

# Try to import Pydantic
try:
    from pydantic import BaseModel

    PYDANTIC_AVAILABLE = True
except ImportError:
    BaseModel = None
    PYDANTIC_AVAILABLE = False


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    LOCAL = "local"
    CUSTOM = "custom"


class ResponseFormat(str, Enum):
    """Response format options."""

    TEXT = "text"
    JSON = "json"
    STRUCTURED = "structured"


@dataclass
class TokenUsage:
    """Token usage statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    # Aliases for Anthropic compatibility
    @property
    def input_tokens(self) -> int:
        return self.prompt_tokens

    @property
    def output_tokens(self) -> int:
        return self.completion_tokens

    def to_dict(self) -> Dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "input_tokens": self.prompt_tokens,
            "output_tokens": self.completion_tokens,
        }


@dataclass
class LLMConfig:
    """
    LLM client configuration.

    Attributes:
        provider: LLM provider (openai, anthropic, etc.)
        api_key: API key for authentication
        api_endpoint: Custom API endpoint (optional)
        model: Model name
        default_temperature: Default temperature
        default_max_tokens: Default max tokens
        timeout: Request timeout in seconds
        retry_count: Number of retries on failure
        retry_delay: Delay between retries in seconds
    """

    provider: str = "openai"
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    model: Optional[str] = None
    default_temperature: float = 0.7
    default_max_tokens: int = 4096
    timeout: int = 120
    retry_count: int = 3
    retry_delay: float = 1.0

    # Provider-specific defaults
    @property
    def effective_model(self) -> str:
        """Get model with provider-specific defaults."""
        if self.model:
            return self.model

        defaults = {
            "openai": "gpt-4",
            "anthropic": "claude-3-5-sonnet-20241022",
            "google": "gemini-pro",
            "azure": "gpt-4",
        }
        return defaults.get(self.provider, "gpt-4")

    @property
    def effective_endpoint(self) -> str:
        """Get API endpoint with provider-specific defaults."""
        if self.api_endpoint:
            return self.api_endpoint

        defaults = {
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com",
            "google": "https://generativelanguage.googleapis.com/v1beta",
        }
        return defaults.get(self.provider, "")


@dataclass
class LLMRequest:
    """
    LLM generation request.

    Attributes:
        prompt: User prompt text
        system_prompt: System/instruction prompt
        messages: Alternative to prompt - list of message dicts
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum tokens to generate
        top_p: Nucleus sampling parameter
        frequency_penalty: Frequency penalty (OpenAI)
        presence_penalty: Presence penalty (OpenAI)
        stop: Stop sequences
        response_format: Expected response format
        response_schema: Pydantic model for structured output
        stream: Whether to stream response
        metadata: Additional request metadata
    """

    prompt: str
    system_prompt: Optional[str] = None
    messages: Optional[List[Dict[str, str]]] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[List[str]] = None
    response_format: ResponseFormat = ResponseFormat.TEXT
    response_schema: Optional[Type] = None  # Pydantic model
    stream: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_messages(self) -> List[Dict[str, str]]:
        """Convert to messages format."""
        if self.messages:
            return self.messages

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": self.prompt})
        return messages


@dataclass
class LLMResponse:
    """
    LLM generation response.

    Attributes:
        success: Whether generation succeeded
        content: Generated text content
        structured_output: Pydantic model instance (if structured)
        usage: Token usage statistics
        model: Model used
        finish_reason: Why generation stopped
        latency_ms: Request latency in milliseconds
        raw_response: Raw API response
        error: Error message if failed
    """

    success: bool
    content: Optional[str] = None
    structured_output: Optional[Any] = None
    usage: Optional[TokenUsage] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None
    latency_ms: Optional[int] = None
    raw_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "content": self.content,
            "usage": self.usage.to_dict() if self.usage else None,
            "model": self.model,
            "finish_reason": self.finish_reason,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }

    @classmethod
    def error_response(cls, error: str, latency_ms: int = None) -> "LLMResponse":
        """Create an error response."""
        return cls(success=False, error=error, latency_ms=latency_ms)

    @classmethod
    def success_response(
        cls,
        content: str,
        usage: TokenUsage = None,
        model: str = None,
        finish_reason: str = None,
        latency_ms: int = None,
        raw_response: Dict = None,
    ) -> "LLMResponse":
        """Create a success response."""
        return cls(
            success=True,
            content=content,
            usage=usage,
            model=model,
            finish_reason=finish_reason,
            latency_ms=latency_ms,
            raw_response=raw_response,
        )


# ==================== Structured Output Schema ====================

if PYDANTIC_AVAILABLE:

    class PromptResponse(BaseModel):
        """Default structured response schema."""

        content: str
        reasoning: Optional[str] = None
        confidence: Optional[float] = None

else:
    PromptResponse = None


# ==================== Cost Pricing ====================

# Pricing per 1000 tokens (as of 2024, update as needed)
LLM_PRICING = {
    "openai": {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "o1-preview": {"input": 0.015, "output": 0.06},
        "o1-mini": {"input": 0.003, "output": 0.012},
    },
    "anthropic": {
        "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
        "claude-3-5-opus-20240229": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
        "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    },
    "google": {
        "gemini-pro": {"input": 0.00025, "output": 0.0005},
        "gemini-1.5-pro": {"input": 0.0035, "output": 0.0105},
        "gemini-1.5-flash": {"input": 0.00035, "output": 0.00105},
    },
}
