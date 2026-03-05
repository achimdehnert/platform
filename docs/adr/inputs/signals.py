"""
aifw/signals.py — Django signal handlers for cache invalidation.

ADR-097 §5.2 — Cache invalidation on AIActionType save/delete.

Fix G-097-02: Use cache.delete_many() instead of 40 individual cache.delete() calls.
Fix G-097-03: This file is imported in aifw/apps.py AppConfig.ready() to ensure
              signals are registered when Django starts.

Do NOT import this module directly — it is imported via aifw/apps.py.
"""
from __future__ import annotations

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from django.core.cache import cache

from .models import AIActionType, TierQualityMapping


# ── Precomputed key sets for bulk invalidation ────────────────────────────────

_QUALITY_LEVELS: tuple[int | None, ...] = (None, 1, 2, 3, 4, 5, 6, 7, 8, 9)
_PRIORITIES: tuple[str | None, ...] = (None, "fast", "balanced", "quality")


def _action_cache_keys_for_code(code: str) -> list[str]:
    """
    Generate all 40 possible cache keys for a given action_code.
    (10 quality_levels × 4 priorities = 40 combinations)
    """
    return [
        f"aifw:action:{code}:{ql}:{prio}"
        for ql in _QUALITY_LEVELS
        for prio in _PRIORITIES
    ]


# ── AIActionType cache invalidation ──────────────────────────────────────────

@receiver([post_save, post_delete], sender=AIActionType)
def _invalidate_action_cache(
    sender: type[AIActionType],
    instance: AIActionType,
    **kwargs: object,
) -> None:
    """
    Invalidate all cache entries for this action_code on any change.

    Uses cache.delete_many() — single Redis MDELETE call instead of 40 individual
    DELETE calls. (Fix G-097-02)

    This handler covers both save and delete: a deactivated row (is_active=False)
    must also clear the cache, otherwise stale active-config results persist.
    """
    keys = _action_cache_keys_for_code(instance.code)
    try:
        cache.delete_many(keys)
    except Exception:
        # If Redis is unavailable, fall back to clearing the entire cache.
        # This is safe — cache is ephemeral, DB is the source of truth.
        try:
            cache.clear()
        except Exception:
            pass  # nosec — cache failure is non-fatal, just reduces performance


# ── TierQualityMapping cache invalidation ────────────────────────────────────

@receiver([post_save, post_delete], sender=TierQualityMapping)
def _invalidate_tier_cache(
    sender: type[TierQualityMapping],
    instance: TierQualityMapping,
    **kwargs: object,
) -> None:
    """
    Invalidate the tier cache entry for this specific tier on any change.

    Single-key delete (tier is unique — only one cache key per tier).
    """
    cache.delete(f"aifw:tier:{instance.tier}")
