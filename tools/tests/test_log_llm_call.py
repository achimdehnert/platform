"""Tests für tools/claude-hooks/log_llm_call.py — DB-URL-Resolver,
Modellnormalisierung, Preise.

Folge-PR zu platform#2606 E1: das Werkzeug (gemergt in #2641, PR #2606) hatte
keine Unit-Tests. `_resolve_db_url()` läuft schon auf Modulebene
(`DB_URL = _resolve_db_url()`) — ein naives `import log_llm_call` würde also
beim Laden bereits `~/.secrets/orchestrator_mcp_db_password` lesen, falls die
Datei existiert. `Path.home` wird deshalb VOR dem Import umgebogen, nicht
erst in den einzelnen Tests — und in den einzelnen Tests wird zusätzlich
`_DB_PASSWORD_FILE`/Env per `monkeypatch` gesetzt, bevor `_resolve_db_url()`
aufgerufen wird. Kein Test liest das echte Home.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

WERKZEUG = Path(__file__).resolve().parents[1] / "claude-hooks" / "log_llm_call.py"


def _modul():
    """Lädt log_llm_call frisch, mit umgebogenem Home und geleerten DB-Envs
    für die Dauer des Imports — Modulebene ruft _resolve_db_url() selbst auf.
    """
    fake_home = Path(tempfile.mkdtemp(prefix="log-llm-call-test-home-"))
    saved = {
        k: os.environ.pop(k, None)
        for k in ("ORCHESTRATOR_DB_URL", "ALLOW_DEV_DB_FALLBACK")
    }
    try:
        with patch.object(Path, "home", return_value=fake_home):
            spec = importlib.util.spec_from_file_location("log_llm_call_test", WERKZEUG)
            modul = importlib.util.module_from_spec(spec)
            sys.modules["log_llm_call_test"] = modul
            spec.loader.exec_module(modul)
    finally:
        for key, value in saved.items():
            if value is not None:
                os.environ[key] = value
    return modul


mod = _modul()


# ---------------------------------------------------------------------------
# _resolve_db_url
# ---------------------------------------------------------------------------


def test_should_prefer_env_var_over_password_file(monkeypatch, tmp_path):
    pw_file = tmp_path / "orchestrator_mcp_db_password"
    pw_file.write_text("irrelevant", encoding="utf-8")
    monkeypatch.setattr(mod, "_DB_PASSWORD_FILE", pw_file)
    monkeypatch.setenv(
        "ORCHESTRATOR_DB_URL", "postgresql://real:secret@db.internal/prod"
    )
    assert mod._resolve_db_url() == "postgresql://real:secret@db.internal/prod"


def test_should_build_quoted_url_from_password_file(monkeypatch, tmp_path):
    pw_file = tmp_path / "orchestrator_mcp_db_password"
    pw_file.write_text("p@ss:wort!", encoding="utf-8")
    monkeypatch.setattr(mod, "_DB_PASSWORD_FILE", pw_file)
    monkeypatch.delenv("ORCHESTRATOR_DB_URL", raising=False)
    url = mod._resolve_db_url()
    quoted = quote("p@ss:wort!", safe="")
    assert url == f"postgresql://orchestrator:{quoted}@127.0.0.1:15435/orchestrator_mcp"
    assert "p@ss:wort!" not in url


def test_should_return_none_without_env_password_or_fallback(monkeypatch, tmp_path):
    pw_file = tmp_path / "missing_password"
    monkeypatch.setattr(mod, "_DB_PASSWORD_FILE", pw_file)
    monkeypatch.delenv("ORCHESTRATOR_DB_URL", raising=False)
    monkeypatch.delenv("ALLOW_DEV_DB_FALLBACK", raising=False)
    assert mod._resolve_db_url() is None


def test_should_use_dev_fallback_when_opted_in(monkeypatch, tmp_path):
    pw_file = tmp_path / "missing_password"
    monkeypatch.setattr(mod, "_DB_PASSWORD_FILE", pw_file)
    monkeypatch.delenv("ORCHESTRATOR_DB_URL", raising=False)
    monkeypatch.setenv("ALLOW_DEV_DB_FALLBACK", "1")
    assert mod._resolve_db_url() == mod._DEV_FALLBACK_DB_URL


def test_should_treat_empty_password_file_as_no_password(monkeypatch, tmp_path):
    pw_file = tmp_path / "empty_password"
    pw_file.write_text("", encoding="utf-8")
    monkeypatch.setattr(mod, "_DB_PASSWORD_FILE", pw_file)
    monkeypatch.delenv("ORCHESTRATOR_DB_URL", raising=False)
    monkeypatch.setenv("ALLOW_DEV_DB_FALLBACK", "1")
    assert mod._resolve_db_url() == mod._DEV_FALLBACK_DB_URL


# ---------------------------------------------------------------------------
# _normalize_model
# ---------------------------------------------------------------------------


def test_should_strip_context_variant_suffix():
    assert mod._normalize_model("claude-fable-5[1m]") == "claude-fable-5"


def test_should_leave_model_without_suffix_unchanged():
    assert mod._normalize_model("claude-fable-5") == "claude-fable-5"


# ---------------------------------------------------------------------------
# _compute_cost
# ---------------------------------------------------------------------------


def test_should_compute_cost_for_known_model_with_context_suffix():
    usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    assert mod._compute_cost("claude-fable-5[1m]", usage) == 60.0


def test_should_fall_back_to_default_pricing_for_unknown_model():
    usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    assert mod._compute_cost("some-unknown-model", usage) == 18.0
    assert mod.DEFAULT_PRICING == {"input": 3.0, "output": 15.0}


# ---------------------------------------------------------------------------
# Zustandsfortschritt (platform#2606 Stufe 1)
#
# Gemessen 2026-09-02 im eigenen Protokoll: 12.574 Ereignisse „insert returned 0
# for N candidate rows", zusammen 2.686.409 vergebliche INSERT-Roundtrips
# (Median N=166, Maximum 1246). Ursache: der Zustand wurde nur bei
# `inserted > 0` fortgeschrieben. Liefen alle Kandidaten in
# `ON CONFLICT DO NOTHING`, blieb er stehen und derselbe Stapel ging bei JEDEM
# weiteren Stop erneut ueber die Leitung — 4.902 ms statt 190 ms je Stop.
#
# Die Gegenprobe ist genauso wichtig: bei einem echten Schreibfehler darf der
# Zustand NICHT fortschreiben, sonst gingen Zeilen still verloren.
# ---------------------------------------------------------------------------


def _fahre_main(monkeypatch, tmp_path, insert_ergebnis, *, model="claude-sonnet-4-5"):
    """Faehrt `main()` mit einem einzigen neuen Turn und gestubbtem Schreibweg."""
    import io
    import json as _json

    turn = {
        "request_id": "req_TEST_1",
        "model": model,
        "usage": {"input_tokens": 10, "output_tokens": 5},
        "timestamp": "2026-09-02T10:00:00.000Z",
        "duration_ms": 1200,
        "cwd": "/home/x/github/platform",
        "git_branch": "main",
        "session_id": "sid",
    }
    gespeichert: list[dict] = []
    monkeypatch.setattr(mod, "_collect_turns", lambda _p: [turn])
    monkeypatch.setattr(mod, "_load_state", lambda _s: {"logged_request_ids": set()})
    monkeypatch.setattr(
        mod, "_save_state", lambda _s, state: gespeichert.append(dict(state))
    )
    monkeypatch.setattr(mod, "_insert_rows", lambda _rows: insert_ergebnis)
    monkeypatch.setattr(mod, "_query_session_total", lambda _s: None)
    monkeypatch.setattr(mod, "_log", lambda _m: None)
    transkript = tmp_path / "t.jsonl"
    transkript.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            _json.dumps({"transcript_path": str(transkript), "session_id": "sid"})
        ),
    )
    rc = mod.main()
    return rc, gespeichert


def test_should_advance_state_when_all_rows_hit_on_conflict(monkeypatch, tmp_path):
    """`0` heisst committet: die Zeilen liegen in der DB und sind fertig."""
    rc, gespeichert = _fahre_main(monkeypatch, tmp_path, 0)

    assert rc == 0
    assert gespeichert, "Zustand nicht gespeichert — derselbe Stapel liefe ewig erneut"
    assert "req_TEST_1" in gespeichert[0]["logged_request_ids"]


def test_should_advance_state_on_a_normal_insert(monkeypatch, tmp_path):
    rc, gespeichert = _fahre_main(monkeypatch, tmp_path, 1)

    assert rc == 0
    assert "req_TEST_1" in gespeichert[0]["logged_request_ids"]


def test_should_not_advance_state_when_the_write_path_did_not_run(
    monkeypatch, tmp_path
):
    """Gegenprobe: `None` heisst „nicht geschrieben" — sonst faellt eine Zeile aus."""
    rc, gespeichert = _fahre_main(monkeypatch, tmp_path, None)

    assert rc == 0
    assert gespeichert == []


def test_should_report_none_when_there_is_no_db_url(monkeypatch):
    """Ohne DB-URL ist der Schreibweg nicht gelaufen — nicht „0 geschrieben"."""
    monkeypatch.setattr(mod, "DB_URL", None)
    monkeypatch.setattr(mod, "_log", lambda _m: None)

    assert mod._insert_rows([{"request_id": "x"}]) is None


def test_should_report_zero_for_an_empty_row_list(monkeypatch):
    """Nichts zu schreiben ist kein Fehlschlag — sonst blockiert der Zustand grundlos."""
    assert mod._insert_rows([]) == 0
