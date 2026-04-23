"""Tests for structured MCP tool response helpers."""

from __future__ import annotations

import json

from mcp_governance.response import fail, from_ssh, ok


class TestOk:
    def test_should_return_success_envelope(self) -> None:
        result = json.loads(ok({"count": 5}))
        assert result["success"] is True
        assert result["data"] == {"count": 5}
        assert result["error"] is None

    def test_should_include_suggestion(self) -> None:
        result = json.loads(ok(suggestion="Next: list servers"))
        assert result["suggestion"] == "Next: list servers"

    def test_should_handle_none_data(self) -> None:
        result = json.loads(ok())
        assert result["success"] is True
        assert result["data"] is None


class TestFail:
    def test_should_return_error_envelope(self) -> None:
        result = json.loads(fail("Not found", code="NOT_FOUND"))
        assert result["success"] is False
        assert result["error"]["code"] == "NOT_FOUND"
        assert result["error"]["message"] == "Not found"

    def test_should_include_suggestion(self) -> None:
        result = json.loads(
            fail("Rate limited", suggestion="Retry in 60s")
        )
        assert result["suggestion"] == "Retry in 60s"

    def test_should_include_retryable(self) -> None:
        result = json.loads(
            fail("Timeout", retryable=True)
        )
        assert result["retryable"] is True

    def test_should_omit_retryable_when_none(self) -> None:
        result = json.loads(fail("Error"))
        assert "retryable" not in result

    def test_should_include_partial_data(self) -> None:
        result = json.loads(
            fail("Partial failure", data={"partial": True})
        )
        assert result["data"] == {"partial": True}


class TestFromSsh:
    def test_should_wrap_success(self) -> None:
        result = json.loads(
            from_ssh("output line", "", 0)
        )
        assert result["success"] is True
        assert result["data"] == "output line"

    def test_should_wrap_failure(self) -> None:
        result = json.loads(
            from_ssh("", "permission denied", 1)
        )
        assert result["success"] is False
        assert result["error"]["code"] == "exit_1"
        assert "permission denied" in result["error"]["message"]

    def test_should_parse_json_output(self) -> None:
        result = json.loads(
            from_ssh('{"key": "value"}', "", 0, parse_json=True)
        )
        assert result["data"] == {"key": "value"}

    def test_should_fallback_on_invalid_json(self) -> None:
        result = json.loads(
            from_ssh("not json", "", 0, parse_json=True)
        )
        assert result["data"] == "not json"
