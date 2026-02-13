"""MCP Tool Specification Standard for the BF Agent Platform.

Extends MCP native tool schema with platform governance metadata.
All schemas are Pydantic v2, immutable, JSON-serializable.

See ADR-010 §3.1 for details.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import ErrorPolicy, SideEffect, TenantMode, ToolCategory


class ParamSpec(BaseModel):
    """Extended parameter specification beyond JSON Schema."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Parameter name in snake_case",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description=(
            "Clear description for AI consumption"
            " — what it does, valid values, edge cases"
        ),
    )
    param_type: str = Field(
        ...,
        description=(
            "JSON Schema type: string, integer, number,"
            " boolean, array, object"
        ),
    )
    required: bool = Field(default=True)
    default: Any = Field(default=None)
    examples: list[Any] = Field(
        default_factory=list,
        description="Concrete examples for AI to understand usage",
    )
    sensitive: bool = Field(
        default=False,
        description="Contains PII or credentials — must not be logged",
    )

    model_config = ConfigDict(frozen=True)


class ReturnSpec(BaseModel):
    """Specification for tool return values."""

    description: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="What the tool returns on success",
    )
    schema_type: str = Field(
        default="object",
        description="JSON Schema type of the return value",
    )
    example: Any = Field(
        default=None,
        description="Example return value for AI consumption",
    )

    model_config = ConfigDict(frozen=True)


class ToolSpec(BaseModel):
    """Platform Tool Specification — the core governance schema.

    Extends MCP's native tool definition (name, description, inputSchema)
    with platform-specific metadata for governance, discovery, and
    composition.

    Design principles:
      - Additive to MCP — does NOT replace or wrap the MCP tool decorator
      - Pydantic v2 with frozen=True — immutable after creation
      - JSON-serializable — can be exported to registry files
    """

    # === Identity ===
    schema_version: str = Field(
        default="1.0",
        pattern=r"^\d+\.\d+$",
        description="ToolSpec schema version — for future migration",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
        description=(
            "Tool name — MUST match the @mcp.tool() function name"
        ),
    )
    server: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
        description=(
            "MCP server this tool belongs to"
            " (e.g., 'llm_mcp', 'travel_mcp')"
        ),
    )
    version: str = Field(
        default="1.0.0",
        pattern=r"^\d+\.\d+\.\d+$",
        description="Semantic version of this tool",
    )

    # === Documentation ===
    description: str = Field(
        ...,
        min_length=20,
        max_length=1000,
        description=(
            "AI-optimized description — what it does,"
            " when to use it, what to expect"
        ),
    )
    long_description: str | None = Field(
        default=None,
        max_length=5000,
        description="Extended documentation for human developers",
    )

    # === Classification ===
    category: ToolCategory = Field(
        ...,
        description="Platform tool category for discovery and grouping",
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=20,
        description=(
            "Free-form tags for search"
            " (e.g., ['llm', 'generation', 'openai'])"
        ),
    )
    domain_codes: list[str] = Field(
        default_factory=list,
        description=(
            "Which platform domains use this tool"
            " (e.g., ['writing', 'travel'])"
        ),
    )

    # === Parameters & Returns ===
    parameters: list[ParamSpec] = Field(
        default_factory=list,
        description=(
            "Extended parameter specs (supplements MCP inputSchema)"
        ),
    )
    returns: ReturnSpec | None = Field(
        default=None,
        description="Return value specification",
    )

    # === Platform Governance ===
    tenant_mode: TenantMode = Field(
        default=TenantMode.GLOBAL,
        description=(
            "Multi-tenancy behavior — critical for DSGVO compliance"
        ),
    )
    side_effects: list[SideEffect] = Field(
        default_factory=lambda: [SideEffect.NONE],
        description=(
            "Side effects this tool produces"
            " — for safety classification"
        ),
    )
    error_policy: ErrorPolicy = Field(
        default=ErrorPolicy.RESULT_OBJECT,
        description="How errors are reported",
    )
    idempotent: bool = Field(
        default=False,
        description=(
            "Can this tool be safely retried without side effects?"
        ),
    )
    estimated_duration_ms: int | None = Field(
        default=None,
        ge=0,
        description="Expected execution time in milliseconds",
    )

    # === Composition ===
    inputs_from: list[str] = Field(
        default_factory=list,
        description=(
            "Tools whose output can serve as input"
            " (for composition graph)"
        ),
    )
    outputs_to: list[str] = Field(
        default_factory=list,
        description="Tools that can consume this tool's output",
    )

    # === Status ===
    is_active: bool = Field(
        default=True,
        description="Whether this tool is currently available",
    )
    deprecated: bool = Field(
        default=False,
        description=(
            "Marked for removal — AI should prefer alternatives"
        ),
    )
    deprecated_by: str | None = Field(
        default=None,
        description="Replacement tool name if deprecated",
    )

    model_config = ConfigDict(frozen=True)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Lowercase, strip, and validate individual tag format."""
        cleaned: list[str] = []
        for tag in v:
            tag = tag.lower().strip()
            if len(tag) > 50:
                raise ValueError(
                    f"Tag too long (max 50 chars): {tag[:20]}..."
                )
            if not all(c.isalnum() or c in "-_" for c in tag):
                raise ValueError(
                    f"Tag must be alphanumeric/dash/underscore: {tag}"
                )
            cleaned.append(tag)
        return cleaned

    @field_validator("name")
    @classmethod
    def name_no_prefix(cls, v: str) -> str:
        """Tool names should not repeat the server name."""
        if v.endswith("_mcp"):
            raise ValueError(
                "Tool name should not include server suffix '_mcp'"
            )
        return v

    def qualified_name(self) -> str:
        """Fully qualified tool name: server.tool."""
        return f"{self.server}.{self.name}"
