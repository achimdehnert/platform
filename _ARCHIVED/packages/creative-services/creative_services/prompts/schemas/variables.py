"""
Variable schema for prompt templates.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class VariableType(str, Enum):
    """Supported variable types for prompt templates."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    OBJECT = "object"


class PromptVariable(BaseModel):
    """
    Definition of a variable used in a prompt template.

    Variables are placeholders in the template that get replaced
    with actual values at execution time.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Variable name (snake_case, starts with letter)",
    )

    var_type: VariableType = Field(
        default=VariableType.STRING,
        description="Expected type of the variable value",
    )

    required: bool = Field(
        default=True,
        description="Whether this variable must be provided",
    )

    default: Any = Field(
        default=None,
        description="Default value if not provided (only for optional variables)",
    )

    description: str | None = Field(
        default=None,
        max_length=500,
        description="Human-readable description of the variable",
    )

    max_length: int | None = Field(
        default=None,
        ge=1,
        description="Maximum length for string variables",
    )

    allowed_values: list[Any] | None = Field(
        default=None,
        description="Whitelist of allowed values (enum-like constraint)",
    )

    sanitize: bool = Field(
        default=True,
        description="Whether to sanitize this variable's value",
    )

    check_injection: bool = Field(
        default=True,
        description="Whether to check for prompt injection",
    )

    @field_validator("default")
    @classmethod
    def default_only_for_optional(cls, v: Any, info) -> Any:
        """Ensure default is only set for optional variables."""
        if v is not None and info.data.get("required", True):
            raise ValueError("Default value can only be set for optional variables")
        return v

    @field_validator("allowed_values")
    @classmethod
    def allowed_values_not_empty(cls, v: list[Any] | None) -> list[Any] | None:
        """Ensure allowed_values is not an empty list."""
        if v is not None and len(v) == 0:
            raise ValueError("allowed_values cannot be an empty list")
        return v

    def validate_value(self, value: Any) -> tuple[bool, str | None]:
        """
        Validate a value against this variable's constraints.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Type check
        type_checks = {
            VariableType.STRING: lambda x: isinstance(x, str),
            VariableType.INTEGER: lambda x: isinstance(x, int) and not isinstance(x, bool),
            VariableType.FLOAT: lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
            VariableType.BOOLEAN: lambda x: isinstance(x, bool),
            VariableType.LIST: lambda x: isinstance(x, list),
            VariableType.OBJECT: lambda x: isinstance(x, dict),
        }

        if not type_checks[self.var_type](value):
            return False, f"Expected {self.var_type.value}, got {type(value).__name__}"

        # Length check for strings
        if self.var_type == VariableType.STRING and self.max_length:
            if len(value) > self.max_length:
                return False, f"String exceeds max length: {len(value)} > {self.max_length}"

        # Allowed values check
        if self.allowed_values is not None:
            if value not in self.allowed_values:
                return False, f"Value not in allowed values: {self.allowed_values}"

        return True, None

    model_config = {"frozen": True}
