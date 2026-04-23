"""ToolSpec validation and compliance checking.

Validates individual ToolSpecs and entire registries for consistency.
Used by CI pipeline (``mcp_governance.registry.build``) to enforce
quality gates before deployment.

See ADR-010 §3.3 for details.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import ToolSpec


@dataclass
class ValidationResult:
    """Result of validating a single ToolSpec."""

    tool_name: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True if no errors (warnings are acceptable)."""
        return len(self.errors) == 0


def validate_spec(spec: ToolSpec) -> ValidationResult:
    """Validate a single ToolSpec for completeness and quality."""
    result = ValidationResult(tool_name=spec.qualified_name())

    if not spec.description or len(spec.description) < 20:
        result.errors.append(
            "Description must be at least 20 characters"
            " for meaningful AI consumption"
        )

    if spec.tenant_mode.value != "global" and not spec.tags:
        result.warnings.append(
            "Tenant-aware tools should have tags for discovery"
        )

    if not spec.parameters:
        result.warnings.append(
            "No extended parameter specs provided"
            " — AI may lack usage context"
        )

    if spec.returns is None:
        result.warnings.append(
            "No return spec — AI cannot predict output format"
        )

    if spec.deprecated and not spec.deprecated_by:
        result.warnings.append(
            "Deprecated tool should specify a replacement"
            " via deprecated_by"
        )

    for param in spec.parameters:
        if not param.examples:
            result.warnings.append(
                f"Parameter '{param.name}' has no examples"
                " — AI tool selection may be less accurate"
            )

    return result


def validate_registry(specs: list[ToolSpec]) -> list[ValidationResult]:
    """Validate an entire registry of ToolSpecs."""
    results: list[ValidationResult] = []

    for spec in specs:
        results.append(validate_spec(spec))

    seen: set[str] = set()
    for spec in specs:
        name = spec.qualified_name()
        if name in seen:
            results.append(
                ValidationResult(
                    tool_name=name,
                    errors=[f"Duplicate qualified name: {name}"],
                )
            )
        seen.add(name)

    all_tool_names = {s.name for s in specs}
    for spec in specs:
        for ref in spec.inputs_from + spec.outputs_to:
            if ref not in all_tool_names:
                for r in results:
                    if r.tool_name == spec.qualified_name():
                        r.warnings.append(
                            f"Composition reference '{ref}'"
                            " not found in registry"
                        )

    return results
