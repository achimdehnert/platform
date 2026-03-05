"""
aifw/types.py — Public type contracts for aifw 0.6.0.

ADR-097 §5.2 — ActionConfig TypedDict (gap G-097-04 filled: LLMResult defined).

These types are exported from aifw.__init__ for consumer-app type checking.
Do NOT import from aifw.types directly — use `from aifw import ActionConfig, LLMResult`.
"""
from __future__ import annotations

from typing import TypedDict


class ActionConfig(TypedDict):
    """
    Resolved configuration for a single LLM action call.

    Returned by get_action_config(). Cached in Redis for 300s.
    All fields are always present (never Optional after lookup).

    prompt_template_key: str | None — None means caller must use action_code as key.
        authoringfw.BaseContentOrchestrator uses: config["prompt_template_key"] or action_code
    """

    action_id: int           # AIActionType.pk
    model_id: int            # LLMModel.pk
    model: str               # LiteLLM model identifier e.g. "anthropic/claude-sonnet-4-20250514"
    provider: str            # Provider name e.g. "anthropic", "openai", "groq"
    base_url: str            # Provider base URL (empty string for standard providers)
    api_key_env_var: str     # Environment variable name for API key e.g. "ANTHROPIC_API_KEY"
    prompt_template_key: str | None  # promptfw template key; None = use action_code as fallback
    max_tokens: int          # Maximum tokens for this action
    temperature: float       # Sampling temperature for this action


class LLMResult(TypedDict):
    """
    Result of a sync_completion() call.

    Returned by aifw.sync_completion(). Used by authoringfw._map_result()
    to construct domain-specific ContentResult instances.

    This TypedDict defines the minimum contract. The actual implementation
    object may have additional fields; only these are guaranteed present.
    """

    content: str             # Generated text content
    model: str               # Actual model used (may differ from config if fallback activated)
    provider: str            # Provider used
    input_tokens: int        # Prompt token count
    output_tokens: int       # Completion token count
    total_tokens: int        # input_tokens + output_tokens
    latency_ms: int          # Wall-clock latency in milliseconds
    success: bool            # True if completion succeeded without error
    quality_level: int | None  # quality_level passed to sync_completion (for logging)
    priority: str | None       # priority passed to sync_completion (for logging)
    action_code: str           # action_code used for this call
    usage_log_id: int | None   # AIUsageLog.pk (None if logging disabled)
