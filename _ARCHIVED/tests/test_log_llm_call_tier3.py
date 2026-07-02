"""Tests for the once-per-session Tier-3 nudge in log_llm_call.py (issue #305).

Loads the hook via importlib so no installation is required.
Covers the trigger matrix from the issue:
  - Routine Opus session (>=8 turns, high cheap-ratio) → nudge exactly once
  - Tier-4 Opus session (low cheap-ratio) → no nudge
  - Sonnet session → no nudge
  - Already-nudged state (idempotency) → no second nudge
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_HOOK = Path.home() / ".claude" / "hooks" / "log_llm_call.py"
_spec = importlib.util.spec_from_file_location("log_llm_call", _HOOK)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

_should = hook._should_emit_tier3_nudge
_OPUS = "claude-opus-4-7"
_SONNET = "claude-sonnet-4-6"

# --- helpers -----------------------------------------------------------------

def _state(nudged: bool = False) -> dict:
    return {"logged_request_ids": set(), "tier3_nudged": nudged}


def _stats(turns: int, cheap_ratio: float, median: float = 0.02) -> tuple:
    return (turns, cheap_ratio, median)


# --- trigger matrix ----------------------------------------------------------

def test_should_nudge_routine_opus_session():
    """>=8 Turns, >=70% cheap on Opus → nudge fires."""
    assert _should(_OPUS, _state(), _stats(10, 0.80)) is True


def test_should_not_nudge_already_nudged():
    """Idempotency: second call must not fire when tier3_nudged=True."""
    assert _should(_OPUS, _state(nudged=True), _stats(10, 0.80)) is False


def test_should_not_nudge_tier4_session():
    """Expensive session (cheap_ratio below threshold) → no nudge."""
    assert _should(_OPUS, _state(), _stats(10, 0.40)) is False


def test_should_not_nudge_sonnet_session():
    """Sonnet model → nudge never fires (already on cheap tier)."""
    assert _should(_SONNET, _state(), _stats(10, 0.95)) is False


def test_should_not_nudge_too_few_turns():
    """<TIER3_MIN_TURNS turns → not enough signal yet."""
    assert _should(_OPUS, _state(), _stats(5, 0.90)) is False


def test_should_not_nudge_missing_stats():
    """DB unavailable (stats=None) → fail-silent, no nudge."""
    assert _should(_OPUS, _state(), None) is False


def test_should_nudge_at_exactly_min_turns():
    """Exactly TIER3_MIN_TURNS turns with high ratio → fires."""
    min_t = hook.TIER3_MIN_TURNS
    assert _should(_OPUS, _state(), _stats(min_t, 0.80)) is True


def test_should_not_nudge_just_below_min_turns():
    """One turn below TIER3_MIN_TURNS → does not fire."""
    min_t = hook.TIER3_MIN_TURNS
    assert _should(_OPUS, _state(), _stats(min_t - 1, 0.90)) is False


def test_should_nudge_cheap_ratio_at_threshold():
    """cheap_ratio exactly at TIER3_CHEAP_RATIO → fires."""
    assert _should(_OPUS, _state(), _stats(10, hook.TIER3_CHEAP_RATIO)) is True


def test_should_not_nudge_cheap_ratio_just_below_threshold():
    """cheap_ratio just below TIER3_CHEAP_RATIO → does not fire."""
    ratio = hook.TIER3_CHEAP_RATIO - 0.01
    assert _should(_OPUS, _state(), _stats(10, ratio)) is False
