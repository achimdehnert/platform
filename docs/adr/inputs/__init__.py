"""
aifw/__init__.py — Public API for aifw 0.6.0.

ADR-097 §6 — Public API Surface.

Exported names:

    Core (unchanged since 0.5.x):
        sync_completion       — execute LLM call

    New in 0.6.0:
        get_action_config     — resolve ActionConfig from DB (cached)
        get_quality_level_for_tier  — resolve quality_level from tier name (cached)
        QualityLevel          — named constants for 1–9 scale
        ActionConfig          — TypedDict for type checkers
        LLMResult             — TypedDict for sync_completion return type

    Exceptions:
        ConfigurationError    — missing AIActionType catch-all row (deployment defect)
        AIFWError             — base exception

Consumer example:
    from aifw import sync_completion, get_quality_level_for_tier, QualityLevel

    quality = get_quality_level_for_tier(user.subscription)   # "premium" → 8
    result = sync_completion(
        action_code="story_writing",
        messages=messages,
        quality_level=quality,
    )
"""

# ── Core ─────────────────────────────────────────────────────────────────────
from .service import sync_completion          # noqa: F401

# ── New 0.6.0 ────────────────────────────────────────────────────────────────
from .service import get_action_config        # noqa: F401
from .service import get_quality_level_for_tier  # noqa: F401
from .constants import QualityLevel           # noqa: F401
from .types import ActionConfig               # noqa: F401
from .types import LLMResult                  # noqa: F401

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import ConfigurationError    # noqa: F401
from .exceptions import AIFWError             # noqa: F401
from .exceptions import ProviderError         # noqa: F401

__version__ = "0.6.0"

__all__ = [
    # Core
    "sync_completion",
    # New 0.6.0
    "get_action_config",
    "get_quality_level_for_tier",
    "QualityLevel",
    "ActionConfig",
    "LLMResult",
    # Exceptions
    "ConfigurationError",
    "AIFWError",
    "ProviderError",
]
