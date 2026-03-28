"""
Hub Visual Identity System — Context Processors (ADR-051)

Injects hub metadata, Schema.org config, and user preferences
into every Django template context.

Installation in settings/base.py:
    TEMPLATES = [{
        ...
        'OPTIONS': {
            'context_processors': [
                ...
                'apps.core.context_processors.hub_identity',
                'apps.core.context_processors.seo_metadata',
            ],
        },
    }]
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.http import HttpRequest

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Hub Configuration Registry
# ---------------------------------------------------------------------------
# Maps APP_NAME (settings.HUB_NAME) to display metadata.
# Extend this dict as new hubs are added.
# In production this could also be loaded from a DB model.

HUB_REGISTRY: dict[str, dict[str, str]] = {
    "bieterpilot": {
        "display_name": "bieterpilot",
        "description": "KI-gestützte Ausschreibungsverwaltung für den deutschen B2B-Markt.",
        "schema_org_type": "SoftwareApplication",
        "og_image": "og-bieterpilot.png",
    },
    "risk-hub": {
        "display_name": "risk-hub",
        "description": "Risikobewertung und -steuerung für professionelle Entscheidungsträger.",
        "schema_org_type": "SoftwareApplication",
        "og_image": "og-risk-hub.png",
    },
    "travel-beat": {
        "display_name": "DriftTales",
        "description": "Redaktionelle Reiseplattform für authentische Entdeckungen.",
        "schema_org_type": "WebApplication",
        "og_image": "og-travel-beat.png",
    },
    "weltenhub": {
        "display_name": "WeltenHub",
        "description": "Plattform für weltumspannendes strategisches Denken und Planung.",
        "schema_org_type": "WebApplication",
        "og_image": "og-weltenhub.png",
    },
    "pptx-hub": {
        "display_name": "Prezimo",
        "description": "KI-gestützte Präsentationserstellung — professionell, schnell, wirkungsvoll.",
        "schema_org_type": "SoftwareApplication",
        "og_image": "og-pptx-hub.png",
    },
    "coach-hub": {
        "display_name": "coach-hub",
        "description": "Coaching-Plattform für nachhaltiges persönliches und berufliches Wachstum.",
        "schema_org_type": "WebApplication",
        "og_image": "og-coach-hub.png",
    },
    "billing-hub": {
        "display_name": "billing-hub",
        "description": "Transparente Abrechnung und Rechnungsmanagement für B2B-Unternehmen.",
        "schema_org_type": "SoftwareApplication",
        "og_image": "og-billing-hub.png",
    },
    "trading-hub": {
        "display_name": "trading-hub",
        "description": "Echtzeit-Trading-Intelligence für professionelle Handelsentscheidungen.",
        "schema_org_type": "FinancialProduct",
        "og_image": "og-trading-hub.png",
    },
    "cad-hub": {
        "display_name": "cad-hub",
        "description": "Technische Dokumentation und CAD-Workflow-Management.",
        "schema_org_type": "SoftwareApplication",
        "og_image": "og-cad-hub.png",
    },
    "research-hub": {
        "display_name": "research-hub",
        "description": "Wissenschaftliche Recherche und Wissensmanagement-Plattform.",
        "schema_org_type": "WebApplication",
        "og_image": "og-research-hub.png",
    },
    "mcp-hub": {
        "display_name": "mcp-hub",
        "description": "MCP-Server-Ökosystem und AI-Agenten-Orchestrierung.",
        "schema_org_type": "SoftwareApplication",
        "og_image": "og-mcp-hub.png",
    },
    "doc-hub": {
        "display_name": "doc-hub",
        "description": "Dokumentenarchivierung und -verwaltung — paperless, strukturiert, auffindbar.",
        "schema_org_type": "SoftwareApplication",
        "og_image": "og-doc-hub.png",
    },
    "bfagent": {
        "display_name": "bfagent",
        "description": "KI-Agenten-Framework mit intelligentem LLM-Routing.",
        "schema_org_type": "SoftwareApplication",
        "og_image": "og-bfagent.png",
    },
    "dev-hub": {
        "display_name": "dev-hub",
        "description": "Developer Portal — Plattform-Transparenz und Engineering-Intelligence.",
        "schema_org_type": "WebApplication",
        "og_image": "og-dev-hub.png",
    },
}

# Fallback for unknown hubs
_DEFAULT_HUB = {
    "display_name": "iil-Platform",
    "description": "IIL GmbH — Privates Institut für Informationslogistik.",
    "schema_org_type": "WebApplication",
    "og_image": "og-default.png",
}


@lru_cache(maxsize=None)
def _get_hub_config(app_name: str) -> dict[str, str]:
    return HUB_REGISTRY.get(app_name, _DEFAULT_HUB)


# ---------------------------------------------------------------------------
# Context Processors
# ---------------------------------------------------------------------------

def hub_identity(request: HttpRequest) -> dict[str, Any]:
    """
    Injects hub identity context into every template.

    Makes available:
        {{ APP_NAME }}           — e.g. "bieterpilot"
        {{ HUB_DISPLAY_NAME }}   — e.g. "bieterpilot" / "DriftTales"
        {{ HUB_DESCRIPTION }}    — Hub tagline (used in meta tags)
        {{ SCHEMA_ORG_TYPE }}    — e.g. "SoftwareApplication"
        {{ user_theme }}         — "light" | "dark" (from session/cookie)
        {{ LANGUAGE_CODE }}      — Django LANGUAGE_CODE
        {{ debug }}              — settings.DEBUG
    """
    app_name: str = getattr(settings, "HUB_NAME", "iil-platform")
    hub = _get_hub_config(app_name)

    # User theme preference (stored in session, falls back to light)
    user_theme = request.session.get("pui_theme", "light")

    return {
        "APP_NAME": app_name,
        "HUB_DISPLAY_NAME": hub["display_name"],
        "HUB_DESCRIPTION": hub["description"],
        "SCHEMA_ORG_TYPE": hub["schema_org_type"],
        "user_theme": user_theme,
        "LANGUAGE_CODE": settings.LANGUAGE_CODE,
        "debug": settings.DEBUG,
    }


def seo_metadata(request: HttpRequest) -> dict[str, Any]:
    """
    Provides per-request SEO metadata.

    Views can override these via context:
        return render(request, template, {
            "page_schema": {
                "@context": "https://schema.org",
                "@type": "Article",
                ...
            }
        })
    """
    app_name: str = getattr(settings, "HUB_NAME", "iil-platform")
    hub = _get_hub_config(app_name)

    # Base Schema.org — overrideable per view
    base_schema: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": hub["schema_org_type"],
        "name": hub["display_name"],
        "description": hub["description"],
        "url": f"{request.scheme}://{request.get_host()}",
        "inLanguage": "de",
        "provider": {
            "@type": "Organization",
            "name": "IIL GmbH",
            "url": "https://iil.pet",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Neu-Ulm",
                "addressCountry": "DE",
            },
        },
    }

    return {
        "BASE_SCHEMA_ORG": base_schema,
    }
