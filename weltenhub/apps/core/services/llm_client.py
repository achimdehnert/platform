"""
Provider-agnostic LLM client for Weltenhub.

Adapted from travel-beat's llm_client for consistency across platform.
Supports OpenAI, Anthropic, and LLM Gateway endpoints.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
import structlog

logger = structlog.get_logger(__name__)

DEFAULT_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class LlmRequest:
    """Request configuration for LLM calls."""

    provider: str
    api_endpoint: str
    api_key: str
    model: Optional[str]
    system: str
    prompt: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000


def generate_text(req: LlmRequest) -> Dict[str, Any]:
    """
    Execute a text generation call and return a unified result dict.

    Returns:
        dict with keys: ok, text, raw, error, latency_ms
    """
    provider = (req.provider or "").lower()
    url = (req.api_endpoint or "").strip()
    start_time = time.time()

    if not url:
        return {
            "ok": False,
            "text": None,
            "raw": None,
            "error": "API endpoint is missing",
            "latency_ms": None,
        }

    headers = {"Content-Type": "application/json"}

    try:
        if "anthropic" in provider:
            return _call_anthropic(req, headers, start_time)
        elif "openai" in provider or "openrouter" in url.lower():
            return _call_openai_compatible(req, headers, start_time)
        elif "gateway" in url.lower() or "localhost:8100" in url:
            return _call_llm_gateway(req, headers, start_time)
        else:
            return _call_openai_compatible(req, headers, start_time)

    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "text": None,
            "raw": None,
            "error": f"Request timeout after {DEFAULT_TIMEOUT_SECONDS}s",
            "latency_ms": int((time.time() - start_time) * 1000),
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "ok": False,
            "text": None,
            "raw": None,
            "error": f"Connection error: {str(e)}",
            "latency_ms": int((time.time() - start_time) * 1000),
        }
    except Exception as e:
        logger.error("llm_client_error", error=str(e), provider=provider)
        return {
            "ok": False,
            "text": None,
            "raw": None,
            "error": str(e),
            "latency_ms": int((time.time() - start_time) * 1000),
        }


def _call_anthropic(
    req: LlmRequest, headers: Dict, start_time: float
) -> Dict[str, Any]:
    """Call Anthropic Claude API."""
    headers["x-api-key"] = req.api_key
    headers["anthropic-version"] = "2023-06-01"

    payload = {
        "model": req.model or "claude-3-5-haiku-20241022",
        "max_tokens": req.max_tokens or 1000,
        "messages": [{"role": "user", "content": req.prompt}],
    }

    if req.system:
        payload["system"] = req.system

    if req.temperature is not None:
        payload["temperature"] = req.temperature

    response = requests.post(
        req.api_endpoint,
        headers=headers,
        json=payload,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )

    latency_ms = int((time.time() - start_time) * 1000)

    if response.status_code != 200:
        return {
            "ok": False,
            "text": None,
            "raw": response.text,
            "error": f"Anthropic API error: {response.status_code}",
            "latency_ms": latency_ms,
        }

    data = response.json()
    content = ""
    if data.get("content"):
        for block in data["content"]:
            if block.get("type") == "text":
                content += block.get("text", "")

    return {
        "ok": True,
        "text": content,
        "raw": data,
        "error": None,
        "latency_ms": latency_ms,
    }


def _call_openai_compatible(
    req: LlmRequest, headers: Dict, start_time: float
) -> Dict[str, Any]:
    """Call OpenAI-compatible API (OpenAI, OpenRouter, etc.)."""
    headers["Authorization"] = f"Bearer {req.api_key}"

    messages = []
    if req.system:
        messages.append({"role": "system", "content": req.system})
    messages.append({"role": "user", "content": req.prompt})

    payload = {
        "model": req.model or "gpt-4o-mini",
        "messages": messages,
        "max_tokens": req.max_tokens or 1000,
    }

    if req.temperature is not None:
        payload["temperature"] = req.temperature

    response = requests.post(
        req.api_endpoint,
        headers=headers,
        json=payload,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )

    latency_ms = int((time.time() - start_time) * 1000)

    if response.status_code != 200:
        return {
            "ok": False,
            "text": None,
            "raw": response.text,
            "error": f"OpenAI API error: {response.status_code}",
            "latency_ms": latency_ms,
        }

    data = response.json()
    content = ""
    if data.get("choices"):
        content = data["choices"][0].get("message", {}).get("content", "")

    return {
        "ok": True,
        "text": content,
        "raw": data,
        "error": None,
        "latency_ms": latency_ms,
    }


def _call_llm_gateway(
    req: LlmRequest, headers: Dict, start_time: float
) -> Dict[str, Any]:
    """Call local LLM Gateway."""
    payload = {
        "model": req.model,
        "max_tokens": req.max_tokens or 1000,
        "temperature": req.temperature or 0.7,
        "system_prompt": req.system,
        "prompt": req.prompt,
    }

    response = requests.post(
        f"{req.api_endpoint}/generate",
        headers=headers,
        json=payload,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )

    latency_ms = int((time.time() - start_time) * 1000)

    if response.status_code != 200:
        return {
            "ok": False,
            "text": None,
            "raw": response.text,
            "error": f"LLM Gateway error: {response.status_code}",
            "latency_ms": latency_ms,
        }

    data = response.json()
    content = data.get("content", "")

    return {
        "ok": True,
        "text": content,
        "raw": data,
        "error": None,
        "latency_ms": latency_ms,
    }
