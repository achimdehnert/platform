"""
CAD-Hub MCP Server.

Model Context Protocol Server für CAD-Funktionen via WSL.
"""

from cad_services.mcp.server import create_server, main


__all__ = ["create_server", "main"]
