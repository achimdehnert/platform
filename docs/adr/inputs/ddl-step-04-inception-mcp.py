# ============================================================================
# DOMAIN DEVELOPMENT LIFECYCLE - INCEPTION MCP SERVER
# Step 4: MCP Server for AI-assisted Business Case Creation
# ============================================================================
#
# Part of: Domain Development Lifecycle System
# Compatible with: ADR-015 Platform Governance System
# Location: mcp-hub/inception_mcp/server.py
#
# Usage:
#   In Windsurf/Claude Desktop:
#   - start_business_case("Ich brauche eine Reisekostenabrechnung...")
#   - answer_question(session_id, "Die Zielgruppe sind Außendienstmitarbeiter")
#   - finalize_business_case(session_id)
#
# ============================================================================

"""
Inception MCP Server - AI-gestützte Business Case Erstellung.

Dieser MCP Server ermöglicht die iterative Erstellung von Business Cases
durch einen Dialog zwischen dem Benutzer und dem Inception Agent.

Flow:
1. start_business_case() - Initialisiert Session mit Freitext
2. answer_question() - Beantwortet iterativ Rückfragen
3. finalize_business_case() - Schließt ab und leitet Use Cases ab
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Optional

# Django Setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'platform.settings')

import django
django.setup()

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Services importieren
from governance.services import (
    InceptionService,
    BusinessCaseService,
    UseCaseService,
    LookupService,
)


# ============================================================================
# SERVER SETUP
# ============================================================================

app = Server("inception-mcp")


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Listet alle verfügbaren Tools."""
    return [
        Tool(
            name="start_business_case",
            description="""
Startet einen neuen Business Case Dialog.

Analysiert die initiale Beschreibung und beginnt den iterativen
Frageprozess zur Vervollständigung des Business Cases.

Args:
    initial_description: Freitext-Beschreibung des Business Cases
    category: Optional - Kategorie vorab (neue_domain, integration, optimierung, erweiterung, produktion)

Returns:
    Session-Info mit:
    - session_id: ID für weitere Aufrufe
    - business_case_code: Code des erstellten BC-Drafts
    - understood: Was wurde bereits extrahiert
    - question: Erste Rückfrage
    - questions_remaining: Anzahl offener Fragen

Example:
    >>> start_business_case(
    ...     "Ich brauche eine Reisekostenabrechnung mit Beleg-Upload und OCR",
    ...     category="neue_domain"
    ... )
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "initial_description": {
                        "type": "string",
                        "description": "Freitext-Beschreibung des Business Cases",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["neue_domain", "integration", "optimierung", "erweiterung", "produktion", "bugfix"],
                        "description": "Optional: Kategorie des Business Cases",
                    },
                },
                "required": ["initial_description"],
            },
        ),
        Tool(
            name="answer_question",
            description="""
Beantwortet die aktuelle Frage des Inception Agents.

Verarbeitet die Antwort, extrahiert relevante Informationen und
gibt die nächste Frage zurück (oder Zusammenfassung wenn fertig).

Args:
    session_id: Session ID vom start_business_case
    answer: Antwort auf die aktuelle Frage

Returns:
    - Bei weiteren Fragen: question + questions_remaining
    - Wenn fertig: status="ready_for_finalization" + summary

Example:
    >>> answer_question(
    ...     session_id="abc-123",
    ...     answer="Die Zielgruppe sind Außendienstmitarbeiter"
    ... )
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID vom start_business_case",
                    },
                    "answer": {
                        "type": "string",
                        "description": "Antwort auf die aktuelle Frage",
                    },
                },
                "required": ["session_id", "answer"],
            },
        ),
        Tool(
            name="finalize_business_case",
            description="""
Finalisiert den Business Case und leitet Use Cases ab.

Schließt den Inception-Prozess ab, markiert den Business Case
als vollständig und generiert automatisch Use Case Entwürfe.

Args:
    session_id: Session ID
    adjustments: Optional - Manuelle Anpassungen vor Finalisierung
    derive_use_cases: Optional - Use Cases automatisch ableiten (default: true)

Returns:
    - business_case: Finalisierter BC mit Code und Status
    - derived_use_cases: Liste der abgeleiteten Use Cases
    - next_steps: Empfohlene nächste Schritte

Example:
    >>> finalize_business_case(
    ...     session_id="abc-123",
    ...     adjustments={"title": "Korrigierter Titel"}
    ... )
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID",
                    },
                    "adjustments": {
                        "type": "object",
                        "description": "Optional: Manuelle Anpassungen",
                    },
                    "derive_use_cases": {
                        "type": "boolean",
                        "description": "Use Cases automatisch ableiten (default: true)",
                        "default": True,
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="get_session_status",
            description="""
Holt den aktuellen Status einer Inception-Session.

Nützlich wenn die Session unterbrochen wurde und fortgesetzt werden soll.

Args:
    session_id: Session ID

Returns:
    - status: in_progress / ready_for_finalization / not_found
    - business_case_code: Code des zugehörigen BC
    - current_question: Aktuelle offene Frage (wenn vorhanden)
    - answered_count: Anzahl beantworteter Fragen
    - questions_remaining: Anzahl offener Fragen
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID",
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="list_business_cases",
            description="""
Listet Business Cases mit optionalen Filtern.

Args:
    status: Optional - Filter nach Status (draft, submitted, approved, ...)
    category: Optional - Filter nach Kategorie
    search: Optional - Volltextsuche
    limit: Optional - Max. Ergebnisse (default: 20)

Returns:
    Liste von Business Cases mit Code, Titel, Status, Kategorie
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter nach Status",
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter nach Kategorie",
                    },
                    "search": {
                        "type": "string",
                        "description": "Volltextsuche",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max. Ergebnisse",
                        "default": 20,
                    },
                },
            },
        ),
        Tool(
            name="get_business_case",
            description="""
Holt Details eines Business Cases.

Args:
    code: Business Case Code (z.B. "BC-001")

Returns:
    Vollständiger Business Case mit Use Cases und ADRs
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Business Case Code (z.B. BC-001)",
                    },
                },
                "required": ["code"],
            },
        ),
        Tool(
            name="get_categories",
            description="""
Listet alle verfügbaren Business Case Kategorien.

Returns:
    Liste der Kategorien mit Code, Name, Beschreibung und Metadaten
""",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="submit_for_review",
            description="""
Reicht einen Business Case zur Prüfung ein.

Ändert den Status von 'draft' zu 'submitted'.

Args:
    code: Business Case Code

Returns:
    Aktualisierter Business Case
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Business Case Code",
                    },
                },
                "required": ["code"],
            },
        ),
        Tool(
            name="detail_use_case",
            description="""
Detailliert einen Use Case mit Flows und Regeln.

Args:
    code: Use Case Code (z.B. "UC-001")
    main_flow: Hauptablauf als Liste von Schritten
    alternative_flows: Optional - Alternative Abläufe
    preconditions: Optional - Vorbedingungen
    postconditions: Optional - Nachbedingungen
    business_rules: Optional - Geschäftsregeln

Returns:
    Aktualisierter Use Case
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Use Case Code",
                    },
                    "main_flow": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "step": {"type": "integer"},
                                "type": {"type": "string"},
                                "description": {"type": "string"},
                            },
                        },
                        "description": "Hauptablauf",
                    },
                    "alternative_flows": {
                        "type": "array",
                        "description": "Alternative Abläufe",
                    },
                    "preconditions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Vorbedingungen",
                    },
                    "postconditions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Nachbedingungen",
                    },
                    "business_rules": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Geschäftsregeln",
                    },
                },
                "required": ["code", "main_flow"],
            },
        ),
    ]


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Führt ein Tool aus."""
    
    try:
        if name == "start_business_case":
            result = await _start_business_case(
                initial_description=arguments["initial_description"],
                category=arguments.get("category"),
            )
        
        elif name == "answer_question":
            result = await _answer_question(
                session_id=arguments["session_id"],
                answer=arguments["answer"],
            )
        
        elif name == "finalize_business_case":
            result = await _finalize_business_case(
                session_id=arguments["session_id"],
                adjustments=arguments.get("adjustments"),
                derive_use_cases=arguments.get("derive_use_cases", True),
            )
        
        elif name == "get_session_status":
            result = await _get_session_status(
                session_id=arguments["session_id"],
            )
        
        elif name == "list_business_cases":
            result = await _list_business_cases(
                status=arguments.get("status"),
                category=arguments.get("category"),
                search=arguments.get("search"),
                limit=arguments.get("limit", 20),
            )
        
        elif name == "get_business_case":
            result = await _get_business_case(
                code=arguments["code"],
            )
        
        elif name == "get_categories":
            result = await _get_categories()
        
        elif name == "submit_for_review":
            result = await _submit_for_review(
                code=arguments["code"],
            )
        
        elif name == "detail_use_case":
            result = await _detail_use_case(
                code=arguments["code"],
                main_flow=arguments["main_flow"],
                alternative_flows=arguments.get("alternative_flows"),
                preconditions=arguments.get("preconditions"),
                postconditions=arguments.get("postconditions"),
                business_rules=arguments.get("business_rules"),
            )
        
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2, ensure_ascii=False, default=str),
        )]
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": str(e),
                "tool": name,
                "arguments": arguments,
            }, indent=2),
        )]


# ============================================================================
# TOOL IMPLEMENTATIONS - INCEPTION
# ============================================================================

async def _start_business_case(
    initial_description: str,
    category: Optional[str] = None,
) -> dict:
    """Startet einen neuen Business Case Dialog."""
    result = InceptionService.start_session(
        initial_input=initial_description,
        category_code=category,
    )
    return result


async def _answer_question(
    session_id: str,
    answer: str,
) -> dict:
    """Beantwortet die aktuelle Frage."""
    result = InceptionService.answer_question(
        session_id=session_id,
        answer=answer,
    )
    return result


async def _finalize_business_case(
    session_id: str,
    adjustments: Optional[dict] = None,
    derive_use_cases: bool = True,
) -> dict:
    """Finalisiert den Business Case."""
    result = InceptionService.finalize(
        session_id=session_id,
        adjustments=adjustments,
        derive_use_cases=derive_use_cases,
    )
    return result


async def _get_session_status(session_id: str) -> dict:
    """Holt den Session-Status."""
    session = InceptionService.get_session(session_id)
    
    if not session:
        return {
            "status": "not_found",
            "session_id": session_id,
        }
    
    from governance.models import BusinessCase
    bc = BusinessCase.all_objects.filter(id=session.business_case_id).first()
    
    return {
        "status": session.status,
        "session_id": session_id,
        "business_case_id": session.business_case_id,
        "business_case_code": bc.code if bc else None,
        "turn": session.turn,
        "answered_count": len(session.answered_questions),
        "questions_remaining": len(session.pending_questions),
        "current_question": session.pending_questions[0] if session.pending_questions else None,
        "extracted_data": session.extracted_data,
    }


# ============================================================================
# TOOL IMPLEMENTATIONS - BUSINESS CASE
# ============================================================================

async def _list_business_cases(
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """Listet Business Cases."""
    from governance.models import BusinessCase
    
    qs = BusinessCase.objects.all()
    
    if status:
        qs = qs.filter(status__code=status)
    
    if category:
        qs = qs.filter(category__code=category)
    
    if search:
        from django.contrib.postgres.search import SearchQuery
        search_query = SearchQuery(search, config='german')
        qs = qs.filter(search_vector=search_query)
    
    qs = qs.select_related('status', 'category')[:limit]
    
    return {
        "business_cases": [
            {
                "code": bc.code,
                "title": bc.title,
                "status": bc.status.code,
                "status_name": bc.status.name,
                "category": bc.category.code,
                "category_name": bc.category.name,
                "use_case_count": bc.use_case_count,
                "created_at": bc.created_at.isoformat(),
            }
            for bc in qs
        ],
        "count": len(qs),
    }


async def _get_business_case(code: str) -> dict:
    """Holt Details eines Business Cases."""
    from governance.models import BusinessCase
    
    bc = BusinessCase.objects.filter(code=code).select_related(
        'status', 'category', 'owner'
    ).first()
    
    if not bc:
        return {"error": f"Business Case {code} nicht gefunden"}
    
    use_cases = list(bc.use_cases.select_related('status', 'priority').values(
        'code', 'title', 'status__code', 'status__name',
        'priority__code', 'actor', 'sort_order',
    ))
    
    adrs = list(bc.adrs.select_related('status').values(
        'code', 'title', 'status__code', 'status__name',
    ))
    
    return {
        "code": bc.code,
        "title": bc.title,
        "status": bc.status.code,
        "status_name": bc.status.name,
        "category": bc.category.code,
        "category_name": bc.category.name,
        "problem_statement": bc.problem_statement,
        "target_audience": bc.target_audience,
        "expected_benefits": bc.expected_benefits,
        "scope": bc.scope,
        "out_of_scope": bc.out_of_scope,
        "success_criteria": bc.success_criteria,
        "assumptions": bc.assumptions,
        "constraints": bc.constraints,
        "risks": bc.risks,
        "architecture_basis": bc.architecture_basis,
        "owner": bc.owner.username if bc.owner else None,
        "created_at": bc.created_at.isoformat(),
        "updated_at": bc.updated_at.isoformat(),
        "use_cases": use_cases,
        "adrs": adrs,
        "is_editable": bc.is_editable,
        "allowed_transitions": bc.allowed_transitions,
    }


async def _get_categories() -> dict:
    """Listet alle Kategorien."""
    categories = LookupService.get_choices('bc_category')
    return {
        "categories": categories,
    }


async def _submit_for_review(code: str) -> dict:
    """Reicht BC zur Prüfung ein."""
    bc = BusinessCaseService.get_by_code(code)
    
    if not bc:
        return {"error": f"Business Case {code} nicht gefunden"}
    
    try:
        bc = BusinessCaseService.submit_for_review(bc)
        return {
            "status": "submitted",
            "business_case": {
                "code": bc.code,
                "title": bc.title,
                "status": bc.status.code,
            },
        }
    except ValueError as e:
        return {"error": str(e)}


# ============================================================================
# TOOL IMPLEMENTATIONS - USE CASE
# ============================================================================

async def _detail_use_case(
    code: str,
    main_flow: list[dict],
    alternative_flows: Optional[list[dict]] = None,
    preconditions: Optional[list[str]] = None,
    postconditions: Optional[list[str]] = None,
    business_rules: Optional[list[str]] = None,
) -> dict:
    """Detailliert einen Use Case."""
    from governance.models import UseCase
    
    uc = UseCase.objects.filter(code=code).first()
    
    if not uc:
        return {"error": f"Use Case {code} nicht gefunden"}
    
    # Update
    uc.main_flow = main_flow
    
    if alternative_flows is not None:
        uc.alternative_flows = alternative_flows
    
    if preconditions is not None:
        uc.preconditions = preconditions
    
    if postconditions is not None:
        uc.postconditions = postconditions
    
    if business_rules is not None:
        uc.business_rules = business_rules
    
    uc.save()
    
    # Status auf 'detailed' wenn noch draft
    if uc.status.code == 'draft':
        uc.status = LookupService.get_choice('uc_status', 'detailed')
        uc.save()
    
    return {
        "status": "updated",
        "use_case": {
            "code": uc.code,
            "title": uc.title,
            "status": uc.status.code,
            "main_flow_steps": len(uc.main_flow),
        },
    }


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Startet den MCP Server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
