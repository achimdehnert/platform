"""
Usage Example: deployment_mcp mit Tool Consolidation
=====================================================

Zeigt wie der deployment_mcp Server von ~77 Tools auf ~9 reduziert wird.

VORHER (77 Tools in Windsurf):
    server_list, server_status, server_power, server_create, server_delete, ...
    container_list, container_logs, compose_up, compose_down, ...
    db_status, db_backup, db_restore, db_migrate, ...
    ssl_check, ssl_renew, dns_list, dns_update, ...
    monitor_status, alert_list, alert_create, ...
    ... (77 total)

NACHHER (9 Tools in Windsurf):
    server_manage     → 8 actions (list, status, power, create, delete, ...)
    docker_manage     → 8 actions (container_list, logs, compose_up, ...)
    database_manage   → 8 actions (status, backup, restore, migrate, ...)
    ssl_manage        → 4 actions (check, renew, list, create)
    dns_manage        → 4 actions (list, create, update, delete)
    monitor_manage    → 5 actions (status, metrics, health, configure, ...)
    alert_manage      → 5 actions (list, create, delete, acknowledge, ...)
    firewall_manage   → 5 actions (list, create, update, delete, apply)
    env_manage        → 4 actions (list, set, delete, export)
    ─────────────────────────────────────────────────────────────
    TOTAL:  9 MCP Tools  statt  77  →  Reduktion: 88%!

Author: BF Agent Team
"""

from contextlib import asynccontextmanager
from typing import Any

# In der echten Implementierung:
# from mcp.server.fastmcp import FastMCP
# from deployment_mcp.clients.hetzner import HetznerClient
# from deployment_mcp.clients.ssh import SSHClient
# from tool_consolidation.fastmcp_bridge import register_consolidated_tools
# from tool_consolidation.hetzner_server import HetznerServerTool

# ─── Für Demo: Mock-Imports ─────────────────────────────────────────────

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from tool_consolidation.hetzner_server import HetznerServerTool


# =============================================================================
# So würde dein deployment_mcp/server.py aussehen:
# =============================================================================

"""
# deployment_mcp/server.py (Refactored)

from mcp.server.fastmcp import FastMCP
from tool_consolidation.fastmcp_bridge import register_consolidated_tools
from tool_consolidation.hetzner_server import HetznerServerTool
# from .docker_tool import DockerTool        # Phase 2
# from .database_tool import DatabaseTool    # Phase 2
# from .ssl_tool import SSLTool             # Phase 3
# from .dns_tool import DNSTool             # Phase 3
# ...

@asynccontextmanager
async def lifespan(server):
    hetzner_client = HetznerClient()
    ssh_client = SSHClient()
    
    # Registriere konsolidierte Tools
    register_consolidated_tools(server, [
        HetznerServerTool(hetzner_client),        # 8 actions → 1 tool
        # DockerTool(ssh_client),                  # 8 actions → 1 tool
        # DatabaseTool(ssh_client),                # 8 actions → 1 tool
        # SSLTool(hetzner_client),                 # 4 actions → 1 tool
        # DNSTool(hetzner_client),                 # 4 actions → 1 tool
        # MonitorTool(ssh_client),                 # 5 actions → 1 tool
        # AlertTool(ssh_client),                   # 5 actions → 1 tool
        # FirewallTool(hetzner_client),            # 5 actions → 1 tool
        # EnvTool(ssh_client),                     # 4 actions → 1 tool
    ])
    
    yield

mcp = FastMCP(
    name="deployment-mcp",
    instructions="Infrastructure management. Use *_manage tools with action parameter.",
    lifespan=lifespan,
)
"""


# =============================================================================
# Demo: Schema-Output für Windsurf
# =============================================================================

def demo_schema_output():
    """Zeigt was Windsurf/Cursor sieht."""
    tool = HetznerServerTool()

    print("=" * 70)
    print("📊 TOOL CONSOLIDATION DEMO")
    print("=" * 70)
    print()
    print(f"Tool Name:    {tool.tool_name}")
    print(f"Actions:      {len(tool.available_actions)}")
    print(f"MCP Tools:    1  (statt {len(tool.available_actions)})")
    print()
    print("─── Tool Description (was das LLM sieht) ───")
    print()
    print(tool.get_tool_description())
    print()
    print("─── Input Schema (JSON Schema) ───")
    print()
    import json
    schema = tool.build_input_schema()
    print(json.dumps(schema, indent=2))
    print()
    print("─── Beispiel LLM-Aufrufe ───")
    print()
    examples = [
        {"action": "list"},
        {"action": "list", "status_filter": "running"},
        {"action": "status", "server_name": "web-prod-1"},
        {"action": "create", "server_name": "api-02", "server_type": "cx32"},
        {"action": "power", "server_name": "web-prod-1", "power_action": "reboot"},
        {"action": "delete", "server_name": "test-01", "confirm": True},
    ]
    for ex in examples:
        print(f"  server_manage({ex})")
    print()
    print("=" * 70)
    print("✅ 8 Server-Operationen → 1 MCP Tool")
    print("   Hochgerechnet: ~77 Tools → ~9 Tools (88% Reduktion)")
    print("=" * 70)


if __name__ == "__main__":
    demo_schema_output()
