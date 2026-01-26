"""Unified LLM client supporting multiple providers."""

import os
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


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


class LLMResponse(BaseModel):
    """Standardized LLM response."""
    
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
