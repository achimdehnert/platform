"""
BF Agent MCP Server
===================

Model Context Protocol Server für BF Agent Integration.

Architecture:
- Clean Architecture: Controller → Service → Repository
- Dependency Injection: Services werden injiziert
- Single Responsibility: Server = Protocol Handling only

Usage:
    python -m bfagent_mcp.server
    python -m bfagent_mcp.server --transport http --port 8765
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, ResourceTemplate, TextContent, Tool

from .config import get_server_settings, get_settings, setup_logging
from .core import (
    BFAgentMCPError,
    DomainNotFoundError,
    DomainStatus,
    HandlerNotFoundError,
    HandlerType,
    ResponseFormat,
)
from .generators import GeneratorFactory
from .repositories import RepositoryFactory
from .schemas import (
    GenerateHandlerInput,
    GetBestPracticesInput,
    GetDomainInput,
    ListDomainsInput,
    ScaffoldDomainInput,
    SearchHandlersInput,
    ValidateHandlerInput,
)
from .services import ServiceFactory

logger = logging.getLogger(__name__)

# MCP Server Instance
mcp_server = Server("bfagent_mcp")
mcp = mcp_server  # Alias for tools that import 'mcp'


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================


def get_tool_definitions() -> List[Tool]:
    """Define all MCP tools."""
    return [
        Tool(
            name="bfagent_list_domains",
            description="""List all BF Agent domains with status, handlers, and phases.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "status_filter": {
                        "type": "string",
                        "enum": ["production", "beta", "development", "planned", "deprecated"],
                    },
                    "include_handler_count": {"type": "boolean", "default": True},
                    "include_phases": {"type": "boolean", "default": True},
                    "response_format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
            },
        ),
        Tool(
            name="bfagent_get_domain",
            description="""Get detailed domain information including handlers and phases.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain_id": {
                        "type": "string",
                        "description": "Domain ID (e.g., 'books', 'cad')",
                    },
                    "include_handlers": {"type": "boolean", "default": True},
                    "include_phases": {"type": "boolean", "default": True},
                    "response_format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
                "required": ["domain_id"],
            },
        ),
        Tool(
            name="bfagent_search_handlers",
            description="""Search handlers by functionality across all domains.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'PDF parsing')",
                    },
                    "domain_filter": {"type": "string"},
                    "handler_type_filter": {
                        "type": "string",
                        "enum": ["ai_powered", "rule_based", "hybrid", "utility"],
                    },
                    "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                    "response_format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="bfagent_generate_handler",
            description="""Generate production-ready handler code with tests.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "handler_name": {"type": "string"},
                    "domain": {"type": "string"},
                    "handler_type": {
                        "type": "string",
                        "enum": ["ai_powered", "rule_based", "hybrid", "utility"],
                        "default": "rule_based",
                    },
                    "description": {"type": "string"},
                    "input_fields": {"type": "array", "items": {"type": "string"}},
                    "output_fields": {"type": "array", "items": {"type": "string"}},
                    "ai_provider": {
                        "type": "string",
                        "enum": ["openai", "anthropic", "ollama", "none"],
                    },
                    "include_tests": {"type": "boolean", "default": True},
                    "use_ai_enhancement": {"type": "boolean", "default": True},
                },
                "required": ["handler_name", "domain", "description"],
            },
        ),
        Tool(
            name="bfagent_scaffold_domain",
            description="""Create complete domain structure with models, admin, and handlers.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain_id": {"type": "string"},
                    "display_name": {"type": "string"},
                    "description": {"type": "string"},
                    "phases": {"type": "array", "items": {"type": "string"}},
                    "initial_handlers": {"type": "array", "items": {"type": "string"}},
                    "include_admin": {"type": "boolean", "default": True},
                    "include_tests": {"type": "boolean", "default": True},
                },
                "required": ["domain_id", "display_name", "description", "phases"],
            },
        ),
        Tool(
            name="bfagent_validate_handler",
            description="""Validate handler code against BF Agent standards. Returns score 0-100.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "strict_mode": {"type": "boolean", "default": False},
                },
                "required": ["code"],
            },
        ),
        Tool(
            name="bfagent_get_best_practices",
            description="""Get best practices for: handlers, pydantic, ai_integration, testing, error_handling, performance.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "include_examples": {"type": "boolean", "default": True},
                    "response_format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
                "required": ["topic"],
            },
        ),
        # =====================================================================
        # REFACTORING TOOLS (NEW!)
        # =====================================================================
        Tool(
            name="bfagent_get_refactor_options",
            description="""Get refactoring options for a domain. Shows available components, risk level,
            dependencies, and protected paths. Use this BEFORE refactoring any domain code.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain_id": {
                        "type": "string",
                        "description": "Domain ID (e.g., 'books', 'core', 'exschutz')",
                    },
                    "response_format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
                "required": ["domain_id"],
            },
        ),
        Tool(
            name="bfagent_check_path_protection",
            description="""Check if a file path is protected before modifying.
            Returns protection status, level, and reason. ALWAYS use this before editing files!""",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "File path to check (e.g., 'apps/books/handlers/chapter_handler.py')",
                    },
                    "response_format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="bfagent_get_naming_convention",
            description="""Get naming conventions for a domain/app. Shows table prefixes,
            class prefixes, and patterns to follow.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_label": {
                        "type": "string",
                        "description": "App label (e.g., 'books', 'bfagent_mcp', 'core')",
                    },
                    "response_format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
                "required": ["app_label"],
            },
        ),
        Tool(
            name="bfagent_list_naming_conventions",
            description="""List all naming conventions for all apps/domains.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "response_format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    }
                },
            },
        ),
        Tool(
            name="bfagent_list_component_types",
            description="""List all component types (handler, service, model, etc.) with their path patterns.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "response_format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    }
                },
            },
        ),
        Tool(
            name="bfagent_start_refactor_session",
            description="""Start a refactoring session for tracking. Call this BEFORE making changes.
            Returns a session ID to use when ending the session.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain_id": {"type": "string", "description": "Domain to refactor"},
                    "components": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Components to refactor: ['handler', 'service', 'model']",
                    },
                },
                "required": ["domain_id", "components"],
            },
        ),
        Tool(
            name="bfagent_end_refactor_session",
            description="""End a refactoring session. Call this AFTER making all changes.
            Records statistics and updates domain tracking.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "integer",
                        "description": "Session ID from start_refactor_session",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["completed", "failed", "cancelled"],
                        "default": "completed",
                    },
                    "summary": {"type": "string", "description": "Summary of changes made"},
                    "files_changed": {"type": "integer", "default": 0},
                    "lines_added": {"type": "integer", "default": 0},
                    "lines_removed": {"type": "integer", "default": 0},
                },
                "required": ["session_id"],
            },
        ),
        # =====================================================================
        # DEVOPS AI STACK TOOLS (NEW!)
        # =====================================================================
        Tool(
            name="bfagent_sentry_capture_error",
            description="""Capture an error in Sentry with context for tracking and AI analysis.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "error_message": {"type": "string", "description": "Error message to capture"},
                    "context": {
                        "type": "object",
                        "description": "Additional context (user, tags, etc.)",
                    },
                },
                "required": ["error_message"],
            },
        ),
        Tool(
            name="bfagent_sentry_get_stats",
            description="""Get Sentry integration status and statistics.""",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="bfagent_grafana_create_dashboard",
            description="""Create a Grafana monitoring dashboard for bfagent.""",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="bfagent_grafana_get_alerts",
            description="""Get Grafana alert rules configuration.""",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="bfagent_chrome_test_page",
            description="""Test a page with Chrome DevTools - captures screenshot, console errors, network analysis.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to test (e.g., '/admin/writing_hub/scene/')",
                    }
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="bfagent_chrome_measure_performance",
            description="""Measure page performance metrics (LCP, FID, CLS).""",
            inputSchema={
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL to measure"}},
                "required": ["url"],
            },
        ),
        Tool(
            name="bfagent_admin_ultimate_check",
            description="""Run complete admin health check combining all DevOps AI tools.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_label": {
                        "type": "string",
                        "description": "App to check (e.g., 'writing_hub')",
                    }
                },
            },
        ),
        # =====================================================================
        # CODE DELEGATION TOOLS (Delegate simple Django tasks to Worker-LLMs)
        # =====================================================================
        Tool(
            name="bfagent_delegate_code",
            description="""Delegate simple Django code generation to Worker-LLMs (DeepSeek V3, GPT-4o mini).
            Supports: django_view, django_template, django_url, django_form, django_model, htmx_component.
            Uses pattern-based templates when possible, falls back to LLM for complex tasks.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "enum": ["django_view", "django_template", "django_url", "django_form", "django_model", "htmx_component", "sql_query"],
                        "description": "Type of code to generate. sql_query routes to existing DB tools.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Natural language description of what to generate",
                    },
                    "context": {
                        "type": "object",
                        "description": "Additional context (class_name, app_name, fields, etc.)",
                    },
                    "model": {
                        "type": "string",
                        "enum": ["auto", "deepseek-v3", "gpt4o-mini", "gemini-flash"],
                        "default": "auto",
                        "description": "LLM model to use (auto = best available)",
                    },
                },
                "required": ["task_type", "description"],
            },
        ),
        # =====================================================================
        # REQUIREMENT MANAGEMENT TOOLS (Cascade ↔ System Communication)
        # =====================================================================
        Tool(
            name="bfagent_update_requirement_status",
            description="""Update the status of a TestRequirement/Bug. Call this when you finish working on a task.
            Status options: draft, ready, in_progress, done, completed, blocked, obsolete, archived.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "requirement_id": {
                        "type": "string",
                        "description": "UUID of the TestRequirement",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["draft", "ready", "in_progress", "done", "completed", "blocked", "obsolete", "archived"],
                        "description": "New status to set",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes about the status change",
                    },
                },
                "required": ["requirement_id", "status"],
            },
        ),
        Tool(
            name="bfagent_record_task_result",
            description="""Record the result of working on a task/bug. Call this when finishing work to sync back to the system.
            Automatically adds feedback and updates status.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "requirement_id": {
                        "type": "string",
                        "description": "UUID of the TestRequirement",
                    },
                    "success": {
                        "type": "boolean",
                        "description": "Whether the task was completed successfully",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Summary of what was done",
                    },
                    "files_changed": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of files that were modified",
                    },
                    "next_steps": {
                        "type": "string",
                        "description": "Optional: What should be done next",
                    },
                },
                "required": ["requirement_id", "success", "summary"],
            },
        ),
        Tool(
            name="bfagent_add_feedback",
            description="""Add feedback/progress note to a requirement. Use for progress updates, blockers, questions, or solutions.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "requirement_id": {
                        "type": "string",
                        "description": "UUID of the TestRequirement",
                    },
                    "feedback_type": {
                        "type": "string",
                        "enum": ["comment", "progress", "blocker", "question", "solution"],
                        "default": "progress",
                    },
                    "content": {
                        "type": "string",
                        "description": "Feedback content/message",
                    },
                },
                "required": ["requirement_id", "content"],
            },
        ),
        Tool(
            name="bfagent_get_requirement",
            description="""Get details of a TestRequirement/Bug by ID. Use to check current status and history.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "requirement_id": {
                        "type": "string",
                        "description": "UUID of the TestRequirement",
                    },
                    "include_feedback": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include feedback history",
                    },
                },
                "required": ["requirement_id"],
            },
        ),
        Tool(
            name="bfagent_analyze_requirement",
            description="""Analyze a requirement and provide feedback on its quality, feasibility, and suggestions.
            Use this when asked to review a requirement before work starts.
            Returns structured analysis with recommendations.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "requirement_id": {
                        "type": "string",
                        "description": "UUID of the TestRequirement to analyze",
                    },
                    "analysis_depth": {
                        "type": "string",
                        "enum": ["quick", "detailed"],
                        "default": "quick",
                        "description": "How detailed the analysis should be",
                    },
                },
                "required": ["requirement_id"],
            },
        ),
        # =====================================================================
        # INITIATIVE TOOLS (Concept → Multiple Tasks)
        # =====================================================================
        Tool(
            name="bfagent_create_initiative",
            description="""Create an Initiative (Epic/Concept) that can spawn multiple requirements/tasks.
            Use this when analyzing a larger topic that will result in multiple features or tasks.
            Workflow: Analysis → Concept → Tasks.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the initiative/concept",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the initiative",
                    },
                    "analysis": {
                        "type": "string",
                        "description": "Analysis results and findings",
                    },
                    "concept": {
                        "type": "string",
                        "description": "Proposed solution/concept",
                    },
                    "domain": {
                        "type": "string",
                        "enum": ["writing_hub", "cad_hub", "mcp_hub", "medtrans", "control_center", "genagent", "core", "multi"],
                        "default": "core",
                        "description": "Primary domain for this initiative",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low"],
                        "default": "medium",
                    },
                    "tasks": {
                        "type": "array",
                        "description": "List of tasks to create from this initiative",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "category": {
                                    "type": "string",
                                    "enum": ["feature", "bug_fix", "enhancement", "refactor", "performance", "security"],
                                    "default": "feature",
                                },
                                "priority": {
                                    "type": "string",
                                    "enum": ["critical", "high", "medium", "low"],
                                    "default": "medium",
                                },
                            },
                            "required": ["name"],
                        },
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for filtering",
                    },
                },
                "required": ["title", "description"],
            },
        ),
        Tool(
            name="bfagent_get_initiative",
            description="""Get details of an Initiative by ID, including linked requirements.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "initiative_id": {
                        "type": "string",
                        "description": "UUID of the Initiative",
                    },
                    "include_requirements": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include linked requirements",
                    },
                },
                "required": ["initiative_id"],
            },
        ),
        Tool(
            name="bfagent_list_initiatives",
            description="""List all initiatives with optional filtering.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["analysis", "concept", "planning", "in_progress", "review", "completed", "on_hold", "cancelled", "all"],
                        "default": "all",
                    },
                    "domain": {
                        "type": "string",
                        "description": "Filter by domain",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum initiatives to return",
                    },
                },
            },
        ),
        Tool(
            name="bfagent_update_initiative",
            description="""Update an Initiative's status, analysis, concept, or workflow fields.
            Use this to document progress through the standard workflow phases.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "initiative_id": {
                        "type": "string",
                        "description": "UUID of the Initiative",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["analysis", "concept", "planning", "in_progress", "review", "completed", "on_hold", "cancelled"],
                    },
                    "workflow_phase": {
                        "type": "string",
                        "enum": ["kickoff", "research", "analysis", "design", "implementation", "testing", "documentation", "review", "deployment"],
                        "description": "Current workflow phase",
                    },
                    "analysis": {
                        "type": "string",
                        "description": "Updated analysis findings",
                    },
                    "concept": {
                        "type": "string",
                        "description": "Updated solution concept",
                    },
                    "next_steps": {
                        "type": "string",
                        "description": "Next planned steps",
                    },
                    "blockers": {
                        "type": "string",
                        "description": "Current blockers/impediments",
                    },
                    "lessons_learned": {
                        "type": "string",
                        "description": "Lessons learned, best practices",
                    },
                    "related_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of relevant file paths",
                    },
                },
                "required": ["initiative_id"],
            },
        ),
        Tool(
            name="bfagent_start_initiative",
            description="""Start working on an Initiative. This fetches the initiative details, logs the start,
            and returns the information needed to begin analysis. Call this when a user wants you to work on an initiative.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "initiative_id": {
                        "type": "string",
                        "description": "UUID of the Initiative to start",
                    },
                },
                "required": ["initiative_id"],
            },
        ),
        Tool(
            name="bfagent_log_initiative_activity",
            description="""Log an activity/progress for an Initiative. Use this to document steps, findings, decisions.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "initiative_id": {
                        "type": "string",
                        "description": "UUID of the Initiative",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["analysis_started", "analysis_completed", "concept_added", "requirement_added", "comment", "error"],
                        "description": "Type of activity",
                    },
                    "details": {
                        "type": "string",
                        "description": "Details about the activity",
                    },
                    "mcp_tool": {
                        "type": "string",
                        "description": "Optional: MCP tool that was used",
                    },
                    "tokens_used": {
                        "type": "integer",
                        "description": "Optional: tokens consumed",
                    },
                },
                "required": ["initiative_id", "action", "details"],
            },
        ),
        # =====================================================================
        # WORKFLOW RULES & ENFORCEMENT
        # =====================================================================
        Tool(
            name="bfagent_check_workflow_rules",
            description="""Check if an Initiative or Requirement follows workflow rules and best practices.
            Returns violations and suggestions for compliance. Use this before status changes or to validate work quality.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "initiative_id": {
                        "type": "string",
                        "description": "UUID of Initiative to check",
                    },
                    "requirement_id": {
                        "type": "string",
                        "description": "UUID of Requirement to check (alternative to initiative_id)",
                    },
                    "rule_category": {
                        "type": "string",
                        "enum": ["workflow", "documentation", "naming", "activity", "all"],
                        "default": "all",
                        "description": "Category of rules to check",
                    },
                    "target_status": {
                        "type": "string",
                        "description": "Optional: Check rules for transitioning TO this status",
                    },
                },
            },
        ),
        Tool(
            name="bfagent_list_workflow_rules",
            description="""List all available workflow rules with their descriptions and severity levels.
            Use this to understand what rules exist and how to comply with them.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["workflow", "documentation", "naming", "activity", "all"],
                        "default": "all",
                    },
                    "response_format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
            },
        ),
        # =====================================================================
        # TASK DELEGATION TOOLS (Complexity-based LLM Routing)
        # =====================================================================
        Tool(
            name="bfagent_delegate_task",
            description="""Delegate a task to a local LLM based on complexity. Use this for LOW/MEDIUM complexity tasks
            to save Cascade tokens. The Auto-Router selects the best LLM (Ollama/vLLM) based on task type and complexity.
            Returns result immediately or indicates if task requires Cascade for HIGH complexity.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Short name for the task",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "The prompt/instruction to execute",
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "Optional system prompt for context",
                    },
                    "complexity": {
                        "type": "string",
                        "enum": ["auto", "low", "medium", "high"],
                        "default": "auto",
                        "description": "Task complexity (auto = estimate from description)",
                    },
                    "task_type": {
                        "type": "string",
                        "enum": ["coding", "writing", "analysis", "translation", "other"],
                        "default": "coding",
                        "description": "Type of task for routing optimization",
                    },
                    "requirement_id": {
                        "type": "string",
                        "description": "Optional: Link to TestRequirement UUID",
                    },
                },
                "required": ["name", "prompt"],
            },
        ),
        Tool(
            name="bfagent_estimate_complexity",
            description="""Estimate the complexity of a task without executing it. Use this to decide whether
            to delegate to local LLM or handle with Cascade. Returns LOW, MEDIUM, or HIGH.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Task description to analyze",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["feature", "bug_fix", "enhancement", "refactor", "performance", "security"],
                        "description": "Task category for better estimation",
                    },
                    "files_affected": {
                        "type": "integer",
                        "description": "Number of files likely affected",
                        "default": 0,
                    },
                },
                "required": ["description"],
            },
        ),
        Tool(
            name="bfagent_get_task_status",
            description="""Get the status of a delegated task by ID.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "UUID of the DelegatedTask",
                    },
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="bfagent_list_delegated_tasks",
            description="""List recent delegated tasks with optional filtering.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "running", "completed", "failed", "all"],
                        "default": "all",
                    },
                    "task_type": {
                        "type": "string",
                        "enum": ["coding", "writing", "analysis", "translation", "all"],
                        "default": "all",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of tasks to return",
                    },
                },
            },
        ),
        Tool(
            name="bfagent_get_routing_info",
            description="""Get information about available LLMs and routing rules. Useful for understanding
            which LLMs are available for task delegation.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_llms": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include list of available LLMs",
                    },
                },
            },
        ),
        # =====================================================================
        # ROUTING ANALYTICS & FEEDBACK TOOLS
        # =====================================================================
        Tool(
            name="bfagent_rate_task_result",
            description="""Rate the quality of a delegated task result. Use this after reviewing LLM output
            to help improve routing decisions. Tracks whether complexity estimation was correct.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "UUID of the DelegatedTask",
                    },
                    "quality": {
                        "type": "string",
                        "enum": ["excellent", "good", "acceptable", "poor", "wrong_routing"],
                        "description": "Quality rating of the result",
                    },
                    "routing_correct": {
                        "type": "boolean",
                        "default": True,
                        "description": "Was the complexity estimation correct?",
                    },
                    "should_have_been": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "correct"],
                        "default": "correct",
                        "description": "If routing was wrong, what should it have been?",
                    },
                    "result_used": {
                        "type": "boolean",
                        "default": True,
                        "description": "Was the result actually used?",
                    },
                    "manual_correction_needed": {
                        "type": "boolean",
                        "default": False,
                        "description": "Did you need to manually fix the result?",
                    },
                    "comment": {
                        "type": "string",
                        "description": "Optional feedback comment",
                    },
                },
                "required": ["task_id", "quality"],
            },
        ),
        Tool(
            name="bfagent_get_routing_analytics",
            description="""Get analytics on routing decisions and their outcomes. Shows success rates,
            quality distribution, and token savings. Use to evaluate Auto-Router performance.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "default": 7,
                        "description": "Number of days to analyze",
                    },
                    "include_details": {
                        "type": "boolean",
                        "default": False,
                        "description": "Include per-task breakdown",
                    },
                },
            },
        ),
        Tool(
            name="bfagent_get_misrouted_tasks",
            description="""Get tasks that were marked as incorrectly routed. Use to identify patterns
            and improve the complexity estimation algorithm.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of tasks to return",
                    },
                },
            },
        ),
        # =====================================================================
        # DOCUMENTATION TOOLS (Auto-Update on Code Changes)
        # =====================================================================
        Tool(
            name="bfagent_scan_hub_docs",
            description="""Scan a hub for documentation status. Shows handler/model counts,
            docstring coverage, and identifies undocumented items. Use before updating docs.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "hub_name": {
                        "type": "string",
                        "description": "Hub to scan (e.g., 'writing_hub', 'cad_hub')",
                    },
                    "response_format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
                "required": ["hub_name"],
            },
        ),
        Tool(
            name="bfagent_update_hub_docs",
            description="""Update documentation for a hub based on current code.
            Extracts docstrings and updates the corresponding .md file in docs/.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "hub_name": {
                        "type": "string",
                        "description": "Hub to update docs for (e.g., 'writing_hub')",
                    },
                },
                "required": ["hub_name"],
            },
        ),
        Tool(
            name="bfagent_list_undocumented",
            description="""List all undocumented classes and functions in a hub.
            Returns file paths and line numbers for items missing docstrings.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "hub_name": {
                        "type": "string",
                        "description": "Hub to check (e.g., 'writing_hub')",
                    },
                },
                "required": ["hub_name"],
            },
        ),
        # =====================================================================
        # TEMPLATE ANALYSIS TOOLS
        # =====================================================================
        Tool(
            name="bfagent_find_duplicate_templates",
            description="""Find duplicate Django templates and show which one Django actually loads.
            Django loads templates in order: 1) DIRS (root templates/), 2) APP_DIRS (app templates/).
            Use this to debug template issues where changes don't appear.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_path": {
                        "type": "string",
                        "description": "Optional: specific template path to check (e.g., 'bfagent/controlling/dashboard.html')",
                    },
                },
            },
        ),
        Tool(
            name="bfagent_cleanup_duplicate_templates",
            description="""Clean up duplicate templates with automatic backup.
            Creates backup before deleting. Use dry_run=True to preview changes.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "dry_run": {
                        "type": "boolean",
                        "default": True,
                        "description": "If true, only show what would be deleted without actually deleting",
                    },
                    "keep_source": {
                        "type": "string",
                        "enum": ["ROOT", "APP"],
                        "default": "ROOT",
                        "description": "Which source to keep (ROOT = templates/, APP = app templates/)",
                    },
                },
            },
        ),
        Tool(
            name="bfagent_restore_template_backup",
            description="""Restore templates from a backup created by cleanup_duplicate_templates.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "backup_dir": {
                        "type": "string",
                        "description": "Backup directory path (e.g., '.template_backup_20260116_143000')",
                    },
                },
                "required": ["backup_dir"],
            },
        ),
        # =====================================================================
        # DJANGO SHELL TOOLS
        # =====================================================================
        Tool(
            name="bfagent_django_shell",
            description="""Execute Python code in Django shell. Uses pipe for clean execution without hanging.
            Perfect for quick queries, model inspection, and debugging.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute (can be multi-line)",
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 30,
                        "description": "Timeout in seconds",
                    },
                },
                "required": ["code"],
            },
        ),
        Tool(
            name="bfagent_django_query",
            description="""Execute a simple Django ORM query. Shortcut for common operations.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "Full model path (e.g., 'apps.bfagent.models_controlling.LLMUsageLog')",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["count", "first", "last", "all", "filter"],
                        "default": "count",
                        "description": "Query action to perform",
                    },
                    "filter_kwargs": {
                        "type": "object",
                        "description": "Filter arguments as dict (e.g., {'success': false})",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Limit for 'all' and 'filter' actions",
                    },
                },
                "required": ["model"],
            },
        ),
        # =====================================================================
        # SESSION TRACKING TOOLS
        # =====================================================================
        Tool(
            name="bfagent_log_user_request",
            description="""Log a user request/session start. Call this FIRST when starting work on a user request.
            Creates audit trail linking user input to all subsequent tool calls.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_request": {
                        "type": "string",
                        "description": "The user's original request/message",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["auto", "route", "ab", "ac", "default"],
                        "default": "default",
                        "description": "Work mode: auto, route, ab, ac, or default",
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional: Additional context (file path, selection, etc.)",
                    },
                },
                "required": ["user_request"],
            },
        ),
        Tool(
            name="bfagent_log_session_end",
            description="""Log session/task completion. Call when finishing work on a user request.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID from log_user_request",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Summary of what was accomplished",
                    },
                    "success": {
                        "type": "boolean",
                        "default": True,
                        "description": "Was the task completed successfully?",
                    },
                },
                "required": ["summary"],
            },
        ),
        # =====================================================================
        # DOCUMENTATION MIGRATION TOOLS
        # =====================================================================
        Tool(
            name="bfagent_docs_analyze_legacy",
            description="""Analyze legacy documentation folder for migration.
            Scans docs_legacy/ and categorizes files by type (handlers, guides, etc.).
            Returns overview with migration suggestions.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "legacy_path": {
                        "type": "string",
                        "default": "docs_legacy",
                        "description": "Path to legacy docs (relative to project root)",
                    },
                    "include_subdirs": {
                        "type": "boolean",
                        "default": True,
                        "description": "Whether to scan subdirectories",
                    },
                },
            },
        ),
        Tool(
            name="bfagent_docs_migrate_file",
            description="""Migrate a single documentation file from legacy to Sphinx structure.
            User controls each migration individually.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Source file path (e.g., 'docs_legacy/HANDLER_GUIDE.md')",
                    },
                    "target": {
                        "type": "string",
                        "description": "Target file path (e.g., 'docs/source/guides/HANDLER_GUIDE.md')",
                    },
                    "delete_source": {
                        "type": "boolean",
                        "default": False,
                        "description": "Delete source file after successful copy",
                    },
                },
                "required": ["source", "target"],
            },
        ),
        Tool(
            name="bfagent_docs_check_duplicates",
            description="""Check for duplicate documentation files between legacy and Sphinx docs.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "legacy_path": {
                        "type": "string",
                        "default": "docs_legacy",
                    },
                    "sphinx_path": {
                        "type": "string",
                        "default": "docs/source",
                    },
                },
            },
        ),
    ]


# =============================================================================
# TOOL HANDLERS
# =============================================================================


@mcp_server.list_tools()
async def list_tools() -> List[Tool]:
    return get_tool_definitions()


def _categorize_tool(tool_name: str) -> str:
    """Kategorisiert ein Tool für bessere Filterung."""
    if "domain" in tool_name or "handler" in tool_name:
        return "domain"
    elif "template" in tool_name:
        return "template"
    elif "shell" in tool_name or "query" in tool_name:
        return "database"
    elif "doc" in tool_name:
        return "documentation"
    elif "requirement" in tool_name or "initiative" in tool_name:
        return "workflow"
    elif "refactor" in tool_name:
        return "refactoring"
    elif "chrome" in tool_name or "sentry" in tool_name or "grafana" in tool_name:
        return "devops"
    return "general"


def _smart_truncate(data: str, max_len: int = 500) -> str:
    """Intelligentes Kürzen mit Hinweis."""
    if not data or len(data) <= max_len:
        return data or ""
    return f"{data[:max_len-30]}... [+{len(data)-max_len+30} chars]"


async def _log_mcp_usage_async(
    tool_name: str,
    arguments: Dict[str, Any],
    result: str = "",
    status: str = "success",
    error_message: str = "",
    duration_ms: int = 0
):
    """
    Log MCP tool usage via OrchestrationCall (async worker).
    
    Nutzt die bestehende Controlling-Infrastruktur statt separater Tabelle.
    """
    try:
        import os
        import sys
        import json
        
        django_path = os.path.join(os.path.dirname(__file__), "../../../")
        if django_path not in sys.path:
            sys.path.insert(0, django_path)
        
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        import django
        django.setup()
        
        from asgiref.sync import sync_to_async
        from apps.bfagent.models_controlling import OrchestrationCall
        from django.utils import timezone
        
        @sync_to_async
        def save_log():
            call_status = 'success' if status == "success" else 'failed'
            
            return OrchestrationCall.objects.create(
                call_type='tool_call',
                name=tool_name,
                description=_smart_truncate(json.dumps(arguments, default=str), 1000),
                status=call_status,
                result_summary=_smart_truncate(result, 500),
                error_message=error_message[:1000] if error_message else None,
                duration_ms=duration_ms,
                metadata={
                    'tool_category': _categorize_tool(tool_name),
                    'triggered_by': 'cascade',
                    'input_args': {k: str(v)[:200] for k, v in arguments.items()},
                },
                session_id=arguments.get('session_id', f"mcp-{timezone.now():%Y%m%d-%H%M%S}"),
            )
        
        await save_log()
    except Exception as e:
        logger.warning(f"Failed to log MCP usage: {e}")


def _log_mcp_usage(
    tool_name: str,
    arguments: Dict[str, Any],
    result: str = "",
    status: str = "success",
    error_message: str = "",
    duration_ms: int = 0
):
    """
    Fire-and-forget logging - blockiert Tool-Ausführung nicht.
    """
    try:
        asyncio.create_task(_log_mcp_usage_async(
            tool_name, arguments, result, status, error_message, duration_ms
        ))
    except Exception as e:
        logger.warning(f"Failed to schedule MCP logging: {e}")


@mcp_server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    logger.debug(f"Tool call: {name}")
    import time
    start_time = time.time()

    try:
        result = await _dispatch_tool(name, arguments)
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Log successful call - await directly to ensure it runs
        try:
            await _log_mcp_usage_async(
                tool_name=name,
                arguments=arguments,
                result=result,
                status="success",
                duration_ms=duration_ms
            )
        except Exception as log_err:
            logger.warning(f"Logging failed: {log_err}")
        
        return [TextContent(type="text", text=result)]
    except DomainNotFoundError as e:
        duration_ms = int((time.time() - start_time) * 1000)
        try:
            await _log_mcp_usage_async(name, arguments, status="error", error_message=e.message, duration_ms=duration_ms)
        except Exception:
            pass
        return [
            TextContent(
                type="text",
                text=f"❌ **Error:** {e.message}\n\nUse `bfagent_list_domains` to see available domains.",
            )
        ]
    except HandlerNotFoundError as e:
        duration_ms = int((time.time() - start_time) * 1000)
        try:
            await _log_mcp_usage_async(name, arguments, status="error", error_message=e.message, duration_ms=duration_ms)
        except Exception:
            pass
        return [TextContent(type="text", text=f"❌ **Error:** {e.message}")]
    except BFAgentMCPError as e:
        duration_ms = int((time.time() - start_time) * 1000)
        try:
            await _log_mcp_usage_async(name, arguments, status="error", error_message=e.message, duration_ms=duration_ms)
        except Exception:
            pass
        return [TextContent(type="text", text=f"❌ **Error ({e.code}):** {e.message}")]
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        try:
            await _log_mcp_usage_async(name, arguments, status="error", error_message=str(e), duration_ms=duration_ms)
        except Exception:
            pass
        logger.exception(f"Unexpected error: {e}")
        return [TextContent(type="text", text=f"❌ **Unexpected Error:** {str(e)}")]


async def _dispatch_tool(name: str, args: Dict[str, Any]) -> str:
    factory = ServiceFactory.get_instance()

    if name == "bfagent_list_domains":
        input_data = ListDomainsInput(**args)
        service = factory.get_domain_service()
        return await service.list_domains(
            status_filter=(
                DomainStatus(input_data.status_filter) if input_data.status_filter else None
            ),
            include_handler_count=input_data.include_handler_count,
            include_phases=input_data.include_phases,
            response_format=input_data.response_format,
        )

    elif name == "bfagent_get_domain":
        input_data = GetDomainInput(**args)
        service = factory.get_domain_service()
        return await service.get_domain(
            domain_id=input_data.domain_id,
            include_handlers=input_data.include_handlers,
            include_phases=input_data.include_phases,
            response_format=input_data.response_format,
        )

    elif name == "bfagent_search_handlers":
        input_data = SearchHandlersInput(**args)
        service = factory.get_handler_service()
        return await service.search_handlers(
            query=input_data.query,
            domain_filter=input_data.domain_filter,
            handler_type_filter=(
                HandlerType(input_data.handler_type_filter)
                if input_data.handler_type_filter
                else None
            ),
            limit=input_data.limit,
            offset=input_data.offset,
            response_format=input_data.response_format,
        )

    elif name == "bfagent_generate_handler":
        input_data = GenerateHandlerInput(**args)
        generator = GeneratorFactory.get_generator(use_ai=input_data.use_ai_enhancement)
        result = await generator.generate_handler(
            name=input_data.handler_name,
            domain=input_data.domain,
            handler_type=input_data.handler_type,
            description=input_data.description,
            input_fields=input_data.input_fields,
            output_fields=input_data.output_fields,
            include_tests=input_data.include_tests,
        )
        return _format_generated_handler(result, input_data)

    elif name == "bfagent_scaffold_domain":
        input_data = ScaffoldDomainInput(**args)
        generator = GeneratorFactory.get_generator()
        result = await generator.generate_domain(
            domain_id=input_data.domain_id,
            display_name=input_data.display_name,
            description=input_data.description,
            phases=input_data.phases,
            include_admin=input_data.include_admin,
            include_tests=input_data.include_tests,
        )
        return _format_scaffold(result, input_data)

    elif name == "bfagent_validate_handler":
        input_data = ValidateHandlerInput(**args)
        service = factory.get_validation_service()
        return await service.validate_handler_formatted(
            code=input_data.code, strict_mode=input_data.strict_mode
        )

    elif name == "bfagent_get_best_practices":
        input_data = GetBestPracticesInput(**args)
        service = factory.get_best_practice_service()
        return await service.get_best_practices(
            topic=input_data.topic,
            include_examples=input_data.include_examples,
            response_format=input_data.response_format,
        )

    # =========================================================================
    # REFACTORING TOOLS
    # =========================================================================

    elif name == "bfagent_get_refactor_options":
        from .services.refactor_service import get_refactor_service

        service = get_refactor_service()
        return await service.get_refactor_options(
            domain_id=args.get("domain_id"),
            response_format=args.get("response_format", "markdown"),
        )

    elif name == "bfagent_check_path_protection":
        from .services.refactor_service import get_refactor_service

        service = get_refactor_service()
        return await service.check_path_protection(
            file_path=args.get("file_path"),
            response_format=args.get("response_format", "markdown"),
        )

    elif name == "bfagent_get_naming_convention":
        from .services.refactor_service import get_refactor_service

        service = get_refactor_service()
        return await service.get_naming_convention(
            app_label=args.get("app_label"),
            response_format=args.get("response_format", "markdown"),
        )

    elif name == "bfagent_list_naming_conventions":
        from .services.refactor_service import get_refactor_service

        service = get_refactor_service()
        return await service.list_naming_conventions(
            response_format=args.get("response_format", "markdown"),
        )

    elif name == "bfagent_list_component_types":
        from .services.refactor_service import get_refactor_service

        service = get_refactor_service()
        return await service.list_component_types(
            response_format=args.get("response_format", "markdown"),
        )

    elif name == "bfagent_start_refactor_session":
        from .services.refactor_service import get_refactor_service

        service = get_refactor_service()
        return await service.start_refactor_session(
            domain_id=args.get("domain_id"),
            components=args.get("components", []),
            triggered_by="windsurf",
        )

    elif name == "bfagent_end_refactor_session":
        from .services.refactor_service import get_refactor_service

        service = get_refactor_service()
        return await service.end_refactor_session(
            session_id=args.get("session_id"),
            status=args.get("status", "completed"),
            summary=args.get("summary", ""),
            files_changed=args.get("files_changed", 0),
            lines_added=args.get("lines_added", 0),
            lines_removed=args.get("lines_removed", 0),
        )

    # =========================================================================
    # DEVOPS AI STACK TOOLS
    # =========================================================================

    elif name == "bfagent_sentry_capture_error":
        try:
            import os
            import sys

            # Add Django project to path
            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django

            django.setup()

            from apps.bfagent.services.sentry_integration import get_sentry_service

            sentry = get_sentry_service()

            if not sentry.is_enabled():
                return "⚠️ **Sentry is DISABLED**\n\nConfigure SENTRY_DSN in .env to enable"

            event_id = sentry.capture_message(
                args.get("error_message"), context=args.get("context", {})
            )

            return f"✅ **Error captured in Sentry**\n\nEvent ID: `{event_id}`"
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_sentry_get_stats":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django

            django.setup()

            from apps.bfagent.services.sentry_integration import get_sentry_service

            sentry = get_sentry_service()
            stats = sentry.get_stats()

            return f"""# Sentry Integration Status

**Enabled:** {'✅ Yes' if stats['enabled'] else '❌ No'}
**SDK Installed:** {'✅ Yes' if stats['sdk_installed'] else '❌ No'}
**DSN Configured:** {'✅ Yes' if stats['dsn_configured'] else '❌ No'}

{'' if stats['enabled'] else '**To enable:** Add SENTRY_DSN to .env file'}
"""
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_grafana_create_dashboard":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django

            django.setup()

            from apps.bfagent.services.grafana_integration import get_grafana_service

            grafana = get_grafana_service()

            if not grafana.is_enabled():
                return (
                    "⚠️ **Grafana is DISABLED**\n\nConfigure GRAFANA_URL and GRAFANA_TOKEN in .env"
                )

            result = grafana.create_bfagent_monitoring_dashboard()
            return "✅ **Dashboard created successfully**"
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_grafana_get_alerts":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django

            django.setup()

            from apps.bfagent.services.grafana_integration import get_grafana_service

            grafana = get_grafana_service()
            alerts = grafana.get_default_alerts()

            output = "# Grafana Alert Rules\n\n"
            for alert in alerts:
                output += f"## {alert['name']}\n"
                output += f"- **Condition:** {alert['condition']}\n"
                output += f"- **Threshold:** {alert['threshold']}\n\n"

            return output
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_chrome_test_page":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django

            django.setup()

            from apps.bfagent.services.chrome_devtools_integration import get_chrome_service

            chrome = get_chrome_service()

            result = chrome.test_admin_page(args.get("url"))

            output = f"""# Page Test Results

**URL:** {result['url']}
**Status:** {result['status']}
**MCP Used:** {'✅ Yes' if result.get('mcp_used') else '❌ Fallback mode'}

**Console Errors:** {len(result.get('console_errors', []))}
**Network Requests:** {len(result.get('network_requests', []))}

{result.get('message', '')}
"""
            return output
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_chrome_measure_performance":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django

            django.setup()

            from apps.bfagent.services.chrome_devtools_integration import get_chrome_service

            chrome = get_chrome_service()

            result = chrome.measure_performance(args.get("url"))

            return f"""# Performance Metrics

**URL:** {args.get("url")}
**MCP Used:** {'✅ Yes' if result.get('mcp_used') else '❌ Fallback mode'}

**Metrics:**
- LCP: {result.get('lcp', 'N/A')}
- FID: {result.get('fid', 'N/A')}
- CLS: {result.get('cls', 'N/A')}
- Page Load: {result.get('page_load', 'N/A')}
"""
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_admin_ultimate_check":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django

            django.setup()

            from asgiref.sync import sync_to_async

            from apps.bfagent.services.admin_diagnostics import get_admin_diagnostics

            admin = get_admin_diagnostics()

            # Wrap sync Django call with sync_to_async
            results = await sync_to_async(admin.ultimate_health_check)(
                app_label=args.get("app_label"), auto_fix=False, visual_testing=False
            )

            summary = results["summary"]
            return f"""# Ultimate Admin Health Check

**App:** {results['app']}
**Timestamp:** {results['timestamp']}

## Summary

**Schema:**
- Missing tables: {summary['schema']['missing_tables']}
- Missing columns: {summary['schema']['missing_columns']}

**Admin:**
- Pages tested: {summary['admin']['tested']}
- Errors found: {summary['admin']['errors']}
- Errors fixed: {summary['admin']['fixed']}

**Database:**
- Unused tables: {summary['unused']['tables']}
- Unused rows: {summary['unused']['rows']:,}

**Services:**
- Active: {summary['services_active']}/3 (Sentry, Grafana, Chrome)

**Status:** {'✅ ALL CHECKS PASSED' if summary['admin']['errors'] == 0 else f"⚠️ {summary['admin']['errors']} error(s) found"}
"""
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    # =========================================================================
    # CODE DELEGATION TOOLS
    # =========================================================================

    elif name == "bfagent_delegate_code":
        try:
            from .tools.code_delegation import handle_code_delegation
            
            result = await handle_code_delegation(args)
            
            if result.get("success"):
                # Check if this is a routed SQL request
                if result.get("routed"):
                    suggested = result.get("suggested_call", {})
                    return f"""# 🔀 SQL Routed to Existing Tool

**Target Tool:** `{result.get('target_tool')}`
**Message:** {result.get('message')}

## Suggested Call:
```python
{suggested.get('tool')}({suggested.get('params')})
```

Use the suggested tool directly for SQL operations."""
                
                # Normal code generation
                method = result.get("method", "unknown")
                duration = result.get("duration_ms", 0)
                code = result.get("code", "")
                
                return f"""# ✅ Code Generated

**Task Type:** {result.get('task_type')}
**Method:** {method} {'(LLM: ' + result.get('model', '') + ')' if method == 'llm' else ''}
**Duration:** {duration:.0f}ms

```python
{code}
```
"""
            else:
                return f"❌ **Error:** {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            return f"❌ **Code Delegation Error:** {str(e)}"

    # =========================================================================
    # REQUIREMENT MANAGEMENT TOOLS
    # =========================================================================

    elif name == "bfagent_update_requirement_status":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django

            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.models_testing import TestRequirement, RequirementFeedback

            requirement_id = args.get("requirement_id")
            new_status = args.get("status")
            notes = args.get("notes", "")

            @sync_to_async
            def update_status():
                req = TestRequirement.objects.get(pk=requirement_id)
                old_status = req.status
                req.status = new_status
                req.save()

                # Add feedback about status change
                RequirementFeedback.objects.create(
                    requirement=req,
                    feedback_type='progress',
                    content=f"Status geändert: {old_status} → {new_status}" + (f"\n{notes}" if notes else ""),
                    is_from_cascade=True
                )
                return req

            req = await update_status()
            return f"""✅ **Status aktualisiert**

**Requirement:** {req.name}
**Neuer Status:** {new_status}
**ID:** `{requirement_id}`
"""
        except TestRequirement.DoesNotExist:
            return f"❌ **Error:** Requirement `{requirement_id}` nicht gefunden"
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_record_task_result":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django

            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.models_testing import TestRequirement, RequirementFeedback

            requirement_id = args.get("requirement_id")
            success = args.get("success", False)
            summary = args.get("summary", "")
            files_changed = args.get("files_changed", [])
            next_steps = args.get("next_steps", "")

            @sync_to_async
            def record_result():
                req = TestRequirement.objects.get(pk=requirement_id)
                
                # Build feedback content
                content = f"## {'✅ Erfolgreich' if success else '❌ Nicht abgeschlossen'}\n\n"
                content += f"**Zusammenfassung:**\n{summary}\n\n"
                
                if files_changed:
                    content += f"**Geänderte Dateien:**\n"
                    for f in files_changed[:10]:  # Max 10 files
                        content += f"- `{f}`\n"
                    content += "\n"
                
                if next_steps:
                    content += f"**Nächste Schritte:**\n{next_steps}\n"

                # Add feedback
                RequirementFeedback.objects.create(
                    requirement=req,
                    feedback_type='solution' if success else 'progress',
                    content=content,
                    is_from_cascade=True
                )

                # Update status
                if success:
                    req.status = 'done'
                    req.save()

                return req

            req = await record_result()
            return f"""✅ **Task-Ergebnis aufgezeichnet**

**Requirement:** {req.name}
**Erfolg:** {'✅ Ja' if success else '❌ Nein'}
**Status:** {req.status}
**Dateien geändert:** {len(files_changed)}

Feedback wurde zum Requirement hinzugefügt.
"""
        except TestRequirement.DoesNotExist:
            return f"❌ **Error:** Requirement `{requirement_id}` nicht gefunden"
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_add_feedback":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django

            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.models_testing import TestRequirement, RequirementFeedback

            requirement_id = args.get("requirement_id")
            feedback_type = args.get("feedback_type", "progress")
            content = args.get("content", "")

            @sync_to_async
            def add_feedback():
                req = TestRequirement.objects.get(pk=requirement_id)
                
                feedback = RequirementFeedback.objects.create(
                    requirement=req,
                    feedback_type=feedback_type,
                    content=content,
                    is_from_cascade=True
                )
                return req, feedback

            req, feedback = await add_feedback()
            
            type_emoji = {
                'comment': '💬',
                'progress': '📊',
                'blocker': '🚫',
                'question': '❓',
                'solution': '✅'
            }
            
            return f"""{type_emoji.get(feedback_type, '📝')} **Feedback hinzugefügt**

**Requirement:** {req.name}
**Typ:** {feedback_type}
**ID:** `{requirement_id}`
"""
        except TestRequirement.DoesNotExist:
            return f"❌ **Error:** Requirement `{requirement_id}` nicht gefunden"
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_get_requirement":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django

            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.models_testing import TestRequirement

            requirement_id = args.get("requirement_id")
            include_feedback = args.get("include_feedback", True)

            @sync_to_async
            def get_requirement():
                req = TestRequirement.objects.get(pk=requirement_id)
                feedbacks = list(req.feedbacks.all()[:10]) if include_feedback else []
                return req, feedbacks

            req, feedbacks = await get_requirement()
            
            output = f"""# {req.name}

**ID:** `{req.pk}`
**Status:** {req.status}
**Priority:** {req.priority}
**Category:** {req.category}
**Domain:** {req.domain}

## Beschreibung
{req.description or 'Keine Beschreibung'}

"""
            if req.url:
                output += f"**URL:** {req.url}\n\n"
            
            if req.actual_behavior:
                output += f"## Aktuelles Verhalten\n{req.actual_behavior}\n\n"
            
            if req.expected_behavior:
                output += f"## Erwartetes Verhalten\n{req.expected_behavior}\n\n"

            if include_feedback and feedbacks:
                output += "## Feedback-Historie\n\n"
                for fb in feedbacks:
                    author = "Cascade" if fb.is_from_cascade else (fb.author.username if fb.author else "System")
                    output += f"**{fb.get_feedback_type_display()}** von {author} ({fb.created_at:%d.%m.%Y %H:%M}):\n"
                    output += f"{fb.content[:200]}{'...' if len(fb.content) > 200 else ''}\n\n"

            return output
        except TestRequirement.DoesNotExist:
            return f"❌ **Error:** Requirement `{requirement_id}` nicht gefunden"
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_analyze_requirement":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.models_testing import TestRequirement, RequirementFeedback

            requirement_id = args.get("requirement_id")
            analysis_depth = args.get("analysis_depth", "quick")

            @sync_to_async
            def analyze_and_save():
                req = TestRequirement.objects.select_related('depends_on', 'initiative').get(pk=requirement_id)
                
                # Build analysis
                issues = []
                suggestions = []
                score = 100
                
                # Check description
                if not req.description or len(req.description) < 20:
                    issues.append("Beschreibung fehlt oder ist zu kurz")
                    score -= 15
                    suggestions.append("Füge eine detaillierte Beschreibung hinzu")
                
                # Check acceptance criteria
                if not req.acceptance_criteria:
                    issues.append("Keine Akzeptanzkriterien definiert")
                    score -= 20
                    suggestions.append("Definiere messbare Akzeptanzkriterien (Given/When/Then)")
                
                # Check dependency status
                if req.depends_on and req.depends_on.status not in ['done', 'completed']:
                    issues.append(f"Abhängigkeit '{req.depends_on.name}' ist noch nicht erledigt")
                    score -= 10
                
                # Check for blocked requirements
                blocked_count = req.blocks.exclude(status__in=['done', 'completed', 'archived']).count()
                if blocked_count > 0:
                    suggestions.append(f"{blocked_count} andere Requirements warten auf dieses")
                
                # Quality assessment
                if score >= 80:
                    quality = "✅ Gut definiert"
                elif score >= 60:
                    quality = "⚠️ Verbesserungspotenzial"
                else:
                    quality = "❌ Überarbeitung empfohlen"
                
                analysis = f"""## Requirement-Analyse: {req.name}

**Qualitätsscore:** {score}/100 {quality}

### Gefundene Probleme
"""
                if issues:
                    for issue in issues:
                        analysis += f"- ⚠️ {issue}\n"
                else:
                    analysis += "- ✅ Keine kritischen Probleme gefunden\n"
                
                analysis += "\n### Empfehlungen\n"
                if suggestions:
                    for sug in suggestions:
                        analysis += f"- 💡 {sug}\n"
                else:
                    analysis += "- ✅ Requirement ist gut vorbereitet\n"
                
                analysis += f"""
### Nächste Schritte
1. {"Beschreibung erweitern" if not req.description else "Beschreibung prüfen"}
2. {"Akzeptanzkriterien hinzufügen" if not req.acceptance_criteria else "Kriterien validieren"}
3. {"Abhängigkeit abwarten" if req.is_blocked_by_dependency else "Arbeit kann beginnen"}

**Freigabe-Empfehlung:** {"✅ Bereit für Arbeit" if score >= 70 and not req.is_blocked_by_dependency else "⏳ Noch nicht bereit"}
"""
                
                # Save as feedback
                RequirementFeedback.objects.create(
                    requirement=req,
                    feedback_type='solution',
                    content=analysis,
                    is_from_cascade=True
                )
                
                return analysis
            
            result = await analyze_and_save()
            return result
            
        except TestRequirement.DoesNotExist:
            return f"❌ **Error:** Requirement `{requirement_id}` nicht gefunden"
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    # =========================================================================
    # INITIATIVE HANDLERS
    # =========================================================================
    
    elif name == "bfagent_create_initiative":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.models_testing import Initiative, TestRequirement

            title = args.get("title")
            description = args.get("description")
            analysis = args.get("analysis", "")
            concept = args.get("concept", "")
            domain = args.get("domain", "core")
            priority = args.get("priority", "medium")
            tasks = args.get("tasks", [])
            tags = args.get("tags", [])

            @sync_to_async
            def create_initiative():
                # Create Initiative
                initiative = Initiative.objects.create(
                    title=title,
                    description=description,
                    analysis=analysis,
                    concept=concept,
                    domain=domain,
                    priority=priority,
                    tags=tags,
                    status="analysis" if not concept else "concept",
                )
                
                # Log creation activity
                initiative.log_activity(
                    action='created',
                    details=f"Initiative erstellt via MCP Tool",
                    actor='cascade',
                    mcp_tool='bfagent_create_initiative'
                )
                
                # Create linked requirements
                created_reqs = []
                for task in tasks:
                    req = TestRequirement.objects.create(
                        name=task.get("name"),
                        description=task.get("description", ""),
                        category=task.get("category", "feature"),
                        priority=task.get("priority", "medium"),
                        domain=domain,
                        initiative=initiative,
                        status="draft",
                    )
                    created_reqs.append(req)
                    initiative.log_activity(
                        action='requirement_added',
                        details=f"Requirement hinzugefügt: {req.name}",
                        actor='cascade',
                        mcp_tool='bfagent_create_initiative'
                    )
                
                return initiative, created_reqs

            initiative, reqs = await create_initiative()
            
            output = f"""✅ **Initiative erstellt**

**Titel:** {initiative.title}
**ID:** `{initiative.pk}`
**Status:** {initiative.get_status_display()}
**Domain:** {initiative.domain}
**Priority:** {initiative.priority}

"""
            if reqs:
                output += f"## Erstellte Tasks ({len(reqs)})\n\n"
                for i, req in enumerate(reqs, 1):
                    output += f"{i}. **{req.name}** (`{req.pk}`)\n"
                    output += f"   - Kategorie: {req.category}, Priorität: {req.priority}\n"
            
            output += f"\n**Admin:** http://localhost:8000/admin/bfagent/initiative/{initiative.pk}/change/"
            
            return output
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_get_initiative":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.models_testing import Initiative

            initiative_id = args.get("initiative_id")
            include_requirements = args.get("include_requirements", True)

            @sync_to_async
            def get_initiative():
                init = Initiative.objects.get(pk=initiative_id)
                reqs = list(init.requirements.all()) if include_requirements else []
                return init, reqs

            init, reqs = await get_initiative()
            
            output = f"""# {init.title}

**ID:** `{init.pk}`
**Status:** {init.get_status_display()}
**Priority:** {init.priority}
**Domain:** {init.domain}
**Fortschritt:** {init.completed_requirements}/{init.requirements_count} ({init.progress_percentage}%)

## Beschreibung
{init.description}

"""
            if init.analysis:
                output += f"## Analyse\n{init.analysis}\n\n"
            
            if init.concept:
                output += f"## Konzept\n{init.concept}\n\n"
            
            if include_requirements and reqs:
                output += f"## Requirements ({len(reqs)})\n\n"
                for req in reqs:
                    status_icon = "✅" if req.status in ["done", "completed"] else "⏳" if req.status == "in_progress" else "📋"
                    output += f"- {status_icon} **{req.name}** ({req.status}) - `{req.pk}`\n"

            return output
        except Initiative.DoesNotExist:
            return f"❌ **Error:** Initiative `{initiative_id}` nicht gefunden"
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_list_initiatives":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.models_testing import Initiative

            status_filter = args.get("status", "all")
            domain_filter = args.get("domain")
            limit = args.get("limit", 10)

            @sync_to_async
            def list_initiatives():
                qs = Initiative.objects.all()
                if status_filter and status_filter != "all":
                    qs = qs.filter(status=status_filter)
                if domain_filter:
                    qs = qs.filter(domain=domain_filter)
                return list(qs[:limit])

            initiatives = await list_initiatives()
            
            if not initiatives:
                return "📋 Keine Initiativen gefunden"
            
            output = f"# Initiativen ({len(initiatives)})\n\n"
            for init in initiatives:
                status_icon = {"analysis": "🔍", "concept": "💡", "planning": "📝", "in_progress": "⏳", "review": "👀", "completed": "✅", "on_hold": "⏸️", "cancelled": "❌"}.get(init.status, "📋")
                output += f"### {status_icon} {init.title}\n"
                output += f"- **ID:** `{init.pk}`\n"
                output += f"- **Status:** {init.get_status_display()}\n"
                output += f"- **Domain:** {init.domain}\n"
                output += f"- **Fortschritt:** {init.completed_requirements}/{init.requirements_count}\n\n"

            return output
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_update_initiative":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.models_testing import Initiative

            initiative_id = args.get("initiative_id")
            new_status = args.get("status")
            new_workflow_phase = args.get("workflow_phase")
            new_analysis = args.get("analysis")
            new_concept = args.get("concept")
            new_next_steps = args.get("next_steps")
            new_blockers = args.get("blockers")
            new_lessons = args.get("lessons_learned")
            new_related_files = args.get("related_files")

            @sync_to_async
            def update_initiative():
                init = Initiative.objects.get(pk=initiative_id)
                updated_fields = []
                
                if new_status:
                    init.status = new_status
                    updated_fields.append(f"Status → {new_status}")
                if new_workflow_phase:
                    init.workflow_phase = new_workflow_phase
                    updated_fields.append(f"Phase → {new_workflow_phase}")
                if new_analysis:
                    init.analysis = new_analysis
                    updated_fields.append("Analyse aktualisiert")
                if new_concept:
                    init.concept = new_concept
                    updated_fields.append("Konzept aktualisiert")
                if new_next_steps:
                    init.next_steps = new_next_steps
                    updated_fields.append("Nächste Schritte aktualisiert")
                if new_blockers:
                    init.blockers = new_blockers
                    updated_fields.append("Blocker dokumentiert")
                if new_lessons:
                    init.lessons_learned = new_lessons
                    updated_fields.append("Lessons Learned hinzugefügt")
                if new_related_files:
                    init.related_files = new_related_files
                    updated_fields.append(f"{len(new_related_files)} Dateien verknüpft")
                
                init.save()
                
                # Log activity
                if updated_fields:
                    init.log_activity(
                        action='status_change',
                        details=", ".join(updated_fields),
                        actor='cascade',
                        mcp_tool='bfagent_update_initiative'
                    )
                
                return init, updated_fields

            init, updated_fields = await update_initiative()
            
            return f"""✅ **Initiative aktualisiert**

**Titel:** {init.title}
**ID:** `{init.pk}`
**Status:** {init.get_status_display()}
**Phase:** {init.get_workflow_phase_display() if hasattr(init, 'get_workflow_phase_display') else init.workflow_phase}

**Änderungen:**
{chr(10).join(f"- {f}" for f in updated_fields) if updated_fields else "- Keine Änderungen"}
"""
        except Initiative.DoesNotExist:
            return f"❌ **Error:** Initiative `{initiative_id}` nicht gefunden"
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_start_initiative":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.models_testing import Initiative

            initiative_id = args.get("initiative_id")

            @sync_to_async
            def start_initiative():
                init = Initiative.objects.get(pk=initiative_id)
                reqs = list(init.requirements.all())
                activities = list(init.activities.all()[:10])
                
                # Log start activity
                init.log_activity(
                    action='analysis_started',
                    details='Cascade hat die Arbeit an der Initiative gestartet',
                    actor='cascade',
                    mcp_tool='bfagent_start_initiative'
                )
                
                return init, reqs, activities

            init, reqs, activities = await start_initiative()
            
            output = f"""# 🚀 Initiative gestartet: {init.title}

**ID:** `{init.pk}`
**Status:** {init.get_status_display()}
**Domain:** {init.domain}
**Priorität:** {init.priority}

## 📋 Beschreibung
{init.description}

"""
            if init.analysis:
                output += f"## 🔍 Bisherige Analyse\n{init.analysis}\n\n"
            
            if init.concept:
                output += f"## 💡 Bisheriges Konzept\n{init.concept}\n\n"
            
            output += f"## 📊 Requirements ({len(reqs)})\n"
            if reqs:
                for req in reqs:
                    status_icon = "✅" if req.status in ["done", "completed"] else "⏳" if req.status == "in_progress" else "📋"
                    output += f"- {status_icon} {req.name} ({req.status})\n"
            else:
                output += "Noch keine Requirements definiert.\n"
            
            output += f"\n## 📜 Letzte Aktivitäten\n"
            if activities:
                for act in activities[:5]:
                    output += f"- {act.created_at:%d.%m %H:%M} - {act.get_action_display()}: {act.details[:50]}...\n"
            else:
                output += "Keine vorherigen Aktivitäten.\n"
            
            output += f"""
---
**Nächste Schritte:**
1. Analysiere die Beschreibung und den Kontext
2. Dokumentiere Erkenntnisse mit `bfagent_log_initiative_activity`
3. Aktualisiere die Initiative mit `bfagent_update_initiative`
4. Erstelle Requirements mit `bfagent_create_initiative` (tasks Parameter)
"""
            return output
        except Initiative.DoesNotExist:
            return f"❌ **Error:** Initiative `{initiative_id}` nicht gefunden"
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_log_initiative_activity":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.models_testing import Initiative

            initiative_id = args.get("initiative_id")
            action = args.get("action")
            details = args.get("details")
            mcp_tool = args.get("mcp_tool", "")
            tokens_used = args.get("tokens_used", 0)

            @sync_to_async
            def log_activity():
                init = Initiative.objects.get(pk=initiative_id)
                activity = init.log_activity(
                    action=action,
                    details=details,
                    actor='cascade',
                    mcp_tool=mcp_tool,
                    tokens_used=tokens_used
                )
                return init, activity

            init, activity = await log_activity()
            
            return f"""✅ **Aktivität dokumentiert**

**Initiative:** {init.title}
**Aktion:** {activity.get_action_display()}
**Details:** {details[:100]}...
**Zeit:** {activity.created_at:%d.%m.%Y %H:%M}
"""
        except Initiative.DoesNotExist:
            return f"❌ **Error:** Initiative `{initiative_id}` nicht gefunden"
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    # =========================================================================
    # WORKFLOW RULES HANDLERS
    # =========================================================================
    
    elif name == "bfagent_check_workflow_rules":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.models_testing import Initiative, TestRequirement
            from .workflow_rules import WorkflowRulesEngine

            initiative_id = args.get("initiative_id")
            requirement_id = args.get("requirement_id")
            rule_category = args.get("rule_category", "all")
            target_status = args.get("target_status")

            engine = WorkflowRulesEngine()

            @sync_to_async
            def check_rules():
                if initiative_id:
                    obj = Initiative.objects.get(pk=initiative_id)
                    result = engine.check_initiative(obj, target_status)
                    obj_type = "Initiative"
                    obj_title = obj.title
                elif requirement_id:
                    obj = TestRequirement.objects.get(pk=requirement_id)
                    result = engine.check_requirement(obj, target_status)
                    obj_type = "Requirement"
                    obj_title = obj.name
                else:
                    return None, None, None
                
                return result, obj_type, obj_title

            result, obj_type, obj_title = await check_rules()
            
            if result is None:
                return "❌ **Error:** Entweder `initiative_id` oder `requirement_id` muss angegeben werden"
            
            output = f"# 🔍 Regel-Check: {obj_type}\n\n**{obj_title}**\n\n"
            output += engine.format_result_markdown(result)
            
            return output
            
        except (Initiative.DoesNotExist, TestRequirement.DoesNotExist):
            return f"❌ **Error:** Objekt nicht gefunden"
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_list_workflow_rules":
        try:
            from .workflow_rules import WorkflowRulesEngine
            
            category = args.get("category", "all")
            response_format = args.get("response_format", "markdown")
            
            engine = WorkflowRulesEngine()
            
            if response_format == "json":
                import json
                rules = engine.get_rules_for_category(category)
                # Convert enums to strings for JSON
                json_rules = {}
                for rule_id, rule in rules.items():
                    json_rules[rule_id] = {
                        "name": rule["name"],
                        "category": rule["category"].value,
                        "severity": rule["severity"].value,
                        "description": rule["description"],
                        "applies_to": rule["applies_to"],
                    }
                return json.dumps(json_rules, indent=2, ensure_ascii=False)
            else:
                return engine.format_rules_markdown(category)
                
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    # =========================================================================
    # TASK DELEGATION HANDLERS
    # =========================================================================
    
    elif name == "bfagent_delegate_task":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.services.task_executor import get_executor

            task_name = args.get("name")
            prompt = args.get("prompt")
            system_prompt = args.get("system_prompt", "")
            complexity = args.get("complexity", "auto")
            task_type = args.get("task_type", "coding")
            requirement_id = args.get("requirement_id")

            @sync_to_async
            def delegate():
                executor = get_executor()
                return executor.create_and_execute(
                    name=task_name,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    complexity=complexity,
                    task_type=task_type,
                    requirement_id=requirement_id
                )

            result = await delegate()

            if result.get('requires_cascade'):
                return f"""🔴 **Task erfordert Cascade**

**Grund:** {result.get('message', 'HIGH complexity task')}
**Komplexität:** {result.get('complexity', 'high')}

Diese Aufgabe ist zu komplex für lokale LLMs. Bitte führe sie selbst aus.
"""
            elif result.get('ok'):
                return f"""✅ **Task delegiert und ausgeführt**

**Task:** {task_name}
**LLM verwendet:** {result.get('llm_used', 'unknown')}
**Latenz:** {result.get('latency_ms', 0)}ms
**Task ID:** `{result.get('task_id')}`

## Ergebnis

{result.get('result', 'Kein Ergebnis')}
"""
            else:
                return f"""❌ **Task fehlgeschlagen**

**Task:** {task_name}
**Fehler:** {result.get('error', 'Unknown error')}
**Task ID:** `{result.get('task_id')}`
"""
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_estimate_complexity":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()

            from apps.bfagent.services.llm_router import get_router

            description = args.get("description", "")
            category = args.get("category")
            files_affected = args.get("files_affected", 0)

            router = get_router()
            complexity = router.estimate_complexity(
                description=description,
                category=category,
                files_affected=files_affected
            )

            complexity_info = {
                'low': ('🟢', 'Kann an lokales LLM delegiert werden (Ollama 8B)'),
                'medium': ('🟡', 'Kann an lokales LLM delegiert werden (Ollama 33B/70B)'),
                'high': ('🔴', 'Sollte von Cascade bearbeitet werden'),
            }
            
            emoji, recommendation = complexity_info.get(complexity.value, ('⚪', 'Unbekannt'))

            return f"""## Komplexitäts-Schätzung

**Ergebnis:** {emoji} **{complexity.value.upper()}**

**Empfehlung:** {recommendation}

**Analyse:**
- Beschreibung: {len(description)} Zeichen
- Kategorie: {category or 'nicht angegeben'}
- Betroffene Dateien: {files_affected}

{'✅ **Delegieren empfohlen** - Nutze `bfagent_delegate_task`' if complexity.value in ['low', 'medium'] else '⚠️ **Selbst bearbeiten** - Task ist zu komplex für lokale LLMs'}
"""
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_get_task_status":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.services.task_executor import get_executor

            task_id = args.get("task_id")

            @sync_to_async
            def get_status():
                executor = get_executor()
                return executor.get_task_result(task_id)

            result = await get_status()

            if 'error' in result and not result.get('status'):
                return f"❌ **Error:** {result['error']}"

            status_emoji = {
                'pending': '⏳',
                'running': '🔄',
                'completed': '✅',
                'failed': '❌',
                'cancelled': '🚫'
            }

            return f"""## Task Status

**ID:** `{result.get('task_id')}`
**Status:** {status_emoji.get(result.get('status'), '❓')} {result.get('status', 'unknown')}
**LLM:** {result.get('llm_used', 'N/A')}
**Tokens:** {result.get('tokens_used', 0)}
**Latenz:** {result.get('latency_ms', 0)}ms
**Dauer:** {result.get('duration_seconds', 0):.2f}s

{"**Ergebnis:**" + chr(10) + result.get('result')[:500] + "..." if result.get('result') else ''}
{"**Fehler:** " + str(result.get('error')) if result.get('error') else ''}
"""
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_list_delegated_tasks":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.models_tasks import DelegatedTask

            status_filter = args.get("status", "all")
            task_type_filter = args.get("task_type", "all")
            limit = args.get("limit", 10)

            @sync_to_async
            def list_tasks():
                qs = DelegatedTask.objects.all()
                if status_filter != "all":
                    qs = qs.filter(status=status_filter)
                if task_type_filter != "all":
                    qs = qs.filter(task_type=task_type_filter)
                return list(qs[:limit].values(
                    'id', 'name', 'status', 'task_type', 'complexity',
                    'complexity_estimated', 'created_at', 'requires_cascade'
                ))

            tasks = await list_tasks()

            if not tasks:
                return "📭 **Keine delegierten Tasks gefunden**"

            output = f"## Delegierte Tasks ({len(tasks)})\n\n"
            
            status_emoji = {'pending': '⏳', 'running': '🔄', 'completed': '✅', 'failed': '❌'}
            
            for task in tasks:
                emoji = status_emoji.get(task['status'], '❓')
                cascade_badge = " 🔴CASCADE" if task['requires_cascade'] else ""
                output += f"- {emoji} **{task['name']}**{cascade_badge}\n"
                output += f"  ID: `{task['id']}` | {task['task_type']} | {task['complexity_estimated'] or task['complexity']}\n\n"

            return output
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_get_routing_info":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.models import Llms

            include_llms = args.get("include_llms", True)

            @sync_to_async
            def get_llms():
                return list(Llms.objects.filter(is_active=True).values(
                    'id', 'name', 'provider', 'is_local'
                ))

            output = """## LLM Auto-Router Info

### Routing-Regeln

| Complexity | Task Type | Bevorzugte LLMs |
|------------|-----------|-----------------|
| **LOW** | Coding | Ollama (small), Ollama (coder) |
| **LOW** | Writing/Other | Ollama (small), API (fast) |
| **MEDIUM** | Coding | Ollama (coder), Ollama (large) |
| **MEDIUM** | Writing/Other | Ollama (large), API (standard) |
| **HIGH** | Alle | **Cascade**, API (premium) |

### Komplexitäts-Keywords

- **HIGH:** refactor, architektur, migration, security, multi-file
- **MEDIUM:** new view, model, api, handler, service
- **LOW:** typo, text, config, template, css, label

"""
            if include_llms:
                llms = await get_llms()
                output += "### Verfügbare LLMs\n\n"
                
                local_llms = [l for l in llms if l['is_local']]
                cloud_llms = [l for l in llms if not l['is_local']]
                
                if local_llms:
                    output += "**Lokal (kostenlos):**\n"
                    for llm in local_llms:
                        output += f"- {llm['name']} ({llm['provider']})\n"
                    output += "\n"
                
                if cloud_llms:
                    output += "**Cloud APIs:**\n"
                    for llm in cloud_llms:
                        output += f"- {llm['name']} ({llm['provider']})\n"

            return output
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_rate_task_result":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.models_tasks import DelegatedTask, TaskFeedback

            task_id = args.get("task_id")
            quality = args.get("quality")
            routing_correct = args.get("routing_correct", True)
            should_have_been = args.get("should_have_been", "correct")
            result_used = args.get("result_used", True)
            manual_correction_needed = args.get("manual_correction_needed", False)
            comment = args.get("comment", "")

            @sync_to_async
            def save_feedback():
                task = DelegatedTask.objects.get(id=task_id)
                feedback, created = TaskFeedback.objects.update_or_create(
                    task=task,
                    defaults={
                        'result_quality': quality,
                        'routing_correct': routing_correct,
                        'should_have_been': should_have_been,
                        'result_used': result_used,
                        'manual_correction_needed': manual_correction_needed,
                        'comment': comment,
                    }
                )
                return task, feedback, created

            task, feedback, created = await save_feedback()

            quality_emoji = {
                'excellent': '⭐⭐⭐',
                'good': '⭐⭐',
                'acceptable': '⭐',
                'poor': '👎',
                'wrong_routing': '❌'
            }

            return f"""{'✅ Feedback gespeichert' if created else '🔄 Feedback aktualisiert'}

**Task:** {task.name}
**Qualität:** {quality_emoji.get(quality, '')} {quality}
**Routing korrekt:** {'✅ Ja' if routing_correct else f'❌ Nein → sollte {should_have_been} sein'}
**Ergebnis verwendet:** {'✅' if result_used else '❌'}
**Manuelle Korrektur:** {'⚠️ Ja' if manual_correction_needed else '✅ Nein'}

{f'**Kommentar:** {comment}' if comment else ''}

Dieses Feedback hilft, den Auto-Router zu verbessern! 🎯
"""
        except DelegatedTask.DoesNotExist:
            return f"❌ **Error:** Task `{task_id}` nicht gefunden"
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_get_routing_analytics":
        try:
            import os
            import sys
            from datetime import timedelta

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()

            from asgiref.sync import sync_to_async
            from django.utils import timezone
            from django.db.models import Count, Avg, Sum
            from apps.bfagent.models_tasks import DelegatedTask, TaskFeedback

            days = args.get("days", 7)
            include_details = args.get("include_details", False)

            @sync_to_async
            def get_analytics():
                since = timezone.now() - timedelta(days=days)
                
                # Basic task stats
                tasks = DelegatedTask.objects.filter(created_at__gte=since)
                total = tasks.count()
                
                by_complexity = tasks.values('complexity_estimated').annotate(count=Count('id'))
                by_status = tasks.values('status').annotate(count=Count('id'))
                
                # Cascade required
                cascade_required = tasks.filter(requires_cascade=True).count()
                delegated = tasks.filter(requires_cascade=False).count()
                
                # Success rate
                completed = tasks.filter(status='completed').count()
                failed = tasks.filter(status='failed').count()
                
                # Metrics
                metrics = tasks.aggregate(
                    total_tokens=Sum('tokens_used'),
                    avg_latency=Avg('latency_ms'),
                    total_cost=Sum('estimated_cost')
                )
                
                # Feedback stats
                feedbacks = TaskFeedback.objects.filter(task__created_at__gte=since)
                feedback_count = feedbacks.count()
                by_quality = feedbacks.values('result_quality').annotate(count=Count('id'))
                wrong_routing = feedbacks.filter(routing_correct=False).count()
                
                # Details if requested
                details = []
                if include_details:
                    recent = tasks.order_by('-created_at')[:10]
                    for t in recent:
                        fb = getattr(t, 'feedback', None)
                        details.append({
                            'name': t.name,
                            'complexity': t.complexity_estimated or t.complexity,
                            'status': t.status,
                            'llm': t.llm_selected.name if t.llm_selected else 'Cascade',
                            'quality': fb.result_quality if fb else 'N/A'
                        })
                
                return {
                    'total': total,
                    'delegated': delegated,
                    'cascade_required': cascade_required,
                    'completed': completed,
                    'failed': failed,
                    'by_complexity': {c['complexity_estimated']: c['count'] for c in by_complexity if c['complexity_estimated']},
                    'by_status': {s['status']: s['count'] for s in by_status},
                    'metrics': metrics,
                    'feedback_count': feedback_count,
                    'by_quality': {q['result_quality']: q['count'] for q in by_quality},
                    'wrong_routing': wrong_routing,
                    'details': details
                }

            stats = await get_analytics()

            # Calculate success rate
            total_exec = stats['completed'] + stats['failed']
            success_rate = (stats['completed'] / total_exec * 100) if total_exec > 0 else 0
            
            # Calculate delegation rate (token savings)
            delegation_rate = (stats['delegated'] / stats['total'] * 100) if stats['total'] > 0 else 0

            output = f"""## 📊 Routing Analytics ({days} Tage)

### Übersicht
| Metrik | Wert |
|--------|------|
| **Gesamt Tasks** | {stats['total']} |
| **Delegiert** | {stats['delegated']} ({delegation_rate:.1f}%) |
| **Cascade erforderlich** | {stats['cascade_required']} |
| **Erfolgsrate** | {success_rate:.1f}% |

### Nach Komplexität
"""
            for complexity, count in stats['by_complexity'].items():
                emoji = {'low': '🟢', 'medium': '🟡', 'high': '🔴'}.get(complexity, '⚪')
                output += f"- {emoji} **{complexity.upper()}**: {count}\n"

            output += f"""
### Performance
- **Tokens verwendet:** {stats['metrics']['total_tokens'] or 0:,}
- **Ø Latenz:** {stats['metrics']['avg_latency'] or 0:.0f}ms
- **Geschätzte Kosten:** ${float(stats['metrics']['total_cost'] or 0):.4f}

### Feedback ({stats['feedback_count']} Bewertungen)
"""
            quality_emoji = {'excellent': '⭐⭐⭐', 'good': '⭐⭐', 'acceptable': '⭐', 'poor': '👎', 'wrong_routing': '❌'}
            for quality, count in stats['by_quality'].items():
                output += f"- {quality_emoji.get(quality, '')} {quality}: {count}\n"
            
            if stats['wrong_routing'] > 0:
                output += f"\n⚠️ **Fehlgeleitete Tasks:** {stats['wrong_routing']}\n"

            if stats['details']:
                output += "\n### Letzte Tasks\n\n"
                for d in stats['details']:
                    output += f"- **{d['name']}** ({d['complexity']}) → {d['llm']} [{d['status']}]\n"

            return output
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_get_misrouted_tasks":
        try:
            import os
            import sys

            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            sys.path.insert(0, django_path)

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()

            from asgiref.sync import sync_to_async
            from apps.bfagent.models_tasks import TaskFeedback

            limit = args.get("limit", 10)

            @sync_to_async
            def get_misrouted():
                feedbacks = TaskFeedback.objects.filter(
                    routing_correct=False
                ).select_related('task').order_by('-created_at')[:limit]
                
                return [{
                    'task_id': str(fb.task.id),
                    'task_name': fb.task.name,
                    'estimated': fb.task.complexity_estimated or fb.task.complexity,
                    'should_have_been': fb.should_have_been,
                    'task_type': fb.task.task_type,
                    'quality': fb.result_quality,
                    'comment': fb.comment,
                    'prompt_preview': fb.task.prompt[:100] + '...' if len(fb.task.prompt) > 100 else fb.task.prompt
                } for fb in feedbacks]

            tasks = await get_misrouted()

            if not tasks:
                return """✅ **Keine fehlgeleiteten Tasks gefunden**

Das Routing funktioniert gut! Weiter so bewerten um den Auto-Router zu verbessern.
"""

            output = f"""## ❌ Fehlgeleitete Tasks ({len(tasks)})

Diese Tasks wurden falsch eingestuft. Analysiere die Muster um den Complexity-Estimator zu verbessern.

"""
            for t in tasks:
                output += f"""### {t['task_name']}
- **ID:** `{t['task_id']}`
- **Geschätzt:** {t['estimated'].upper()} → **Sollte:** {t['should_have_been'].upper()}
- **Task-Typ:** {t['task_type']}
- **Qualität:** {t['quality']}
- **Prompt:** `{t['prompt_preview']}`
{f"- **Kommentar:** {t['comment']}" if t['comment'] else ''}

"""

            output += """### 💡 Verbesserungsvorschläge

Basierend auf diesen Fehlern solltest du prüfen:
1. Fehlen bestimmte Keywords in der Complexity-Estimation?
2. Werden bestimmte Task-Typen systematisch falsch eingestuft?
3. Sollten die Schwellwerte angepasst werden?
"""

            return output
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    # =========================================================================
    # DOCUMENTATION TOOLS
    # =========================================================================
    elif name == "bfagent_scan_hub_docs":
        try:
            from .services.doc_service import DocumentationService
            
            hub_name = args.get("hub_name")
            response_format = args.get("response_format", "markdown")
            
            service = DocumentationService()
            result = service.scan_hub(hub_name)
            
            if response_format == "json":
                return json.dumps(result, indent=2)
            
            return f"""# 📊 Dokumentations-Status: {hub_name}

## Handler
- **Gesamt:** {result['handlers']['total']}
- **Dokumentiert:** {result['handlers']['documented']}
- **Coverage:** {result['handlers']['coverage']}
- **Namen:** {', '.join(result['handlers']['names']) if result['handlers']['names'] else 'Keine'}

## Models
- **Gesamt:** {result['models']['total']}
- **Dokumentiert:** {result['models']['documented']}
- **Coverage:** {result['models']['coverage']}
- **Namen:** {', '.join(result['models']['names']) if result['models']['names'] else 'Keine'}
"""
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_update_hub_docs":
        try:
            from .services.doc_service import DocumentationService
            
            hub_name = args.get("hub_name")
            
            service = DocumentationService()
            result = service.update_documentation(hub_name)
            
            status = "✅" if result.success else "⚠️"
            output = f"""{status} **{result.message}**

**Aktualisierte Dateien:** {len(result.files_updated)}
"""
            if result.files_updated:
                for f in result.files_updated:
                    output += f"- `{f}`\n"
            
            if result.warnings:
                output += "\n**Warnungen:**\n"
                for w in result.warnings:
                    output += f"- {w}\n"
            
            return output
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_list_undocumented":
        try:
            from .services.doc_service import DocumentationService
            
            hub_name = args.get("hub_name")
            
            service = DocumentationService()
            undocumented = service.list_undocumented(hub_name)
            
            if not undocumented:
                return f"""✅ **Alle Items in {hub_name} sind dokumentiert!**

Keine fehlenden Docstrings gefunden.
"""
            
            output = f"""## ⚠️ Undokumentierte Items in {hub_name}

{len(undocumented)} Items ohne Docstring gefunden:

"""
            for item in undocumented:
                output += f"- {item}\n"
            
            output += """
### 💡 Empfehlung

Füge Google-Style Docstrings hinzu:

```python
def my_function(param: str) -> dict:
    \"\"\"
    Kurze Beschreibung.
    
    Args:
        param: Beschreibung des Parameters.
        
    Returns:
        Beschreibung des Rückgabewerts.
    \"\"\"
```
"""
            return output
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    # =========================================================================
    # TEMPLATE ANALYSIS TOOLS
    # =========================================================================

    elif name == "bfagent_find_duplicate_templates":
        try:
            from .tools.template_analysis import find_duplicate_templates
            
            template_path = args.get("template_path")
            result = find_duplicate_templates(template_path)
            
            if template_path:
                if result.get("error"):
                    return f"❌ **Error:** {result['error']}"
                
                output = f"""## Template Analysis: `{template_path}`

**Status:** {'⚠️ DUPLIKAT' if result['is_duplicate'] else '✅ Einzigartig'}

**Aktives Template:** `{result['active_template']['source']}`
- Pfad: `{result['active_template']['path']}`
"""
                if result.get("warning"):
                    output += f"\n{result['warning']}\n"
                
                if result['is_duplicate']:
                    output += "\n**Alle Fundorte:**\n"
                    for loc in result['all_locations']:
                        marker = "✅" if loc['priority'] == 0 else "❌"
                        output += f"- {marker} {loc['source']}: `{loc['full_path']}`\n"
                
                return output
            else:
                output = f"""## Template Duplikat-Analyse

**Gesamt:** {result['total_templates']} Templates
**Duplikate:** {result['duplicate_count']}

{result['summary']}
"""
                if result['duplicates']:
                    output += "\n### Gefundene Duplikate:\n\n"
                    for path, info in list(result['duplicates'].items())[:15]:
                        output += f"**`{path}`**\n"
                        output += f"- ✅ Aktiv: {info['active']}\n"
                        output += f"- ❌ Ignoriert: {', '.join(info['ignored'])}\n\n"
                
                return output
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_cleanup_duplicate_templates":
        try:
            from .tools.template_analysis import cleanup_duplicate_templates
            
            dry_run = args.get("dry_run", True)
            keep_source = args.get("keep_source", "ROOT")
            
            result = cleanup_duplicate_templates(dry_run, keep_source)
            
            output = f"""## Template Cleanup

**Modus:** {'🔍 Dry-Run (Vorschau)' if dry_run else '🗑️ Echtes Löschen'}
**Behalte:** {keep_source}

{result['message']}

**Dateien:** {result['files_to_delete']}
"""
            if result.get('actions'):
                output += "\n### Aktionen:\n"
                for action in result['actions'][:20]:
                    output += f"- {action['action']}: `{action['file']}`\n"
            
            if result.get('backup_dir'):
                output += f"\n**Backup:** `{result['backup_dir']}`"
            
            if result.get('hint'):
                output += f"\n\n💡 {result['hint']}"
            
            return output
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_restore_template_backup":
        try:
            from .tools.template_analysis import restore_template_backup
            
            backup_dir = args.get("backup_dir")
            result = restore_template_backup(backup_dir)
            
            if result.get("error"):
                return f"❌ **Error:** {result['error']}"
            
            output = f"""## Template Restore

{result['message']}

**Wiederhergestellt:** {result['count']} Dateien
"""
            if result.get('restored'):
                output += "\n### Dateien:\n"
                for f in result['restored'][:20]:
                    output += f"- `{f}`\n"
            
            return output
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    # =========================================================================
    # DJANGO SHELL TOOLS
    # =========================================================================

    elif name == "bfagent_django_shell":
        try:
            from .tools.django_shell import django_shell_exec
            
            code = args.get("code")
            timeout = args.get("timeout", 30)
            
            result = django_shell_exec(code, timeout)
            
            if result["success"]:
                output = f"""## Django Shell Output

```
{result['output'] or '(keine Ausgabe)'}
```
"""
            else:
                output = f"""## ❌ Django Shell Error

**Fehler:** {result.get('errors', 'Unbekannt')}
**Return Code:** {result['return_code']}
"""
            return output
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_django_query":
        try:
            from .tools.django_shell import django_query
            
            model = args.get("model")
            action = args.get("action", "count")
            filter_kwargs = args.get("filter_kwargs")
            limit = args.get("limit", 10)
            
            result = django_query(model, action, filter_kwargs, limit)
            
            if result["success"]:
                model_name = model.rsplit(".", 1)[-1]
                output = f"""## {model_name}.{action}()

```
{result['output'] or '(keine Ergebnisse)'}
```
"""
            else:
                output = f"❌ **Error:** {result.get('errors', result.get('error', 'Unbekannt'))}"
            
            return output
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    # =========================================================================
    # SESSION TRACKING TOOLS
    # =========================================================================

    elif name == "bfagent_log_user_request":
        try:
            import os
            import sys
            import uuid
            
            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            if django_path not in sys.path:
                sys.path.insert(0, django_path)
            
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()
            
            from apps.bfagent.models_controlling import OrchestrationCall
            
            user_request = args.get("user_request", "")
            mode = args.get("mode", "default")
            context = args.get("context", "")
            
            # Create session with unique ID
            session_id = f"session-{uuid.uuid4().hex[:8]}"
            
            # Create OrchestrationCall with call_type='request'
            call = OrchestrationCall.objects.create(
                call_type='request',
                name=f"User Request ({mode})",
                description=_smart_truncate(user_request, 2000),
                status='running',
                session_id=session_id,
                metadata={
                    'mode': mode,
                    'context': context,
                    'user_request_full': user_request[:5000],
                },
            )
            
            return f"""## 📝 Session gestartet

**Session ID:** `{session_id}`
**Modus:** {mode}
**Request:** {_smart_truncate(user_request, 200)}

Alle folgenden Tool-Aufrufe werden dieser Session zugeordnet.
"""
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_log_session_end":
        try:
            import os
            import sys
            
            django_path = os.path.join(os.path.dirname(__file__), "../../../")
            if django_path not in sys.path:
                sys.path.insert(0, django_path)
            
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            import django
            django.setup()
            
            from apps.bfagent.models_controlling import OrchestrationCall
            from django.utils import timezone
            
            session_id = args.get("session_id")
            summary = args.get("summary", "")
            success = args.get("success", True)
            
            # Find and update session
            if session_id:
                try:
                    session = OrchestrationCall.objects.filter(
                        session_id=session_id,
                        call_type='request'
                    ).first()
                    if session:
                        session.status = 'success' if success else 'failed'
                        session.result_summary = summary[:500]
                        session.ended_at = timezone.now()
                        session.save()
                except Exception:
                    pass
            
            return f"""## ✅ Session beendet

**Summary:** {summary}
**Status:** {'Erfolgreich' if success else 'Fehlgeschlagen'}
"""
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    # =========================================================================
    # DOCUMENTATION MIGRATION TOOLS
    # =========================================================================

    elif name == "bfagent_docs_analyze_legacy":
        try:
            from .tools.docs_migration import analyze_legacy_docs, format_analysis_report
            
            legacy_path = args.get("legacy_path", "docs_legacy")
            include_subdirs = args.get("include_subdirs", True)
            
            analysis = analyze_legacy_docs(legacy_path, include_subdirs)
            return format_analysis_report(analysis)
            
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_docs_migrate_file":
        try:
            from .tools.docs_migration import migrate_file
            
            source = args.get("source")
            target = args.get("target")
            delete_source = args.get("delete_source", False)
            
            result = migrate_file(source, target, delete_source)
            
            if result.success:
                return f"""## ✅ Migration erfolgreich

**Quelle:** `{result.source}`
**Ziel:** `{result.target}`
**Aktion:** {result.message}
"""
            else:
                return f"""## ❌ Migration fehlgeschlagen

**Quelle:** `{result.source}`
**Ziel:** `{result.target}`
**Fehler:** {result.message}
"""
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    elif name == "bfagent_docs_check_duplicates":
        try:
            from .tools.docs_migration import check_duplicates
            
            legacy_path = args.get("legacy_path", "docs_legacy")
            sphinx_path = args.get("sphinx_path", "docs/source")
            
            duplicates = check_duplicates(legacy_path, sphinx_path)
            
            if not duplicates:
                return "## ✅ Keine Duplikate gefunden\n\nLegacy und Sphinx Docs haben keine überlappenden Dateien."
            
            lines = [f"## ⚠️ {len(duplicates)} Duplikate gefunden\n"]
            for legacy, sphinx in duplicates[:20]:
                lines.append(f"- `{Path(legacy).name}`")
                lines.append(f"  - Legacy: `{legacy}`")
                lines.append(f"  - Sphinx: `{sphinx}`")
            
            if len(duplicates) > 20:
                lines.append(f"\n... und {len(duplicates) - 20} weitere")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"❌ **Error:** {str(e)}"

    raise BFAgentMCPError(f"Unknown tool: {name}", code="UNKNOWN_TOOL")


def _format_generated_handler(result, input_data) -> str:
    output = f"""# Generated Handler: {result.metadata['handler_name']}

**Domain:** {result.metadata['domain']} | **Type:** {result.metadata['handler_type']}

## Handler Code

**File:** `apps/{input_data.domain}/handlers/{result.handler_filename}`

```python
{result.handler_code}
```

"""
    if result.test_code:
        output += f"""## Test Code

**File:** `apps/{input_data.domain}/tests/{result.test_filename}`

```python
{result.test_code}
```

"""
    output += """## Next Steps

1. Copy handler to `apps/{domain}/handlers/`
2. Register in `handlers/__init__.py`
3. Implement `process()` method
4. Run tests
"""
    return output


def _format_scaffold(result, input_data) -> str:
    output = f"""# Domain Scaffold: {input_data.display_name}

**ID:** `{input_data.domain_id}` | **Phases:** {' → '.join(input_data.phases)}

## Structure

```
{result.directory_structure}
```

## Files

"""
    for filename, content in result.files.items():
        output += f"### {filename}\n\n```python\n{content}\n```\n\n"

    output += f"""## Commands

```bash
mkdir -p apps/{input_data.domain_id}/handlers
python manage.py makemigrations {input_data.domain_id}
python manage.py migrate
```
"""
    return output


# =============================================================================
# RESOURCES
# =============================================================================


@mcp_server.list_resources()
async def list_resources() -> List[Resource]:
    return [Resource(uri="bfagent://domains", name="All Domains", mimeType="text/markdown")]


@mcp_server.list_resource_templates()
async def list_resource_templates() -> List[ResourceTemplate]:
    return [
        ResourceTemplate(
            uriTemplate="bfagent://handlers/{domain}",
            name="Domain Handlers",
            mimeType="text/markdown",
        ),
        ResourceTemplate(
            uriTemplate="bfagent://best-practices/{topic}",
            name="Best Practices",
            mimeType="text/markdown",
        ),
    ]


@mcp_server.read_resource()
async def read_resource(uri: str) -> str:
    factory = ServiceFactory.get_instance()

    if uri == "bfagent://domains":
        return await factory.get_domain_service().list_domains()
    elif uri.startswith("bfagent://handlers/"):
        domain_id = uri.replace("bfagent://handlers/", "")
        return await factory.get_domain_service().get_domain(domain_id)
    elif uri.startswith("bfagent://best-practices/"):
        topic = uri.replace("bfagent://best-practices/", "")
        return await factory.get_best_practice_service().get_best_practices(topic)

    raise ValueError(f"Unknown resource: {uri}")


# =============================================================================
# MAIN
# =============================================================================


async def run_server(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8765):
    setup_logging()
    logger.info(f"Starting BF Agent MCP Server v{get_server_settings().server_version}")

    if transport == "stdio":
        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.run(
                read_stream, write_stream, mcp_server.create_initialization_options()
            )
    else:
        raise NotImplementedError("HTTP transport coming soon")


def main():
    parser = argparse.ArgumentParser(description="BF Agent MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "--version", action="version", version=f"v{get_server_settings().server_version}"
    )

    args = parser.parse_args()

    if args.debug:
        import os

        os.environ["BFAGENT_LOG_LEVEL"] = "DEBUG"

    try:
        asyncio.run(run_server(args.transport, args.host, args.port))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
