"""
Anthropic LLM Client
====================

LLM client for Anthropic API (Claude models).

Usage:
    from apps.core.services.llm import AnthropicClient

    client = AnthropicClient(api_key="sk-ant-...")
    response = client.generate("Hello, Claude!")
"""

import json
import logging
import time
from typing import Any, Dict, Generator, Optional, Type, TypeVar

from .base import BaseLLMClient
from .exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMContentFilterError,
    LLMContextLengthError,
    LLMException,
    LLMRateLimitError,
    LLMValidationError,
)
from .models import LLMConfig, LLMRequest, LLMResponse, ResponseFormat, TokenUsage

# Try to import Pydantic
try:
    from pydantic import BaseModel

    PYDANTIC_AVAILABLE = True
except ImportError:
    BaseModel = None
    PYDANTIC_AVAILABLE = False

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="BaseModel")


class AnthropicClient(BaseLLMClient):
    """
    Anthropic API client for Claude models.

    Supports:
    - Messages API (Claude 3+)
    - Tool use / function calling
    - Structured outputs
    - Streaming

    Example:
        client = AnthropicClient(api_key="sk-ant-...")
        response = client.generate(
            prompt="Explain quantum computing",
            system_prompt="You are a physics teacher"
        )
    """

    provider = "anthropic"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, **kwargs):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key
            model: Model name (default: claude-3-5-sonnet-20241022)
            **kwargs: Additional config options
        """
        config = LLMConfig(
            provider="anthropic",
            api_key=api_key,
            model=model or "claude-3-5-sonnet-20241022",
            api_endpoint="https://api.anthropic.com",
            **{k: v for k, v in kwargs.items() if hasattr(LLMConfig, k)},
        )
        super().__init__(config, **kwargs)

    def _init_client(self) -> None:
        """Initialize Anthropic client."""
        # Try to get API key from Django settings if not provided
        if not self.config.api_key:
            try:
                from django.conf import settings

                self.config.api_key = getattr(settings, "ANTHROPIC_API_KEY", None)
            except Exception:
                pass

        if not self.config.api_key:
            self.logger.warning("No Anthropic API key configured")

        # Try to use official SDK if available
        try:
            from anthropic import Anthropic

            self._client = Anthropic(api_key=self.config.api_key)
            self._use_sdk = True
            self.logger.debug("Using Anthropic SDK")

        except ImportError:
            self._client = None
            self._use_sdk = False
            self.logger.debug("Anthropic SDK not available, using HTTP")

    def _generate(self, request: LLMRequest) -> LLMResponse:
        """Generate using Anthropic API."""
        if self._use_sdk:
            return self._generate_sdk(request)
        else:
            return self._generate_http(request)

    def _generate_sdk(self, request: LLMRequest) -> LLMResponse:
        """Generate using Anthropic SDK."""
        start_time = time.perf_counter()

        try:
            # Build messages - Anthropic doesn't use system in messages
            messages = []
            for msg in request.to_messages():
                if msg["role"] != "system":
                    messages.append(msg)

            # Build request kwargs
            kwargs = {
                "model": self.config.effective_model,
                "messages": messages,
                "max_tokens": request.max_tokens or self.config.default_max_tokens,
            }

            # Add system prompt
            if request.system_prompt:
                kwargs["system"] = request.system_prompt

            # Add temperature (only if not 1.0, which is default)
            if request.temperature is not None:
                kwargs["temperature"] = request.temperature

            if request.top_p is not None:
                kwargs["top_p"] = request.top_p

            if request.stop:
                kwargs["stop_sequences"] = request.stop

            # Handle structured output using tools
            if request.response_format == ResponseFormat.STRUCTURED and request.response_schema:
                return self._generate_structured_sdk(request, kwargs, start_time)

            # Make request
            response = self._client.messages.create(**kwargs)

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # Extract content
            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text

            # Build usage
            usage = TokenUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )

            return LLMResponse.success_response(
                content=content,
                usage=usage,
                model=response.model,
                finish_reason=response.stop_reason,
                latency_ms=latency_ms,
                raw_response={"id": response.id},
            )

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return self._handle_error(e, latency_ms)

    def _generate_structured_sdk(
        self, request: LLMRequest, kwargs: Dict[str, Any], start_time: float
    ) -> LLMResponse:
        """Generate structured output using tool use."""
        schema = request.response_schema

        # Create tool definition
        tool = {
            "name": "generate_response",
            "description": f"Generate {schema.__name__}",
            "input_schema": schema.model_json_schema(),
        }

        kwargs["tools"] = [tool]
        kwargs["tool_choice"] = {"type": "tool", "name": "generate_response"}

        # Make request
        response = self._client.messages.create(**kwargs)

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Extract tool use
        tool_use = None
        for block in response.content:
            if hasattr(block, "type") and block.type == "tool_use":
                tool_use = block
                break

        if tool_use:
            arguments = tool_use.input

            # Validate with Pydantic
            try:
                validated = schema.model_validate(arguments)

                usage = TokenUsage(
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                    total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                )

                result = LLMResponse.success_response(
                    content=json.dumps(arguments),
                    usage=usage,
                    model=response.model,
                    finish_reason=response.stop_reason,
                    latency_ms=latency_ms,
                )
                result.structured_output = validated
                return result

            except Exception as e:
                raise LLMValidationError(
                    f"Structured output validation failed: {e}", content=json.dumps(arguments)
                )
        else:
            # No tool use, try to parse text content
            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text

            raise LLMValidationError("No structured output returned from tool use", content=content)

    def _generate_http(self, request: LLMRequest) -> LLMResponse:
        """Generate using HTTP requests (no SDK)."""
        import requests as http_requests

        start_time = time.perf_counter()

        url = f"{self.config.effective_endpoint}/v1/messages"

        # Build messages
        messages = []
        system_content = request.system_prompt or ""

        for msg in request.to_messages():
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                messages.append(
                    {"role": msg["role"], "content": [{"type": "text", "text": msg["content"]}]}
                )

        # Build payload
        payload = {
            "model": self.config.effective_model,
            "messages": messages,
            "max_tokens": request.max_tokens or self.config.default_max_tokens,
        }

        if system_content:
            payload["system"] = system_content

        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p

        # Make request
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
        }

        try:
            response = http_requests.post(
                url, headers=headers, json=payload, timeout=self.config.timeout
            )

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            if response.status_code >= 400:
                return self._handle_http_error(response, latency_ms)

            data = response.json()

            # Extract content
            content = ""
            for block in data.get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    content += block.get("text", "")

            # Build usage
            usage_data = data.get("usage", {})
            usage = TokenUsage(
                prompt_tokens=usage_data.get("input_tokens", 0),
                completion_tokens=usage_data.get("output_tokens", 0),
                total_tokens=usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0),
            )

            return LLMResponse.success_response(
                content=content,
                usage=usage,
                model=data.get("model"),
                finish_reason=data.get("stop_reason"),
                latency_ms=latency_ms,
                raw_response=data,
            )

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return self._handle_error(e, latency_ms)

    def _generate_stream(self, request: LLMRequest) -> Generator[str, None, None]:
        """Stream generation."""
        if not self._use_sdk:
            # Fallback to non-streaming
            response = self._generate(request)
            if response.success and response.content:
                yield response.content
            return

        messages = []
        for msg in request.to_messages():
            if msg["role"] != "system":
                messages.append(msg)

        kwargs = {
            "model": self.config.effective_model,
            "messages": messages,
            "max_tokens": request.max_tokens or self.config.default_max_tokens,
        }

        if request.system_prompt:
            kwargs["system"] = request.system_prompt
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature

        try:
            with self._client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    yield text

        except Exception as e:
            self.logger.error(f"Streaming error: {e}")

    def _handle_error(self, error: Exception, latency_ms: int) -> LLMResponse:
        """Convert exception to LLMResponse."""
        error_str = str(error).lower()

        if "rate_limit" in error_str or "overloaded" in error_str:
            raise LLMRateLimitError(
                f"Rate limit exceeded: {error}", provider=self.provider, original_error=error
            )
        elif "authentication" in error_str or "api_key" in error_str or "invalid" in error_str:
            raise LLMAuthenticationError(
                f"Authentication failed: {error}", provider=self.provider, original_error=error
            )
        elif "context" in error_str or "token" in error_str:
            raise LLMContextLengthError(
                f"Context length exceeded: {error}", provider=self.provider, original_error=error
            )
        elif "connection" in error_str or "timeout" in error_str:
            raise LLMConnectionError(
                f"Connection error: {error}", provider=self.provider, original_error=error
            )

        return LLMResponse.error_response(error=str(error), latency_ms=latency_ms)

    def _handle_http_error(self, response, latency_ms: int) -> LLMResponse:
        """Handle HTTP error response."""
        try:
            data = response.json()
            error_message = data.get("error", {}).get("message", str(data))
        except Exception:
            error_message = response.text

        if response.status_code == 429:
            raise LLMRateLimitError(f"Rate limit exceeded: {error_message}", provider=self.provider)
        elif response.status_code == 401:
            raise LLMAuthenticationError(
                f"Authentication failed: {error_message}", provider=self.provider
            )

        return LLMResponse.error_response(
            error=f"HTTP {response.status_code}: {error_message}", latency_ms=latency_ms
        )
