"""
Pydantic Configuration Models for Handlers
Type-safe handler configuration with IDE support and validation
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============================================================================
# BASE MODELS
# ============================================================================


class BaseHandlerConfig(BaseModel):
    """Base configuration for all handlers with strict validation"""

    model_config = ConfigDict(
        extra="forbid",  # Reject unknown fields
        validate_assignment=True,  # Validate on attribute assignment
        strict=True,  # Strict type checking
        frozen=False,  # Allow mutation (for flexibility)
    )


# ============================================================================
# INPUT HANDLER CONFIGS
# ============================================================================


class ProjectFieldsConfig(BaseHandlerConfig):
    """Configuration for ProjectFieldsInputHandler"""

    fields: List[str] = Field(
        ...,
        description="List of project fields to load",
        min_length=1,
        examples=[["book_title", "author_name"]],
    )
    include_metadata: bool = Field(default=False, description="Include field metadata in output")

    @field_validator("fields")
    @classmethod
    def validate_field_names(cls, v: List[str]) -> List[str]:
        """Ensure field names are valid"""
        for field in v:
            if not field.replace("_", "").isalnum():
                raise ValueError(f"Invalid field name: {field}")
        return v


class ChapterDataConfig(BaseHandlerConfig):
    """Configuration for ChapterDataHandler"""

    chapter_id: Optional[int] = Field(
        default=None, description="Specific chapter ID to load. If None, load from context"
    )
    load_full_content: bool = Field(default=True, description="Load full chapter content")
    include_related: bool = Field(
        default=False, description="Include related characters and locations"
    )


class CharacterDataConfig(BaseHandlerConfig):
    """Configuration for CharacterDataHandler"""

    character_ids: Optional[List[int]] = Field(
        default=None, description="Specific character IDs to load. If None, load all"
    )
    load_full_profile: bool = Field(default=True, description="Load complete character profiles")
    include_relationships: bool = Field(
        default=False, description="Include character relationships"
    )


class UserInputConfig(BaseHandlerConfig):
    """Configuration for UserInputHandler"""

    prompt: str = Field(..., description="Prompt to show user", min_length=1)
    input_type: Literal["text", "textarea", "number", "select"] = Field(
        default="text", description="Type of input to collect"
    )
    required: bool = Field(default=True, description="Whether input is required")
    default_value: Optional[str] = Field(default=None, description="Default value")
    validation_regex: Optional[str] = Field(
        default=None, description="Regex pattern for validation"
    )


class WorldDataConfig(BaseHandlerConfig):
    """Configuration for WorldDataHandler"""

    load_locations: bool = Field(default=True, description="Load location data")
    load_rules: bool = Field(default=True, description="Load world rules and physics")
    load_history: bool = Field(default=False, description="Load historical events")


# ============================================================================
# PROCESSING HANDLER CONFIGS
# ============================================================================


class TemplateRendererConfig(BaseHandlerConfig):
    """Configuration for TemplateRendererHandler"""

    template: str = Field(..., description="Mustache-style template string", min_length=1)
    strict_mode: bool = Field(default=True, description="Raise error on missing variables")
    escape_html: bool = Field(default=False, description="Escape HTML in output")


class LLMProcessorConfig(BaseHandlerConfig):
    """Configuration for LLM Processing Handler"""

    model: str = Field(
        default="gpt-4",
        description="LLM model to use",
        examples=["gpt-4", "gpt-3.5-turbo", "claude-3-sonnet"],
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for sampling (0.0 = deterministic, 2.0 = very random)",
    )
    max_tokens: int = Field(default=2000, gt=0, le=8000, description="Maximum tokens to generate")
    system_prompt: Optional[str] = Field(default=None, description="System prompt to set context")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Nucleus sampling threshold")
    frequency_penalty: float = Field(
        default=0.0, ge=-2.0, le=2.0, description="Frequency penalty (-2.0 to 2.0)"
    )
    presence_penalty: float = Field(
        default=0.0, ge=-2.0, le=2.0, description="Presence penalty (-2.0 to 2.0)"
    )
    stop_sequences: Optional[List[str]] = Field(
        default=None, description="Stop sequences for generation"
    )


class FrameworkGeneratorConfig(BaseHandlerConfig):
    """Configuration for FrameworkGeneratorHandler"""

    framework: Literal["heros_journey", "three_act", "save_the_cat", "freytag"] = Field(
        default="three_act", description="Story framework to use"
    )
    detail_level: Literal["minimal", "standard", "detailed"] = Field(
        default="standard", description="Level of detail in output"
    )
    include_examples: bool = Field(default=True, description="Include examples for each beat")


# ============================================================================
# OUTPUT HANDLER CONFIGS
# ============================================================================


class SimpleTextFieldConfig(BaseHandlerConfig):
    """Configuration for SimpleTextFieldHandler"""

    field_name: str = Field(..., description="Name of field to update", min_length=1)
    model_name: str = Field(default="Chapter", description="Django model name to update")
    overwrite: bool = Field(default=True, description="Overwrite existing value if present")
    append: bool = Field(default=False, description="Append to existing value instead of replacing")
    separator: str = Field(default="\n\n", description="Separator to use when appending")


class ChapterCreatorConfig(BaseHandlerConfig):
    """Configuration for ChapterCreatorHandler"""

    auto_number: bool = Field(default=True, description="Automatically assign chapter number")
    set_as_current: bool = Field(default=True, description="Set as current active chapter")
    include_metadata: bool = Field(default=True, description="Include generation metadata")


class MarkdownFileConfig(BaseHandlerConfig):
    """Configuration for MarkdownExporter"""

    output_dir: str = Field(..., description="Directory to save markdown files")
    filename_template: str = Field(
        default="{title}.md", description="Template for filename (can use context variables)"
    )
    include_frontmatter: bool = Field(default=True, description="Include YAML frontmatter")
    frontmatter_fields: List[str] = Field(
        default_factory=lambda: ["title", "author", "date"],
        description="Fields to include in frontmatter",
    )
    overwrite_existing: bool = Field(default=False, description="Overwrite existing files")


# ============================================================================
# HANDLER GENERATOR CONFIGS
# ============================================================================


class HandlerRequirements(BaseModel):
    """Requirements for generating a new handler"""

    handler_id: str = Field(
        ..., pattern=r"^[a-z][a-z0-9_]*$", description="Handler identifier (snake_case)"
    )
    display_name: str = Field(..., min_length=3, description="Human-readable name")
    description: str = Field(..., min_length=10, description="What the handler does")
    category: Literal["input", "processing", "output"] = Field(..., description="Handler category")
    dependencies: List[str] = Field(default_factory=list, description="Python package dependencies")
    config_parameters: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Configuration parameters with types and defaults"
    )
    input_requirements: List[str] = Field(
        default_factory=list, description="Required inputs from context"
    )
    output_format: Dict[str, str] = Field(
        default_factory=dict, description="Expected output structure"
    )
    error_scenarios: Dict[str, str] = Field(
        default_factory=dict, description="Error conditions and handling"
    )


class GeneratedHandler(BaseModel):
    """Generated handler code and metadata"""

    handler_code: str = Field(..., description="Complete Python handler class code")
    config_model_code: str = Field(..., description="Pydantic config model code")
    test_code: str = Field(..., description="Complete pytest test suite")
    documentation: str = Field(..., description="Markdown documentation")
    example_usage: str = Field(..., description="Example usage code")


class HandlerValidation(BaseModel):
    """Validation results for generated handler"""

    is_valid: bool = Field(..., description="Overall validation status")
    syntax_valid: bool = Field(..., description="Python syntax is valid")
    tests_pass: bool = Field(default=False, description="All tests pass")
    syntax_errors: List[str] = Field(default_factory=list, description="Syntax errors found")
    schema_errors: List[str] = Field(default_factory=list, description="Schema validation errors")
    test_failures: List[str] = Field(default_factory=list, description="Test failures")
    warnings: List[str] = Field(default_factory=list, description="Non-critical warnings")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")


# ============================================================================
# REGISTRY: Map handler_id to config model
# ============================================================================

HANDLER_CONFIG_REGISTRY: Dict[str, type[BaseHandlerConfig]] = {
    # Input Handlers
    "project_fields": ProjectFieldsConfig,
    "chapter_data": ChapterDataConfig,
    "character_data": CharacterDataConfig,
    "user_input": UserInputConfig,
    "world_data": WorldDataConfig,
    # Processing Handlers
    "template_renderer": TemplateRendererConfig,
    "llm_processor": LLMProcessorConfig,
    "framework_generator": FrameworkGeneratorConfig,
    # Output Handlers
    "simple_text_field": SimpleTextFieldConfig,
    "chapter_creator": ChapterCreatorConfig,
    "markdown_file": MarkdownFileConfig,
}


def get_config_model(handler_id: str) -> Optional[type[BaseHandlerConfig]]:
    """Get Pydantic config model for handler"""
    return HANDLER_CONFIG_REGISTRY.get(handler_id)


def validate_handler_config(handler_id: str, config: Dict[str, Any]) -> BaseHandlerConfig:
    """Validate handler config and return Pydantic model instance"""
    config_model = get_config_model(handler_id)
    if not config_model:
        # Fallback: return config as-is if no model defined
        return config

    # Validate and return
    return config_model.model_validate(config)
