"""
MCP Orchestration Service for n8n Integration
==============================================

Provides REST API endpoints for n8n to discover and execute MCP tools
across all registered MCP servers.

Architecture:
- Discovery: List all available MCP servers and their tools
- Execution: Call any MCP tool from any server
- Context: Manage workflow context between tool calls
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


# =============================================================================
# MCP SERVER REGISTRY
# =============================================================================

MCP_SERVERS = {
    "bfagent-mcp": {
        "name": "BF Agent MCP",
        "description": "Core platform functionality - domain management, handler generation, refactoring, DevOps",
        "location": "packages/bfagent_mcp/",
        "tools_count": 21,
        "categories": ["domain_management", "handler_generation", "refactoring", "devops"],
        "status": "production",
    },
    "book-writing-mcp": {
        "name": "Book Writing MCP",
        "description": "Complete book writing workflow - project management, outline, characters, world building, AI generation",
        "location": "mcp-hub/book_writing_mcp/",
        "tools_count": 37,
        "categories": [
            "project_management",
            "outline",
            "characters",
            "world_building",
            "ai_generation",
            "analysis",
        ],
        "status": "production",
    },
    "cad-mcp": {
        "name": "CAD MCP",
        "description": "BIM/CAD processing - DWG/DXF parser, IFC parser, DIN277 calculator, GAEB generator",
        "location": "mcp-hub/cad_mcp/",
        "tools_count": 10,
        "categories": ["input", "processing", "output", "integration", "transform"],
        "status": "production",
    },
    "analytics-mcp": {
        "name": "Analytics MCP",
        "description": "Data analytics and visualization tools",
        "location": "mcp-hub/analytics_mcp/",
        "status": "development",
    },
    "research-mcp": {
        "name": "Research MCP",
        "description": "Research and knowledge management tools",
        "location": "mcp-hub/research_mcp/",
        "status": "development",
    },
}


# =============================================================================
# TOOL DEFINITIONS (Detailed registry)
# =============================================================================

MCP_TOOLS = {
    "bfagent-mcp": [
        {
            "name": "bfagent_list_domains",
            "description": "List all BF Agent domains with status, handlers, and phases",
            "category": "domain_management",
            "input_schema": {
                "status_filter": {"type": "string", "optional": True},
                "include_handler_count": {"type": "boolean", "default": True},
                "include_phases": {"type": "boolean", "default": True},
            },
        },
        {
            "name": "bfagent_get_domain",
            "description": "Get detailed domain information including handlers and phases",
            "category": "domain_management",
            "input_schema": {
                "domain_id": {"type": "string", "required": True},
                "include_handlers": {"type": "boolean", "default": True},
            },
        },
        {
            "name": "bfagent_search_handlers",
            "description": "Search handlers by functionality across all domains",
            "category": "domain_management",
            "input_schema": {
                "query": {"type": "string", "required": True},
                "domain_filter": {"type": "string", "optional": True},
            },
        },
        {
            "name": "bfagent_generate_handler",
            "description": "Generate production-ready handler code with tests",
            "category": "handler_generation",
            "input_schema": {
                "domain": {"type": "string", "required": True},
                "handler_name": {"type": "string", "required": True},
                "handler_type": {"type": "string", "default": "rule_based"},
            },
        },
    ],
    "book-writing-mcp": [
        # Project Management
        {
            "name": "book_create_project",
            "description": "Create a new book project with title, genre, and optional premise",
            "category": "project_management",
            "input_schema": {
                "title": {"type": "string", "required": True},
                "genre": {"type": "string", "required": True},
                "book_type": {"type": "string", "default": "novel"},
                "description": {"type": "string", "optional": True},
            },
        },
        {
            "name": "book_get_project",
            "description": "Get project details including characters, chapters, and world",
            "category": "project_management",
            "input_schema": {
                "project_id": {"type": "integer", "required": True},
            },
        },
        {
            "name": "book_list_projects",
            "description": "List all book projects with optional filters",
            "category": "project_management",
            "input_schema": {
                "genre": {"type": "string", "optional": True},
                "status": {"type": "string", "optional": True},
                "limit": {"type": "integer", "default": 20},
            },
        },
        # Planning Phase
        {
            "name": "book_generate_premise",
            "description": "Generate story premise using AI from project context",
            "category": "planning",
            "input_schema": {
                "project_id": {"type": "integer", "required": True},
                "inspiration": {"type": "string", "optional": True},
            },
        },
        {
            "name": "book_identify_themes",
            "description": "Identify story themes from premise",
            "category": "planning",
            "input_schema": {
                "project_id": {"type": "integer", "required": True},
            },
        },
        {
            "name": "book_generate_logline",
            "description": "Generate one-sentence logline for the story",
            "category": "planning",
            "input_schema": {
                "project_id": {"type": "integer", "required": True},
                "style": {"type": "string", "default": "concise"},
            },
        },
        # Characters Phase
        {
            "name": "book_generate_characters",
            "description": "Generate character cast using AI based on project context",
            "category": "characters",
            "input_schema": {
                "project_id": {"type": "integer", "required": True},
                "character_count": {"type": "integer", "default": 5},
            },
        },
        {
            "name": "book_create_character",
            "description": "Create a specific character manually",
            "category": "characters",
            "input_schema": {
                "project_id": {"type": "integer", "required": True},
                "name": {"type": "string", "required": True},
                "role": {"type": "string", "required": True},
                "description": {"type": "string", "optional": True},
            },
        },
        {
            "name": "book_list_characters",
            "description": "List all characters in a project",
            "category": "characters",
            "input_schema": {
                "project_id": {"type": "integer", "required": True},
            },
        },
        # World Building Phase
        {
            "name": "book_generate_world",
            "description": "Generate world setting using AI",
            "category": "world_building",
            "input_schema": {
                "project_id": {"type": "integer", "required": True},
            },
        },
        {
            "name": "book_create_world",
            "description": "Create world setting manually",
            "category": "world_building",
            "input_schema": {
                "project_id": {"type": "integer", "required": True},
                "name": {"type": "string", "required": True},
                "world_type": {"type": "string", "default": "primary"},
                "geography": {"type": "string", "optional": True},
                "culture": {"type": "string", "optional": True},
            },
        },
        # Outline Phase
        {
            "name": "book_generate_outline",
            "description": "Generate story outline using selected framework",
            "category": "outline",
            "input_schema": {
                "project_id": {"type": "integer", "required": True},
                "framework": {"type": "string", "default": "save_the_cat"},
                "num_chapters": {"type": "integer", "default": 12},
            },
        },
        {
            "name": "book_get_outline",
            "description": "Get current outline for a project",
            "category": "outline",
            "input_schema": {
                "project_id": {"type": "integer", "required": True},
            },
        },
        # Chapter Writing Phase
        {
            "name": "book_write_chapter",
            "description": "Write a specific chapter using AI with full context",
            "category": "chapters",
            "input_schema": {
                "project_id": {"type": "integer", "required": True},
                "chapter_number": {"type": "integer", "required": True},
                "use_ai": {"type": "boolean", "default": True},
            },
        },
        {
            "name": "book_write_all_chapters",
            "description": "Write all chapters sequentially with context propagation",
            "category": "chapters",
            "input_schema": {
                "project_id": {"type": "integer", "required": True},
                "use_ai": {"type": "boolean", "default": True},
            },
        },
        {
            "name": "book_get_chapter",
            "description": "Get chapter content and metadata",
            "category": "chapters",
            "input_schema": {
                "project_id": {"type": "integer", "required": True},
                "chapter_number": {"type": "integer", "required": True},
            },
        },
        # Full Workflow
        {
            "name": "book_run_workflow",
            "description": "Run complete book writing workflow (planning → characters → world → outline → chapters)",
            "category": "workflow",
            "input_schema": {
                "project_id": {"type": "integer", "required": True},
                "use_ai": {"type": "boolean", "default": False},
                "skip_phases": {"type": "array", "optional": True},
            },
        },
        {
            "name": "book_run_phase",
            "description": "Run a specific workflow phase",
            "category": "workflow",
            "input_schema": {
                "project_id": {"type": "integer", "required": True},
                "phase": {"type": "string", "required": True},
                "use_ai": {"type": "boolean", "default": False},
            },
        },
        # Export
        {
            "name": "book_export_manuscript",
            "description": "Export book as formatted manuscript (Markdown, DOCX, PDF)",
            "category": "export",
            "input_schema": {
                "project_id": {"type": "integer", "required": True},
                "format": {"type": "string", "default": "markdown"},
            },
        },
    ],
    "cad-mcp": [
        {
            "name": "cad_parse_dwg",
            "description": "Parse DWG/DXF files and extract geometry, rooms, doors, windows",
            "category": "input",
            "input_schema": {
                "file_path": {"type": "string", "required": True},
                "format": {"type": "string", "default": "dxf"},
            },
        },
        {
            "name": "cad_calculate_din277",
            "description": "Calculate building areas according to DIN 277:2021 standard",
            "category": "processing",
            "input_schema": {
                "project_id": {"type": "string", "required": True},
                "include_nrf": {"type": "boolean", "default": True},
            },
        },
        {
            "name": "cad_generate_raumbuch",
            "description": "Generate Excel room schedule (Raumbuch) with areas and equipment",
            "category": "output",
            "input_schema": {
                "project_id": {"type": "string", "required": True},
                "output_path": {"type": "string", "required": True},
            },
        },
    ],
}


# =============================================================================
# API ENDPOINTS
# =============================================================================


@csrf_exempt
@require_http_methods(["GET"])
def list_mcp_servers(request):
    """
    List all available MCP servers

    GET /api/mcp/servers

    Response:
        {
            "servers": [
                {
                    "id": "bfagent-mcp",
                    "name": "BF Agent MCP",
                    "description": "...",
                    "tools_count": 21,
                    "status": "production"
                }
            ]
        }
    """
    try:
        servers = [
            {
                "id": server_id,
                "name": server_data["name"],
                "description": server_data["description"],
                "tools_count": server_data.get("tools_count", 0),
                "categories": server_data.get("categories", []),
                "status": server_data.get("status", "unknown"),
            }
            for server_id, server_data in MCP_SERVERS.items()
        ]

        return JsonResponse(
            {
                "success": True,
                "servers": servers,
                "total": len(servers),
            }
        )

    except Exception as e:
        logger.error(f"Error listing MCP servers: {e}")
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@csrf_exempt
@require_http_methods(["GET"])
def list_mcp_tools(request):
    """
    List all tools for a specific MCP server

    GET /api/mcp/tools?server=bfagent-mcp
    GET /api/mcp/tools (all servers)

    Response:
        {
            "tools": [
                {
                    "name": "bfagent_list_domains",
                    "server": "bfagent-mcp",
                    "description": "...",
                    "category": "domain_management"
                }
            ]
        }
    """
    try:
        server_id = request.GET.get("server")

        if server_id:
            # Tools for specific server
            if server_id not in MCP_TOOLS:
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"Server '{server_id}' not found",
                    },
                    status=404,
                )

            tools = [{**tool, "server": server_id} for tool in MCP_TOOLS[server_id]]
        else:
            # All tools from all servers
            tools = []
            for server_id, server_tools in MCP_TOOLS.items():
                tools.extend([{**tool, "server": server_id} for tool in server_tools])

        return JsonResponse(
            {
                "success": True,
                "tools": tools,
                "total": len(tools),
            }
        )

    except Exception as e:
        logger.error(f"Error listing MCP tools: {e}")
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@csrf_exempt
@require_http_methods(["POST"])
def execute_mcp_tool(request):
    """
    Execute a tool from any MCP server

    POST /api/mcp/execute
    Body:
        {
            "server": "book-writing-mcp",
            "tool": "book_create_project",
            "params": {
                "title": "My Fantasy Novel",
                "genre": "Fantasy"
            },
            "context_id": "workflow_123"  # optional
        }

    Response:
        {
            "success": true,
            "result": { ... },
            "execution_time_ms": 150
        }
    """
    try:
        import time

        # Parse request body
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid JSON in request body",
                },
                status=400,
            )

        server = body.get("server")
        tool = body.get("tool")
        params = body.get("params", {})
        context_id = body.get("context_id")

        # Validate inputs
        if not server or not tool:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Missing required fields: 'server' and 'tool'",
                },
                status=400,
            )

        # Verify server exists
        if server not in MCP_SERVERS:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Server '{server}' not found",
                },
                status=404,
            )

        # Verify tool exists
        server_tools = MCP_TOOLS.get(server, [])
        tool_def = next((t for t in server_tools if t["name"] == tool), None)

        if not tool_def:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Tool '{tool}' not found in server '{server}'",
                },
                status=404,
            )

        # Execute tool
        start_time = time.time()

        # Route to actual tool implementation
        if server == "book-writing-mcp":
            from .mcp_book_tools import execute_book_tool
            result = execute_book_tool(tool, params)
        else:
            # Fallback to mock for other servers
            result = {
                "message": f"Tool '{tool}' executed successfully (mock)",
                "server": server,
                "tool": tool,
                "params": params,
                "context_id": context_id,
            }

        execution_time = (time.time() - start_time) * 1000  # ms

        # Store context if provided
        if context_id:
            _store_workflow_context(
                context_id,
                {
                    "last_tool": tool,
                    "last_result": result,
                },
            )

        return JsonResponse(
            {
                "success": True,
                "result": result,
                "execution_time_ms": round(execution_time, 2),
            }
        )

    except Exception as e:
        logger.error(f"Error executing MCP tool: {e}")
        import traceback

        traceback.print_exc()

        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@csrf_exempt
@require_http_methods(["GET"])
def get_tool_info(request, server: str, tool: str):
    """
    Get detailed information about a specific tool

    GET /api/mcp/tool/<server>/<tool>

    Response:
        {
            "name": "book_create_project",
            "server": "book-writing-mcp",
            "description": "...",
            "input_schema": { ... },
            "examples": [ ... ]
        }
    """
    try:
        # Verify server exists
        if server not in MCP_TOOLS:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Server '{server}' not found",
                },
                status=404,
            )

        # Find tool
        server_tools = MCP_TOOLS[server]
        tool_def = next((t for t in server_tools if t["name"] == tool), None)

        if not tool_def:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Tool '{tool}' not found in server '{server}'",
                },
                status=404,
            )

        return JsonResponse(
            {
                "success": True,
                "tool": {**tool_def, "server": server},
            }
        )

    except Exception as e:
        logger.error(f"Error getting tool info: {e}")
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


# =============================================================================
# WORKFLOW CONTEXT MANAGEMENT
# =============================================================================

# In-memory context storage (TODO: move to database)
_WORKFLOW_CONTEXTS: Dict[str, Dict[str, Any]] = {}


def _store_workflow_context(context_id: str, data: Dict[str, Any]):
    """Store workflow context data"""
    if context_id not in _WORKFLOW_CONTEXTS:
        _WORKFLOW_CONTEXTS[context_id] = {}

    _WORKFLOW_CONTEXTS[context_id].update(data)


@csrf_exempt
@require_http_methods(["GET"])
def get_workflow_context(request, context_id: str):
    """
    Get workflow context

    GET /api/mcp/context/<context_id>
    """
    try:
        context = _WORKFLOW_CONTEXTS.get(context_id)

        if not context:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Context '{context_id}' not found",
                },
                status=404,
            )

        return JsonResponse(
            {
                "success": True,
                "context": context,
            }
        )

    except Exception as e:
        logger.error(f"Error getting workflow context: {e}")
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@csrf_exempt
@require_http_methods(["POST"])
def create_workflow_context(request):
    """
    Create a new workflow context

    POST /api/mcp/context
    Body:
        {
            "context_id": "workflow_123",
            "initial_data": { ... }
        }
    """
    try:
        body = json.loads(request.body)
        context_id = body.get("context_id")
        initial_data = body.get("initial_data", {})

        if not context_id:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Missing required field: 'context_id'",
                },
                status=400,
            )

        _WORKFLOW_CONTEXTS[context_id] = initial_data

        return JsonResponse(
            {
                "success": True,
                "context_id": context_id,
                "message": "Context created successfully",
            }
        )

    except Exception as e:
        logger.error(f"Error creating workflow context: {e}")
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_workflow_context(request, context_id: str):
    """
    Delete workflow context

    DELETE /api/mcp/context/<context_id>
    """
    try:
        if context_id in _WORKFLOW_CONTEXTS:
            del _WORKFLOW_CONTEXTS[context_id]
            return JsonResponse(
                {
                    "success": True,
                    "message": f"Context '{context_id}' deleted successfully",
                }
            )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Context '{context_id}' not found",
                },
                status=404,
            )

    except Exception as e:
        logger.error(f"Error deleting workflow context: {e}")
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )
