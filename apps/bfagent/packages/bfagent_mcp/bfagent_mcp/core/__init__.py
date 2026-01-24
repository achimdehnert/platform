"""
BF Agent MCP Server - Core Module
==================================

Enthält:
- Abstract Base Classes (Interfaces)
- Custom Exceptions
- Type Definitions
- Constants

Folgt dem Dependency Inversion Principle:
High-level modules sollten nicht von low-level modules abhängen.
Beide sollten von Abstraktionen abhängen.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, Protocol, TypeVar, runtime_checkable

# =============================================================================
# TYPE VARIABLES
# =============================================================================

T = TypeVar("T")
TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


# =============================================================================
# ENUMS (Zentralisiert für Konsistenz)
# =============================================================================

class DomainStatus(str, Enum):
    """Status einer Domain im System."""
    PRODUCTION = "production"
    BETA = "beta"
    DEVELOPMENT = "development"
    PLANNED = "planned"
    DEPRECATED = "deprecated"


class HandlerType(str, Enum):
    """Typ eines Handlers."""
    AI_POWERED = "ai_powered"
    RULE_BASED = "rule_based"
    HYBRID = "hybrid"
    UTILITY = "utility"


class AIProvider(str, Enum):
    """Verfügbare AI Provider."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    STABILITY = "stability"
    TESSERACT = "tesseract"
    NONE = "none"


class ResponseFormat(str, Enum):
    """Output-Format für Responses."""
    MARKDOWN = "markdown"
    JSON = "json"


class ValidationSeverity(str, Enum):
    """Schweregrad von Validierungsfehlern."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# =============================================================================
# DATA TRANSFER OBJECTS (DTOs)
# =============================================================================

@dataclass(frozen=True)
class DomainDTO:
    """
    Immutable Data Transfer Object für Domain-Daten.
    
    Trennt Datenbank-Repräsentation von API-Repräsentation.
    """
    id: int
    domain_id: str
    display_name: str
    description: str
    status: DomainStatus
    icon: str = ""
    color: str = "#3B82F6"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass(frozen=True)
class PhaseDTO:
    """Immutable DTO für Workflow-Phasen."""
    id: int
    name: str
    display_name: str
    order: int
    description: str = ""
    color: str = "#3B82F6"
    icon: str = ""
    estimated_duration_seconds: int = 0


@dataclass(frozen=True)
class HandlerDTO:
    """Immutable DTO für Handler-Daten."""
    id: int
    name: str
    domain_id: str
    handler_type: HandlerType
    description: str
    ai_provider: AIProvider = AIProvider.NONE
    estimated_duration_seconds: int = 0
    is_active: bool = True
    version: str = "1.0.0"
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class TagDTO:
    """Immutable DTO für Tags."""
    id: int
    name: str
    category: str = "general"
    description: str = ""


@dataclass
class ValidationIssue:
    """Einzelnes Validierungsproblem."""
    severity: ValidationSeverity
    category: str
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Ergebnis einer Code-Validierung."""
    is_valid: bool
    score: int  # 0-100
    issues: List[ValidationIssue] = field(default_factory=list)
    
    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]
    
    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]


@dataclass
class GeneratedCode:
    """Ergebnis einer Code-Generierung."""
    handler_code: str
    test_code: str
    schema_code: str
    handler_filename: str
    test_filename: str
    schema_filename: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DomainScaffold:
    """Ergebnis eines Domain-Scaffoldings."""
    files: Dict[str, str]  # filename -> content
    directory_structure: str
    migration_sql: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# ABSTRACT INTERFACES (Protocols)
# =============================================================================

@runtime_checkable
class Repository(Protocol[T]):
    """
    Repository Interface nach Repository Pattern.
    
    Abstrahiert Data Access von Business Logic.
    """
    
    async def get_by_id(self, id: int) -> Optional[T]:
        """Findet Entity nach ID."""
        ...
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Gibt alle Entities zurück (paginiert)."""
        ...
    
    async def count(self) -> int:
        """Zählt alle Entities."""
        ...


class DomainRepositoryProtocol(Repository[DomainDTO], Protocol):
    """Spezialisiertes Repository für Domains."""
    
    async def get_by_domain_id(self, domain_id: str) -> Optional[DomainDTO]:
        """Findet Domain nach domain_id (slug)."""
        ...
    
    async def get_by_status(self, status: DomainStatus) -> List[DomainDTO]:
        """Findet Domains nach Status."""
        ...
    
    async def get_with_handlers(self, domain_id: str) -> Optional[Dict[str, Any]]:
        """Lädt Domain mit allen zugehörigen Handlern."""
        ...


class HandlerRepositoryProtocol(Repository[HandlerDTO], Protocol):
    """Spezialisiertes Repository für Handler."""
    
    async def get_by_domain(self, domain_id: str) -> List[HandlerDTO]:
        """Findet Handler nach Domain."""
        ...
    
    async def search(
        self, 
        query: str, 
        domain_id: Optional[str] = None,
        handler_type: Optional[HandlerType] = None,
        limit: int = 10
    ) -> List[tuple[HandlerDTO, float]]:
        """Sucht Handler nach Query mit Relevanz-Score."""
        ...


class PhaseRepositoryProtocol(Repository[PhaseDTO], Protocol):
    """Spezialisiertes Repository für Phasen."""
    
    async def get_by_domain(self, domain_id: str) -> List[PhaseDTO]:
        """Findet Phasen einer Domain (sortiert nach order)."""
        ...


class CodeGeneratorProtocol(Protocol):
    """Interface für Code-Generatoren."""
    
    async def generate_handler(
        self,
        name: str,
        domain: str,
        handler_type: HandlerType,
        description: str,
        input_fields: List[str],
        output_fields: List[str],
    ) -> GeneratedCode:
        """Generiert Handler-Code."""
        ...
    
    async def generate_domain(
        self,
        domain_id: str,
        display_name: str,
        description: str,
        phases: List[str],
    ) -> DomainScaffold:
        """Generiert Domain-Scaffold."""
        ...


class CodeValidatorProtocol(Protocol):
    """Interface für Code-Validatoren."""
    
    async def validate(self, code: str) -> ValidationResult:
        """Validiert Python-Code gegen BF Agent Standards."""
        ...


class AIServiceProtocol(Protocol):
    """Interface für AI-Services."""
    
    async def generate_code(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generiert Code via AI."""
        ...
    
    async def enhance_code(
        self,
        code: str,
        instructions: str,
    ) -> str:
        """Verbessert bestehenden Code via AI."""
        ...


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class BFAgentMCPError(Exception):
    """Base Exception für alle MCP Server Fehler."""
    
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class DomainNotFoundError(BFAgentMCPError):
    """Domain wurde nicht gefunden."""
    
    def __init__(self, domain_id: str):
        super().__init__(
            f"Domain '{domain_id}' not found",
            code="DOMAIN_NOT_FOUND"
        )
        self.domain_id = domain_id


class HandlerNotFoundError(BFAgentMCPError):
    """Handler wurde nicht gefunden."""
    
    def __init__(self, handler_id: int):
        super().__init__(
            f"Handler with ID {handler_id} not found",
            code="HANDLER_NOT_FOUND"
        )
        self.handler_id = handler_id


class ValidationError(BFAgentMCPError):
    """Validierungsfehler."""
    
    def __init__(self, message: str, issues: List[ValidationIssue] = None):
        super().__init__(message, code="VALIDATION_ERROR")
        self.issues = issues or []


class CodeGenerationError(BFAgentMCPError):
    """Fehler bei Code-Generierung."""
    
    def __init__(self, message: str):
        super().__init__(message, code="CODE_GENERATION_ERROR")


class AIServiceError(BFAgentMCPError):
    """Fehler bei AI-Service-Aufruf."""
    
    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message, code="AI_SERVICE_ERROR")
        self.provider = provider


class ConfigurationError(BFAgentMCPError):
    """Konfigurationsfehler."""
    
    def __init__(self, message: str):
        super().__init__(message, code="CONFIGURATION_ERROR")


# =============================================================================
# CONSTANTS
# =============================================================================

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Validation
MAX_HANDLER_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 1000
MIN_DESCRIPTION_LENGTH = 10

# Code Generation
HANDLER_TEMPLATE_VERSION = "2.0"
SUPPORTED_PYTHON_VERSIONS = ["3.10", "3.11", "3.12"]

# Search
DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 50
MIN_SEARCH_QUERY_LENGTH = 2


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "DomainStatus",
    "HandlerType", 
    "AIProvider",
    "ResponseFormat",
    "ValidationSeverity",
    # DTOs
    "DomainDTO",
    "PhaseDTO",
    "HandlerDTO",
    "TagDTO",
    "ValidationIssue",
    "ValidationResult",
    "GeneratedCode",
    "DomainScaffold",
    # Protocols
    "Repository",
    "DomainRepositoryProtocol",
    "HandlerRepositoryProtocol",
    "PhaseRepositoryProtocol",
    "CodeGeneratorProtocol",
    "CodeValidatorProtocol",
    "AIServiceProtocol",
    # Exceptions
    "BFAgentMCPError",
    "DomainNotFoundError",
    "HandlerNotFoundError",
    "ValidationError",
    "CodeGenerationError",
    "AIServiceError",
    "ConfigurationError",
    # Constants
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "DEFAULT_SEARCH_LIMIT",
    "MAX_SEARCH_LIMIT",
]
