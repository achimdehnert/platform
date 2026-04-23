"""LLM client for docs-agent — talks to llm_mcp HTTP gateway.

Supports both the llm_mcp HTTP gateway (production) and direct
OpenAI/Anthropic API calls (standalone mode).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM backend."""

    gateway_url: str = "http://localhost:8100" # noqa: hardcode
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 1000
    response_format: str = "json"
    api_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> LLMConfig:
        """Create config from environment variables."""
        return cls(
            gateway_url=os.environ.get(
                "DOCS_AGENT_LLM_URL", "http://localhost:8100" # noqa: hardcode
            ),
            model=os.environ.get(
                "DOCS_AGENT_LLM_MODEL", "gpt-4o-mini"
            ),
            api_key=os.environ.get("OPENAI_API_KEY"),
        )


@dataclass
class LLMResponse:
    """Response from LLM call."""

    success: bool
    content: str | dict | list | None = None
    error: Optional[str] = None
    model_used: Optional[str] = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0


async def generate(
    prompt: str,
    *,
    system_prompt: Optional[str] = None,
    config: Optional[LLMConfig] = None,
) -> LLMResponse:
    """Generate text via LLM.

    Tries llm_mcp HTTP gateway first, falls back to direct OpenAI call.

    Args:
        prompt: User prompt.
        system_prompt: Optional system prompt.
        config: LLM configuration. Uses env defaults if None.

    Returns:
        LLMResponse with content or error.
    """
    if config is None:
        config = LLMConfig.from_env()

    # Try HTTP gateway first
    try:
        return await _call_gateway(prompt, system_prompt, config)
    except Exception as exc:
        logger.debug("Gateway unavailable: %s \u2014 trying direct API", exc)

    # Fallback: direct OpenAI call
    if config.api_key:
        try:
            return await _call_openai_direct(prompt, system_prompt, config)
        except Exception as exc:
            logger.error("Direct OpenAI call failed: %s", exc)
            return LLMResponse(success=False, error=str(exc))

    return LLMResponse(
        success=False,
        error="No LLM backend available (gateway down, no API key)",
    )


async def _call_gateway(
    prompt: str,
    system_prompt: Optional[str],
    config: LLMConfig,
) -> LLMResponse:
    """Call llm_mcp HTTP gateway."""
    import httpx

    payload: dict[str, Any] = {
        "prompt": prompt,
        "model": config.model,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "response_format": config.response_format,
    }
    if system_prompt:
        payload["system_prompt"] = system_prompt

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{config.gateway_url}/generate",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    if data.get("success"):
        usage = data.get("usage", {})
        return LLMResponse(
            success=True,
            content=data.get("content"),
            model_used=data.get("model_used"),
            tokens_in=usage.get("tokens_in", 0),
            tokens_out=usage.get("tokens_out", 0),
            cost=data.get("cost_estimate", 0.0),
        )

    return LLMResponse(
        success=False,
        error=data.get("error", "Unknown gateway error"),
    )


async def _call_openai_direct(
    prompt: str,
    system_prompt: Optional[str],
    config: LLMConfig,
) -> LLMResponse:
    """Direct OpenAI API call (fallback)."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=config.api_key)

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    kwargs: dict[str, Any] = {
        "model": config.model,
        "messages": messages,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    if config.response_format == "json" and "gpt-4" in config.model:
        kwargs["response_format"] = {"type": "json_object"}

    response = await client.chat.completions.create(**kwargs)

    content = response.choices[0].message.content or ""
    parsed: str | dict | list = content
    if config.response_format == "json":
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            pass

    usage = response.usage
    return LLMResponse(
        success=True,
        content=parsed,
        model_used=config.model,
        tokens_in=usage.prompt_tokens if usage else 0,
        tokens_out=usage.completion_tokens if usage else 0,
    )
