"""Tests for the once-per-session Tier-3 model-nudge logic (issue #305).

Covers:
- _load_state backward compat (old bare-list format)
- _load_state / _save_state roundtrip with tier3_nudged flag
- _should_emit_tier3_nudge trigger matrix:
    * routine Opus session (≥8 turns, ≥70% cheap) → True
    * tier-4 Opus session (< 70% cheap)           → False
    * Sonnet session                               → False
    * already nudged this session                  → False (idempotent)
    * not enough turns yet                         → False
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Load the hook module from the sibling directory without installing it.
_HOOK_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_HOOK_DIR))
import log_llm_call as hook  # noqa: E402


# ---------------------------------------------------------------------------
# _load_state / _save_state
# ---------------------------------------------------------------------------


def test_should_load_empty_state_when_file_missing(tmp_path):
    with patch.object(hook, "STATE_DIR", tmp_path):
        state = hook._load_state("sess-abc")
    assert state == {"logged_request_ids": set(), "tier3_nudged": False}


def test_should_migrate_old_list_format_to_dict(tmp_path):
    sid = "sess-old"
    safe = "sess-old"
    (tmp_path / f"{safe}.json").write_text(json.dumps(["req-1", "req-2"]))
    with patch.object(hook, "STATE_DIR", tmp_path):
        state = hook._load_state(sid)
    assert state["logged_request_ids"] == {"req-1", "req-2"}
    assert state["tier3_nudged"] is False


def test_should_roundtrip_tier3_nudged_flag(tmp_path):
    sid = "sess-new"
    with patch.object(hook, "STATE_DIR", tmp_path):
        initial = hook._load_state(sid)
        initial["tier3_nudged"] = True
        initial["logged_request_ids"].add("req-x")
        hook._save_state(sid, initial)
        reloaded = hook._load_state(sid)
    assert reloaded["tier3_nudged"] is True
    assert "req-x" in reloaded["logged_request_ids"]


def test_should_load_false_nudge_when_not_set(tmp_path):
    sid = "sess-notset"
    with patch.object(hook, "STATE_DIR", tmp_path):
        state = hook._load_state(sid)
        hook._save_state(sid, state)
        reloaded = hook._load_state(sid)
    assert reloaded["tier3_nudged"] is False


# ---------------------------------------------------------------------------
# _should_emit_tier3_nudge trigger matrix
# ---------------------------------------------------------------------------

_ROUTINE_STATS = (10, 0.80, 0.03)   # 10 turns, 80% cheap, median $0.03
_TIER4_STATS   = (10, 0.40, 0.25)   # 10 turns, 40% cheap (expensive session)
_FEW_TURNS     = (4,  0.90, 0.02)   # 4 turns — not enough signal yet


@pytest.mark.parametrize("model,state,stats,expected", [
    # routine Opus session → fire
    (
        "claude-opus-4-7",
        {"tier3_nudged": False},
        _ROUTINE_STATS,
        True,
    ),
    # already nudged → don't repeat
    (
        "claude-opus-4-7",
        {"tier3_nudged": True},
        _ROUTINE_STATS,
        False,
    ),
    # Sonnet session → no nudge
    (
        "claude-sonnet-4-6",
        {"tier3_nudged": False},
        _ROUTINE_STATS,
        False,
    ),
    # Tier-4 Opus (expensive turns) → no nudge
    (
        "claude-opus-4-7",
        {"tier3_nudged": False},
        _TIER4_STATS,
        False,
    ),
    # too few turns → no nudge
    (
        "claude-opus-4-7",
        {"tier3_nudged": False},
        _FEW_TURNS,
        False,
    ),
    # stats is None (DB unavailable) → no nudge
    (
        "claude-opus-4-7",
        {"tier3_nudged": False},
        None,
        False,
    ),
])
def test_should_emit_tier3_nudge(model, state, stats, expected):
    result = hook._should_emit_tier3_nudge(model, state, stats)
    assert result is expected


def test_should_nudge_exactly_once_across_calls():
    """Simulates two consecutive hook runs; nudge fires only on the first."""
    state = {"logged_request_ids": set(), "tier3_nudged": False}
    stats = _ROUTINE_STATS
    model = "claude-opus-4-7"

    first = hook._should_emit_tier3_nudge(model, state, stats)
    assert first is True

    # Simulate saving the nudged flag (as main() does after firing).
    state["tier3_nudged"] = True

    second = hook._should_emit_tier3_nudge(model, state, stats)
    assert second is False


# ---------------------------------------------------------------------------
# _resolve_db_url — SEC-5 (Issue #1198): kein stillschweigender Passwort-
# Fallback mehr; Dev-Only-Opt-in nur bei explizitem ALLOW_DEV_DB_FALLBACK=1.
# ---------------------------------------------------------------------------


def test_should_return_none_when_no_env_var_and_no_dev_opt_in(monkeypatch):
    monkeypatch.delenv("ORCHESTRATOR_DB_URL", raising=False)
    monkeypatch.delenv("ALLOW_DEV_DB_FALLBACK", raising=False)
    assert hook._resolve_db_url() is None


def test_should_use_dev_fallback_only_with_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("ORCHESTRATOR_DB_URL", raising=False)
    monkeypatch.setenv("ALLOW_DEV_DB_FALLBACK", "1")
    assert hook._resolve_db_url() == hook._DEV_FALLBACK_DB_URL
    assert "change-me-in-production" in hook._DEV_FALLBACK_DB_URL  # documents the known dev-only value


def test_should_prefer_explicit_env_var_over_dev_fallback(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_DB_URL", "postgresql://real:secret@db.internal/prod")
    monkeypatch.setenv("ALLOW_DEV_DB_FALLBACK", "1")
    assert hook._resolve_db_url() == "postgresql://real:secret@db.internal/prod"


def test_should_skip_insert_gracefully_when_db_url_is_none(monkeypatch):
    """Hook-Contract (exit 0 immer): fehlendes DB_URL darf nicht crashen."""
    monkeypatch.setattr(hook, "DB_URL", None)
    assert hook._insert_rows([{"request_id": "r1"}]) == 0


def test_should_return_none_from_stats_queries_when_db_url_is_none(monkeypatch):
    monkeypatch.setattr(hook, "DB_URL", None)
    assert hook._query_session_total("sess-x") is None
    assert hook._query_session_tier3_stats("sess-x") is None
