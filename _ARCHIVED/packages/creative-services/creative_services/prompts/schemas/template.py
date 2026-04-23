"""
Prompt Template Spec schema - the core template definition.
"""

from pydantic import BaseModel, Field, field_validator

from .variables import PromptVariable
from .llm_config import LLMConfig


class PromptTemplateSpec(BaseModel):
    """
    Specification for a prompt template.

    This is the core schema that defines a reusable prompt template.
    Templates are immutable after creation - use model_copy() for modifications.

    Example:
        template = PromptTemplateSpec(
            template_key="character.backstory.v1",
            domain_code="writing",
            system_prompt="You are a creative writing assistant...",
            user_prompt="Create a backstory for {{ character_name }}...",
            variables=[
                PromptVariable(name="character_name", required=True),
                PromptVariable(name="genre", required=False, default="fantasy"),
            ],
        )

        # To modify, create a new version:
        new_template = template.model_copy(update={"is_active": False})
    """

    # === Identity ===
    template_key: str = Field(
        ...,
        min_length=3,
        max_length=200,
        pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$",
        description="Unique key: domain.category.name.version (e.g., 'writing.character.backstory.v1')",
    )

    domain_code: str = Field(
        ...,
        min_length=2,
        max_length=50,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Domain code for validation (e.g., 'writing', 'cad', 'support')",
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Human-readable name",
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Detailed description of what this template does",
    )

    category: str | None = Field(
        default=None,
        max_length=100,
        description="Category for organization (e.g., 'character', 'chapter', 'analysis')",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Tags for filtering and search",
    )

    # === Versioning ===
    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for migration support",
    )

    # === Prompts ===
    system_prompt: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="System prompt (Jinja2 template)",
    )

    user_prompt: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="User prompt (Jinja2 template)",
    )

    # === Variables ===
    variables: list[PromptVariable] = Field(
        default_factory=list,
        description="Variable definitions for this template",
    )

    # === LLM Configuration ===
    llm_config: LLMConfig = Field(
        default_factory=LLMConfig,
        description="LLM configuration (tier, parameters, retry)",
    )

    # === Inheritance ===
    parent_key: str | None = Field(
        default=None,
        description="Parent template key for inheritance",
    )

    # === Security ===
    sanitize_user_input: bool = Field(
        default=True,
        description="Whether to sanitize user-provided variables",
    )

    max_variable_length: int = Field(
        default=10000,
        ge=100,
        le=100000,
        description="Maximum length for any single variable value",
    )

    check_injection: bool = Field(
        default=True,
        description="Whether to check for prompt injection attempts",
    )

    # === Experimentation ===
    experiment_variant: str | None = Field(
        default=None,
        max_length=50,
        description="A/B test variant identifier",
    )

    # === Cost Control ===
    max_cost_per_execution: float | None = Field(
        default=None,
        ge=0.0,
        description="Maximum cost in dollars per execution",
    )

    daily_quota_key: str | None = Field(
        default=None,
        description="Key for daily quota tracking",
    )

    # === Tracking ===
    track_executions: str = Field(
        default="sample",
        pattern=r"^(none|sample|all)$",
        description="Execution tracking mode: none, sample, all",
    )

    sample_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Sample rate for execution tracking (when track_executions='sample')",
    )

    # === Metadata ===
    author: str | None = Field(
        default=None,
        max_length=200,
        description="Author of this template",
    )

    is_active: bool = Field(
        default=True,
        description="Whether this template is active and usable",
    )

    # Immutability: Templates are immutable after creation.
    # For modifications: template.model_copy(update={"is_active": False})
    model_config = {"frozen": True}

    # === Validators ===

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Ensure tags are lowercase and valid."""
        validated = []
        for tag in v:
            tag = tag.lower().strip()
            if tag and len(tag) <= 50:
                validated.append(tag)
        return list(set(validated))  # Remove duplicates

    @field_validator("variables")
    @classmethod
    def validate_unique_variable_names(cls, v: list[PromptVariable]) -> list[PromptVariable]:
        """Ensure variable names are unique."""
        names = [var.name for var in v]
        if len(names) != len(set(names)):
            duplicates = [n for n in names if names.count(n) > 1]
            raise ValueError(f"Duplicate variable names: {set(duplicates)}")
        return v

    # === Helper Methods ===

    def get_variable_defaults(self) -> dict:
        """Get default values for all variables that have them."""
        return {v.name: v.default for v in self.variables if v.default is not None}

    def get_required_variables(self) -> list[str]:
        """Get names of all required variables."""
        return [v.name for v in self.variables if v.required]

    def get_optional_variables(self) -> list[str]:
        """Get names of all optional variables."""
        return [v.name for v in self.variables if not v.required]

    def get_variable(self, name: str) -> PromptVariable | None:
        """Get a variable definition by name."""
        for v in self.variables:
            if v.name == name:
                return v
        return None

    def has_variable(self, name: str) -> bool:
        """Check if a variable exists in this template."""
        return any(v.name == name for v in self.variables)
