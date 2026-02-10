"""
Tool Consolidation Pattern for MCP Servers
==========================================

Wiederverwendbares Dispatch-Pattern um viele MCP Tools
auf wenige konsolidierte Meta-Tools zu reduzieren.

Motivation:
- Windsurf: ~100 Tool Limit
- Cursor: 40 Tool Hard-Limit
- Claude Code: Context-Window-Verbrauch (~700 Tokens/Tool)
- LLMs funktionieren besser mit 10-20 Tools als mit 50+

Pattern:
    VORHER:  server_list, server_create, server_delete, server_power, ...  (8 Tools)
    NACHHER: server_manage(action="list|create|delete|power", ...)         (1 Tool)

Author: BF Agent Team
"""

__version__ = "0.1.0"
