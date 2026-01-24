"""
BF Agent MCP Server - Extended Data Loader
============================================

Initial data für die neuen "Self-Dogfooding" Models:
- CodingConventions: Coding-Regeln und Standards
- ProjectStructure: Projekt-Struktur-Konventionen
- MCPContext: Kontext-Templates für Windsurf
"""

from __future__ import annotations
from typing import Any


# =============================================================================
# CODING CONVENTIONS - Initial Data
# =============================================================================

def get_initial_conventions() -> list[dict[str, Any]]:
    """
    Coding Conventions für BF Agent.
    
    Diese Regeln werden von MCP an Windsurf weitergegeben,
    um konsistenten Code zu generieren.
    """
    return [
        # === PATTERNS ===
        {
            "name": "handler_inheritance",
            "display_name": "Handler Inheritance",
            "category": "patterns",
            "severity": "error",
            "rule": "Alle Handler MÜSSEN von BaseHandler erben",
            "rationale": "BaseHandler bietet Logging, Error Handling, und Lifecycle Management",
            "example_good": """class PDFExtractorHandler(BaseHandler):
    \"\"\"Extracts text from PDF files.\"\"\"
    
    class InputSchema(BaseModel):
        file_path: str
    
    class OutputSchema(BaseModel):
        text: str
        pages: int""",
            "example_bad": """class PDFExtractor:
    def extract(self, file_path):
        # Kein Schema, kein Logging, kein Error Handling
        pass""",
            "applies_to": ["handler"],
            "order": 1,
        },
        {
            "name": "three_phase_pattern",
            "display_name": "Three-Phase Processing Pattern",
            "category": "patterns",
            "severity": "warning",
            "rule": "Handler folgen dem Drei-Phasen-Pattern: validate_input → process → save_result",
            "rationale": "Klare Trennung von Validierung, Verarbeitung und Persistenz",
            "example_good": """async def execute(self, input_data: InputSchema) -> OutputSchema:
    # Phase 1: Validate
    validated = await self.validate_input(input_data)
    
    # Phase 2: Process
    result = await self.process(validated)
    
    # Phase 3: Save
    await self.save_result(result)
    
    return result""",
            "example_bad": """def execute(self, data):
    # Alles in einer Methode vermischt
    if data.get('file'):
        text = extract(data['file'])
        db.save(text)
        return text""",
            "applies_to": ["handler"],
            "order": 2,
        },
        {
            "name": "pydantic_schemas",
            "display_name": "Pydantic Input/Output Schemas",
            "category": "validation",
            "severity": "error",
            "rule": "Input und Output MÜSSEN als Pydantic BaseModel definiert sein",
            "rationale": "Automatische Validierung, Serialisierung und Dokumentation",
            "example_good": """class InputSchema(BaseModel):
    text: str = Field(..., min_length=1)
    language: str = Field(default="de")
    
class OutputSchema(BaseModel):
    translated: str
    confidence: float = Field(ge=0, le=1)""",
            "example_bad": """def process(self, data: dict) -> dict:
    # Keine Validierung, keine Typsicherheit
    return {"result": data["input"]}""",
            "applies_to": ["handler", "service"],
            "order": 3,
        },
        {
            "name": "dependency_injection",
            "display_name": "Dependency Injection",
            "category": "patterns",
            "severity": "warning",
            "rule": "Services und Repositories werden per Constructor Injection übergeben",
            "rationale": "Testbarkeit, Austauschbarkeit, klare Abhängigkeiten",
            "example_good": """class BookService:
    def __init__(
        self,
        book_repo: BookRepository,
        ai_client: AIClient,
    ):
        self.book_repo = book_repo
        self.ai_client = ai_client""",
            "example_bad": """class BookService:
    def get_book(self, id):
        # Hardcoded Dependencies
        repo = BookRepository()
        return repo.get(id)""",
            "applies_to": ["service", "handler"],
            "order": 4,
        },
        
        # === NAMING ===
        {
            "name": "handler_naming",
            "display_name": "Handler Naming Convention",
            "category": "naming",
            "severity": "warning",
            "rule": "Handler-Klassen enden mit 'Handler', Dateien mit '_handler.py'",
            "rationale": "Konsistente Benennung ermöglicht automatische Discovery",
            "example_good": """# Datei: pdf_extractor_handler.py
class PDFExtractorHandler(BaseHandler):
    pass""",
            "example_bad": """# Datei: pdf.py
class PDFExtract:
    pass""",
            "applies_to": ["handler"],
            "check_pattern": r"class \w+Handler\(BaseHandler\)",
            "order": 10,
        },
        {
            "name": "service_naming",
            "display_name": "Service Naming Convention",
            "category": "naming",
            "severity": "warning",
            "rule": "Service-Klassen enden mit 'Service', Dateien mit '_service.py' oder 'services.py'",
            "rationale": "Konsistente Benennung für Business Logic Layer",
            "example_good": """# Datei: book_service.py
class BookService:
    pass""",
            "example_bad": """# Datei: books.py
class BookManager:
    pass""",
            "applies_to": ["service"],
            "order": 11,
        },
        {
            "name": "model_naming",
            "display_name": "Model Naming Convention",
            "category": "naming",
            "severity": "info",
            "rule": "Model-Klassen sind Singular (Book, nicht Books), Dateien: models.py",
            "rationale": "Django Convention",
            "example_good": """class Book(models.Model):
    title = models.CharField(max_length=200)""",
            "example_bad": """class Books(models.Model):
    pass""",
            "applies_to": ["model"],
            "order": 12,
        },
        
        # === ERROR HANDLING ===
        {
            "name": "specific_exceptions",
            "display_name": "Specific Exceptions",
            "category": "error_handling",
            "severity": "warning",
            "rule": "Nutze spezifische Exception-Klassen statt generischer Exceptions",
            "rationale": "Bessere Fehlerbehandlung, klare Fehlermeldungen",
            "example_good": """class HandlerNotFoundError(BFAgentError):
    pass

raise HandlerNotFoundError(f"Handler {name} not found")""",
            "example_bad": """raise Exception("Something went wrong")""",
            "applies_to": ["handler", "service"],
            "order": 20,
        },
        {
            "name": "error_logging",
            "display_name": "Error Logging",
            "category": "error_handling",
            "severity": "warning",
            "rule": "Alle Exceptions werden geloggt bevor sie re-raised werden",
            "rationale": "Debugging und Monitoring",
            "example_good": """try:
    result = await process()
except ProcessingError as e:
    logger.exception(f"Processing failed: {e}")
    raise""",
            "example_bad": """try:
    result = process()
except:
    raise""",
            "applies_to": ["handler", "service"],
            "order": 21,
        },
        
        # === DOCUMENTATION ===
        {
            "name": "docstrings",
            "display_name": "Docstrings Required",
            "category": "documentation",
            "severity": "info",
            "rule": "Klassen und öffentliche Methoden brauchen Docstrings",
            "rationale": "Selbstdokumentierender Code",
            "example_good": '''class PDFHandler(BaseHandler):
    """
    Extracts text from PDF documents.
    
    Supports: PDF 1.4+, encrypted PDFs (with password)
    
    Example:
        handler = PDFHandler()
        result = await handler.execute(InputSchema(path="doc.pdf"))
    """''',
            "example_bad": """class PDFHandler(BaseHandler):
    def execute(self, input):
        pass""",
            "applies_to": ["handler", "service", "model"],
            "order": 30,
        },
        {
            "name": "type_hints",
            "display_name": "Type Hints",
            "category": "documentation",
            "severity": "warning",
            "rule": "Funktionen und Methoden haben vollständige Type Hints",
            "rationale": "IDE Support, statische Analyse, Dokumentation",
            "example_good": """async def process(
    self,
    input_data: InputSchema,
    options: Optional[ProcessOptions] = None,
) -> OutputSchema:""",
            "example_bad": """def process(self, data, options=None):""",
            "applies_to": ["handler", "service"],
            "order": 31,
        },
        
        # === TESTING ===
        {
            "name": "test_naming",
            "display_name": "Test Naming Convention",
            "category": "testing",
            "severity": "info",
            "rule": "Tests beginnen mit 'test_', beschreiben das erwartete Verhalten",
            "rationale": "Pytest Convention, lesbare Test-Reports",
            "example_good": """def test_extract_returns_text_from_valid_pdf():
    pass

def test_extract_raises_error_for_corrupted_file():
    pass""",
            "example_bad": """def pdf_test():
    pass""",
            "applies_to": ["test"],
            "order": 40,
        },
        {
            "name": "test_isolation",
            "display_name": "Test Isolation",
            "category": "testing",
            "severity": "warning",
            "rule": "Tests sind unabhängig voneinander, nutzen Fixtures für Setup",
            "rationale": "Parallele Ausführung, keine Test-Reihenfolge-Abhängigkeit",
            "example_good": """@pytest.fixture
def sample_pdf(tmp_path):
    path = tmp_path / "test.pdf"
    create_sample_pdf(path)
    return path

def test_extract(sample_pdf):
    result = handler.extract(sample_pdf)
    assert result.text""",
            "example_bad": """# Global state between tests
PDF_PATH = None

def test_create():
    global PDF_PATH
    PDF_PATH = create_pdf()

def test_extract():
    # Depends on test_create running first!
    extract(PDF_PATH)""",
            "applies_to": ["test"],
            "order": 41,
        },
        
        # === ASYNC ===
        {
            "name": "async_handlers",
            "display_name": "Async Handler Methods",
            "category": "patterns",
            "severity": "warning",
            "rule": "Handler execute() und process() Methoden sind async",
            "rationale": "Non-blocking I/O, bessere Performance",
            "example_good": """async def execute(self, input: InputSchema) -> OutputSchema:
    result = await self.process(input)
    return result""",
            "example_bad": """def execute(self, input):
    result = self.process(input)
    return result""",
            "applies_to": ["handler"],
            "order": 50,
        },
    ]


# =============================================================================
# PROJECT STRUCTURE - Initial Data
# =============================================================================

def get_initial_structures() -> list[dict[str, Any]]:
    """
    Projekt-Struktur Konventionen für BF Agent.
    
    Definiert wo verschiedene Komponenten liegen.
    """
    return [
        {
            "component_type": "handler",
            "path_pattern": "apps/{domain}/handlers/",
            "file_naming_pattern": "{name}_handler.py",
            "class_naming_pattern": "{Name}Handler",
            "description": "Handler führen einzelne Verarbeitungsschritte aus. "
                          "Jeder Handler hat Input/Output Schema und folgt dem Drei-Phasen-Pattern.",
            "boilerplate_template": '''"""
{Name}Handler - {description}
"""

from pydantic import BaseModel, Field
from apps.core.handlers.base import BaseHandler


class {Name}Handler(BaseHandler):
    """
    {description}
    """
    
    class InputSchema(BaseModel):
        \"\"\"Input für {Name}Handler.\"\"\"
        # TODO: Define input fields
        pass
    
    class OutputSchema(BaseModel):
        \"\"\"Output von {Name}Handler.\"\"\"
        # TODO: Define output fields
        pass
    
    async def validate_input(self, input_data: InputSchema) -> InputSchema:
        \"\"\"Validate and prepare input.\"\"\"
        return input_data
    
    async def process(self, input_data: InputSchema) -> OutputSchema:
        \"\"\"Main processing logic.\"\"\"
        # TODO: Implement processing
        raise NotImplementedError
    
    async def save_result(self, result: OutputSchema) -> None:
        \"\"\"Persist result if needed.\"\"\"
        pass
''',
        },
        {
            "component_type": "service",
            "path_pattern": "apps/{domain}/services/",
            "file_naming_pattern": "{name}_service.py",
            "class_naming_pattern": "{Name}Service",
            "description": "Services orchestrieren Business Logic und koordinieren Handler.",
            "boilerplate_template": '''"""
{Name}Service - {description}
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


class {Name}Service:
    """
    {description}
    """
    
    def __init__(self, repository: {Name}Repository):
        self.repository = repository
    
    async def get_by_id(self, id: int) -> Optional[{Name}]:
        \"\"\"Get {name} by ID.\"\"\"
        return await self.repository.get_by_id(id)
''',
        },
        {
            "component_type": "model",
            "path_pattern": "apps/{domain}/",
            "file_naming_pattern": "models.py",
            "class_naming_pattern": "{Name}",
            "description": "Django Models definieren die Datenbankstruktur.",
            "boilerplate_template": '''"""
{Name} Model
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class {Name}(models.Model):
    """
    {description}
    """
    
    # TODO: Define fields
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _("{Name}")
        verbose_name_plural = _("{Name}s")
        ordering = ["-created_at"]
    
    def __str__(self):
        return self.name
''',
        },
        {
            "component_type": "test",
            "path_pattern": "apps/{domain}/tests/",
            "file_naming_pattern": "test_{name}.py",
            "class_naming_pattern": "Test{Name}",
            "description": "Tests mit pytest. Jeder Handler/Service hat eigene Test-Datei.",
            "boilerplate_template": '''"""
Tests for {Name}
"""

import pytest
from unittest.mock import Mock, AsyncMock


class Test{Name}:
    """Test suite for {Name}."""
    
    @pytest.fixture
    def instance(self):
        \"\"\"Create test instance.\"\"\"
        return {Name}()
    
    def test_initialization(self, instance):
        \"\"\"Test basic initialization.\"\"\"
        assert instance is not None
    
    @pytest.mark.asyncio
    async def test_process(self, instance):
        \"\"\"Test processing logic.\"\"\"
        # TODO: Implement test
        pass
''',
        },
        {
            "component_type": "schema",
            "path_pattern": "apps/{domain}/",
            "file_naming_pattern": "schemas.py",
            "class_naming_pattern": "{Name}Schema",
            "description": "Pydantic Schemas für Validierung und Serialisierung.",
            "boilerplate_template": '''"""
Schemas for {domain}
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class {Name}Schema(BaseModel):
    """Schema for {Name}."""
    
    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=100)
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
''',
        },
        {
            "component_type": "admin",
            "path_pattern": "apps/{domain}/",
            "file_naming_pattern": "admin.py",
            "class_naming_pattern": "{Name}Admin",
            "description": "Django Admin Konfiguration für Models.",
            "boilerplate_template": '''"""
Admin configuration for {domain}
"""

from django.contrib import admin
from .models import {Name}


@admin.register({Name})
class {Name}Admin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    ordering = ["-created_at"]
''',
        },
    ]


# =============================================================================
# MCP CONTEXT - Initial Data
# =============================================================================

def get_initial_contexts() -> list[dict[str, Any]]:
    """
    MCP Context Templates für verschiedene Aufgaben.
    
    Wird an Windsurf gesendet um Kontext zu liefern.
    """
    return [
        {
            "context_type": "create_handler",
            "display_name": "Create New Handler",
            "context_template": """# Handler erstellen: {name}

## Ziel
{description}

## Domain: {domain}

## Projekt-Struktur
Datei: `apps/{domain}/handlers/{name_snake}_handler.py`
Test: `apps/{domain}/tests/test_{name_snake}.py`

## Relevante Best Practices
{best_practices}

## Coding Conventions
{conventions}

## Ähnliche Handler als Referenz
{similar_handlers}

## Checklist
- [ ] Von BaseHandler erben
- [ ] InputSchema definieren
- [ ] OutputSchema definieren
- [ ] Drei-Phasen-Pattern: validate → process → save
- [ ] Async methods
- [ ] Docstrings
- [ ] Type hints
- [ ] Tests schreiben
""",
            "required_info": ["name", "domain", "description"],
            "include_conventions": True,
            "include_best_practices": True,
            "include_similar_code": True,
            "include_structure": True,
            "best_practice_topics": ["handlers", "pydantic", "error_handling"],
            "convention_categories": ["patterns", "naming", "error_handling"],
        },
        {
            "context_type": "fix_bug",
            "display_name": "Fix Bug",
            "context_template": """# Bug Fix

## Problem
{description}

## Betroffene Datei
{file_path}

## Relevante Conventions
{conventions}

## Error Handling Best Practices
{best_practices}

## Debugging Checklist
- [ ] Error Logs prüfen
- [ ] Input validieren
- [ ] Edge Cases prüfen
- [ ] Tests schreiben die den Bug reproduzieren
""",
            "required_info": ["description", "file_path"],
            "include_conventions": True,
            "include_best_practices": True,
            "include_similar_code": False,
            "include_structure": False,
            "best_practice_topics": ["error_handling", "testing"],
            "convention_categories": ["error_handling"],
        },
        {
            "context_type": "review",
            "display_name": "Code Review",
            "context_template": """# Code Review

## Zu prüfender Code
```
{code}
```

## Review Kriterien

### Patterns
{pattern_conventions}

### Naming
{naming_conventions}

### Error Handling
{error_conventions}

### Documentation
{doc_conventions}

## Checklist
- [ ] Folgt Handler/Service Pattern
- [ ] Input/Output validiert
- [ ] Exceptions richtig behandelt
- [ ] Docstrings vorhanden
- [ ] Type hints komplett
- [ ] Tests vorhanden
""",
            "required_info": ["code"],
            "include_conventions": True,
            "include_best_practices": True,
            "include_similar_code": False,
            "include_structure": False,
            "best_practice_topics": ["handlers", "pydantic", "testing"],
            "convention_categories": ["patterns", "naming", "error_handling", "documentation"],
        },
        {
            "context_type": "create_test",
            "display_name": "Create Tests",
            "context_template": """# Tests erstellen für: {name}

## Zu testender Code
{code}

## Test-Datei
`apps/{domain}/tests/test_{name_snake}.py`

## Testing Best Practices
{best_practices}

## Conventions
{conventions}

## Test Checklist
- [ ] Happy Path testen
- [ ] Edge Cases testen
- [ ] Error Cases testen
- [ ] Mocks für externe Dependencies
- [ ] Fixtures für Test Data
""",
            "required_info": ["name", "domain", "code"],
            "include_conventions": True,
            "include_best_practices": True,
            "include_similar_code": True,
            "include_structure": True,
            "best_practice_topics": ["testing"],
            "convention_categories": ["testing"],
        },
    ]


# =============================================================================
# SYNC FUNCTIONS
# =============================================================================

async def sync_conventions_to_db() -> dict[str, int]:
    """
    Synchronisiert Coding Conventions in die Datenbank.
    """
    try:
        from .models_extension import CodingConvention
    except ImportError:
        return {"error": "Models not available"}
    
    from asgiref.sync import sync_to_async
    
    created = 0
    updated = 0
    
    for conv_data in get_initial_conventions():
        name = conv_data.pop("name")
        obj, was_created = await sync_to_async(
            CodingConvention.objects.update_or_create
        )(
            name=name,
            defaults=conv_data
        )
        if was_created:
            created += 1
        else:
            updated += 1
    
    return {"created": created, "updated": updated}


async def sync_structures_to_db() -> dict[str, int]:
    """
    Synchronisiert Project Structures in die Datenbank.
    """
    try:
        from .models_extension import ProjectStructure
    except ImportError:
        return {"error": "Models not available"}
    
    from asgiref.sync import sync_to_async
    
    created = 0
    updated = 0
    
    for struct_data in get_initial_structures():
        component_type = struct_data.pop("component_type")
        obj, was_created = await sync_to_async(
            ProjectStructure.objects.update_or_create
        )(
            component_type=component_type,
            defaults=struct_data
        )
        if was_created:
            created += 1
        else:
            updated += 1
    
    return {"created": created, "updated": updated}


async def sync_contexts_to_db() -> dict[str, int]:
    """
    Synchronisiert MCP Contexts in die Datenbank.
    """
    try:
        from .models_extension import MCPContext
    except ImportError:
        return {"error": "Models not available"}
    
    from asgiref.sync import sync_to_async
    
    created = 0
    updated = 0
    
    for ctx_data in get_initial_contexts():
        context_type = ctx_data.pop("context_type")
        obj, was_created = await sync_to_async(
            MCPContext.objects.update_or_create
        )(
            context_type=context_type,
            defaults=ctx_data
        )
        if was_created:
            created += 1
        else:
            updated += 1
    
    return {"created": created, "updated": updated}


async def sync_all_extended_data() -> dict[str, Any]:
    """
    Synchronisiert alle erweiterten Daten.
    """
    return {
        "conventions": await sync_conventions_to_db(),
        "structures": await sync_structures_to_db(),
        "contexts": await sync_contexts_to_db(),
    }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "get_initial_conventions",
    "get_initial_structures",
    "get_initial_contexts",
    "sync_conventions_to_db",
    "sync_structures_to_db",
    "sync_contexts_to_db",
    "sync_all_extended_data",
]
