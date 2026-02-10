"""
FastMCP Registration Helper
============================

Brücke zwischen ConsolidatedTool und FastMCP.
Registriert konsolidierte Tools automatisch als MCP Tools.

Usage:
    from fastmcp import FastMCP
    from tool_consolidation.fastmcp_bridge import register_consolidated_tools
    from tool_consolidation.hetzner_server import HetznerServerTool
    
    mcp = FastMCP("deployment")
    
    register_consolidated_tools(mcp, [
        HetznerServerTool(client),
        DockerTool(ssh_client),
        DatabaseTool(ssh_client),
    ])
    # → Registriert: server_manage, docker_manage, database_manage

Author: BF Agent Team
"""

from __future__ import annotations

import logging
from typing import Any

from .base import ConsolidatedTool

logger = logging.getLogger(__name__)


def register_consolidated_tools(
    mcp,  # FastMCP instance (no type hint to avoid import dependency)
    tools: list[ConsolidatedTool],
) -> dict[str, ConsolidatedTool]:
    """Registriere mehrere ConsolidatedTools bei FastMCP.
    
    Args:
        mcp: FastMCP Server-Instanz
        tools: Liste von ConsolidatedTool-Instanzen
        
    Returns:
        Dict von tool_name → tool_instance (für Referenz)
    
    Example:
        registry = register_consolidated_tools(mcp, [
            HetznerServerTool(hetzner_client),
            DockerTool(ssh_client),
        ])
    """
    registry = {}

    for tool in tools:
        _register_single(mcp, tool)
        registry[tool.tool_name] = tool
        logger.info(
            f"✅ Registered consolidated tool: {tool.tool_name} "
            f"({len(tool.available_actions)} actions: {', '.join(tool.available_actions)})"
        )

    logger.info(
        f"📊 Tool consolidation: {sum(len(t.available_actions) for t in tools)} actions "
        f"→ {len(tools)} MCP tools"
    )

    return registry


def _register_single(mcp, tool: ConsolidatedTool) -> None:
    """Registriere ein einzelnes ConsolidatedTool bei FastMCP.
    
    Erzeugt eine Tool-Funktion die FastMCP versteht,
    mit dem generierten Input-Schema und der Action-Beschreibung.
    """
    tool_name = tool.tool_name
    description = tool.get_tool_description()
    input_schema = tool.build_input_schema()

    # MCP Annotations basierend auf Actions
    has_readonly_only = all(
        meta.read_only for meta in tool._actions.values()
    )
    has_destructive = any(
        meta.destructive for meta in tool._actions.values()
    )

    # Erstelle die Tool-Handler-Funktion
    async def handler(arguments: dict[str, Any] = {}) -> str:
        return await tool.dispatch(arguments)

    # Setze Name und Docstring für FastMCP
    handler.__name__ = tool_name
    handler.__doc__ = description

    # Registriere bei FastMCP via low-level API
    # FastMCP v2.x: mcp.tool() decorator oder mcp._tool_manager.add_tool()
    # Wir nutzen die einfachste Variante:
    mcp.tool(
        name=tool_name,
        description=description,
    )(handler)


def register_with_raw_mcp(
    server,  # mcp.server.Server instance
    tools: list[ConsolidatedTool],
) -> dict[str, ConsolidatedTool]:
    """Alternative: Registriere bei raw MCP SDK (ohne FastMCP).
    
    Für Server die direkt mcp.server.Server nutzen (wie dein book_writing_mcp).
    
    Args:
        server: mcp.server.Server Instanz
        tools: Liste von ConsolidatedTool-Instanzen
    """
    from mcp.types import Tool

    registry = {}
    all_mcp_tools = []

    for tool in tools:
        mcp_tool = Tool(
            name=tool.tool_name,
            description=tool.get_tool_description(),
            inputSchema=tool.build_input_schema(),
        )
        all_mcp_tools.append(mcp_tool)
        registry[tool.tool_name] = tool

    # Registriere list_tools Handler
    @server.list_tools()
    async def list_tools():
        return all_mcp_tools

    # Registriere call_tool Dispatcher
    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]):
        from mcp.types import CallToolResult, TextContent

        if name in registry:
            result = await registry[name].dispatch(arguments)
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )
        return CallToolResult(
            content=[TextContent(type="text", text=f"❌ Unknown tool: {name}")],
            isError=True,
        )

    return registry
