# -*- coding: utf-8 -*-
"""
URL Routing Rules für BF Agent.

Definiert verbindliche Konventionen für URL-Routing im Projekt.
Diese Regeln werden vom DjangoAgent zur Validierung verwendet.
"""

# =============================================================================
# APP → URL PREFIX MAPPING
# =============================================================================
# Jede Django App hat ein definiertes URL-Prefix in config/urls.py

APP_URL_PREFIXES = {
    # Format: "app_name": "url_prefix"
    
    # Core Apps
    "bfagent": "bookwriting",           # Book Writing Studio
    "control_center": "control-center", # Control Center (+ Agent/LLM Controlling)
    "core": "",                          # Core (root level APIs)
    
    # Hub Apps (alle mit -hub Suffix)
    "writing_hub": "writing-hub",
    "cad_hub": "cad-hub",
    "mcp_hub": "mcp-hub",
    "expert_hub": "expert-hub",
    "media_hub": "media-hub",
    "ui_hub": "ui-hub",
    "dlm_hub": "dlm-hub",
    "hub": "hub",                        # Central Hub
    
    # Feature Apps
    "presentation_studio": "pptx-studio",
    "genagent": "genagent",
    "workflow_system": "workflow",
    "checklist_system": "checklists",
    
    # API Prefixes
    "api.workflow": "api/workflow",
    "api.mcp": "api/mcp",
    "api.domains": "api/domains",
    "api.n8n": "api/n8n",
}

# Reverse Mapping für schnelle Lookups
URL_TO_APP = {v: k for k, v in APP_URL_PREFIXES.items() if v}


# =============================================================================
# URL NAMING CONVENTIONS
# =============================================================================

URL_NAMING_RULES = {
    # URL-Pfade
    "path_style": "kebab-case",          # z.B. /control-center/ nicht /control_center/
    "no_trailing_numbers": True,         # z.B. /hub/ nicht /hub2/
    "max_depth": 4,                       # z.B. /app/resource/id/action/ max
    
    # URL Names (für reverse())
    "name_style": "kebab-case",          # z.B. "project-list" nicht "project_list"
    "namespace_required": True,           # z.B. "bfagent:project-list" nicht "project-list"
    "namespace_separator": ":",           # Standard Django
    
    # Ressourcen-Patterns
    "list_suffix": "-list",              # z.B. project-list
    "detail_suffix": "-detail",          # z.B. project-detail
    "create_suffix": "-create",          # z.B. project-create
    "update_suffix": "-update",          # z.B. project-update (oder -edit)
    "delete_suffix": "-delete",          # z.B. project-delete
}


# =============================================================================
# STANDARD URL PATTERNS
# =============================================================================

STANDARD_URL_PATTERNS = {
    # CRUD Operationen
    "list": "{resource}/",                      # GET /projects/
    "detail": "{resource}/<int:pk>/",           # GET /projects/1/
    "create": "{resource}/create/",             # GET/POST /projects/create/
    "update": "{resource}/<int:pk>/edit/",      # GET/POST /projects/1/edit/
    "delete": "{resource}/<int:pk>/delete/",    # POST /projects/1/delete/
    
    # Nested Resources
    "nested_list": "{parent}/<int:pk>/{child}/",
    "nested_detail": "{parent}/<int:pk>/{child}/<int:child_pk>/",
    
    # API Patterns
    "api_list": "api/{resource}/",
    "api_detail": "api/{resource}/<int:pk>/",
    
    # HTMX Partials
    "htmx_partial": "{resource}/<int:pk>/{action}/",
}


# =============================================================================
# FORBIDDEN PATTERNS
# =============================================================================

FORBIDDEN_URL_PATTERNS = [
    # Keine Unterstriche in URLs
    r"_",
    
    # Keine camelCase
    r"[a-z][A-Z]",
    
    # Keine doppelten Slashes
    r"//",
    
    # Keine .html Endungen
    r"\.html$",
    
    # Keine Versionsnummern in Pfaden (außer API)
    r"/v\d+/(?!api)",
]


# =============================================================================
# HUB-SPEZIFISCHE REGELN
# =============================================================================

HUB_ROUTING_RULES = {
    # Alle Hubs folgen demselben Pattern
    "base_pattern": "{hub_name}/",
    "dashboard": "{hub_name}/dashboard/",
    "settings": "{hub_name}/settings/",
    
    # Hub-interne Ressourcen
    "resource_pattern": "{hub_name}/{resource}/",
    "resource_detail": "{hub_name}/{resource}/<int:pk>/",
    
    # Naming Convention
    "hub_suffix": "-hub",                # z.B. writing-hub, cad-hub
    "url_prefix_matches_app": True,      # App "writing_hub" → URL "/writing-hub/"
}


# =============================================================================
# VALIDATION HELPER
# =============================================================================

def get_correct_url_prefix(app_name: str) -> str:
    """Gibt das korrekte URL-Prefix für eine App zurück."""
    return APP_URL_PREFIXES.get(app_name, app_name.replace("_", "-"))


def validate_url_path(path: str) -> tuple[bool, list[str]]:
    """
    Validiert einen URL-Pfad gegen die Routing-Regeln.
    
    Returns:
        (valid, errors) Tuple
    """
    import re
    errors = []
    
    # Check forbidden patterns
    for pattern in FORBIDDEN_URL_PATTERNS:
        if re.search(pattern, path):
            errors.append(f"URL enthält verbotenes Pattern: {pattern}")
    
    # Check kebab-case
    parts = path.strip("/").split("/")
    for part in parts:
        if part and "_" in part:
            errors.append(f"URL-Teil '{part}' enthält Unterstrich, verwende kebab-case")
    
    # Check for wrong app prefixes
    if parts:
        first_part = parts[0]
        for app_name, correct_prefix in APP_URL_PREFIXES.items():
            # Wenn jemand den App-Namen als Prefix verwendet
            app_kebab = app_name.replace("_", "-")
            if first_part == app_name and first_part != correct_prefix:
                errors.append(
                    f"Falsches Prefix '/{first_part}/'. "
                    f"Korrekt: '/{correct_prefix}/'"
                )
    
    return len(errors) == 0, errors


def get_url_pattern_for_view(view_type: str, resource: str) -> str:
    """Generiert das Standard-URL-Pattern für einen View-Typ."""
    pattern = STANDARD_URL_PATTERNS.get(view_type)
    if pattern:
        return pattern.format(resource=resource)
    return None
