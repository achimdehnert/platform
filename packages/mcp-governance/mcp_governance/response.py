"""Structured MCP tool response helpers.

Provides a consistent JSON envelope for all tool responses so that
AI consumers can reliably parse success/failure, extract data, and
act on suggestions without ad-hoc string parsing.

Extracted from ``deployment_mcp/response.py`` and promoted to shared
platform package per ADR-010 §3.4.

Envelope schema::

    {
        "success": true,
        "data": { ... },
        "error": null,
        "suggestion": null
    }
"""

from __future__ import annotations

import json
from typing import Any


def ok(
    data: Any = None,
    *,
    suggestion: str | None = None,
) -> str:
    """Return a successful structured response."""
    return json.dumps(
        {
            "success": True,
            "data": data,
            "error": None,
            "suggestion": suggestion,
        },
        indent=2,
        default=str,
    )


def fail(
    message: str,
    *,
    code: str = "error",
    data: Any = None,
    suggestion: str | None = None,
    retryable: bool | None = None,
) -> str:
    """Return a failure structured response."""
    payload: dict[str, Any] = {
        "success": False,
        "data": data,
        "error": {"code": code, "message": message},
        "suggestion": suggestion,
    }
    if retryable is not None:
        payload["retryable"] = retryable
    return json.dumps(payload, indent=2, default=str)


def from_ssh(
    stdout: str,
    stderr: str,
    exit_code: int,
    *,
    parse_json: bool = False,
) -> str:
    """Build a structured response from SSH command output.

    If *parse_json* is True the stdout is decoded as JSON and
    placed under ``data``; otherwise the raw string is returned.
    """
    if exit_code != 0:
        return fail(
            stderr.strip() or "Command failed",
            code=f"exit_{exit_code}",
            suggestion="Check command syntax or server state.",
        )

    payload: Any = stdout.strip()
    if parse_json and payload:
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            pass

    return ok(payload)
