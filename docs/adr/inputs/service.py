"""
aifw/service.py — Core service functions for aifw 0.6.0.

ADR-097 §5 — Service Layer Specification.

Public API (exported from aifw.__init__):
    sync_completion()          — execute LLM call (extended with quality_level, priority)
    get_action_config()        — resolve AIActionType + cache
    get_quality_level_for_tier()  — resolve TierQualityMapping + cache

Internal:
    _lookup_cascade()          — 4-step deterministic DB lookup
    _to_action_config()        — model → TypedDict conversion
    _action_cache_key()        — cache key formatter
"""
from __future__ import annotations

import logging
from typing import Any

from django.core.cache import cache

from .constants import QualityLevel, VALID_PRIORITIES
from .exceptions import ConfigurationError
from .models import AIActionType, TierQualityMapping, AIUsageLog
from .types import ActionConfig, LLMResult

log = logging.getLogger("aifw.service")

# ── Cache TTLs ────────────────────────────────────────────────────────────────
_ACTION_CACHE_TTL: int = 300   # 5 min — AIActionType rows change rarely (< 10/day)
_TIER_CACHE_TTL: int = 600     # 10 min — tier configs change very rarely (days/weeks)
                                # Fix: ADR-097 used 300s; upgraded to 600s (M-095-04)


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _action_cache_key(
    code: str,
    quality_level: int | None,
    priority: str | None,
) -> str:
    """Deterministic, collision-free cache key for a (code, ql, priority) triple."""
    return f"aifw:action:{code}:{quality_level}:{priority}"


def _to_action_config(obj: AIActionType) -> ActionConfig:
    """Convert an AIActionType ORM object to the ActionConfig TypedDict."""
    model = obj.default_model
    return ActionConfig(
        action_id=obj.pk,
        model_id=model.pk,
        model=model.model_identifier,      # LiteLLM format: "anthropic/claude-sonnet-4-20250514"
        provider=model.provider,
        base_url=model.base_url or "",
        api_key_env_var=model.api_key_env_var or "",
        prompt_template_key=obj.prompt_template_key,   # may be None — see ActionConfig docstring
        max_tokens=obj.max_tokens,
        temperature=obj.temperature,
    )


# ──────────────────────────────────────────────────────────────────────────────
# _lookup_cascade — 4-step deterministic DB lookup (ADR-097 §5.1)
# ──────────────────────────────────────────────────────────────────────────────

def _lookup_cascade(
    code: str,
    quality_level: int | None,
    priority: str | None,
) -> AIActionType:
    """
    4-level deterministic lookup cascade (ADR-095 §5.4).

    Steps:
        1. Exact match:    (code, quality_level, priority)         — requires both non-None
        2. Level match:    (code, quality_level, priority=NULL)    — requires quality_level non-None
        3. Priority match: (code, quality_level=NULL, priority)    — requires priority non-None
        4. Full catch-all: (code, quality_level=NULL, priority=NULL)

    Steps are skipped when the corresponding parameter is None (they would produce
    the same result as a later step — skipping avoids the redundant DB query).

    .first() is used at each step as a safety net. Uniqueness is guaranteed by
    the 4 partial unique indexes from the migration — a single row is the invariant.

    Raises:
        ConfigurationError: If no row matches at any level. This is a DEPLOYMENT DEFECT.
            A catch-all row must exist for every action_code.
    """
    base_qs = AIActionType.objects.select_related(
        "default_model",
        "default_model__provider" if hasattr(AIActionType, "_meta") else "default_model",
    ).filter(is_active=True)

    # Step 1 — Exact match (skip if either param is None)
    if quality_level is not None and priority is not None:
        obj = base_qs.filter(
            code=code,
            quality_level=quality_level,
            priority=priority,
        ).first()
        if obj is not None:
            log.debug("_lookup_cascade: step=1 (exact) hit for code=%r ql=%s p=%r", code, quality_level, priority)
            return obj

    # Step 2 — Level match: priority is catch-all (skip if quality_level is None)
    if quality_level is not None:
        obj = base_qs.filter(
            code=code,
            quality_level=quality_level,
            priority__isnull=True,
        ).first()
        if obj is not None:
            log.debug("_lookup_cascade: step=2 (level) hit for code=%r ql=%s", code, quality_level)
            return obj

    # Step 3 — Priority match: quality is catch-all (skip if priority is None)
    if priority is not None:
        obj = base_qs.filter(
            code=code,
            quality_level__isnull=True,
            priority=priority,
        ).first()
        if obj is not None:
            log.debug("_lookup_cascade: step=3 (priority) hit for code=%r p=%r", code, priority)
            return obj

    # Step 4 — Full catch-all (both NULL)
    obj = base_qs.filter(
        code=code,
        quality_level__isnull=True,
        priority__isnull=True,
    ).first()
    if obj is not None:
        log.debug("_lookup_cascade: step=4 (catchall) hit for code=%r", code)
        return obj

    raise ConfigurationError(
        f"No active AIActionType found for code={code!r}, "
        f"quality_level={quality_level}, priority={priority!r}. "
        f"A catch-all row (quality_level=NULL, priority=NULL) must exist for every action_code. "
        f"Run: python manage.py check_aifw_config --fix"
    )


# ──────────────────────────────────────────────────────────────────────────────
# get_action_config — public API with Redis cache (ADR-097 §5.2)
# ──────────────────────────────────────────────────────────────────────────────

def get_action_config(
    action_code: str,
    quality_level: int | None = None,
    priority: str | None = None,
) -> ActionConfig:
    """
    Resolve and return the full action configuration for a (code, ql, priority) triple.

    Result is cached in Redis for _ACTION_CACHE_TTL seconds.
    Cache is invalidated on AIActionType save/delete (via signal in aifw/signals.py).

    Args:
        action_code:   AIActionType.code e.g. "story_writing"
        quality_level: 1–9 integer or None (catch-all). Use QualityLevel constants.
        priority:      "fast"|"balanced"|"quality"|None. Explicit override only.

    Returns:
        ActionConfig TypedDict with model, template_key, max_tokens, etc.

    Raises:
        ConfigurationError: If no AIActionType row matches at any cascade level.

    Example:
        from aifw import get_action_config, QualityLevel
        config = get_action_config("story_writing", QualityLevel.PREMIUM, "quality")
        # → ActionConfig(model="anthropic/claude-sonnet-4-20250514", ...)
    """
    cache_key = _action_cache_key(action_code, quality_level, priority)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    obj = _lookup_cascade(action_code, quality_level, priority)
    result = _to_action_config(obj)
    cache.set(cache_key, result, timeout=_ACTION_CACHE_TTL)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# get_quality_level_for_tier — public API with Redis cache (ADR-097 §5.3)
# ──────────────────────────────────────────────────────────────────────────────

def get_quality_level_for_tier(tier: str | None) -> int:
    """
    DB-driven tier→quality_level lookup. Replaces hardcoded TIER_QUALITY_MAP dicts.

    Falls back to QualityLevel.BALANCED (5) when:
        - tier is None
        - tier is not found in TierQualityMapping
        - matching TierQualityMapping row is inactive

    Cached for _TIER_CACHE_TTL seconds. Invalidated on TierQualityMapping save/delete.

    Args:
        tier: Subscription tier name e.g. "premium", "pro", "freemium".
              Typically from user.subscription or equivalent field.
              None is treated as "no tier" → BALANCED fallback.

    Returns:
        int: quality_level 1–9

    Example:
        from aifw import get_quality_level_for_tier
        quality = get_quality_level_for_tier(user.subscription)  # "premium" → 8
    """
    if not tier:
        return QualityLevel.BALANCED

    cache_key = f"aifw:tier:{tier}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    obj = TierQualityMapping.objects.filter(tier=tier, is_active=True).first()
    if obj is None:
        log.warning(
            "get_quality_level_for_tier: tier=%r not found in TierQualityMapping. "
            "Falling back to BALANCED (%d). "
            "Run: python manage.py check_aifw_config to verify seeding.",
            tier,
            QualityLevel.BALANCED,
        )
        result = QualityLevel.BALANCED
    else:
        result = obj.quality_level

    cache.set(cache_key, result, timeout=_TIER_CACHE_TTL)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# sync_completion — extended public API (ADR-097 §5.4)
# ──────────────────────────────────────────────────────────────────────────────

def sync_completion(
    action_code: str,
    messages: list[dict[str, Any]],
    quality_level: int | None = None,   # NEW in 0.6.0 — optional, default=None
    priority: str | None = None,        # NEW in 0.6.0 — optional, default=None
    **kwargs: Any,                       # forward compatibility
) -> LLMResult:
    """
    Execute a synchronous LLM completion.

    Backwards-compatible extension: existing call sites with only action_code + messages
    work identically after upgrading to 0.6.0 (quality_level=None → catch-all).

    Args:
        action_code:   Action identifier for config lookup e.g. "story_writing"
        messages:      Chat messages list [{"role": "user", "content": "..."}]
        quality_level: 1–9 quality scale or None (catch-all — legacy behaviour)
        priority:      "fast"|"balanced"|"quality"|None (explicit override only)
        **kwargs:      Forwarded to LiteLLM for override (temperature, max_tokens, etc.)

    Returns:
        LLMResult TypedDict

    Raises:
        ConfigurationError: No matching AIActionType row (deployment defect)
        ProviderError:      LLM provider returned an error
    """
    # 1. Resolve config (cached)
    config = get_action_config(action_code, quality_level, priority)

    # ── LiteLLM call (placeholder — actual implementation uses existing litellm logic) ──
    # In the real implementation this calls litellm.completion() with config["model"],
    # handles fallback_model on ProviderError, and records timing.
    import time
    t0 = time.perf_counter()

    # ... litellm.completion(model=config["model"], messages=messages, ...) ...

    latency_ms = int((time.perf_counter() - t0) * 1000)

    # Placeholder result (replace with actual litellm response parsing)
    raw_content = ""          # litellm_response.choices[0].message.content
    input_tokens = 0          # litellm_response.usage.prompt_tokens
    output_tokens = 0         # litellm_response.usage.completion_tokens
    model_used = config["model"]

    # 2. Log usage (quality_level as dedicated column — OQ-2)
    log_entry = AIUsageLog.objects.create(
        action_code=action_code,
        model=model_used,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=_calculate_cost(model_used, input_tokens, output_tokens),
        latency_ms=latency_ms,
        success=True,
        quality_level=quality_level,   # NEW dedicated column
    )

    return LLMResult(
        content=raw_content,
        model=model_used,
        provider=config["provider"],
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        latency_ms=latency_ms,
        success=True,
        quality_level=quality_level,
        priority=priority,
        action_code=action_code,
        usage_log_id=log_entry.pk,
    )


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Placeholder — real implementation uses LiteLLM cost calculation."""
    # litellm.completion_cost() or custom cost table
    return 0.0
