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
