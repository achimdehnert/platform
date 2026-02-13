"""Tests for ToolSpec validator and registry validation."""

from __future__ import annotations

from mcp_governance.spec.enums import (
    TenantMode,
    ToolCategory,
)
from mcp_governance.spec.models import ParamSpec, ReturnSpec, ToolSpec
from mcp_governance.spec.validator import (
    validate_registry,
    validate_spec,
)


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


class TestValidateSpec:
    def test_should_pass_minimal_valid_spec(self) -> None:
        result = validate_spec(_make_tool())
        assert result.is_valid
        assert len(result.warnings) >= 1

    def test_should_warn_no_params(self) -> None:
        result = validate_spec(_make_tool())
        warnings = " ".join(result.warnings)
        assert "parameter" in warnings.lower()

    def test_should_warn_no_return_spec(self) -> None:
        result = validate_spec(_make_tool())
        warnings = " ".join(result.warnings)
        assert "return" in warnings.lower()

    def test_should_warn_deprecated_without_replacement(self) -> None:
        result = validate_spec(
            _make_tool(deprecated=True, deprecated_by=None)
        )
        warnings = " ".join(result.warnings)
        assert "replacement" in warnings.lower()

    def test_should_not_warn_deprecated_with_replacement(self) -> None:
        result = validate_spec(
            _make_tool(
                deprecated=True,
                deprecated_by="new_docker_manage",
            )
        )
        dep_warnings = [
            w for w in result.warnings if "replacement" in w.lower()
        ]
        assert len(dep_warnings) == 0

    def test_should_warn_tenant_aware_without_tags(self) -> None:
        result = validate_spec(
            _make_tool(
                tenant_mode=TenantMode.TENANT_AWARE,
                tags=[],
            )
        )
        warnings = " ".join(result.warnings)
        assert "tag" in warnings.lower()

    def test_should_pass_complete_spec(self) -> None:
        spec = _make_tool(
            parameters=[
                ParamSpec(
                    name="container_id",
                    description=(
                        "Docker container ID or name to manage"
                    ),
                    param_type="string",
                    examples=["bfagent-web-1", "abc123def"],
                ),
            ],
            returns=ReturnSpec(
                description=(
                    "JSON object with container status"
                    " and resource usage"
                ),
                example={"status": "running", "cpu": "2.3%"},
            ),
            tags=["docker", "devops"],
        )
        result = validate_spec(spec)
        assert result.is_valid
        assert len(result.warnings) == 0


class TestValidateRegistry:
    def test_should_detect_duplicates(self) -> None:
        specs = [_make_tool(), _make_tool()]
        results = validate_registry(specs)
        errors = [
            r for r in results
            if any("Duplicate" in e for e in r.errors)
        ]
        assert len(errors) == 1

    def test_should_validate_composition_refs(self) -> None:
        specs = [
            _make_tool(
                inputs_from=["nonexistent_tool"],
            ),
        ]
        results = validate_registry(specs)
        warnings = []
        for r in results:
            warnings.extend(r.warnings)
        ref_warnings = [
            w for w in warnings if "not found" in w.lower()
        ]
        assert len(ref_warnings) == 1

    def test_should_pass_valid_registry(self) -> None:
        specs = [
            _make_tool(name="docker_manage"),
            _make_tool(name="ssh_manage", server="deployment_mcp"),
            _make_tool(
                name="generate_text",
                server="llm_mcp",
                category=ToolCategory.AI_LLM,
                description=(
                    "Generate text using LLM providers"
                    " like OpenAI or Anthropic"
                ),
            ),
        ]
        results = validate_registry(specs)
        errors = [r for r in results if not r.is_valid]
        assert len(errors) == 0
