"""Test that the deployment_mcp pilot toolspec validates correctly."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from mcp_governance.spec.validator import validate_registry, validate_spec


def _load_pilot_specs():
    """Load TOOLS from the deployment_mcp toolspec.py."""
    # tests/ -> mcp-governance/ -> packages/ -> platform/ -> github/
    github_root = Path(__file__).resolve().parents[4]
    toolspec_path = (
        github_root
        / "mcp-hub"
        / "deployment_mcp"
        / "toolspec.py"
    )
    spec = importlib.util.spec_from_file_location(
        "toolspec", toolspec_path,
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.TOOLS


class TestDeploymentMcpToolspec:
    def test_should_load_all_specs(self) -> None:
        specs = _load_pilot_specs()
        assert len(specs) == 11

    def test_should_validate_all_specs(self) -> None:
        specs = _load_pilot_specs()
        for spec in specs:
            result = validate_spec(spec)
            assert result.is_valid, (
                f"{spec.qualified_name()}: {result.errors}"
            )

    def test_should_all_belong_to_deployment_mcp(self) -> None:
        specs = _load_pilot_specs()
        for spec in specs:
            assert spec.server == "deployment_mcp"

    def test_should_have_unique_names(self) -> None:
        specs = _load_pilot_specs()
        names = [s.name for s in specs]
        assert len(names) == len(set(names))

    def test_should_pass_registry_validation(self) -> None:
        specs = _load_pilot_specs()
        results = validate_registry(specs)
        errors = [r for r in results if not r.is_valid]
        assert len(errors) == 0, (
            f"Registry errors: {[r.errors for r in errors]}"
        )

    def test_should_have_parameters_and_returns(self) -> None:
        specs = _load_pilot_specs()
        for spec in specs:
            assert len(spec.parameters) >= 1, (
                f"{spec.name} has no parameters"
            )
            assert spec.returns is not None, (
                f"{spec.name} has no return spec"
            )
