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


def test_should_skip_external_without_optin(monkeypatch):
    monkeypatch.delenv("PRINT_AGENT_ALLOW_EXTERNAL", raising=False)

    def _boom(*a, **k):  # litellm darf hier gar nicht erreicht werden
        raise AssertionError("litellm.completion für externen Anbieter ohne Opt-in aufgerufen")

    monkeypatch.setattr(print_agent.litellm, "completion", _boom)
    assert print_agent._try_completion("groq/llama-3.1-8b-instant", "hi") is None


def test_should_allow_external_with_optin_but_still_need_key(monkeypatch):
    monkeypatch.setenv("PRINT_AGENT_ALLOW_EXTERNAL", "1")
    monkeypatch.setattr(print_agent, "get_secret", lambda name: None)

    def _boom(*a, **k):  # ohne Key darf kein Call rausgehen
        raise AssertionError("litellm.completion ohne API-Key aufgerufen")

    monkeypatch.setattr(print_agent.litellm, "completion", _boom)
    # Opt-in gesetzt, aber kein Key -> sauber übersprungen, kein Call
    assert print_agent._try_completion("groq/llama-3.1-8b-instant", "hi") is None


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

    monkeypatch.setattr(print_agent.litellm, "completion", _fake)
    out = print_agent._try_completion("ollama/qwen2.5:3b", "hi")
    assert out == {"summary": "s", "keywords": ["a"]}
    assert "api_key" not in captured          # lokal: kein Key
    assert captured.get("api_base") == print_agent._OLLAMA_HOST
