"""
DB-driven LLM completion service (ADR-089).

Provides:
- completion(): Async DB-driven completion via LiteLLM
- sync_completion(): Sync wrapper
- completion_with_fallback(): Tries default, then fallback model

Invariants:
- All calls go through DB lookup (AIActionType → LLMModel → LLMProvider)
- API keys resolved via read_secret() (ADR-045)
- No silent fallback: LLMConfigurationError if no model configured
- Every call logged in AIUsageLog
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    """Result of a DB-driven LLM completion."""

    content: str
    model: str
    provider: str
    action_code: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    cost: Decimal = field(default_factory=lambda: Decimal("0"))
    success: bool = True
    error: str = ""
    raw_response: Optional[dict] = None

    @property
    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out


def _get_api_key(provider) -> str:
    """Resolve API key via ADR-045 read_secret() pattern.

    Priority: /run/secrets/<key_lower> → os.environ[KEY] → Error.
    NEVER silently return empty string.
    """
    from bfagent_llm.django_app.models import LLMConfigurationError

    env_var = provider.api_key_env_var
    if not env_var:
        raise LLMConfigurationError(
            f"Provider '{provider.name}' hat kein api_key_env_var konfiguriert."
        )

    # ADR-045: try read_secret() first (/run/secrets/ priority)
    try:
        from config.secrets import read_secret

        value = read_secret(env_var, required=False)
        if value:
            return value
    except ImportError:
        pass

    # Fallback: os.environ (legacy, before SOPS migration)
    value = os.environ.get(env_var, "")
    if value:
        return value

    raise LLMConfigurationError(
        f"API-Key für Provider '{provider.name}' nicht gefunden. "
        f"Erwartet: /run/secrets/{env_var.lower()} oder env {env_var}."
    )


def _build_litellm_model_string(llm_model) -> str:
    """Build LiteLLM-compatible model string.

    LiteLLM format: 'provider/model' (e.g. 'openai/gpt-4o', 'groq/llama-3.3-70b').
    """
    provider_name = llm_model.provider.name
    model_name = llm_model.name

    # LiteLLM uses specific provider prefixes
    LITELLM_PROVIDER_MAP = {
        "openai": "openai",
        "anthropic": "anthropic",
        "groq": "groq",
        "google": "gemini",
        "mistral": "mistral",
        "cohere": "cohere",
        "ollama": "ollama",
        "vllm": "openai",  # vLLM uses OpenAI-compatible API
    }

    litellm_prefix = LITELLM_PROVIDER_MAP.get(provider_name, provider_name)
    return f"{litellm_prefix}/{model_name}"


def _log_usage(
    *,
    tenant_id: UUID | str,
    action_type,
    llm_model,
    user=None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    latency_ms: int = 0,
    success: bool = True,
    error_message: str = "",
) -> None:
    """Log LLM usage to AIUsageLog (fire-and-forget)."""
    try:
        from bfagent_llm.django_app.models import AIUsageLog

        AIUsageLog.objects.create(
            tenant_id=tenant_id,
            action_type=action_type,
            model_used=llm_model,
            user=user,
            input_tokens=tokens_in,
            output_tokens=tokens_out,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
        )
    except Exception as exc:
        logger.warning("Failed to log LLM usage: %s", exc)


async def completion(
    action_code: str,
    messages: list[dict[str, str]],
    tenant_id: UUID | str | None = None,
    tools: list[dict] | None = None,
    user: Any = None,
    **overrides: Any,
) -> LLMResult:
    """DB-driven completion via LiteLLM (ADR-089).

    1. AIActionType[tenant_id, code] → LLMModel → LLMProvider
    2. _build_litellm_model_string() → 'provider/model'
    3. _get_api_key() → ADR-045 read_secret()
    4. litellm.acompletion() → unified response
    5. AIUsageLog.create() → cost + usage tracking

    Args:
        action_code: Action identifier (e.g. 'character_generation')
        messages: Chat messages [{"role": "...", "content": "..."}]
        tenant_id: Tenant UUID (required for multi-tenant apps)
        tools: Optional tool definitions for function calling
        user: Optional Django user for usage attribution
        **overrides: Override max_tokens, temperature, model

    Returns:
        LLMResult with content, tokens, cost, latency

    Raises:
        LLMConfigurationError: No model configured for this action
    """
    from bfagent_llm.django_app.models import (
        AIActionType,
        LLMConfigurationError,
    )

    try:
        import litellm
    except ImportError:
        raise ImportError(
            "litellm package required. "
            "Install with: pip install bfagent-llm[django]"
        )

    # 1. DB Lookup
    lookup = {"code": action_code, "is_active": True}
    if tenant_id:
        lookup["tenant_id"] = tenant_id

    try:
        action = AIActionType.objects.select_related(
            "default_model__provider",
            "fallback_model__provider",
        ).get(**lookup)
    except AIActionType.DoesNotExist:
        raise LLMConfigurationError(
            f"AIActionType '{action_code}' nicht gefunden "
            f"(tenant_id={tenant_id})."
        )
    except AIActionType.MultipleObjectsReturned:
        raise LLMConfigurationError(
            f"Mehrere AIActionTypes '{action_code}' gefunden. "
            f"tenant_id muss angegeben werden."
        )

    # 2. Get model (explicit, no silent fallback)
    llm_model = action.get_model()

    # 3. Build LiteLLM string + API key
    model_string = _build_litellm_model_string(llm_model)
    api_key = _get_api_key(llm_model.provider)

    # 4. Prepare call parameters
    max_tokens = overrides.pop("max_tokens", action.max_tokens)
    temperature = overrides.pop("temperature", action.temperature)

    call_kwargs: dict[str, Any] = {
        "model": model_string,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "api_key": api_key,
    }

    if llm_model.provider.base_url:
        call_kwargs["api_base"] = llm_model.provider.base_url

    if tools:
        call_kwargs["tools"] = tools

    call_kwargs.update(overrides)

    # 5. Execute via LiteLLM
    start_time = time.monotonic()
    try:
        response = await litellm.acompletion(**call_kwargs)

        latency_ms = int((time.monotonic() - start_time) * 1000)
        content = response.choices[0].message.content or ""
        usage = response.usage
        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0

        # 6. Log usage
        _log_usage(
            tenant_id=tenant_id or "00000000-0000-0000-0000-000000000000",
            action_type=action,
            llm_model=llm_model,
            user=user,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            success=True,
        )

        return LLMResult(
            content=content,
            model=response.model or model_string,
            provider=llm_model.provider.name,
            action_code=action_code,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            success=True,
            raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
        )

    except Exception as exc:
        latency_ms = int((time.monotonic() - start_time) * 1000)

        _log_usage(
            tenant_id=tenant_id or "00000000-0000-0000-0000-000000000000",
            action_type=action,
            llm_model=llm_model,
            user=user,
            latency_ms=latency_ms,
            success=False,
            error_message=str(exc),
        )

        return LLMResult(
            content="",
            model=model_string,
            provider=llm_model.provider.name,
            action_code=action_code,
            latency_ms=latency_ms,
            success=False,
            error=str(exc),
        )


async def completion_with_fallback(
    action_code: str,
    messages: list[dict[str, str]],
    tenant_id: UUID | str | None = None,
    **kwargs: Any,
) -> LLMResult:
    """Completion with automatic fallback to fallback_model.

    1. Try default_model
    2. If fails → try fallback_model
    3. If both fail → return error result
    """
    from bfagent_llm.django_app.models import AIActionType, LLMConfigurationError

    # First attempt: uses default_model via normal completion()
    result = await completion(
        action_code=action_code,
        messages=messages,
        tenant_id=tenant_id,
        **kwargs,
    )

    if result.success:
        return result

    # Fallback: explicitly use fallback_model
    logger.warning(
        "Default model failed for '%s': %s. Trying fallback.",
        action_code,
        result.error,
    )

    lookup = {"code": action_code, "is_active": True}
    if tenant_id:
        lookup["tenant_id"] = tenant_id

    try:
        action = AIActionType.objects.select_related(
            "fallback_model__provider",
        ).get(**lookup)
    except AIActionType.DoesNotExist:
        return result

    if not action.fallback_model or not action.fallback_model.is_active:
        logger.warning(
            "No active fallback_model for '%s'.", action_code
        )
        return result

    # Override model to use fallback
    fallback_model_string = _build_litellm_model_string(
        action.fallback_model
    )
    return await completion(
        action_code=action_code,
        messages=messages,
        tenant_id=tenant_id,
        model=fallback_model_string,
        **kwargs,
    )


def sync_completion(
    action_code: str,
    messages: list[dict[str, str]],
    tenant_id: UUID | str | None = None,
    **kwargs: Any,
) -> LLMResult:
    """Synchronous wrapper for completion()."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                asyncio.run,
                completion(
                    action_code=action_code,
                    messages=messages,
                    tenant_id=tenant_id,
                    **kwargs,
                ),
            )
            return future.result(timeout=120)
    else:
        return asyncio.run(
            completion(
                action_code=action_code,
                messages=messages,
                tenant_id=tenant_id,
                **kwargs,
            )
        )
