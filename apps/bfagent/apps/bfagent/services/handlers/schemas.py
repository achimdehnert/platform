"""
Pydantic schemas for handler data validation - COMPLETE
Pydantic 2.x compatible
"""

from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HandlerConfig(BaseModel):
    """Base configuration for handlers"""

    handler: str
    config: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "forbid"
        validate_assignment = True


# ==================== INPUT HANDLER CONFIGS ====================


class ProjectFieldsConfig(BaseModel):
    """Configuration for ProjectFieldsInputHandler"""

    fields: Optional[List[str]] = None
    mode: Literal["specified", "all"] = "specified"

    class Config:
        extra = "forbid"

    @model_validator(mode="after")
    def validate_mode_fields(self):
        if self.mode == "specified" and not self.fields:
            raise ValueError("'fields' required when mode='specified'")
        return self


class ChapterDataConfig(BaseModel):
    """Configuration for ChapterDataHandler"""

    include_outline: bool = False
    include_characters: bool = False
    include_content: bool = False
    include_ai_content: bool = False
    chapter_ids: Optional[List[int]] = None
    limit: Optional[int] = Field(None, gt=0, le=100)
    order_by: str = "chapter_number"

    class Config:
        extra = "forbid"

    @field_validator("order_by")
    @classmethod
    def validate_order_by(cls, v):
        allowed = [
            "chapter_number",
            "-chapter_number",
            "title",
            "-title",
            "created_at",
            "-created_at",
        ]
        if v not in allowed:
            raise ValueError(f"order_by must be one of: {', '.join(allowed)}")
        return v


class CharacterDataConfig(BaseModel):
    """Configuration for CharacterDataHandler"""

    featured_only: bool = False
    include_description: bool = True
    include_backstory: bool = False
    include_relationships: bool = False
    include_arc: bool = False
    character_ids: Optional[List[int]] = None
    limit: Optional[int] = Field(None, gt=0, le=50)
    role_filter: Optional[Literal["protagonist", "antagonist", "supporting"]] = None

    class Config:
        extra = "forbid"


class WorldDataConfig(BaseModel):
    """Configuration for WorldDataHandler"""

    include_locations: bool = True
    include_cultures: bool = False
    include_magic_systems: bool = False
    include_history: bool = False
    include_rules: bool = False
    location_ids: Optional[List[int]] = None
    limit: Optional[int] = Field(None, gt=0, le=50)

    class Config:
        extra = "forbid"


class UserInputConfig(BaseModel):
    """Configuration for UserInputHandler"""

    # No configuration needed, but keep for consistency

    class Config:
        extra = "forbid"


# ==================== PROCESSING HANDLER CONFIGS ====================


class TemplateRendererConfig(BaseModel):
    """Configuration for TemplateRendererHandler"""

    template: str = Field(..., min_length=1)
    strict: bool = False

    class Config:
        extra = "forbid"

    @field_validator("template")
    @classmethod
    def validate_template_syntax(cls, v):
        import re

        pattern = r"\{\{\s*[\w]+\s*\}\}"
        if not re.search(pattern, v):
            raise ValueError("Template must contain at least one {{variable}}")
        return v


class LLMProcessorConfig(BaseModel):
    """Configuration for LLMProcessingHandler"""

    llm_id: Optional[int] = None
    llm_name: Optional[str] = None
    fallback_llm_id: Optional[int] = None
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(4000, ge=1, le=100000)
    top_p: float = Field(1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    stream: bool = False

    class Config:
        extra = "forbid"

    @model_validator(mode="after")
    def validate_llm_selection(self):
        if not self.llm_id and not self.llm_name:
            raise ValueError("Must specify either 'llm_id' or 'llm_name'")
        return self


class FrameworkGeneratorConfig(BaseModel):
    """Configuration for FrameworkGeneratorHandler"""

    framework: Literal["heros_journey", "save_the_cat", "three_act"]
    output_format: Literal["markdown", "plain", "json"] = "markdown"
    num_chapters: Optional[int] = Field(None, ge=1, le=100)
    include_suggestions: bool = False

    class Config:
        extra = "forbid"


# ==================== OUTPUT HANDLER CONFIGS ====================


class SimpleTextFieldConfig(BaseModel):
    """Configuration for SimpleTextFieldHandler"""

    target_model: Literal["BookProjects", "BookChapters", "Characters"]
    target_field: str = Field(..., min_length=1)
    target_instance: Literal["current", "specific"] = "current"
    target_instance_id: Optional[int] = None
    action_name: str = "text_generation"
    min_length: int = Field(0, ge=0)
    max_length: int = Field(100000, ge=1)

    class Config:
        extra = "forbid"

    @model_validator(mode="after")
    def validate_instance_selection(self):
        if self.target_instance == "specific" and not self.target_instance_id:
            raise ValueError("target_instance_id required when target_instance='specific'")
        return self


class ChapterCreatorConfig(BaseModel):
    """Configuration for ChapterCreatorHandler"""

    target_model: str = "BookChapters"
    fields: Dict[str, str]
    auto_number: bool = True
    start_number: int = Field(1, ge=1)
    action_name: str = "create_chapters"
    default_status: str = "draft"
    required_fields: List[str] = Field(default_factory=lambda: ["title"])

    class Config:
        extra = "forbid"

    @field_validator("fields")
    @classmethod
    def validate_fields_not_empty(cls, v):
        if not v:
            raise ValueError("fields dict cannot be empty")
        return v


class MarkdownFileConfig(BaseModel):
    """Configuration for MarkdownExporter"""

    output_dir: str = Field(..., min_length=1)
    filename_template: str = Field(..., min_length=1)
    create_backup: bool = True
    add_frontmatter: bool = True
    overwrite: bool = False
    frontmatter_fields: List[str] = Field(default_factory=lambda: ["title", "author", "date"])

    class Config:
        extra = "forbid"

    @field_validator("output_dir")
    @classmethod
    def validate_output_dir(cls, v):
        from pathlib import Path

        path = Path(v)
        if path.exists() and not path.is_dir():
            raise ValueError(f"output_dir exists but is not a directory: {v}")
        return v


# ==================== DATA SCHEMAS ====================


class LLMResponse(BaseModel):
    """Schema for LLM processing response"""

    generated_content: str
    llm_name: str
    llm_id: int
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    tokens_used: int = Field(ge=0)
    generation_cost: Decimal = Field(ge=0)
    execution_time_ms: int = Field(ge=0)
    model_version: str
    finish_reason: str

    class Config:
        extra = "forbid"


class ValidationResult(BaseModel):
    """Standard validation result schema"""

    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    details: Optional[Dict[str, Any]] = None

    class Config:
        extra = "forbid"


# ==================== ALL CONFIGS EXPORT ====================

__all__ = [
    # Base
    "HandlerConfig",
    # Input
    "ProjectFieldsConfig",
    "ChapterDataConfig",
    "CharacterDataConfig",
    "WorldDataConfig",
    "UserInputConfig",
    # Processing
    "TemplateRendererConfig",
    "LLMProcessorConfig",
    "FrameworkGeneratorConfig",
    # Output
    "SimpleTextFieldConfig",
    "ChapterCreatorConfig",
    "MarkdownFileConfig",
    # Data
    "LLMResponse",
    "ValidationResult",
]
