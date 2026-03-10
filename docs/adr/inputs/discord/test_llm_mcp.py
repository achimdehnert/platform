"""
tests/test_llm_mcp.py

Produktionsreife Tests für:
  - llm_mcp FastAPI Endpoint
  - Rate Limiter
  - Discord Message Chunker
  - Context Builder Secret-Filter
"""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

# ─── llm_mcp Tests ────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    # Settings vor Import patchen
    import os
    os.environ.setdefault("LLM_MCP_API_KEY", "test-key")
    os.environ.setdefault("LLM_MCP_OPENROUTER_API_KEY", "test-openrouter-key")

    from llm_mcp.main import app
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "model" in data
    assert data["uptime_s"] >= 0


def test_chat_requires_auth(client: TestClient) -> None:
    resp = client.post("/v1/chat", json={
        "message": "Test",
        "user_id": "123456",
    })
    assert resp.status_code == 401


def test_chat_invalid_api_key(client: TestClient) -> None:
    resp = client.post(
        "/v1/chat",
        json={"message": "Test", "user_id": "123456"},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert resp.status_code == 403


@respx.mock
def test_chat_success(client: TestClient) -> None:
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "choices": [{"message": {"content": "Testantwort"}}],
                "model": "openai/gpt-4o",
                "usage": {"total_tokens": 150},
            },
        )
    )

    resp = client.post(
        "/v1/chat",
        json={
            "message": "Was ist der Unterschied zwischen Layer 1 und Layer 2?",
            "user_id": "987654",
            "correlation_id": "test-001",
        },
        headers={"Authorization": "Bearer test-key"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "Testantwort"
    assert data["tokens_used"] == 150
    assert data["correlation_id"] == "test-001"
    assert data["latency_ms"] >= 0


@respx.mock
def test_chat_openrouter_retry_on_500(client: TestClient) -> None:
    """Bei OpenRouter 500 → 1x Retry → Erfolg."""
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return Response(500, json={"error": "Internal Server Error"})
        return Response(
            200,
            json={
                "choices": [{"message": {"content": "Retry erfolgreich"}}],
                "model": "openai/gpt-4o",
                "usage": {"total_tokens": 80},
            },
        )

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(side_effect=side_effect)

    resp = client.post(
        "/v1/chat",
        json={"message": "Test", "user_id": "111"},
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    assert call_count == 2, "Genau 1 Retry erwartet"


def test_chat_message_too_long(client: TestClient) -> None:
    resp = client.post(
        "/v1/chat",
        json={"message": "x" * 4001, "user_id": "111"},
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 422  # Pydantic Validation Error


# ─── Rate Limiter Tests ───────────────────────────────────────────────────────

def test_rate_limit_allows_burst():
    from orchestrator_mcp.discord.rate_limit import check_rate_limit, _buckets
    _buckets.clear()

    user_id = "test-user-rl"
    # Burst: 5 Anfragen erlaubt
    results = [check_rate_limit(user_id, "chat") for _ in range(5)]
    assert all(allowed for allowed, _ in results)

    # 6. Anfrage: Rate-Limited
    allowed, retry_after = check_rate_limit(user_id, "chat")
    assert not allowed
    assert retry_after > 0


def test_rate_limit_refills_over_time():
    from orchestrator_mcp.discord.rate_limit import check_rate_limit, _buckets, _Bucket
    import time

    user_id = "refill-test"
    _buckets.clear()
    # Bucket auf 0 setzen
    _buckets[f"{user_id}:chat"] = _Bucket(tokens=0.0, last_refill=time.monotonic() - 3.0)

    # Nach 3s bei 0.5/s → 1.5 Tokens → 1 Anfrage erlaubt
    allowed, _ = check_rate_limit(user_id, "chat")
    assert allowed


def test_rate_limit_different_commands_isolated():
    from orchestrator_mcp.discord.rate_limit import check_rate_limit, _buckets
    _buckets.clear()

    user_id = "isolation-test"
    # Deploy exhausten (capacity=2)
    for _ in range(2):
        check_rate_limit(user_id, "deploy")
    deploy_blocked, _ = check_rate_limit(user_id, "deploy")
    assert not deploy_blocked

    # Chat sollte unabhängig noch erlaubt sein
    chat_allowed, _ = check_rate_limit(user_id, "chat")
    assert chat_allowed


# ─── Discord Chunker Tests ────────────────────────────────────────────────────

def test_split_text_short():
    from orchestrator_mcp.discord.utils import _split_text
    text = "Kurzer Text"
    result = _split_text(text, 1990)
    assert result == [text]


def test_split_text_long():
    from orchestrator_mcp.discord.utils import _split_text
    text = "A" * 5000
    chunks = _split_text(text, 1990)
    assert len(chunks) == 3
    assert all(len(c) <= 1990 for c in chunks)
    assert "".join(chunks) == text


def test_split_text_preserves_content():
    from orchestrator_mcp.discord.utils import _split_text
    text = "\n".join(f"Zeile {i}" for i in range(200))
    limit = 500
    chunks = _split_text(text, limit)
    reassembled = "\n".join(chunks)
    # Inhalt vollständig (Leerzeilen können getrimmt werden)
    for i in range(200):
        assert f"Zeile {i}" in reassembled


# ─── Context Builder Secret Filter Tests ─────────────────────────────────────

def test_filter_secrets_removes_api_keys():
    from orchestrator_mcp.discord.context_builder import _filter_secrets
    text = "API_KEY=sk-abc123456789abcdef\nNormaler Text hier\nTOKEN: Bearer xyz789"
    result = _filter_secrets(text)
    assert "sk-abc123456789abcdef" not in result
    assert "Normaler Text hier" in result


def test_filter_secrets_removes_ips():
    from orchestrator_mcp.discord.context_builder import _filter_secrets
    text = "Server läuft auf 192.168.1.100:8080\nKeine IP hier"
    result = _filter_secrets(text)
    assert "192.168.1.100" not in result
    assert "Keine IP hier" in result


def test_filter_secrets_preserves_normal_text():
    from orchestrator_mcp.discord.context_builder import _filter_secrets
    text = "## Entscheidung\nWir nutzen Django 4.2 mit HTMX. Status: Accepted."
    result = _filter_secrets(text)
    assert "Django 4.2" in result
    assert "Status: Accepted" in result
