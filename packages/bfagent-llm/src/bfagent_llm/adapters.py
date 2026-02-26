"""
LLM Client Adapters
===================

Provides adapters for different LLM providers:
- GatewayLLMAdapter: BFAgent LLM Gateway
- OpenAILLMAdapter: Direct OpenAI API
- AnthropicLLMAdapter: Direct Anthropic API
- GroqLLMAdapter: Groq LPU-accelerated inference (ADR-084 v3)
- FallbackLLMAdapter: Chain with automatic fallback
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

from bfagent_llm.service import LLMClientProtocol, LLMResponse

logger = logging.getLogger(__name__)

# Groq model name mapping: short name → Groq API model ID
GROQ_MODEL_MAP: Dict[str, str] = {
    "qwen3-32b": "qwen/qwen3-32b",
    "gpt-oss-120b": "openai/gpt-oss-120b",
    "gpt-oss-20b": "openai/gpt-oss-20b",
    "llama-3.3-70b": "meta-llama/llama-3.3-70b-versatile",
    "llama-3.3-70b-versatile": "meta-llama/llama-3.3-70b-versatile",
    "llama-4-scout-17b": "meta-llama/llama-4-scout-17b-16e-instruct",
    "llama-3.1-8b": "meta-llama/llama-3.1-8b-instant",
    "llama-3.1-8b-instant": "meta-llama/llama-3.1-8b-instant",
    "compound": "groq/compound",
    "compound-mini": "groq/compound-mini",
    "kimi-k2": "moonshotai/kimi-k2-instruct-0905",
}


class GatewayLLMAdapter(LLMClientProtocol):
    """
    Adapter for BFAgent LLM Gateway.
    
    The gateway provides a unified API for multiple LLM providers
    with built-in rate limiting, caching, and fallback.
    
    Usage:
        adapter = GatewayLLMAdapter(base_url="http://llm-gateway:8100")
        response = await adapter.complete(messages, model="gpt-4o-mini", ...)
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8100",  # noqa: hardcode
        timeout: float = 120.0,
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key
        self._client: Optional[Any] = None
    
    async def _get_client(self):
        """Get or create httpx client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> LLMResponse:
        """Execute completion via gateway."""
        client = await self._get_client()
        
        payload = {
            "prompt": messages[-1]["content"] if messages else "",
            "system_prompt": next(
                (m["content"] for m in messages if m["role"] == "system"),
                "",
            ),
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        response = await client.post(
            f"{self.base_url}/generate",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        
        data = response.json()
        
        return LLMResponse(
            content=data.get("content", ""),
            model=data.get("model", model),
            tokens_in=data.get("usage", {}).get("prompt_tokens", 0),
            tokens_out=data.get("usage", {}).get("completion_tokens", 0),
            raw_response=data,
        )
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


class OpenAILLMAdapter(LLMClientProtocol):
    """
    Adapter for direct OpenAI API access.
    
    Usage:
        adapter = OpenAILLMAdapter(api_key="sk-...")
        response = await adapter.complete(messages, model="gpt-4o-mini", ...)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        organization: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key
        self.organization = organization
        self.base_url = base_url
        self._client: Optional[Any] = None
    
    def _get_client(self):
        """Get or create OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError(
                    "openai package required. Install with: pip install openai"
                )
            
            kwargs = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.organization:
                kwargs["organization"] = self.organization
            if self.base_url:
                kwargs["base_url"] = self.base_url
            
            self._client = AsyncOpenAI(**kwargs)
        
        return self._client
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> LLMResponse:
        """Execute completion via OpenAI API."""
        client = self._get_client()
        
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        
        choice = response.choices[0]
        usage = response.usage
        
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            tokens_in=usage.prompt_tokens if usage else 0,
            tokens_out=usage.completion_tokens if usage else 0,
            raw_response=response.model_dump(),
        )


class AnthropicLLMAdapter(LLMClientProtocol):
    """
    Adapter for direct Anthropic API access.
    
    Usage:
        adapter = AnthropicLLMAdapter(api_key="sk-ant-...")
        response = await adapter.complete(messages, model="claude-3-sonnet", ...)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self._client: Optional[Any] = None
    
    def _get_client(self):
        """Get or create Anthropic client."""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError:
                raise ImportError(
                    "anthropic package required. Install with: pip install anthropic"
                )
            
            kwargs = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.base_url:
                kwargs["base_url"] = self.base_url
            
            self._client = AsyncAnthropic(**kwargs)
        
        return self._client
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> LLMResponse:
        """Execute completion via Anthropic API."""
        client = self._get_client()
        
        system = next(
            (m["content"] for m in messages if m["role"] == "system"),
            "",
        )
        
        chat_messages = [
            m for m in messages if m["role"] in ("user", "assistant")
        ]
        
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=chat_messages,
            **kwargs,
        )
        
        content = ""
        if response.content:
            content = response.content[0].text if response.content else ""
        
        return LLMResponse(
            content=content,
            model=response.model,
            tokens_in=response.usage.input_tokens if response.usage else 0,
            tokens_out=response.usage.output_tokens if response.usage else 0,
            raw_response=response.model_dump(),
        )


class GroqLLMAdapter(LLMClientProtocol):
    """
    Adapter for Groq LPU-accelerated inference (ADR-084 v3).

    Groq provides an OpenAI-compatible API with ultra-fast inference
    on custom LPU hardware. Developer tier is free ($0 per token).

    Supported models (via GROQ_MODEL_MAP):
      - qwen/qwen3-32b (best coding)
      - openai/gpt-oss-120b (largest reasoning)
      - meta-llama/llama-3.3-70b-versatile (proven workhorse)
      - meta-llama/llama-3.1-8b-instant (ultra-fast)
      - groq/compound, groq/compound-mini (agentic)
      - moonshotai/kimi-k2-instruct-0905 (MoE)

    Usage:
        adapter = GroqLLMAdapter(api_key="gsk_...")
        response = await adapter.complete(
            messages, model="qwen3-32b", ...
        )
    """

    GROQ_BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self._client: Optional[Any] = None

    def _resolve_model(self, model: str) -> str:
        """Resolve short name to full Groq model ID."""
        if model in GROQ_MODEL_MAP:
            return GROQ_MODEL_MAP[model]
        if "/" in model:
            return model
        return model

    def _get_client(self):
        """Get or create OpenAI client pointed at Groq."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError(
                    "openai package required. "
                    "Install with: pip install openai"
                )

            if not self.api_key:
                raise ValueError(
                    "Groq API key required. Set GROQ_API_KEY env var "
                    "or pass api_key to GroqLLMAdapter."
                )

            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.GROQ_BASE_URL,
            )

        return self._client

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> LLMResponse:
        """Execute completion via Groq API."""
        client = self._get_client()
        resolved_model = self._resolve_model(model)

        response = await client.chat.completions.create(
            model=resolved_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            tokens_in=usage.prompt_tokens if usage else 0,
            tokens_out=usage.completion_tokens if usage else 0,
            cost=Decimal("0"),  # Groq developer tier = free
            raw_response=response.model_dump(),
        )


class FallbackLLMAdapter(LLMClientProtocol):
    """
    Adapter that chains multiple adapters with automatic fallback.
    
    Usage:
        adapter = FallbackLLMAdapter([
            GroqLLMAdapter(api_key="gsk_..."),
            OpenAILLMAdapter(api_key="sk-..."),
        ])
        response = await adapter.complete(messages, model="gpt-4o-mini", ...)
    """
    
    def __init__(self, adapters: List[LLMClientProtocol]):
        if not adapters:
            raise ValueError("At least one adapter required")
        self.adapters = adapters
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> LLMResponse:
        """Execute completion with fallback."""
        last_error = None
        
        for i, adapter in enumerate(self.adapters):
            try:
                return await adapter.complete(
                    messages=messages,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs,
                )
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Adapter {i} ({type(adapter).__name__}) failed: {e}"
                )
                continue
        
        raise last_error or RuntimeError("All adapters failed")
