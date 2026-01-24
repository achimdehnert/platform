"""
BF Agent MCP Server - Data Loader v3
======================================

Initial Data für:
1. Naming Conventions (für alle Domains/Apps)
2. MCP Models (Component Types, Risk Levels, etc.)

Reihenfolge ist wichtig wegen Foreign Keys!
"""

from __future__ import annotations
from typing import Any


# =============================================================================
# 1. NAMING CONVENTIONS
# =============================================================================

def get_naming_conventions() -> list[dict[str, Any]]:
    """
    Naming Conventions für alle Apps/Domains.
    
    Definiert Table/Class Prefixes pro App.
    """
    return [
        # Core - Basis-Framework
        {
            "app_label": "core",
            "domain_id": "core",
            "display_name": "Core Framework",
            "table_prefix": "core_",
            "class_prefix": "Core",
            "description": "Basis-Framework: Handler, Services, Models. "
                          "Wird von allen anderen Domains verwendet.",
            "example_tables": ["core_domain", "core_handler", "core_tag"],
            "example_classes": ["CoreDomain", "CoreHandler", "CoreTag"],
        },
        
        # MCP - BF Agent MCP Server
        {
            "app_label": "bfagent_mcp",
            "domain_id": "bfagent_mcp",
            "display_name": "MCP Server",
            "table_prefix": "mcp_",
            "class_prefix": "MCP",
            "description": "BF Agent MCP Server für Windsurf/Claude Integration. "
                          "Refactoring, Conventions, Context.",
            "example_tables": [
                "mcp_component_type", "mcp_risk_level", "mcp_domain_config",
                "mcp_protected_path", "mcp_refactor_session"
            ],
            "example_classes": [
                "MCPComponentType", "MCPRiskLevel", "MCPDomainConfig",
                "MCPProtectedPath", "MCPRefactorSession"
            ],
        },
        
        # Books - Book Writing
        {
            "app_label": "books",
            "domain_id": "books",
            "display_name": "Book Writing",
            "table_prefix": "books_",
            "class_prefix": "Books",
            "description": "Book Writing Domain - Kapitel, Abschnitte, AI-Content.",
            "example_tables": ["books_chapter", "books_section", "books_project"],
            "example_classes": ["BooksChapter", "BooksSection", "BooksProject"],
        },
        
        # MedTrans - Medical Translation
        {
            "app_label": "medtrans",
            "domain_id": "medtrans",
            "display_name": "Medical Translation",
            "table_prefix": "medtrans_",
            "class_prefix": "MedTrans",
            "description": "Medical Translation Domain - Übersetzungen mit Fachbegriffen.",
            "example_tables": ["medtrans_document", "medtrans_term", "medtrans_translation"],
            "example_classes": ["MedTransDocument", "MedTransTerm", "MedTransTranslation"],
        },
        
        # ExSchutz - Explosion Protection
        {
            "app_label": "exschutz",
            "domain_id": "exschutz",
            "display_name": "Explosion Protection",
            "table_prefix": "exschutz_",
            "class_prefix": "ExSchutz",
            "description": "Explosionsschutz Domain - BetrSichV Compliance, Research.",
            "example_tables": ["exschutz_zone", "exschutz_substance", "exschutz_document"],
            "example_classes": ["ExSchutzZone", "ExSchutzSubstance", "ExSchutzDocument"],
        },
        
        # Comic - Comic Creator
        {
            "app_label": "comic",
            "domain_id": "comic",
            "display_name": "Comic Creator",
            "table_prefix": "comic_",
            "class_prefix": "Comic",
            "description": "Comic Creator Domain - Panels, Characters, Image Generation.",
            "example_tables": ["comic_panel", "comic_character", "comic_story"],
            "example_classes": ["ComicPanel", "ComicCharacter", "ComicStory"],
        },
        
        # CAD - CAD Analysis
        {
            "app_label": "cad",
            "domain_id": "cad",
            "display_name": "CAD Analysis",
            "table_prefix": "cad_",
            "class_prefix": "CAD",
            "description": "CAD Analysis Domain - DXF/DWG Verarbeitung, Layer, Entities.",
            "example_tables": ["cad_drawing", "cad_layer", "cad_entity"],
            "example_classes": ["CADDrawing", "CADLayer", "CADEntity"],
        },
        
        # DSGVO - Data Protection
        {
            "app_label": "dsgvo",
            "domain_id": "dsgvo",
            "display_name": "Data Protection (DSGVO)",
            "table_prefix": "dsgvo_",
            "class_prefix": "DSGVO",
            "description": "Datenschutz Domain - DSGVO Compliance, Processing Records.",
            "example_tables": ["dsgvo_processing", "dsgvo_audit", "dsgvo_subject_request"],
            "example_classes": ["DSGVOProcessing", "DSGVOAudit", "DSGVOSubjectRequest"],
        },
    ]


# =============================================================================
# 2. MCP COMPONENT TYPES
# =============================================================================

def get_mcp_component_types() -> list[dict[str, Any]]:
    """
    Komponenten-Typen für BF Agent - mit MCP Prefix.
    """
    return [
        {
            "name": "handler",
            "display_name": "Handler",
            "default_path_pattern": "apps/{domain}/handlers/",
            "default_file_pattern": "{name}_handler.py",
            "default_class_pattern": "{Name}Handler",
            "icon": "🔧",
            "color": "#8b5cf6",
            "is_directory": True,
            "supports_refactoring": True,
            "order": 1,
            "description": "Handler führen einzelne Verarbeitungsschritte aus.",
        },
        {
            "name": "service",
            "display_name": "Service",
            "default_path_pattern": "apps/{domain}/services/",
            "default_file_pattern": "{name}_service.py",
            "default_class_pattern": "{Name}Service",
            "icon": "⚙️",
            "color": "#3b82f6",
            "is_directory": True,
            "supports_refactoring": True,
            "order": 2,
            "description": "Services orchestrieren Business Logic.",
        },
        {
            "name": "repository",
            "display_name": "Repository",
            "default_path_pattern": "apps/{domain}/repositories/",
            "default_file_pattern": "{name}_repository.py",
            "default_class_pattern": "{Name}Repository",
            "icon": "🗄️",
            "color": "#06b6d4",
            "is_directory": True,
            "supports_refactoring": True,
            "order": 3,
            "description": "Repositories abstrahieren Datenbankzugriffe.",
        },
        {
            "name": "model",
            "display_name": "Model",
            "default_path_pattern": "apps/{domain}/",
            "default_file_pattern": "models.py",
            "default_class_pattern": "{Name}",
            "icon": "📊",
            "color": "#22c55e",
            "is_directory": False,
            "supports_refactoring": True,
            "order": 4,
            "description": "Django Models definieren die Datenbankstruktur.",
        },
        {
            "name": "schema",
            "display_name": "Schema",
            "default_path_pattern": "apps/{domain}/",
            "default_file_pattern": "schemas.py",
            "default_class_pattern": "{Name}Schema",
            "icon": "📋",
            "color": "#eab308",
            "is_directory": False,
            "supports_refactoring": True,
            "order": 5,
            "description": "Pydantic Schemas für Validierung.",
        },
        {
            "name": "test",
            "display_name": "Test",
            "default_path_pattern": "apps/{domain}/tests/",
            "default_file_pattern": "test_{name}.py",
            "default_class_pattern": "Test{Name}",
            "icon": "🧪",
            "color": "#f97316",
            "is_directory": True,
            "supports_refactoring": True,
            "order": 6,
            "description": "Tests mit pytest.",
        },
        {
            "name": "admin",
            "display_name": "Admin",
            "default_path_pattern": "apps/{domain}/",
            "default_file_pattern": "admin.py",
            "default_class_pattern": "{Name}Admin",
            "icon": "👤",
            "color": "#ec4899",
            "is_directory": False,
            "supports_refactoring": True,
            "order": 7,
            "description": "Django Admin Konfiguration.",
        },
        {
            "name": "view",
            "display_name": "View",
            "default_path_pattern": "apps/{domain}/",
            "default_file_pattern": "views.py",
            "default_class_pattern": "{Name}View",
            "icon": "👁️",
            "color": "#14b8a6",
            "is_directory": False,
            "supports_refactoring": True,
            "order": 8,
            "description": "Django Views für HTTP Requests.",
        },
        {
            "name": "template",
            "display_name": "Template",
            "default_path_pattern": "apps/{domain}/templates/{domain}/",
            "default_file_pattern": "{name}.html",
            "default_class_pattern": "",
            "icon": "📄",
            "color": "#84cc16",
            "is_directory": True,
            "supports_refactoring": True,
            "order": 10,
            "description": "Django/Jinja2 HTML Templates.",
        },
        {
            "name": "migration",
            "display_name": "Migration",
            "default_path_pattern": "apps/{domain}/migrations/",
            "default_file_pattern": "*.py",
            "default_class_pattern": "Migration",
            "icon": "🔄",
            "color": "#78716c",
            "is_directory": True,
            "supports_refactoring": False,  # Niemals automatisch ändern!
            "order": 12,
            "description": "Django Migrations - nicht refactoren!",
        },
    ]


# =============================================================================
# 3. MCP RISK LEVELS
# =============================================================================

def get_mcp_risk_levels() -> list[dict[str, Any]]:
    """Risk Levels für Refactoring."""
    return [
        {
            "name": "critical",
            "display_name": "Critical",
            "severity_score": 100,
            "color": "#dc2626",
            "icon": "🔴",
            "requires_approval": True,
            "requires_backup": True,
            "description": "Kritische Komponenten - Self-Protection, zentrale Infrastruktur.",
        },
        {
            "name": "high",
            "display_name": "High",
            "severity_score": 80,
            "color": "#ea580c",
            "icon": "🟠",
            "requires_approval": True,
            "requires_backup": True,
            "description": "Core-Komponenten die alle Domains betreffen.",
        },
        {
            "name": "medium",
            "display_name": "Medium",
            "severity_score": 50,
            "color": "#ca8a04",
            "icon": "🟡",
            "requires_approval": False,
            "requires_backup": True,
            "description": "Standard Domain-Komponenten.",
        },
        {
            "name": "low",
            "display_name": "Low",
            "severity_score": 25,
            "color": "#16a34a",
            "icon": "🟢",
            "requires_approval": False,
            "requires_backup": True,
            "description": "Isolierte Komponenten mit wenig Abhängigkeiten.",
        },
        {
            "name": "minimal",
            "display_name": "Minimal",
            "severity_score": 10,
            "color": "#0891b2",
            "icon": "🔵",
            "requires_approval": False,
            "requires_backup": False,
            "description": "Experimentelle oder sehr isolierte Komponenten.",
        },
    ]


# =============================================================================
# 4. MCP PROTECTION LEVELS
# =============================================================================

def get_mcp_protection_levels() -> list[dict[str, Any]]:
    """Protection Levels für geschützte Pfade."""
    return [
        {
            "name": "absolute",
            "display_name": "Absolute",
            "severity_score": 100,
            "blocks_refactoring": True,
            "requires_confirmation": False,
            "color": "#dc2626",
            "icon": "🔒",
            "description": "Kann niemals refactored werden.",
        },
        {
            "name": "warn",
            "display_name": "Warning",
            "severity_score": 50,
            "blocks_refactoring": False,
            "requires_confirmation": True,
            "color": "#ca8a04",
            "icon": "⚠️",
            "description": "Warnung vor Refactoring.",
        },
        {
            "name": "review",
            "display_name": "Review Required",
            "severity_score": 30,
            "blocks_refactoring": False,
            "requires_confirmation": True,
            "color": "#2563eb",
            "icon": "👁️",
            "description": "Manuelles Review erforderlich.",
        },
    ]


# =============================================================================
# 5. MCP PATH CATEGORIES
# =============================================================================

def get_mcp_path_categories() -> list[dict[str, Any]]:
    """Kategorien für Protected Paths."""
    return [
        {"name": "mcp", "display_name": "MCP Package", "icon": "🤖", "color": "#8b5cf6", "order": 1},
        {"name": "config", "display_name": "Configuration", "icon": "⚙️", "color": "#3b82f6", "order": 2},
        {"name": "security", "display_name": "Security", "icon": "🔐", "color": "#dc2626", "order": 3},
        {"name": "infrastructure", "display_name": "Infrastructure", "icon": "🏗️", "color": "#78716c", "order": 4},
        {"name": "external", "display_name": "External/Vendor", "icon": "📦", "color": "#6b7280", "order": 5},
        {"name": "generated", "display_name": "Generated", "icon": "🔄", "color": "#0891b2", "order": 6},
    ]


# =============================================================================
# 6. MCP PROTECTED PATHS
# =============================================================================

def get_mcp_protected_paths() -> list[dict[str, Any]]:
    """Protected Paths mit Category und Level."""
    return [
        # MCP Package
        {"path_pattern": "packages/bfagent_mcp/**", "reason": "MCP Server - Self-Protection", "protection_level": "absolute", "category": "mcp"},
        # Config
        {"path_pattern": "config/**", "reason": "Django Configuration", "protection_level": "absolute", "category": "config"},
        {"path_pattern": "settings/**", "reason": "Django Settings", "protection_level": "absolute", "category": "config"},
        # Security
        {"path_pattern": ".env*", "reason": "Environment Secrets", "protection_level": "absolute", "category": "security"},
        {"path_pattern": "*.env*", "reason": "Environment Files", "protection_level": "absolute", "category": "security"},
        # Infrastructure
        {"path_pattern": "manage.py", "reason": "Django Entry Point", "protection_level": "absolute", "category": "infrastructure"},
        {"path_pattern": "wsgi.py", "reason": "WSGI Entry Point", "protection_level": "absolute", "category": "infrastructure"},
        {"path_pattern": "asgi.py", "reason": "ASGI Entry Point", "protection_level": "absolute", "category": "infrastructure"},
        {"path_pattern": "Dockerfile*", "reason": "Docker Config", "protection_level": "warn", "category": "infrastructure"},
        {"path_pattern": "docker-compose*.yml", "reason": "Docker Compose", "protection_level": "warn", "category": "infrastructure"},
        {"path_pattern": ".github/**", "reason": "GitHub Actions", "protection_level": "warn", "category": "infrastructure"},
        # External
        {"path_pattern": "node_modules/**", "reason": "NPM Packages", "protection_level": "absolute", "category": "external"},
        {"path_pattern": "static/vendor/**", "reason": "Vendor Libraries", "protection_level": "absolute", "category": "external"},
        {"path_pattern": ".venv/**", "reason": "Virtual Environment", "protection_level": "absolute", "category": "external"},
        # Generated
        {"path_pattern": "**/migrations/**", "reason": "Django Migrations", "protection_level": "review", "category": "generated"},
    ]


# =============================================================================
# 7. MCP DOMAIN CONFIGS
# =============================================================================

def get_mcp_domain_configs() -> list[dict[str, Any]]:
    """Domain Refactoring Configs."""
    return [
        {
            "domain_id": "core",
            "base_path": "apps/core/",
            "risk_level": "high",
            "risk_notes": "Core ist das Fundament für alle Domains.",
            "is_refactor_ready": True,
            "is_protected": False,
            "refactor_order": 1,
            "depends_on": [],
            "components": ["handler", "service", "repository", "model", "schema", "test", "admin"],
        },
        {
            "domain_id": "books",
            "base_path": "apps/books/",
            "risk_level": "medium",
            "risk_notes": "Book Writing Domain - 12+ Handler.",
            "is_refactor_ready": True,
            "is_protected": False,
            "refactor_order": 10,
            "depends_on": ["core"],
            "components": ["handler", "service", "model", "schema", "test", "admin", "view", "template"],
        },
        {
            "domain_id": "medtrans",
            "base_path": "apps/medtrans/",
            "risk_level": "medium",
            "risk_notes": "Medical Translation - Compliance-relevant.",
            "is_refactor_ready": True,
            "is_protected": False,
            "refactor_order": 20,
            "depends_on": ["core"],
            "components": ["handler", "service", "model", "schema", "test", "admin"],
        },
        {
            "domain_id": "exschutz",
            "base_path": "apps/exschutz/",
            "risk_level": "medium",
            "risk_notes": "Explosionsschutz - BetrSichV Compliance.",
            "is_refactor_ready": True,
            "is_protected": False,
            "refactor_order": 30,
            "depends_on": ["core"],
            "components": ["handler", "service", "model", "schema", "test"],
        },
        {
            "domain_id": "comic",
            "base_path": "apps/comic/",
            "risk_level": "low",
            "risk_notes": "Comic Creator - relativ isoliert.",
            "is_refactor_ready": True,
            "is_protected": False,
            "refactor_order": 40,
            "depends_on": ["core"],
            "components": ["handler", "service", "model", "schema", "test"],
        },
        {
            "domain_id": "cad",
            "base_path": "apps/cad/",
            "risk_level": "low",
            "risk_notes": "CAD Analysis - ezdxf.",
            "is_refactor_ready": True,
            "is_protected": False,
            "refactor_order": 50,
            "depends_on": ["core"],
            "components": ["handler", "service", "model", "schema", "test"],
        },
        {
            "domain_id": "dsgvo",
            "base_path": "apps/dsgvo/",
            "risk_level": "medium",
            "risk_notes": "Datenschutz - DSGVO Compliance.",
            "is_refactor_ready": True,
            "is_protected": False,
            "refactor_order": 60,
            "depends_on": ["core"],
            "components": ["handler", "service", "model", "schema", "test", "admin"],
        },
        {
            "domain_id": "bfagent_mcp",
            "base_path": "packages/bfagent_mcp/",
            "risk_level": "critical",
            "risk_notes": "MCP Package - SELF-PROTECTION!",
            "is_refactor_ready": False,
            "is_protected": True,
            "refactor_order": 999,
            "depends_on": ["core"],
            "components": ["service", "repository", "model", "schema", "test"],
        },
    ]


# =============================================================================
# SYNC FUNCTIONS
# =============================================================================

async def sync_naming_conventions() -> dict[str, int]:
    """Sync Naming Conventions to DB."""
    try:
        from .models_naming import TableNamingConvention
        from .models import Domain
    except ImportError:
        return {"error": "Models not available"}
    
    from asgiref.sync import sync_to_async
    
    created, updated = 0, 0
    
    for data in get_naming_conventions():
        app_label = data.pop("app_label")
        domain_id = data.pop("domain_id", None)
        
        # Get domain if specified
        domain = None
        if domain_id:
            try:
                domain = await sync_to_async(Domain.objects.get)(domain_id=domain_id)
            except Domain.DoesNotExist:
                pass
        
        data["domain"] = domain
        
        obj, was_created = await sync_to_async(
            TableNamingConvention.objects.update_or_create
        )(app_label=app_label, defaults=data)
        
        created += 1 if was_created else 0
        updated += 0 if was_created else 1
    
    return {"created": created, "updated": updated}


async def sync_mcp_component_types() -> dict[str, int]:
    """Sync MCPComponentType to DB."""
    try:
        from .models_mcp import MCPComponentType
    except ImportError:
        return {"error": "Models not available"}
    
    from asgiref.sync import sync_to_async
    
    created, updated = 0, 0
    for data in get_mcp_component_types():
        name = data.pop("name")
        obj, was_created = await sync_to_async(
            MCPComponentType.objects.update_or_create
        )(name=name, defaults=data)
        created += 1 if was_created else 0
        updated += 0 if was_created else 1
    
    return {"created": created, "updated": updated}


async def sync_mcp_risk_levels() -> dict[str, int]:
    """Sync MCPRiskLevel to DB."""
    try:
        from .models_mcp import MCPRiskLevel
    except ImportError:
        return {"error": "Models not available"}
    
    from asgiref.sync import sync_to_async
    
    created, updated = 0, 0
    for data in get_mcp_risk_levels():
        name = data.pop("name")
        obj, was_created = await sync_to_async(
            MCPRiskLevel.objects.update_or_create
        )(name=name, defaults=data)
        created += 1 if was_created else 0
        updated += 0 if was_created else 1
    
    return {"created": created, "updated": updated}


async def sync_mcp_protection_levels() -> dict[str, int]:
    """Sync MCPProtectionLevel to DB."""
    try:
        from .models_mcp import MCPProtectionLevel
    except ImportError:
        return {"error": "Models not available"}
    
    from asgiref.sync import sync_to_async
    
    created, updated = 0, 0
    for data in get_mcp_protection_levels():
        name = data.pop("name")
        obj, was_created = await sync_to_async(
            MCPProtectionLevel.objects.update_or_create
        )(name=name, defaults=data)
        created += 1 if was_created else 0
        updated += 0 if was_created else 1
    
    return {"created": created, "updated": updated}


async def sync_mcp_path_categories() -> dict[str, int]:
    """Sync MCPPathCategory to DB."""
    try:
        from .models_mcp import MCPPathCategory
    except ImportError:
        return {"error": "Models not available"}
    
    from asgiref.sync import sync_to_async
    
    created, updated = 0, 0
    for data in get_mcp_path_categories():
        name = data.pop("name")
        obj, was_created = await sync_to_async(
            MCPPathCategory.objects.update_or_create
        )(name=name, defaults=data)
        created += 1 if was_created else 0
        updated += 0 if was_created else 1
    
    return {"created": created, "updated": updated}


async def sync_mcp_protected_paths() -> dict[str, int]:
    """Sync MCPProtectedPath to DB."""
    try:
        from .models_mcp import MCPProtectedPath, MCPProtectionLevel, MCPPathCategory
    except ImportError:
        return {"error": "Models not available"}
    
    from asgiref.sync import sync_to_async
    
    created, updated, skipped = 0, 0, 0
    
    for data in get_mcp_protected_paths():
        path_pattern = data.pop("path_pattern")
        level_name = data.pop("protection_level")
        category_name = data.pop("category")
        
        try:
            protection_level = await sync_to_async(MCPProtectionLevel.objects.get)(name=level_name)
            category = await sync_to_async(MCPPathCategory.objects.get)(name=category_name)
        except (MCPProtectionLevel.DoesNotExist, MCPPathCategory.DoesNotExist):
            skipped += 1
            continue
        
        data["protection_level"] = protection_level
        data["category"] = category
        
        obj, was_created = await sync_to_async(
            MCPProtectedPath.objects.update_or_create
        )(path_pattern=path_pattern, defaults=data)
        
        created += 1 if was_created else 0
        updated += 0 if was_created else 1
    
    return {"created": created, "updated": updated, "skipped": skipped}


async def sync_mcp_domain_configs() -> dict[str, int]:
    """Sync MCPDomainConfig and MCPDomainComponent to DB."""
    try:
        from .models_mcp import MCPDomainConfig, MCPDomainComponent, MCPRiskLevel, MCPComponentType
        from .models import Domain
    except ImportError:
        return {"error": "Models not available"}
    
    from asgiref.sync import sync_to_async
    
    created, updated, skipped = 0, 0, 0
    components_created = 0
    
    for data in get_mcp_domain_configs():
        domain_id = data.pop("domain_id")
        risk_level_name = data.pop("risk_level")
        depends_on_ids = data.pop("depends_on", [])
        component_names = data.pop("components", [])
        
        try:
            domain = await sync_to_async(Domain.objects.get)(domain_id=domain_id)
            risk_level = await sync_to_async(MCPRiskLevel.objects.get)(name=risk_level_name)
        except (Domain.DoesNotExist, MCPRiskLevel.DoesNotExist):
            skipped += 1
            continue
        
        data["risk_level"] = risk_level
        
        obj, was_created = await sync_to_async(
            MCPDomainConfig.objects.update_or_create
        )(domain=domain, defaults=data)
        
        created += 1 if was_created else 0
        updated += 0 if was_created else 1
        
        # Set dependencies
        if depends_on_ids:
            deps = await sync_to_async(list)(Domain.objects.filter(domain_id__in=depends_on_ids))
            await sync_to_async(obj.depends_on.set)(deps)
        
        # Create components
        for comp_name in component_names:
            try:
                comp_type = await sync_to_async(MCPComponentType.objects.get)(name=comp_name)
                _, comp_created = await sync_to_async(
                    MCPDomainComponent.objects.get_or_create
                )(
                    domain_config=obj,
                    component_type=comp_type,
                    defaults={"is_refactorable": comp_type.supports_refactoring}
                )
                if comp_created:
                    components_created += 1
            except MCPComponentType.DoesNotExist:
                pass
    
    return {"created": created, "updated": updated, "skipped": skipped, "components": components_created}


async def sync_all_mcp_data() -> dict[str, Any]:
    """
    Synchronisiert ALLE MCP-Daten in korrekter Reihenfolge.
    """
    results = {}
    
    # 1. Naming Conventions
    results["naming_conventions"] = await sync_naming_conventions()
    
    # 2. Reference Tables (keine FKs)
    results["component_types"] = await sync_mcp_component_types()
    results["risk_levels"] = await sync_mcp_risk_levels()
    results["protection_levels"] = await sync_mcp_protection_levels()
    results["path_categories"] = await sync_mcp_path_categories()
    
    # 3. Protected Paths (braucht level, category)
    results["protected_paths"] = await sync_mcp_protected_paths()
    
    # 4. Domain Configs (braucht Domain, risk_level, component_types)
    results["domain_configs"] = await sync_mcp_domain_configs()
    
    return results


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Data Getters
    "get_naming_conventions",
    "get_mcp_component_types",
    "get_mcp_risk_levels",
    "get_mcp_protection_levels",
    "get_mcp_path_categories",
    "get_mcp_protected_paths",
    "get_mcp_domain_configs",
    # Sync Functions
    "sync_naming_conventions",
    "sync_mcp_component_types",
    "sync_mcp_risk_levels",
    "sync_mcp_protection_levels",
    "sync_mcp_path_categories",
    "sync_mcp_protected_paths",
    "sync_mcp_domain_configs",
    "sync_all_mcp_data",
]
