"""Unified LLM client supporting multiple providers.

Provides two APIs:
- generate(prompt, system_prompt): Simple text completion (httpx-based)
- complete(messages, tools, tool_choice): Messages API with tool-use (SDK-based)

The complete() method requires optional SDK dependencies:
    pip install creative-services[anthropic]  # for Anthropic
    pip install creative-services[openai]     # for OpenAI/Groq
    pip install creative-services[all]        # both
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    OLLAMA = "ollama"


class LLMConfig(BaseModel):
    """Configuration for LLM client."""
    
    provider: LLMProvider = Field(default=LLMProvider.OPENAI)
    model: str = Field(default="gpt-4o-mini")
    api_key: Optional[str] = Field(default=None)
    base_url: Optional[str] = Field(default=None)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=1)
    timeout: float = Field(default=120.0)
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.api_key is None:
            self._load_api_key_from_env()
    
    def _load_api_key_from_env(self):
        """Load API key from environment based on provider."""
        env_vars = {
            LLMProvider.OPENAI: "OPENAI_API_KEY",
            LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            LLMProvider.GROQ: "GROQ_API_KEY",
        }
        if self.provider in env_vars:
            self.api_key = os.getenv(env_vars[self.provider])


@dataclass(frozen=True)
class ToolCall:
    """Single tool call from an LLM response."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class CompletionResponse:
    """Response from complete() with optional tool calls.

    Returned by LLMClient.complete() and DynamicLLMClient.complete().
    Supports both text-only and tool-use responses.
    """

    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    provider: "LLMProvider" = None  # type: ignore[assignment]
    usage: dict[str, Any] = field(default_factory=dict)
    latency_ms: int = 0

    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return len(self.tool_calls) > 0

    @property
    def total_tokens(self) -> int:
        """Get total tokens from usage dict."""
        return self.usage.get("total_tokens", 0) or (
            self.usage.get("prompt_tokens", 0)
            + self.usage.get("completion_tokens", 0)
        )

    @property
    def first_tool_call(self) -> ToolCall | None:
        """Get first tool call, or None."""
        return self.tool_calls[0] if self.tool_calls else None


class LLMResponse(BaseModel):
    """Standardized LLM response (for generate() API)."""
    
    content: str
    model: str
    provider: LLMProvider
    usage: dict[str, Any] = Field(default_factory=dict)  # Allow nested dicts from OpenAI API
    raw_response: Optional[dict[str, Any]] = None
    
    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self.usage.get('total_tokens', 0) or (
            self.usage.get('prompt_tokens', 0) + self.usage.get('completion_tokens', 0)
        )


class LLMClient:
    """Unified client for multiple LLM providers."""
    
    # Provider-specific default models
    DEFAULT_MODELS = {
        LLMProvider.OPENAI: "gpt-4o-mini",
        LLMProvider.ANTHROPIC: "claude-3-5-sonnet-20241022",
        LLMProvider.GROQ: "llama-3.3-70b-versatile",
        LLMProvider.OLLAMA: "llama3.2",
    }
    
    # Provider-specific base URLs
    BASE_URLS = {
        LLMProvider.OPENAI: "https://api.openai.com/v1",
        LLMProvider.ANTHROPIC: "https://api.anthropic.com/v1",
        LLMProvider.GROQ: "https://api.groq.com/openai/v1",
        LLMProvider.OLLAMA: "http://localhost:11434/api",
    }
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._client = httpx.AsyncClient(timeout=self.config.timeout)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.aclose()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate text from the configured LLM provider."""
        
        if self.config.provider == LLMProvider.ANTHROPIC:
            return await self._generate_anthropic(prompt, system_prompt, **kwargs)
        elif self.config.provider == LLMProvider.OLLAMA:
            return await self._generate_ollama(prompt, system_prompt, **kwargs)
        else:
            # OpenAI-compatible (OpenAI, Groq)
            return await self._generate_openai_compatible(prompt, system_prompt, **kwargs)
    
    async def _generate_openai_compatible(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate using OpenAI-compatible API (OpenAI, Groq)."""
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        base_url = self.config.base_url or self.BASE_URLS[self.config.provider]
        
        response = await self._client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.config.model,
                "messages": messages,
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            },
        )
        response.raise_for_status()
        data = response.json()
        
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data["model"],
            provider=self.config.provider,
            usage=data.get("usage", {}),
            raw_response=data,
        )
    
    async def _generate_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate using Anthropic API."""
        
        base_url = self.config.base_url or self.BASE_URLS[LLMProvider.ANTHROPIC]
        
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        response = await self._client.post(
            f"{base_url}/messages",
            headers={
                "x-api-key": self.config.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        
        return LLMResponse(
            content=data["content"][0]["text"],
            model=data["model"],
            provider=LLMProvider.ANTHROPIC,
            usage={
                "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                "output_tokens": data.get("usage", {}).get("output_tokens", 0),
            },
            raw_response=data,
        )
    
    async def _generate_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate using Ollama API."""
        
        base_url = self.config.base_url or self.BASE_URLS[LLMProvider.OLLAMA]
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = await self._client.post(
            f"{base_url}/generate",
            json={
                "model": self.config.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", self.config.temperature),
                },
            },
        )
        response.raise_for_status()
        data = response.json()
        
        return LLMResponse(
            content=data["response"],
            model=self.config.model,
            provider=LLMProvider.OLLAMA,
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
            raw_response=data,
        )
    
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
        **kwargs: Any,
    ) -> CompletionResponse:
        """Messages-based completion with tool-use support.

        Uses official SDKs (anthropic/openai) for native tool-use.
        Falls back to httpx if SDKs are not installed.

        Args:
            messages: Chat messages [{"role": "...", "content": "..."}].
            tools: Tool definitions (provider-native format).
            tool_choice: "auto", "none", or {"type": "function", ...}.
            **kwargs: Override temperature, max_tokens, etc.

        Returns:
            CompletionResponse with content and/or tool_calls.

        Raises:
            ImportError: If required SDK is not installed.
            httpx.HTTPStatusError: On API errors.
        """
        temperature = kwargs.get("temperature", self.config.temperature)
        max_tokens = kwargs.get("max_tokens", self.config.max_tokens)

        if self.config.provider == LLMProvider.ANTHROPIC:
            return await self._complete_anthropic(
                messages, tools, tool_choice, temperature, max_tokens,
            )
        elif self.config.provider in (LLMProvider.OPENAI, LLMProvider.GROQ):
            return await self._complete_openai_compatible(
                messages, tools, tool_choice, temperature, max_tokens,
            )
        else:
            raise ValueError(
                f"complete() not supported for provider {self.config.provider}. "
                f"Use generate() instead."
            )

    async def _complete_anthropic(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        tool_choice: str,
        temperature: float,
        max_tokens: int,
    ) -> CompletionResponse:
        """Complete using Anthropic SDK with tool-use support."""
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            raise ImportError(
                "anthropic SDK required for complete(). "
                "Install: pip install creative-services[anthropic]"
            ) from exc

        start_time = time.perf_counter()
        api_key = self.config.api_key
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY")

        client = AsyncAnthropic(api_key=api_key)

        # Separate system prompt from messages (Anthropic pattern)
        system_prompt: str | None = None
        api_messages: list[dict[str, Any]] = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                api_messages.append(msg)

        request_kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system_prompt:
            request_kwargs["system"] = system_prompt

        if tools:
            # Convert OpenAI-style tools to Anthropic format if needed
            request_kwargs["tools"] = [
                self._to_anthropic_tool(t) for t in tools
            ]
            if tool_choice == "auto":
                request_kwargs["tool_choice"] = {"type": "auto"}
            elif tool_choice == "none":
                request_kwargs["tool_choice"] = {"type": "none"}
            elif tool_choice == "required":
                request_kwargs["tool_choice"] = {"type": "any"}
            else:
                request_kwargs["tool_choice"] = {"type": "auto"}

        response = await client.messages.create(**request_kwargs)
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Extract content and tool calls
        content_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if hasattr(block, "text"):
                content_parts.append(block.text)
            elif hasattr(block, "type") and block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    )
                )

        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": (
                response.usage.input_tokens + response.usage.output_tokens
            ),
        }

        return CompletionResponse(
            content="\n".join(content_parts) if content_parts else None,
            tool_calls=tool_calls,
            model=response.model,
            provider=LLMProvider.ANTHROPIC,
            usage=usage,
            latency_ms=latency_ms,
        )

    async def _complete_openai_compatible(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        tool_choice: str,
        temperature: float,
        max_tokens: int,
    ) -> CompletionResponse:
        """Complete using OpenAI SDK with tool-use support.

        Also works for Groq (OpenAI-compatible API).
        """
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError(
                "openai SDK required for complete(). "
                "Install: pip install creative-services[openai]"
            ) from exc

        start_time = time.perf_counter()
        api_key = self.config.api_key
        if not api_key:
            env_var = (
                "GROQ_API_KEY"
                if self.config.provider == LLMProvider.GROQ
                else "OPENAI_API_KEY"
            )
            api_key = os.getenv(env_var)

        base_url = self.config.base_url or self.BASE_URLS.get(
            self.config.provider
        )

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url and self.config.provider != LLMProvider.OPENAI:
            client_kwargs["base_url"] = base_url

        client = AsyncOpenAI(**client_kwargs)

        request_kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            # Ensure OpenAI format: [{"type": "function", "function": {...}}]
            request_kwargs["tools"] = [
                self._to_openai_tool(t) for t in tools
            ]
            if tool_choice == "auto":
                request_kwargs["tool_choice"] = "auto"
            elif tool_choice == "none":
                request_kwargs["tool_choice"] = "none"
            elif tool_choice == "required":
                request_kwargs["tool_choice"] = "required"
            else:
                request_kwargs["tool_choice"] = "auto"

        response = await client.chat.completions.create(**request_kwargs)
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Extract content and tool calls
        message = response.choices[0].message
        content = message.content
        tool_calls: list[ToolCall] = []

        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    )
                )

        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        return CompletionResponse(
            content=content,
            tool_calls=tool_calls,
            model=response.model,
            provider=self.config.provider,
            usage=usage,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _to_anthropic_tool(tool: dict[str, Any]) -> dict[str, Any]:
        """Normalize tool definition to Anthropic format.

        Accepts both Anthropic-native and OpenAI-style tool defs.
        """
        # Already Anthropic format: {"name": ..., "input_schema": ...}
        if "input_schema" in tool:
            return tool
        # OpenAI format: {"type": "function", "function": {"name": ..., "parameters": ...}}
        if "function" in tool:
            func = tool["function"]
            return {
                "name": func["name"],
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {}),
            }
        # Minimal format: {"name": ..., "parameters": ...}
        return {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "input_schema": tool.get("parameters", {}),
        }

    @staticmethod
    def _to_openai_tool(tool: dict[str, Any]) -> dict[str, Any]:
        """Normalize tool definition to OpenAI format.

        Accepts both OpenAI-native and Anthropic-style tool defs.
        """
        # Already OpenAI format
        if "type" in tool and tool["type"] == "function" and "function" in tool:
            return tool
        # Anthropic format: {"name": ..., "input_schema": ...}
        if "input_schema" in tool:
            return {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool["input_schema"],
                },
            }
        # Minimal format: {"name": ..., "parameters": ...}
        return {
            "type": "function",
            "function": {
                "name": tool.get("name", "unknown"),
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {}),
            },
        }

    @classmethod
    def for_provider(
        cls,
        provider: LLMProvider,
        model: Optional[str] = None,
        **kwargs,
    ) -> "LLMClient":
        """Factory method to create client for specific provider."""
        
        config = LLMConfig(
            provider=provider,
            model=model or cls.DEFAULT_MODELS.get(provider, "gpt-4o-mini"),
            **kwargs,
        )
        return cls(config)
