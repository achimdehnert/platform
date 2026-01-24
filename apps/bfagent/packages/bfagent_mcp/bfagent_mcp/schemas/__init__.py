"""
BF Agent MCP Server - Pydantic Schemas
======================================

Input/Output Schemas für MCP Tools.

Separation of Concerns:
- Diese Schemas sind NUR für API Input/Output Validierung
- DTOs (core/) sind für interne Datenübertragung
- Django Models (models.py) sind für Persistenz

Jedes Schema hat:
- Strikte Validierung mit Constraints
- Klare Dokumentation für MCP Clients
- Konsistente Namenskonvention: {Action}{Resource}Input/Output
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..core import (
    DomainStatus,
    HandlerType,
    ResponseFormat,
    MAX_PAGE_SIZE,
    DEFAULT_PAGE_SIZE,
    MAX_SEARCH_LIMIT,
    DEFAULT_SEARCH_LIMIT,
    MAX_HANDLER_NAME_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MIN_DESCRIPTION_LENGTH,
    MIN_SEARCH_QUERY_LENGTH,
)


# =============================================================================
# BASE CONFIGURATION
# =============================================================================

class BaseSchema(BaseModel):
    """Base Schema mit gemeinsamer Konfiguration."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
        use_enum_values=True,
    )


# =============================================================================
# DOMAIN SCHEMAS
# =============================================================================

class ListDomainsInput(BaseSchema):
    """
    Input für das Auflisten von Domains.
    
    Ermöglicht Filterung nach Status und Formatauswahl.
    """
    
    status_filter: Optional[DomainStatus] = Field(
        default=None,
        description="Filter by domain status. Options: production, beta, development, planned, deprecated"
    )
    include_handler_count: bool = Field(
        default=True,
        description="Include the number of handlers per domain"
    )
    include_phases: bool = Field(
        default=True,
        description="Include workflow phases for each domain"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable, 'json' for structured data"
    )


class ListDomainsOutput(BaseSchema):
    """Output für Domain-Liste."""
    
    total: int = Field(..., description="Total number of domains matching filter")
    domains: List[Dict[str, Any]] = Field(..., description="List of domain objects")


class GetDomainInput(BaseSchema):
    """
    Input für Domain-Details.
    
    Lädt detaillierte Informationen zu einer spezifischen Domain.
    """
    
    domain_id: str = Field(
        ...,
        description="Domain identifier (slug), e.g., 'books', 'cad', 'medtrans'",
        min_length=1,
        max_length=50,
        pattern=r'^[a-z][a-z0-9_]*$'
    )
    include_handlers: bool = Field(
        default=True,
        description="Include all handlers in this domain"
    )
    include_phases: bool = Field(
        default=True,
        description="Include workflow phases"
    )
    include_statistics: bool = Field(
        default=False,
        description="Include usage statistics (execution counts, success rates)"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )


# =============================================================================
# HANDLER SCHEMAS
# =============================================================================

class SearchHandlersInput(BaseSchema):
    """
    Input für Handler-Suche.
    
    Unterstützt semantische Suche nach Funktionalität.
    """
    
    query: str = Field(
        ...,
        description="Search query describing desired functionality. Examples: 'PDF parsing', 'image generation', 'text extraction', 'OCR'",
        min_length=MIN_SEARCH_QUERY_LENGTH,
        max_length=200
    )
    domain_filter: Optional[str] = Field(
        default=None,
        description="Limit search to specific domain",
        max_length=50
    )
    handler_type_filter: Optional[HandlerType] = Field(
        default=None,
        description="Filter by handler type: ai_powered, rule_based, hybrid, utility"
    )
    tags_filter: Optional[List[str]] = Field(
        default=None,
        description="Filter by tags (e.g., ['pdf', 'extraction'])",
        max_length=10
    )
    include_inactive: bool = Field(
        default=False,
        description="Include inactive/deprecated handlers"
    )
    limit: int = Field(
        default=DEFAULT_SEARCH_LIMIT,
        description="Maximum number of results",
        ge=1,
        le=MAX_SEARCH_LIMIT
    )
    offset: int = Field(
        default=0,
        description="Offset for pagination",
        ge=0
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )


class SearchHandlersOutput(BaseSchema):
    """Output für Handler-Suche."""
    
    query: str = Field(..., description="Original search query")
    total: int = Field(..., description="Total matching handlers")
    has_more: bool = Field(..., description="More results available")
    results: List[Dict[str, Any]] = Field(..., description="Handler results with relevance scores")


class GetHandlerInput(BaseSchema):
    """Input für einzelnen Handler."""
    
    handler_id: int = Field(
        ...,
        description="Handler database ID",
        gt=0
    )
    include_schema: bool = Field(
        default=True,
        description="Include input/output Pydantic schemas"
    )
    include_source: bool = Field(
        default=False,
        description="Include handler source code (if available)"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )


# =============================================================================
# CODE GENERATION SCHEMAS
# =============================================================================

class GenerateHandlerInput(BaseSchema):
    """
    Input für Handler-Code-Generierung.
    
    Generiert produktionsreifen Handler-Code nach BF Agent Patterns.
    """
    
    handler_name: str = Field(
        ...,
        description="Name for the handler. Should be PascalCase and end with 'Handler'. Examples: 'PDFTextExtractHandler', 'ImageResizeHandler'",
        min_length=3,
        max_length=MAX_HANDLER_NAME_LENGTH
    )
    domain: str = Field(
        ...,
        description="Target domain for the handler. Must be an existing domain.",
        min_length=1,
        max_length=50
    )
    handler_type: HandlerType = Field(
        default=HandlerType.RULE_BASED,
        description="Handler type determining the processing approach"
    )
    description: str = Field(
        ...,
        description="Detailed description of handler functionality. Be specific about what it does, inputs, and outputs.",
        min_length=MIN_DESCRIPTION_LENGTH,
        max_length=MAX_DESCRIPTION_LENGTH
    )
    input_fields: List[str] = Field(
        default_factory=list,
        description="List of input field names. Examples: ['file_path', 'output_format', 'quality']",
        max_length=20
    )
    output_fields: List[str] = Field(
        default_factory=list,
        description="List of output field names. Examples: ['extracted_text', 'page_count', 'confidence']",
        max_length=20
    )
    ai_provider: Optional[str] = Field(
        default=None,
        description="AI provider to use (for ai_powered handlers): 'openai', 'anthropic', 'ollama'"
    )
    include_tests: bool = Field(
        default=True,
        description="Generate comprehensive test file"
    )
    include_docstrings: bool = Field(
        default=True,
        description="Include detailed docstrings"
    )
    use_ai_enhancement: bool = Field(
        default=True,
        description="Use AI to enhance generated code with best practices"
    )
    
    @field_validator('handler_name')
    @classmethod
    def validate_handler_name(cls, v: str) -> str:
        """Ensure handler name follows conventions."""
        # Add Handler suffix if missing
        if not v.endswith('Handler'):
            v = f"{v}Handler"
        # Ensure PascalCase
        if not v[0].isupper():
            v = v[0].upper() + v[1:]
        # Remove spaces and special chars
        v = ''.join(c for c in v if c.isalnum())
        return v
    
    @field_validator('input_fields', 'output_fields')
    @classmethod
    def validate_field_names(cls, v: List[str]) -> List[str]:
        """Ensure field names are valid Python identifiers."""
        validated = []
        for field in v:
            # Convert to snake_case
            field = field.strip().lower().replace(' ', '_').replace('-', '_')
            # Remove invalid characters
            field = ''.join(c for c in field if c.isalnum() or c == '_')
            if field and field[0].isdigit():
                field = f"field_{field}"
            if field:
                validated.append(field)
        return validated


class GenerateHandlerOutput(BaseSchema):
    """Output für Handler-Generierung."""
    
    handler_name: str
    domain: str
    files: Dict[str, str] = Field(..., description="Generated files: filename -> content")
    instructions: List[str] = Field(..., description="Next steps for integration")
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# DOMAIN SCAFFOLDING SCHEMAS
# =============================================================================

class ScaffoldDomainInput(BaseSchema):
    """
    Input für Domain-Scaffolding.
    
    Erstellt komplette Domain-Struktur mit Models, Admin, URLs, etc.
    """
    
    domain_id: str = Field(
        ...,
        description="Unique domain identifier (lowercase slug). Examples: 'contracts', 'invoices', 'reports'",
        min_length=2,
        max_length=30,
        pattern=r'^[a-z][a-z0-9_]*$'
    )
    display_name: str = Field(
        ...,
        description="Human-readable name. Examples: 'Contract Analysis', 'Invoice Processing'",
        min_length=3,
        max_length=100
    )
    description: str = Field(
        ...,
        description="Comprehensive description of domain purpose and capabilities",
        min_length=20,
        max_length=1000
    )
    phases: List[str] = Field(
        ...,
        description="Workflow phases in order. Examples: ['Upload', 'Extraction', 'Analysis', 'Report']",
        min_length=2,
        max_length=10
    )
    initial_handlers: List[str] = Field(
        default_factory=list,
        description="Initial handlers to scaffold (names only)",
        max_length=20
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization",
        max_length=10
    )
    include_admin: bool = Field(
        default=True,
        description="Generate Django Admin configuration"
    )
    include_api: bool = Field(
        default=True,
        description="Generate REST API endpoints (urls.py, views.py)"
    )
    include_tests: bool = Field(
        default=True,
        description="Generate test structure"
    )
    include_migrations: bool = Field(
        default=True,
        description="Generate initial migration"
    )
    
    @field_validator('phases')
    @classmethod
    def validate_phases(cls, v: List[str]) -> List[str]:
        """Normalize phase names."""
        return [p.strip().title() for p in v if p.strip()]
    
    @field_validator('initial_handlers')
    @classmethod
    def validate_handlers(cls, v: List[str]) -> List[str]:
        """Ensure handler names follow conventions."""
        validated = []
        for name in v:
            name = name.strip()
            if not name.endswith('Handler'):
                name = f"{name}Handler"
            if name[0].islower():
                name = name[0].upper() + name[1:]
            validated.append(name)
        return validated


class ScaffoldDomainOutput(BaseSchema):
    """Output für Domain-Scaffolding."""
    
    domain_id: str
    display_name: str
    directory_structure: str
    files: Dict[str, str] = Field(..., description="Generated files")
    commands: List[str] = Field(..., description="Commands to run after scaffolding")
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# VALIDATION SCHEMAS
# =============================================================================

class ValidateHandlerInput(BaseSchema):
    """
    Input für Handler-Validierung.
    
    Prüft Code gegen BF Agent Standards und Best Practices.
    """
    
    code: str = Field(
        ...,
        description="Python handler code to validate",
        min_length=50,
        max_length=100000
    )
    check_inheritance: bool = Field(
        default=True,
        description="Validate BaseHandler inheritance"
    )
    check_pydantic: bool = Field(
        default=True,
        description="Validate Pydantic schema usage"
    )
    check_docstrings: bool = Field(
        default=True,
        description="Validate docstring presence and format"
    )
    check_error_handling: bool = Field(
        default=True,
        description="Validate error handling patterns"
    )
    check_three_phase: bool = Field(
        default=True,
        description="Validate three-phase pattern (validate, process, save_result)"
    )
    check_type_hints: bool = Field(
        default=True,
        description="Validate type hint coverage"
    )
    check_logging: bool = Field(
        default=True,
        description="Validate logging usage"
    )
    strict_mode: bool = Field(
        default=False,
        description="Treat warnings as errors"
    )


class ValidateHandlerOutput(BaseSchema):
    """Output für Handler-Validierung."""
    
    is_valid: bool
    score: int = Field(..., ge=0, le=100)
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    suggestions: List[str]
    summary: str


# =============================================================================
# BEST PRACTICES SCHEMAS
# =============================================================================

class GetBestPracticesInput(BaseSchema):
    """
    Input für Best Practices Dokumentation.
    
    Verfügbare Topics: handlers, pydantic, ai_integration, testing, error_handling, performance
    """
    
    topic: str = Field(
        ...,
        description="Topic for best practices. Available: 'handlers', 'pydantic', 'ai_integration', 'testing', 'error_handling', 'performance'",
        min_length=2,
        max_length=50
    )
    include_examples: bool = Field(
        default=True,
        description="Include code examples"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )


class GetBestPracticesOutput(BaseSchema):
    """Output für Best Practices."""
    
    topic: str
    content: str
    related_topics: List[str] = Field(default_factory=list)


# =============================================================================
# PAGINATION SCHEMAS
# =============================================================================

class PaginationParams(BaseSchema):
    """Wiederverwendbare Pagination-Parameter."""
    
    limit: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Maximum items per page"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip"
    )


class PaginatedResponse(BaseSchema):
    """Wiederverwendbare Pagination-Response."""
    
    total: int = Field(..., description="Total number of items")
    count: int = Field(..., description="Number of items in this response")
    offset: int = Field(..., description="Current offset")
    has_more: bool = Field(..., description="More items available")
    next_offset: Optional[int] = Field(None, description="Offset for next page")


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Base
    "BaseSchema",
    # Domain
    "ListDomainsInput",
    "ListDomainsOutput", 
    "GetDomainInput",
    # Handler
    "SearchHandlersInput",
    "SearchHandlersOutput",
    "GetHandlerInput",
    # Generation
    "GenerateHandlerInput",
    "GenerateHandlerOutput",
    # Scaffolding
    "ScaffoldDomainInput",
    "ScaffoldDomainOutput",
    # Validation
    "ValidateHandlerInput",
    "ValidateHandlerOutput",
    # Best Practices
    "GetBestPracticesInput",
    "GetBestPracticesOutput",
    # Pagination
    "PaginationParams",
    "PaginatedResponse",
]
