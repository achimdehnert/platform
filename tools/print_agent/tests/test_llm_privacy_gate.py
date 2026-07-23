"""Datenschutz-Gate fürs LLM-Enrichment (#1297).

Kern-Invariante: Ohne ausdrückliches Opt-in (PRINT_AGENT_ALLOW_EXTERNAL=1) darf
_try_completion für einen externen Anbieter litellm NIE aufrufen — der
Dokumentinhalt verlässt die Maschine dann nicht. Lokale Ollama-Modelle laufen
key-frei gegen den lokalen Host.
"""
import sys
from pathlib import Path

import pytest

pytest.importorskip("weasyprint")
pytest.importorskip("litellm")
pytest.importorskip("markdown")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import print_agent  # noqa: E402


def test_should_classify_ollama_as_local():
    assert print_agent._is_local_model("ollama/qwen2.5:3b") is True
    assert print_agent._is_local_model("ollama_chat/qwen2.5:7b") is True
    assert print_agent._is_local_model("cerebras/llama3.1-8b") is False
    assert print_agent._is_local_model("groq/llama-3.1-8b-instant") is False


def test_should_default_to_local_ollama():
    assert print_agent._DEFAULT_PRIMARY.startswith("ollama/")
    assert print_agent._DEFAULT_FALLBACK == ""


def _record_calls(monkeypatch):
    """Zeichnet litellm-Aufrufe auf, statt in ihnen zu werfen.

    Eine ``raise AssertionError``-Attrappe taugt hier NICHT: ``_try_completion``
    umschließt den Aufruf mit ``try/except Exception`` und gibt bei jedem Fehler
    ``None`` zurück. Ein unerlaubter Call sähe damit exakt wie ein sauberes
    Überspringen aus — der Test wäre vakuum und könnte eine Regression im Gate
    nicht erkennen (real gegengeprüft: mit Wächter-Attrappe lief der Fall auch
    ohne Gate grün durch).
    """
    calls = []

    def _fake(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("kein echter LLM-Call im Test")

    monkeypatch.setattr(print_agent.litellm, "completion", _fake)
    return calls


def test_should_skip_external_without_optin(monkeypatch):
    monkeypatch.delenv("PRINT_AGENT_ALLOW_EXTERNAL", raising=False)
    calls = _record_calls(monkeypatch)
    assert print_agent._try_completion("groq/llama-3.1-8b-instant", "hi") is None
    assert calls == [], "litellm.completion für externen Anbieter ohne Opt-in aufgerufen"


def test_should_allow_external_with_optin_but_still_need_key(monkeypatch):
    monkeypatch.setenv("PRINT_AGENT_ALLOW_EXTERNAL", "1")
    monkeypatch.setattr(print_agent, "get_secret", lambda name: None)
    calls = _record_calls(monkeypatch)
    # Opt-in gesetzt, aber kein Key -> sauber übersprungen, kein Call
    assert print_agent._try_completion("groq/llama-3.1-8b-instant", "hi") is None
    assert calls == [], "litellm.completion ohne API-Key aufgerufen"


def test_should_call_ollama_without_key_and_with_api_base(monkeypatch):
    captured = {}

    class _Msg:
        content = '{"summary": "s", "keywords": ["a"]}'

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    def _fake(**kwargs):
        captured.update(kwargs)
        return _Resp()

    monkeypatch.delenv("PRINT_AGENT_ALLOW_EXTERNAL", raising=False)
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    monkeypatch.setattr(print_agent.litellm, "completion", _fake)
    out = print_agent._try_completion("ollama/qwen2.5:3b", "hi")
    assert out == {"summary": "s", "keywords": ["a"]}
    assert "api_key" not in captured          # lokal: kein Key
    # Literal statt Modulkonstante: ein Vergleich mit sich selbst könnte einen
    # falschen Host nicht auffangen.
    assert captured.get("api_base") == "http://127.0.0.1:11434"


def test_should_skip_remote_ollama_without_optin(monkeypatch):
    """ollama/ allein ist keine Zusage — ein entfernter Host trägt den Inhalt fort."""
    monkeypatch.delenv("PRINT_AGENT_ALLOW_EXTERNAL", raising=False)
    monkeypatch.setenv("OLLAMA_HOST", "http://88.99.38.75:11434")
    calls = _record_calls(monkeypatch)
    assert print_agent._try_completion("ollama/qwen2.5:3b", "hi") is None
    assert calls == [], "litellm.completion gegen entfernten Ollama ohne Opt-in aufgerufen"
