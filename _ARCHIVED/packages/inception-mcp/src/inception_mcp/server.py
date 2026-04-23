"""
Inception MCP Server
====================

Main MCP server for DDL Business Case creation.
Tools for starting, refining, and finalizing Business Cases.
"""

import asyncio
import logging
import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from pydantic import AnyUrl

from .tools import (
    start_business_case,
    answer_question,
    finalize_business_case,
    list_business_cases,
    get_business_case,
    get_categories,
    submit_for_review,
    get_session_status,
)
from .db import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inception-mcp")

# Create MCP server instance
server = Server("inception-mcp")


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

TOOLS = [
    Tool(
        name="start_business_case",
        description="""Start a new Business Case from a free-text description.
        
Analyzes the initial description, creates a draft BC in the database,
and returns the first clarifying question.

Returns: session_id, bc_code, question, questions_remaining""",
        inputSchema={
            "type": "object",
            "properties": {
                "initial_description": {
                    "type": "string",
                    "description": "Free-text description of the business need or feature request",
                },
                "category": {
                    "type": "string",
                    "description": "Optional category code (feature, enhancement, bugfix, etc.)",
                },
            },
            "required": ["initial_description"],
        },
    ),
    Tool(
        name="answer_question",
        description="""Answer a clarifying question in an active inception session.
        
Extracts data from the answer, updates the BC draft,
and returns the next question or a summary if complete.

Returns: question OR summary + ready_for_finalization""",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID from start_business_case",
                },
                "answer": {
                    "type": "string",
                    "description": "The user's answer to the current question",
                },
            },
            "required": ["session_id", "answer"],
        },
    ),
    Tool(
        name="finalize_business_case",
        description="""Finalize a Business Case after all questions are answered.
        
Validates the BC, sets status to 'submitted', and optionally derives Use Cases.

Returns: bc_code, derived_use_cases[], next_steps[]""",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID from start_business_case",
                },
                "adjustments": {
                    "type": "object",
                    "description": "Optional final adjustments to BC fields",
                },
                "derive_use_cases": {
                    "type": "boolean",
                    "description": "Whether to auto-derive Use Cases (default: true)",
                    "default": True,
                },
            },
            "required": ["session_id"],
        },
    ),
    Tool(
        name="list_business_cases",
        description="""List Business Cases with optional filters.

Returns: Array of BC summaries with code, title, status, category, priority""",
        inputSchema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status code (draft, submitted, approved, etc.)",
                },
                "category": {
                    "type": "string",
                    "description": "Filter by category code",
                },
                "search": {
                    "type": "string",
                    "description": "Search in title and problem_statement",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default: 20)",
                    "default": 20,
                },
            },
        },
    ),
    Tool(
        name="get_business_case",
        description="""Get full details of a specific Business Case.

Returns: Complete BC with all fields, related Use Cases, and status history""",
        inputSchema={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Business Case code (e.g., 'BC-042')",
                },
            },
            "required": ["code"],
        },
    ),
    Tool(
        name="get_categories",
        description="""Get all available Business Case categories.

Returns: Array of category choices with code, name, color, icon""",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="submit_for_review",
        description="""Submit a Business Case for review.

Changes status from 'draft' to 'submitted'.

Returns: success, new_status, message""",
        inputSchema={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Business Case code to submit",
                },
            },
            "required": ["code"],
        },
    ),
    Tool(
        name="get_session_status",
        description="""Get the current status of an inception session.

Returns: session state, current question, BC draft summary""",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID to check",
                },
            },
            "required": ["session_id"],
        },
    ),
]


# =============================================================================
# HANDLERS
# =============================================================================

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Return list of available tools."""
    return TOOLS


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    """Handle tool calls."""
    arguments = arguments or {}
    
    try:
        if name == "start_business_case":
            result = await start_business_case(
                initial_description=arguments["initial_description"],
                category=arguments.get("category"),
            )
        elif name == "answer_question":
            result = await answer_question(
                session_id=arguments["session_id"],
                answer=arguments["answer"],
            )
        elif name == "finalize_business_case":
            result = await finalize_business_case(
                session_id=arguments["session_id"],
                adjustments=arguments.get("adjustments"),
                derive_use_cases=arguments.get("derive_use_cases", True),
            )
        elif name == "list_business_cases":
            result = await list_business_cases(
                status=arguments.get("status"),
                category=arguments.get("category"),
                search=arguments.get("search"),
                limit=arguments.get("limit", 20),
            )
        elif name == "get_business_case":
            result = await get_business_case(code=arguments["code"])
        elif name == "get_categories":
            result = await get_categories()
        elif name == "submit_for_review":
            result = await submit_for_review(code=arguments["code"])
        elif name == "get_session_status":
            result = await get_session_status(session_id=arguments["session_id"])
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        
        return [TextContent(type="text", text=str(result))]
        
    except Exception as e:
        logger.exception(f"Error in tool {name}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run the MCP server."""
    logger.info("Starting Inception MCP Server...")
    asyncio.run(run_server())


async def run_server():
    """Async server runner."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    main()
