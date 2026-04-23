"""Tests for ToolSpec, ParamSpec, ReturnSpec Pydantic models."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from mcp_governance.spec.enums import (
    ErrorPolicy,
    SideEffect,
    TenantMode,
    ToolCategory,
)
from mcp_governance.spec.models import ParamSpec, ReturnSpec, ToolSpec


# ── ParamSpec ────────────────────────────────────────────────────────


class TestParamSpec:
    def test_should_create_valid_param(self) -> None:
        p = ParamSpec(
            name="host",
            description="Target hostname or IP address for SSH",
            param_type="string",
        )
        assert p.name == "host"
        assert p.required is True
        assert p.sensitive is False

    def test_should_reject_invalid_name(self) -> None:
        with pytest.raises(ValidationError, match="pattern"):
            ParamSpec(
                name="HostName",
                description="Invalid uppercase name for testing",
                param_type="string",
            )

    def test_should_reject_short_description(self) -> None:
        with pytest.raises(ValidationError, match="too_short"):
            ParamSpec(
                name="host",
                description="Too short",
                param_type="string",
            )

    def test_should_be_frozen(self) -> None:
        p = ParamSpec(
            name="host",
            description="Target hostname or IP address for SSH",
            param_type="string",
        )
        with pytest.raises(ValidationError):
            p.name = "other"


# ── ReturnSpec ───────────────────────────────────────────────────────


class TestReturnSpec:
    def test_should_create_valid_return(self) -> None:
        r = ReturnSpec(
            description="JSON object with server status and metrics",
        )
        assert r.schema_type == "object"
        assert r.example is None

    def test_should_be_frozen(self) -> None:
        r = ReturnSpec(
            description="JSON object with server status and metrics",
        )
        with pytest.raises(ValidationError):
            r.description = "changed"


# ── ToolSpec ─────────────────────────────────────────────────────────


def _make_tool(**overrides: object) -> ToolSpec:
    """Create a minimal valid ToolSpec with optional overrides."""
    defaults: dict = {
        "name": "docker_manage",
        "server": "deployment_mcp",
        "description": (
            "Manage Docker containers and compose stacks"
            " on remote servers via SSH"
        ),
        "category": ToolCategory.DEVOPS_DEPLOY,
    }
    defaults.update(overrides)
    return ToolSpec(**defaults)


class TestToolSpec:
    def test_should_create_minimal_tool(self) -> None:
        t = _make_tool()
        assert t.name == "docker_manage"
        assert t.schema_version == "1.0"
        assert t.version == "1.0.0"
        assert t.tenant_mode == TenantMode.GLOBAL
        assert t.error_policy == ErrorPolicy.RESULT_OBJECT
        assert t.is_active is True
        assert t.deprecated is False

    def test_should_generate_qualified_name(self) -> None:
        t = _make_tool()
        assert t.qualified_name() == "deployment_mcp.docker_manage"

    def test_should_reject_mcp_suffix_in_name(self) -> None:
        with pytest.raises(
            ValidationError, match="server suffix"
        ):
            _make_tool(name="deployment_mcp")

    def test_should_lowercase_tags(self) -> None:
        t = _make_tool(tags=["Docker", "COMPOSE", "ssh"])
        assert t.tags == ["docker", "compose", "ssh"]

    def test_should_reject_invalid_tag_chars(self) -> None:
        with pytest.raises(
            ValidationError, match="alphanumeric"
        ):
            _make_tool(tags=["docker compose"])

    def test_should_reject_long_tags(self) -> None:
        with pytest.raises(ValidationError, match="Tag too long"):
            _make_tool(tags=["a" * 51])

    def test_should_serialize_to_json(self) -> None:
        t = _make_tool(tags=["docker", "devops"])
        data = json.loads(t.model_dump_json())
        assert data["name"] == "docker_manage"
        assert data["server"] == "deployment_mcp"
        assert data["category"] == "devops.deploy"
        assert data["tags"] == ["docker", "devops"]
        assert data["schema_version"] == "1.0"

    def test_should_roundtrip_json(self) -> None:
        original = _make_tool(
            tags=["docker"],
            tenant_mode=TenantMode.TENANT_AWARE,
            side_effects=[SideEffect.DEPLOYMENT],
        )
        json_str = original.model_dump_json()
        restored = ToolSpec.model_validate_json(json_str)
        assert restored == original

    def test_should_be_frozen(self) -> None:
        t = _make_tool()
        with pytest.raises(ValidationError):
            t.name = "other"

    def test_should_reject_short_description(self) -> None:
        with pytest.raises(ValidationError, match="too_short"):
            _make_tool(description="Too short")

    def test_should_accept_all_categories(self) -> None:
        for cat in ToolCategory:
            t = _make_tool(category=cat)
            assert t.category == cat
