"""
OpenAI LLM Client
=================

LLM client for OpenAI API (GPT-4, GPT-3.5, etc.).
Also supports OpenAI-compatible APIs (Azure, local proxies).

Usage:
    from apps.core.services.llm import OpenAIClient

    client = OpenAIClient(api_key="sk-...")
    response = client.generate("Hello, world!")
"""

import json
import logging
import time
from typing import Any, Dict, Generator, Optional, Type, TypeVar

from .base import BaseLLMClient
from .exceptions import (
    LLMAuthenticationError,
    LLMConfigurationError,
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


class OpenAIClient(BaseLLMClient):
    """
    OpenAI API client.

    Supports:
    - Chat completions (GPT-4, GPT-3.5)
    - Function calling / tool use
    - Structured outputs (JSON mode)
    - Streaming

    Also works with OpenAI-compatible APIs:
    - Azure OpenAI
    - Local proxies (vLLM, Ollama)
    - Together AI, Anyscale, etc.

    Example:
        # Standard OpenAI
        client = OpenAIClient(api_key="sk-...")

        # Azure OpenAI
        client = OpenAIClient(
            api_key="...",
            api_endpoint="https://my-resource.openai.azure.com",
            model="gpt-4"
        )

        # Local Ollama
        client = OpenAIClient(
            api_endpoint="http://localhost:11434/v1",
            model="llama2"
        )
    """

    provider = "openai"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4)
            api_endpoint: Custom API endpoint
            **kwargs: Additional config options
        """
        config = LLMConfig(
            provider="openai",
            api_key=api_key,
            model=model,
            api_endpoint=api_endpoint,
            **{k: v for k, v in kwargs.items() if hasattr(LLMConfig, k)},
        )
        super().__init__(config, **kwargs)

    def _init_client(self) -> None:
        """Initialize OpenAI client."""
        # Try to get API key from Django settings if not provided
        if not self.config.api_key:
            try:
                from django.conf import settings

                self.config.api_key = getattr(settings, "OPENAI_API_KEY", None)
            except Exception:
                pass

        if not self.config.api_key:
            self.logger.warning("No OpenAI API key configured")

        # Try to use official SDK if available
        try:
            from openai import OpenAI

            client_kwargs = {}
            if self.config.api_key:
                client_kwargs["api_key"] = self.config.api_key
            if self.config.api_endpoint:
                client_kwargs["base_url"] = self.config.api_endpoint

            self._client = OpenAI(**client_kwargs)
            self._use_sdk = True
            self.logger.debug("Using OpenAI SDK")

        except ImportError:
            self._client = None
            self._use_sdk = False
            self.logger.debug("OpenAI SDK not available, using HTTP")

    def _generate(self, request: LLMRequest) -> LLMResponse:
        """Generate using OpenAI API."""
        if self._use_sdk:
            return self._generate_sdk(request)
        else:
            return self._generate_http(request)

    def _generate_sdk(self, request: LLMRequest) -> LLMResponse:
        """Generate using OpenAI SDK."""
        start_time = time.perf_counter()

        try:
            # Build messages
            messages = request.to_messages()

            # Build request kwargs
            kwargs = {
                "model": self.config.effective_model,
                "messages": messages,
                "temperature": request.temperature or self.config.default_temperature,
                "max_tokens": request.max_tokens or self.config.default_max_tokens,
            }

            if request.top_p is not None:
                kwargs["top_p"] = request.top_p
            if request.frequency_penalty is not None:
                kwargs["frequency_penalty"] = request.frequency_penalty
            if request.presence_penalty is not None:
                kwargs["presence_penalty"] = request.presence_penalty
            if request.stop:
                kwargs["stop"] = request.stop

            # Handle structured output
            if request.response_format == ResponseFormat.STRUCTURED and request.response_schema:
                return self._generate_structured_sdk(request, kwargs, start_time)
            elif request.response_format == ResponseFormat.JSON:
                kwargs["response_format"] = {"type": "json_object"}

            # Make request
            response = self._client.chat.completions.create(**kwargs)

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # Extract content
            content = response.choices[0].message.content

            # Build usage
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

            return LLMResponse.success_response(
                content=content,
                usage=usage,
                model=response.model,
                finish_reason=response.choices[0].finish_reason,
                latency_ms=latency_ms,
                raw_response={"id": response.id},
            )

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return self._handle_error(e, latency_ms)

    def _generate_structured_sdk(
        self, request: LLMRequest, kwargs: Dict[str, Any], start_time: float
    ) -> LLMResponse:
        """Generate structured output using function calling."""
        schema = request.response_schema

        # Create function/tool definition
        function = {
            "name": "generate_response",
            "description": f"Generate {schema.__name__}",
            "parameters": schema.model_json_schema(),
        }

        kwargs["tools"] = [{"type": "function", "function": function}]
        kwargs["tool_choice"] = {"type": "function", "function": {"name": "generate_response"}}

        # Make request
        response = self._client.chat.completions.create(**kwargs)

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Extract tool call
        message = response.choices[0].message
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            arguments = json.loads(tool_call.function.arguments)

            # Validate with Pydantic
            try:
                validated = schema.model_validate(arguments)

                usage = TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                )

                result = LLMResponse.success_response(
                    content=json.dumps(arguments),
                    usage=usage,
                    model=response.model,
                    finish_reason=response.choices[0].finish_reason,
                    latency_ms=latency_ms,
                )
                result.structured_output = validated
                return result

            except Exception as e:
                raise LLMValidationError(
                    f"Structured output validation failed: {e}", content=json.dumps(arguments)
                )
        else:
            raise LLMValidationError("No structured output returned", content=message.content)

    def _generate_http(self, request: LLMRequest) -> LLMResponse:
        """Generate using HTTP requests (no SDK)."""
        import requests as http_requests

        start_time = time.perf_counter()

        # Build URL
        url = self.config.effective_endpoint
        if not url.endswith("/chat/completions"):
            if "/v1/" not in url:
                url = f"{url}/v1/chat/completions"
            else:
                url = f"{url}/chat/completions"

        # Build payload
        payload = {
            "model": self.config.effective_model,
            "messages": request.to_messages(),
            "temperature": request.temperature or self.config.default_temperature,
            "max_tokens": request.max_tokens or self.config.default_max_tokens,
        }

        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.response_format == ResponseFormat.JSON:
            payload["response_format"] = {"type": "json_object"}

        # Make request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
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
            content = data["choices"][0]["message"]["content"]

            # Build usage
            usage_data = data.get("usage", {})
            usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            return LLMResponse.success_response(
                content=content,
                usage=usage,
                model=data.get("model"),
                finish_reason=data["choices"][0].get("finish_reason"),
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

        messages = request.to_messages()

        kwargs = {
            "model": self.config.effective_model,
            "messages": messages,
            "temperature": request.temperature or self.config.default_temperature,
            "max_tokens": request.max_tokens or self.config.default_max_tokens,
            "stream": True,
        }

        try:
            stream = self._client.chat.completions.create(**kwargs)

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            self.logger.error(f"Streaming error: {e}")

    def _handle_error(self, error: Exception, latency_ms: int) -> LLMResponse:
        """Convert exception to LLMResponse."""
        error_str = str(error)

        # Try to extract OpenAI error types
        if "rate_limit" in error_str.lower():
            raise LLMRateLimitError(
                f"Rate limit exceeded: {error}", provider=self.provider, original_error=error
            )
        elif "authentication" in error_str.lower() or "invalid_api_key" in error_str.lower():
            raise LLMAuthenticationError(
                f"Authentication failed: {error}", provider=self.provider, original_error=error
            )
        elif "context_length" in error_str.lower():
            raise LLMContextLengthError(
                f"Context length exceeded: {error}", provider=self.provider, original_error=error
            )
        elif "content_filter" in error_str.lower():
            raise LLMContentFilterError(
                f"Content filtered: {error}", provider=self.provider, original_error=error
            )
        elif "connection" in error_str.lower() or "timeout" in error_str.lower():
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
