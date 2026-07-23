"""Datenschutz-Gate des Print-Agents (#1297) — CI-gegatet.

**Warum hier und nicht in ``tools/print_agent/tests/``:** jener Testort läuft in
keinem Workflow (``make test`` listet ihn nicht), und selbst mit Pfad-Eintrag
würden seine Fälle still übersprungen — er importiert ``print_agent``, das
``litellm``/``markdown``/``weasyprint`` zieht, während CI nur ``pytest pyyaml
pydantic`` installiert. Die Invariante wäre dann dauergrün ohne Prüfung.

``llm_gate`` kommt mit der Standardbibliothek aus und ist deshalb von hier aus
echt prüfbar. Kern-Invariante: **kein** Aufruf, der den Dokumentinhalt von
dieser Maschine wegträgt, ohne ausdrückliches Opt-in.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "print_agent"))
import llm_gate  # noqa: E402


def test_should_default_to_local_ollama_without_fallback():
    assert llm_gate.DEFAULT_PRIMARY.startswith("ollama/")
    assert llm_gate.DEFAULT_FALLBACK == ""
    assert llm_gate.is_loopback_host(llm_gate.DEFAULT_OLLAMA_HOST)


def test_should_classify_ollama_prefixes_as_local_model():
    assert llm_gate.is_local_model("ollama/qwen2.5:3b")
    assert llm_gate.is_local_model("ollama_chat/qwen2.5:7b")
    assert not llm_gate.is_local_model("cerebras/llama3.1-8b")
    assert not llm_gate.is_local_model("groq/llama-3.1-8b-instant")


def test_should_treat_only_loopback_targets_as_this_machine():
    assert llm_gate.is_loopback_host("http://127.0.0.1:11434")
    assert llm_gate.is_loopback_host("http://localhost:11434")
    assert llm_gate.is_loopback_host("http://[::1]:11434")
    # ollama-on-dev ist ein anderer Rechner — der Auszug verließe die Maschine.
    assert not llm_gate.is_loopback_host("http://88.99.38.75:11434")
    assert not llm_gate.is_loopback_host("https://ollama.example.org")
    assert not llm_gate.is_loopback_host("")


def test_should_require_optin_for_external_provider(monkeypatch):
    monkeypatch.delenv("PRINT_AGENT_ALLOW_EXTERNAL", raising=False)
    assert llm_gate.leaves_machine("groq/llama-3.1-8b-instant")
    assert llm_gate.skip_reason("groq/llama-3.1-8b-instant") is not None


def test_should_require_optin_for_remote_ollama(monkeypatch):
    """Der eigentliche Befund: ollama/ heißt nicht automatisch 'auf dieser Maschine'."""
    monkeypatch.delenv("PRINT_AGENT_ALLOW_EXTERNAL", raising=False)
    monkeypatch.setenv("OLLAMA_HOST", "http://88.99.38.75:11434")
    assert llm_gate.leaves_machine("ollama/qwen2.5:3b")
    reason = llm_gate.skip_reason("ollama/qwen2.5:3b")
    assert reason is not None
    assert "88.99.38.75" in reason


def test_should_allow_local_ollama_without_optin(monkeypatch):
    monkeypatch.delenv("PRINT_AGENT_ALLOW_EXTERNAL", raising=False)
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    assert not llm_gate.leaves_machine("ollama/qwen2.5:3b")
    assert llm_gate.skip_reason("ollama/qwen2.5:3b") is None


def test_should_allow_leaving_machine_only_with_optin(monkeypatch):
    monkeypatch.setenv("PRINT_AGENT_ALLOW_EXTERNAL", "1")
    assert llm_gate.skip_reason("groq/llama-3.1-8b-instant") is None
    monkeypatch.setenv("OLLAMA_HOST", "http://88.99.38.75:11434")
    assert llm_gate.skip_reason("ollama/qwen2.5:3b") is None


def test_should_read_optin_flag_case_insensitively(monkeypatch):
    for truthy in ("1", "true", "TRUE", "yes", "On"):
        monkeypatch.setenv("PRINT_AGENT_ALLOW_EXTERNAL", truthy)
        assert llm_gate.external_allowed(), truthy
    for falsy in ("", "0", "false", "no", "irgendwas"):
        monkeypatch.setenv("PRINT_AGENT_ALLOW_EXTERNAL", falsy)
        assert not llm_gate.external_allowed(), falsy


def test_should_read_ollama_host_per_call_not_at_import(monkeypatch):
    """Ein beim Import eingefrorener Host würde eine Änderung zur Laufzeit verschlucken."""
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9999")
    assert llm_gate.ollama_host() == "http://127.0.0.1:9999"
    monkeypatch.setenv("OLLAMA_HOST", "http://88.99.38.75:11434")
    assert llm_gate.ollama_host() == "http://88.99.38.75:11434"
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    assert llm_gate.ollama_host() == llm_gate.DEFAULT_OLLAMA_HOST
