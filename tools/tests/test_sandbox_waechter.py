"""Tests fuer tools/sandbox/waechter.py (platform#3685) — nur die Budget-Logik, kein Agent-Start."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "sandbox" / "waechter.py"
_spec = importlib.util.spec_from_file_location("waechter", _SCRIPT)
w = importlib.util.module_from_spec(_spec)
sys.modules["waechter"] = w
_spec.loader.exec_module(w)


def _assistant(mid: str, tokens: int, werkzeuge: tuple[str, ...] = ()) -> str:
    inhalt = [{"type": "tool_use", "id": f"{mid}-{i}", "name": n} for i, n in enumerate(werkzeuge)]
    return json.dumps({"type": "assistant", "message": {"id": mid, "usage": {"output_tokens": tokens}, "content": inhalt}})


def test_should_count_usage_once_per_message():
    z = w.Zaehler(max_tokens=1000, max_agenten=5)
    for _ in range(3):  # stream-json wiederholt die Nachricht je Inhaltsblock
        assert z.verarbeite(_assistant("m1", 100)) is None
    z.verarbeite(_assistant("m2", 50))
    assert z.tokens == 150


def test_should_stop_at_token_limit():
    z = w.Zaehler(max_tokens=100, max_agenten=5)
    assert z.verarbeite(_assistant("m1", 100)) is None
    assert z.verarbeite(_assistant("m2", 1)) == "max_tokens"


def test_should_stop_when_too_many_subagents():
    z = w.Zaehler(max_tokens=10_000, max_agenten=2)
    assert z.verarbeite(_assistant("m1", 1, ("Agent", "Bash"))) is None
    assert z.verarbeite(_assistant("m2", 1, ("Task",))) is None
    assert z.verarbeite(_assistant("m3", 1, ("Agent",))) == "max_agenten"


def test_should_ignore_non_json_lines():
    assert w.Zaehler(max_tokens=1, max_agenten=1).verarbeite("kein json\n") is None


def test_should_never_report_budget_end_as_done():
    z = w.Zaehler(max_tokens=10, max_agenten=1)
    z.verarbeite(json.dumps({"type": "result", "subtype": "success", "total_cost_usd": 0.1, "result": "ok"}))
    assert w.status_von(z, None, 0) == "fertig"
    assert w.status_von(z, "max_tokens", 0) == "abgebrochen: Budget (max_tokens)"
    z.verarbeite(json.dumps({"type": "result", "subtype": "error_max_budget_usd"}))
    assert w.status_von(z, None, 1) == "abgebrochen: Budget (max_usd)"
    assert w.status_von(w.Zaehler(1, 1), None, 1).startswith("fehler")
