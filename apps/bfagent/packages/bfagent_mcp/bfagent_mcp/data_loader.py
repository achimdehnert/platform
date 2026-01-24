"""
BF Agent MCP Server - Django Management Command
================================================

Management commands for setting up MCP integration.

Usage:
    # Load initial data (domains, handlers, best practices)
    python manage.py mcp_setup --load-initial
    
    # Sync mock data to database
    python manage.py mcp_setup --sync-mock
    
    # Verify database consistency
    python manage.py mcp_setup --verify
    
    # Run MCP server
    python manage.py mcp_server
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


# =============================================================================
# DATA LOADER - Lädt Mock-Daten in Django DB
# =============================================================================

def get_initial_domains() -> List[Dict[str, Any]]:
    """Get initial domain data for database seeding."""
    return [
        {
            "domain_id": "books",
            "display_name": "Book Writing Platform",
            "description": "AI-powered book creation with character generation, story structures (Save the Cat, Hero's Journey), bilingual content, and automated illustration generation.",
            "status": "production",
            "icon": "book-open",
            "color": "#8B5CF6",
            "phases": [
                {"name": "concept", "display_name": "Concept Development", "order": 1},
                {"name": "structure", "display_name": "Story Structure", "order": 2},
                {"name": "characters", "display_name": "Character Design", "order": 3},
                {"name": "writing", "display_name": "Content Writing", "order": 4},
                {"name": "illustration", "display_name": "Illustration", "order": 5},
                {"name": "export", "display_name": "Export & Publishing", "order": 6},
            ],
            "handlers": [
                {
                    "name": "StoryStructureHandler",
                    "description": "Generates story structure using Save the Cat beat sheet or Hero's Journey archetypes.",
                    "handler_type": "ai_powered",
                    "ai_provider": "openai",
                },
                {
                    "name": "CharacterGeneratorHandler",
                    "description": "Creates character profiles with personality traits, backstory, and visual descriptions.",
                    "handler_type": "ai_powered",
                    "ai_provider": "openai",
                },
                {
                    "name": "IllustrationHandler",
                    "description": "Generates book illustrations using DALL-E 3 or Stability AI.",
                    "handler_type": "ai_powered",
                    "ai_provider": "openai",
                },
                {
                    "name": "PDFExportHandler",
                    "description": "Exports book to PDF with proper formatting, pagination, and embedded images.",
                    "handler_type": "utility",
                },
            ],
        },
        {
            "domain_id": "cad",
            "display_name": "CAD Analysis",
            "description": "Technical drawing analysis with DXF/DWG parsing, dimension extraction, and standards compliance checking.",
            "status": "beta",
            "icon": "ruler",
            "color": "#F59E0B",
            "phases": [
                {"name": "upload", "display_name": "File Upload", "order": 1},
                {"name": "parse", "display_name": "DXF Parsing", "order": 2},
                {"name": "analyze", "display_name": "Analysis", "order": 3},
                {"name": "validate", "display_name": "Validation", "order": 4},
                {"name": "report", "display_name": "Report Generation", "order": 5},
            ],
            "handlers": [
                {
                    "name": "DXFParserHandler",
                    "description": "Parses DXF files and extracts geometric entities using ezdxf.",
                    "handler_type": "rule_based",
                },
                {
                    "name": "DimensionExtractorHandler",
                    "description": "Extracts dimensions using OCR (Tesseract) and pattern matching.",
                    "handler_type": "hybrid",
                    "ai_provider": "tesseract",
                },
                {
                    "name": "ComplianceCheckerHandler",
                    "description": "Validates drawings against DIN/ISO standards.",
                    "handler_type": "rule_based",
                },
            ],
        },
        {
            "domain_id": "medtrans",
            "display_name": "Medical Translation",
            "description": "Professional medical document translation with terminology database integration.",
            "status": "production",
            "icon": "stethoscope",
            "color": "#10B981",
            "phases": [
                {"name": "extract", "display_name": "Content Extraction", "order": 1},
                {"name": "translate", "display_name": "Translation", "order": 2},
                {"name": "validate", "display_name": "Terminology Validation", "order": 3},
                {"name": "reconstruct", "display_name": "Document Reconstruction", "order": 4},
            ],
            "handlers": [
                {
                    "name": "PPTXExtractorHandler",
                    "description": "Extracts text from PowerPoint presentations preserving structure.",
                    "handler_type": "rule_based",
                },
                {
                    "name": "MedicalTranslationHandler",
                    "description": "Translates medical content with specialized glossary.",
                    "handler_type": "ai_powered",
                    "ai_provider": "openai",
                },
            ],
        },
        {
            "domain_id": "exschutz",
            "display_name": "Explosion Protection",
            "description": "Automated explosion protection documentation per BetrSichV and ATEX standards.",
            "status": "development",
            "icon": "shield-alert",
            "color": "#EF4444",
            "phases": [
                {"name": "input", "display_name": "Data Input", "order": 1},
                {"name": "zone", "display_name": "Zone Classification", "order": 2},
                {"name": "risk", "display_name": "Risk Assessment", "order": 3},
                {"name": "measures", "display_name": "Protection Measures", "order": 4},
                {"name": "document", "display_name": "Documentation", "order": 5},
            ],
        },
    ]


def get_initial_best_practices() -> List[Dict[str, Any]]:
    """Get initial best practices data."""
    return [
        {
            "topic": "handlers",
            "display_name": "Handler Best Practices",
            "content": """# Handler Best Practices

## Three-Phase Pattern

Every handler follows Input → Process → Output:

```python
class MyHandler(BaseHandler):
    async def validate(self, context: Dict) -> MyInput:
        return MyInput(**context)
    
    async def process(self, validated: MyInput) -> MyOutput:
        # Business logic
        return MyOutput(...)
    
    async def save_result(self, result: MyOutput) -> HandlerResult:
        return HandlerResult(success=True)
```

## Key Principles

1. **Pydantic for All I/O** - Type-safe with validation
2. **Transaction Safety** - Atomic operations with rollback
3. **Comprehensive Logging** - Structured with context
4. **Error Recovery** - Graceful degradation
""",
            "order": 1,
        },
        {
            "topic": "pydantic",
            "display_name": "Pydantic Patterns",
            "content": """# Pydantic Best Practices

## Schema Definition

```python
from pydantic import BaseModel, Field, ConfigDict

class MyInput(BaseModel):
    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
    )
    
    name: str = Field(..., min_length=1, max_length=100)
    count: int = Field(default=10, ge=1, le=1000)
```

## Validators

- Use `@field_validator` for complex validation
- Use `@model_validator` for cross-field validation
- Always provide clear error messages
""",
            "order": 2,
        },
        {
            "topic": "ai_integration",
            "display_name": "AI Integration",
            "content": """# AI Provider Integration

## Multi-Provider Support

```python
from apps.core.ai import AIRouter

router = AIRouter()
router.register("openai", OpenAIProvider())
router.register("ollama", OllamaProvider())

# Automatic routing based on content
response = await router.complete(prompt, content_type="safe")
```

## Best Practices

- Use local models (Ollama) for sensitive content
- Implement retry with exponential backoff
- Track token usage for cost management
- Cache responses where appropriate
""",
            "order": 3,
        },
        {
            "topic": "testing",
            "display_name": "Testing Patterns",
            "content": """# Testing Best Practices

## Test Structure

```python
@pytest.mark.asyncio
class TestMyHandler:
    @pytest.fixture
    def handler(self):
        return MyHandler()
    
    async def test_validate_success(self, handler):
        result = await handler.validate({"input": "test"})
        assert result.input == "test"
    
    async def test_process_creates_output(self, handler):
        input_data = MyInput(input="test")
        result = await handler.process(input_data)
        assert result is not None
```

## Coverage Goals

- Unit tests: 80%+ coverage
- Integration tests: Critical paths
- E2E tests: Happy paths
""",
            "order": 4,
        },
    ]


# =============================================================================
# DATABASE SYNC FUNCTIONS
# =============================================================================

async def sync_domains_to_db():
    """Sync initial domains to database."""
    from bfagent_mcp.django_integration import (
        ensure_django_setup,
        get_domain_model,
        get_phase_model,
        get_handler_model,
        get_tag_model,
    )
    
    ensure_django_setup()
    
    Domain = get_domain_model()
    Phase = get_phase_model()
    Handler = get_handler_model()
    
    created_domains = 0
    created_phases = 0
    created_handlers = 0
    
    for domain_data in get_initial_domains():
        # Create or update domain
        domain, created = Domain.objects.update_or_create(
            domain_id=domain_data["domain_id"],
            defaults={
                "display_name": domain_data["display_name"],
                "description": domain_data["description"],
                "status": domain_data["status"],
                "icon": domain_data.get("icon", ""),
                "color": domain_data.get("color", "#6366F1"),
            }
        )
        
        if created:
            created_domains += 1
        
        # Create phases
        for phase_data in domain_data.get("phases", []):
            phase, created = Phase.objects.update_or_create(
                domain=domain,
                name=phase_data["name"],
                defaults={
                    "display_name": phase_data["display_name"],
                    "order": phase_data["order"],
                }
            )
            if created:
                created_phases += 1
        
        # Create handlers
        for handler_data in domain_data.get("handlers", []):
            handler, created = Handler.objects.update_or_create(
                domain=domain,
                name=handler_data["name"],
                defaults={
                    "description": handler_data["description"],
                    "handler_type": handler_data.get("handler_type", "rule_based"),
                    "ai_provider": handler_data.get("ai_provider", "none"),
                }
            )
            if created:
                created_handlers += 1
    
    return {
        "domains": created_domains,
        "phases": created_phases,
        "handlers": created_handlers,
    }


async def sync_best_practices_to_db():
    """Sync best practices to database."""
    from bfagent_mcp.django_integration import (
        ensure_django_setup,
        get_best_practice_model,
    )
    
    ensure_django_setup()
    BestPractice = get_best_practice_model()
    
    created = 0
    for bp_data in get_initial_best_practices():
        _, was_created = BestPractice.objects.update_or_create(
            topic=bp_data["topic"],
            defaults={
                "display_name": bp_data["display_name"],
                "content": bp_data["content"],
                "order": bp_data["order"],
            }
        )
        if was_created:
            created += 1
    
    return created


async def verify_database():
    """Verify database consistency."""
    from bfagent_mcp.django_integration import (
        ensure_django_setup,
        get_domain_model,
        get_handler_model,
        get_phase_model,
    )
    
    ensure_django_setup()
    
    Domain = get_domain_model()
    Handler = get_handler_model()
    Phase = get_phase_model()
    
    issues = []
    
    # Check for domains without phases
    for domain in Domain.objects.filter(is_active=True):
        phase_count = Phase.objects.filter(domain=domain).count()
        if phase_count == 0:
            issues.append(f"Domain '{domain.domain_id}' has no phases")
    
    # Check for handlers without domain
    orphan_handlers = Handler.objects.filter(domain__isnull=True).count()
    if orphan_handlers > 0:
        issues.append(f"{orphan_handlers} handlers have no domain")
    
    return {
        "domains": Domain.objects.filter(is_active=True).count(),
        "handlers": Handler.objects.filter(is_active=True).count(),
        "phases": Phase.objects.count(),
        "issues": issues,
    }


# =============================================================================
# DJANGO MANAGEMENT COMMAND (Copy this to your management/commands/)
# =============================================================================

MANAGEMENT_COMMAND_TEMPLATE = '''
"""
MCP Setup Management Command.

Copy this file to:
    apps/core/management/commands/mcp_setup.py
    
Usage:
    python manage.py mcp_setup --load-initial
    python manage.py mcp_setup --verify
"""

from django.core.management.base import BaseCommand
import asyncio


class Command(BaseCommand):
    help = "Setup MCP integration"
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--load-initial",
            action="store_true",
            help="Load initial domains and best practices"
        )
        parser.add_argument(
            "--verify",
            action="store_true",
            help="Verify database consistency"
        )
    
    def handle(self, *args, **options):
        from bfagent_mcp.data_loader import (
            sync_domains_to_db,
            sync_best_practices_to_db,
            verify_database,
        )
        
        if options["load_initial"]:
            self.stdout.write("Loading initial data...")
            
            result = asyncio.run(sync_domains_to_db())
            self.stdout.write(
                f"Created: {result['domains']} domains, "
                f"{result['phases']} phases, "
                f"{result['handlers']} handlers"
            )
            
            bp_count = asyncio.run(sync_best_practices_to_db())
            self.stdout.write(f"Created: {bp_count} best practices")
            
            self.stdout.write(self.style.SUCCESS("Initial data loaded!"))
        
        if options["verify"]:
            self.stdout.write("Verifying database...")
            
            result = asyncio.run(verify_database())
            self.stdout.write(
                f"Found: {result['domains']} domains, "
                f"{result['handlers']} handlers, "
                f"{result['phases']} phases"
            )
            
            if result["issues"]:
                for issue in result["issues"]:
                    self.stdout.write(self.style.WARNING(f"Issue: {issue}"))
            else:
                self.stdout.write(self.style.SUCCESS("No issues found!"))
'''


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "get_initial_domains",
    "get_initial_best_practices",
    "sync_domains_to_db",
    "sync_best_practices_to_db",
    "verify_database",
    "MANAGEMENT_COMMAND_TEMPLATE",
]
