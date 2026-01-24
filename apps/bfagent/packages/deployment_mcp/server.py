"""Deployment MCP Server - Infrastructure Management via Model Context Protocol."""

import asyncio
import logging
import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .tools import (
    # Hetzner Server Tools
    server_list,
    server_status,
    server_power,
    server_create,
    server_delete,
    server_rebuild,
    server_types_list,
    images_list,
    locations_list,
    # Firewall Tools
    firewall_list,
    firewall_get,
    firewall_create,
    firewall_delete,
    firewall_set_rules,
    firewall_apply,
    firewall_remove,
    # SSH Key Tools
    ssh_key_list,
    ssh_key_create,
    ssh_key_delete,
    # Docker Container Tools
    container_list,
    container_status,
    container_logs,
    container_restart,
    container_start,
    container_stop,
    # Docker Compose Tools
    compose_ps,
    compose_up,
    compose_down,
    compose_logs,
    compose_pull,
    compose_restart,
    # BF Agent Tools
    bfagent_deploy_web,
    # PostgreSQL Tools
    db_list,
    db_status,
    db_create,
    db_drop,
    db_query,
    db_backup,
    db_backup_list,
    db_restore,
    db_migrate,
    # Environment Tools
    env_list,
    env_get,
    env_set,
    env_delete,
    env_validate,
    # Secret Tools
    secret_list,
    secret_set,
    secret_delete,
    # SSL Tools
    ssl_status,
    ssl_expiring,
    ssl_renew,
    ssl_obtain,
    ssl_revoke,
    ssl_delete,
    ssl_certbot_info,
    # DNS Tools
    dns_zone_list,
    dns_zone_get,
    dns_zone_create,
    dns_zone_delete,
    dns_record_list,
    dns_record_get,
    dns_record_create,
    dns_record_update,
    dns_record_delete,
    dns_find_records,
    dns_set_a_record,
    dns_set_cname_record,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_tool_allowlist() -> set[str] | None:
    allow = os.environ.get("DEPLOYMENT_MCP_TOOL_ALLOWLIST", "").strip()
    if not allow:
        return None
    return {t.strip() for t in allow.split(",") if t.strip()}


# Tool registry with handlers
TOOL_HANDLERS: dict[str, Any] = {
    # Hetzner Server Tools
    "server_list": server_list,
    "server_status": server_status,
    "server_power": server_power,
    "server_create": server_create,
    "server_delete": server_delete,
    "server_rebuild": server_rebuild,
    "server_types_list": server_types_list,
    "images_list": images_list,
    "locations_list": locations_list,
    # Firewall Tools
    "firewall_list": firewall_list,
    "firewall_get": firewall_get,
    "firewall_create": firewall_create,
    "firewall_delete": firewall_delete,
    "firewall_set_rules": firewall_set_rules,
    "firewall_apply": firewall_apply,
    "firewall_remove": firewall_remove,
    # SSH Key Tools
    "ssh_key_list": ssh_key_list,
    "ssh_key_create": ssh_key_create,
    "ssh_key_delete": ssh_key_delete,
    # Docker Container Tools
    "container_list": container_list,
    "container_status": container_status,
    "container_logs": container_logs,
    "container_restart": container_restart,
    "container_start": container_start,
    "container_stop": container_stop,
    # Docker Compose Tools
    "compose_ps": compose_ps,
    "compose_up": compose_up,
    "compose_down": compose_down,
    "compose_logs": compose_logs,
    "compose_pull": compose_pull,
    "compose_restart": compose_restart,
    # BF Agent Tools
    "bfagent_deploy_web": bfagent_deploy_web,
    # PostgreSQL Tools
    "db_list": db_list,
    "db_status": db_status,
    "db_create": db_create,
    "db_drop": db_drop,
    "db_query": db_query,
    "db_backup": db_backup,
    "db_backup_list": db_backup_list,
    "db_restore": db_restore,
    "db_migrate": db_migrate,
    # Environment Tools
    "env_list": env_list,
    "env_get": env_get,
    "env_set": env_set,
    "env_delete": env_delete,
    "env_validate": env_validate,
    # Secret Tools
    "secret_list": secret_list,
    "secret_set": secret_set,
    "secret_delete": secret_delete,
    # SSL Tools
    "ssl_status": ssl_status,
    "ssl_expiring": ssl_expiring,
    "ssl_renew": ssl_renew,
    "ssl_obtain": ssl_obtain,
    "ssl_revoke": ssl_revoke,
    "ssl_delete": ssl_delete,
    "ssl_certbot_info": ssl_certbot_info,
    # DNS Zone Tools
    "dns_zone_list": dns_zone_list,
    "dns_zone_get": dns_zone_get,
    "dns_zone_create": dns_zone_create,
    "dns_zone_delete": dns_zone_delete,
    # DNS Record Tools
    "dns_record_list": dns_record_list,
    "dns_record_get": dns_record_get,
    "dns_record_create": dns_record_create,
    "dns_record_update": dns_record_update,
    "dns_record_delete": dns_record_delete,
    "dns_find_records": dns_find_records,
    "dns_set_a_record": dns_set_a_record,
    "dns_set_cname_record": dns_set_cname_record,
}


_ALLOWLIST = _get_tool_allowlist()
if _ALLOWLIST is not None:
    TOOL_HANDLERS = {name: handler for name, handler in TOOL_HANDLERS.items() if name in _ALLOWLIST}


def get_tool_definitions() -> list[Tool]:
    """Get all tool definitions."""
    tools: list[Tool] = [
        # =====================================================================
        # HETZNER SERVER TOOLS (Phase 1.1 + 3.1)
        # =====================================================================
        Tool(
            name="server_list",
            description="List all Hetzner Cloud servers",
            inputSchema={
                "type": "object",
                "properties": {
                    "label_selector": {"type": "string", "description": "Filter by labels"},
                },
            },
        ),
        Tool(
            name="server_status",
            description="Get server status by ID or name",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "integer"},
                    "name": {"type": "string"},
                },
            },
        ),
        Tool(
            name="server_power",
            description="Execute power action (poweron, poweroff, reboot, reset, shutdown)",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "integer"},
                    "action": {"type": "string", "enum": ["poweron", "poweroff", "reboot", "reset", "shutdown"]},
                },
                "required": ["server_id", "action"],
            },
        ),
        Tool(
            name="server_create",
            description="Create a new Hetzner server (requires confirm=true)",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Server name"},
                    "server_type": {"type": "string", "description": "Server type (cx22, cx32, etc.)"},
                    "image": {"type": "string", "description": "OS image (ubuntu-24.04, debian-12)"},
                    "location": {"type": "string", "description": "Datacenter (fsn1, nbg1, hel1)"},
                    "ssh_keys": {"type": "array", "items": {"type": "string"}, "description": "SSH key names"},
                    "labels": {"type": "object", "description": "Labels"},
                    "user_data": {"type": "string", "description": "Cloud-init user data"},
                    "confirm": {"type": "boolean", "description": "Must be true to execute"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="server_delete",
            description="Delete a Hetzner server (requires confirm=true)",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "integer"},
                    "confirm": {"type": "boolean"},
                },
                "required": ["server_id"],
            },
        ),
        Tool(
            name="server_rebuild",
            description="Rebuild server with new image (destroys data, requires confirm=true)",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "integer"},
                    "image": {"type": "string"},
                    "confirm": {"type": "boolean"},
                },
                "required": ["server_id", "image"],
            },
        ),
        Tool(
            name="server_types_list",
            description="List available Hetzner server types",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="images_list",
            description="List available OS images",
            inputSchema={
                "type": "object",
                "properties": {
                    "type_filter": {"type": "string", "description": "Filter by type (system, snapshot, backup)"},
                },
            },
        ),
        Tool(
            name="locations_list",
            description="List available datacenter locations",
            inputSchema={"type": "object", "properties": {}},
        ),
        # =====================================================================
        # FIREWALL TOOLS (Phase 3.1)
        # =====================================================================
        Tool(
            name="firewall_list",
            description="List all Hetzner firewalls",
            inputSchema={
                "type": "object",
                "properties": {
                    "label_selector": {"type": "string"},
                },
            },
        ),
        Tool(
            name="firewall_get",
            description="Get firewall details including rules",
            inputSchema={
                "type": "object",
                "properties": {
                    "firewall_id": {"type": "integer"},
                },
                "required": ["firewall_id"],
            },
        ),
        Tool(
            name="firewall_create",
            description="Create a new firewall with rules",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "rules": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "direction": {"type": "string", "enum": ["in", "out"]},
                                "protocol": {"type": "string", "enum": ["tcp", "udp", "icmp", "gre", "esp"]},
                                "port": {"type": "string"},
                                "source_ips": {"type": "array", "items": {"type": "string"}},
                                "destination_ips": {"type": "array", "items": {"type": "string"}},
                                "description": {"type": "string"},
                            },
                        },
                    },
                    "labels": {"type": "object"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="firewall_delete",
            description="Delete a firewall (requires confirm=true)",
            inputSchema={
                "type": "object",
                "properties": {
                    "firewall_id": {"type": "integer"},
                    "confirm": {"type": "boolean"},
                },
                "required": ["firewall_id"],
            },
        ),
        Tool(
            name="firewall_set_rules",
            description="Set firewall rules (replaces all existing)",
            inputSchema={
                "type": "object",
                "properties": {
                    "firewall_id": {"type": "integer"},
                    "rules": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["firewall_id", "rules"],
            },
        ),
        Tool(
            name="firewall_apply",
            description="Apply firewall to servers",
            inputSchema={
                "type": "object",
                "properties": {
                    "firewall_id": {"type": "integer"},
                    "server_ids": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["firewall_id", "server_ids"],
            },
        ),
        Tool(
            name="firewall_remove",
            description="Remove firewall from servers",
            inputSchema={
                "type": "object",
                "properties": {
                    "firewall_id": {"type": "integer"},
                    "server_ids": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["firewall_id", "server_ids"],
            },
        ),
        # =====================================================================
        # SSH KEY TOOLS (Phase 3.1)
        # =====================================================================
        Tool(
            name="ssh_key_list",
            description="List all SSH keys in Hetzner",
            inputSchema={
                "type": "object",
                "properties": {
                    "label_selector": {"type": "string"},
                },
            },
        ),
        Tool(
            name="ssh_key_create",
            description="Create a new SSH key",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "public_key": {"type": "string"},
                    "labels": {"type": "object"},
                },
                "required": ["name", "public_key"],
            },
        ),
        Tool(
            name="ssh_key_delete",
            description="Delete an SSH key (requires confirm=true)",
            inputSchema={
                "type": "object",
                "properties": {
                    "key_id": {"type": "integer"},
                    "confirm": {"type": "boolean"},
                },
                "required": ["key_id"],
            },
        ),
        # =====================================================================
        # DOCKER CONTAINER TOOLS (Phase 1.2)
        # =====================================================================
        Tool(
            name="container_list",
            description="List Docker containers",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "all_containers": {"type": "boolean"},
                },
            },
        ),
        Tool(
            name="container_status",
            description="Get container status and stats",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {"type": "string"},
                    "host": {"type": "string"},
                },
                "required": ["container_id"],
            },
        ),
        Tool(
            name="container_logs",
            description="Get container logs",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {"type": "string"},
                    "host": {"type": "string"},
                    "lines": {"type": "integer", "default": 100},
                    "since": {"type": "string"},
                },
                "required": ["container_id"],
            },
        ),
        Tool(
            name="container_restart",
            description="Restart a container",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {"type": "string"},
                    "host": {"type": "string"},
                },
                "required": ["container_id"],
            },
        ),
        Tool(
            name="container_start",
            description="Start a container",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {"type": "string"},
                    "host": {"type": "string"},
                },
                "required": ["container_id"],
            },
        ),
        Tool(
            name="container_stop",
            description="Stop a container",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {"type": "string"},
                    "host": {"type": "string"},
                    "timeout": {"type": "integer", "default": 10},
                },
                "required": ["container_id"],
            },
        ),
        # =====================================================================
        # DOCKER COMPOSE TOOLS (Phase 2.1)
        # =====================================================================
        Tool(
            name="compose_ps",
            description="List compose services",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "project_path": {"type": "string"},
                },
            },
        ),
        Tool(
            name="compose_up",
            description="Start compose services",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "project_path": {"type": "string"},
                    "build": {"type": "boolean"},
                    "services": {"type": "array", "items": {"type": "string"}},
                },
            },
        ),
        Tool(
            name="compose_down",
            description="Stop compose services",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "project_path": {"type": "string"},
                    "volumes": {"type": "boolean"},
                    "remove_orphans": {"type": "boolean"},
                    "confirm": {"type": "boolean"},
                },
            },
        ),
        Tool(
            name="compose_logs",
            description="Get compose logs",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "project_path": {"type": "string"},
                    "service": {"type": "string"},
                    "lines": {"type": "integer", "default": 100},
                },
            },
        ),
        Tool(
            name="compose_pull",
            description="Pull compose images",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "project_path": {"type": "string"},
                    "services": {"type": "array", "items": {"type": "string"}},
                },
            },
        ),
        Tool(
            name="compose_restart",
            description="Restart compose services",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "project_path": {"type": "string"},
                    "services": {"type": "array", "items": {"type": "string"}},
                },
            },
        ),
        # =====================================================================
        # BF AGENT TOOLS
        # =====================================================================
        Tool(
            name="bfagent_deploy_web",
            description="Deploy bfagent-web on a remote host via SSH using docker compose (set image tag in .env, pull, up, and verify via HTTP)",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_tag": {"type": "string", "description": "Image tag (prefer full git SHA)"},
                    "host": {"type": "string", "description": "Override SSH host"},
                    "project_dir": {"type": "string", "default": "/opt/bfagent-app"},
                    "compose_file": {"type": "string", "default": "docker-compose.prod.yml"},
                    "env_file": {"type": "string", "default": ".env.prod"},
                    "service": {"type": "string", "default": "bfagent-web"},
                    "image_repo": {"type": "string", "default": "ghcr.io/achimdehnert/bfagent/bfagent-web"},
                    "verify_url": {"type": "string", "default": "https://bfagent.iil.pet/login/"},
                    "expect_http_status": {"type": "integer", "default": 200},
                    "pull": {"type": "boolean", "default": True},
                    "recreate": {"type": "boolean", "default": True},
                },
                "required": ["image_tag"],
            },
        ),
        # =====================================================================
        # POSTGRESQL TOOLS (Phase 1.3 + 2.2)
        # =====================================================================
        Tool(
            name="db_list",
            description="List all PostgreSQL databases",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                },
            },
        ),
        Tool(
            name="db_status",
            description="Get PostgreSQL server status",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                },
            },
        ),
        Tool(
            name="db_create",
            description="Create a new database",
            inputSchema={
                "type": "object",
                "properties": {
                    "db_name": {"type": "string"},
                    "host": {"type": "string"},
                    "owner": {"type": "string"},
                    "encoding": {"type": "string", "default": "UTF8"},
                },
                "required": ["db_name"],
            },
        ),
        Tool(
            name="db_drop",
            description="Drop a database (requires confirm=true)",
            inputSchema={
                "type": "object",
                "properties": {
                    "db_name": {"type": "string"},
                    "host": {"type": "string"},
                    "force": {"type": "boolean"},
                    "confirm": {"type": "boolean"},
                },
                "required": ["db_name"],
            },
        ),
        Tool(
            name="db_query",
            description="Execute SQL query (read-only recommended)",
            inputSchema={
                "type": "object",
                "properties": {
                    "db_name": {"type": "string"},
                    "sql": {"type": "string"},
                    "host": {"type": "string"},
                },
                "required": ["db_name", "sql"],
            },
        ),
        Tool(
            name="db_backup",
            description="Create database backup",
            inputSchema={
                "type": "object",
                "properties": {
                    "db_name": {"type": "string"},
                    "host": {"type": "string"},
                    "backup_path": {"type": "string"},
                    "format_type": {"type": "string", "enum": ["custom", "plain", "tar"]},
                },
                "required": ["db_name"],
            },
        ),
        Tool(
            name="db_backup_list",
            description="List available database backups",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "backup_path": {"type": "string"},
                },
            },
        ),
        Tool(
            name="db_restore",
            description="Restore database from backup (requires confirm=true)",
            inputSchema={
                "type": "object",
                "properties": {
                    "db_name": {"type": "string"},
                    "backup_file": {"type": "string"},
                    "host": {"type": "string"},
                    "create_db": {"type": "boolean", "default": True},
                    "confirm": {"type": "boolean"},
                },
                "required": ["db_name", "backup_file"],
            },
        ),
        Tool(
            name="db_migrate",
            description="Run database migrations",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                    "host": {"type": "string"},
                    "command": {"type": "string", "default": "alembic upgrade head"},
                },
                "required": ["project_path"],
            },
        ),
        # =====================================================================
        # ENVIRONMENT TOOLS (Phase 2.3)
        # =====================================================================
        Tool(
            name="env_list",
            description="List environment variables from .env file",
            inputSchema={
                "type": "object",
                "properties": {
                    "env_file": {"type": "string"},
                    "host": {"type": "string"},
                    "mask_sensitive": {"type": "boolean", "default": True},
                },
                "required": ["env_file"],
            },
        ),
        Tool(
            name="env_get",
            description="Get specific environment variable",
            inputSchema={
                "type": "object",
                "properties": {
                    "env_file": {"type": "string"},
                    "key": {"type": "string"},
                    "host": {"type": "string"},
                    "mask_sensitive": {"type": "boolean", "default": True},
                },
                "required": ["env_file", "key"],
            },
        ),
        Tool(
            name="env_set",
            description="Set environment variable",
            inputSchema={
                "type": "object",
                "properties": {
                    "env_file": {"type": "string"},
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                    "host": {"type": "string"},
                },
                "required": ["env_file", "key", "value"],
            },
        ),
        Tool(
            name="env_delete",
            description="Delete environment variable (requires confirm=true)",
            inputSchema={
                "type": "object",
                "properties": {
                    "env_file": {"type": "string"},
                    "key": {"type": "string"},
                    "host": {"type": "string"},
                    "confirm": {"type": "boolean"},
                },
                "required": ["env_file", "key"],
            },
        ),
        Tool(
            name="env_validate",
            description="Validate required environment variables",
            inputSchema={
                "type": "object",
                "properties": {
                    "env_file": {"type": "string"},
                    "required_keys": {"type": "array", "items": {"type": "string"}},
                    "host": {"type": "string"},
                },
                "required": ["env_file", "required_keys"],
            },
        ),
        # =====================================================================
        # SECRET TOOLS (Phase 2.3)
        # =====================================================================
        Tool(
            name="secret_list",
            description="List secrets (sensitive env vars) without values",
            inputSchema={
                "type": "object",
                "properties": {
                    "env_file": {"type": "string"},
                    "host": {"type": "string"},
                },
                "required": ["env_file"],
            },
        ),
        Tool(
            name="secret_set",
            description="Set a secret (sensitive env var)",
            inputSchema={
                "type": "object",
                "properties": {
                    "env_file": {"type": "string"},
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                    "host": {"type": "string"},
                },
                "required": ["env_file", "key", "value"],
            },
        ),
        Tool(
            name="secret_delete",
            description="Delete a secret (requires confirm=true)",
            inputSchema={
                "type": "object",
                "properties": {
                    "env_file": {"type": "string"},
                    "key": {"type": "string"},
                    "host": {"type": "string"},
                    "confirm": {"type": "boolean"},
                },
                "required": ["env_file", "key"],
            },
        ),
        # =====================================================================
        # SSL TOOLS (Phase 3.2)
        # =====================================================================
        Tool(
            name="ssl_status",
            description="Get SSL certificate status for a domain or list all certificates",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domain to check (optional)"},
                    "host": {"type": "string"},
                },
            },
        ),
        Tool(
            name="ssl_expiring",
            description="Get certificates expiring within specified days",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "default": 30},
                    "host": {"type": "string"},
                },
            },
        ),
        Tool(
            name="ssl_renew",
            description="Renew SSL certificate using certbot (requires confirm=true)",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Specific domain (optional)"},
                    "force": {"type": "boolean", "description": "Force renewal"},
                    "host": {"type": "string"},
                    "confirm": {"type": "boolean"},
                },
            },
        ),
        Tool(
            name="ssl_obtain",
            description="Obtain a new SSL certificate (requires confirm=true)",
            inputSchema={
                "type": "object",
                "properties": {
                    "domains": {"type": "array", "items": {"type": "string"}},
                    "email": {"type": "string"},
                    "webroot_path": {"type": "string"},
                    "standalone": {"type": "boolean"},
                    "dry_run": {"type": "boolean"},
                    "host": {"type": "string"},
                    "confirm": {"type": "boolean"},
                },
                "required": ["domains", "email"],
            },
        ),
        Tool(
            name="ssl_revoke",
            description="Revoke an SSL certificate (requires confirm=true)",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "reason": {"type": "string", "default": "unspecified"},
                    "host": {"type": "string"},
                    "confirm": {"type": "boolean"},
                },
                "required": ["domain"],
            },
        ),
        Tool(
            name="ssl_delete",
            description="Delete a certificate from certbot (requires confirm=true)",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "host": {"type": "string"},
                    "confirm": {"type": "boolean"},
                },
                "required": ["domain"],
            },
        ),
        Tool(
            name="ssl_certbot_info",
            description="Get certbot installation info and certificate list",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                },
            },
        ),
        # =====================================================================
        # DNS ZONE TOOLS (Phase 3.2)
        # =====================================================================
        Tool(
            name="dns_zone_list",
            description="List all DNS zones (Hetzner DNS)",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="dns_zone_get",
            description="Get DNS zone details",
            inputSchema={
                "type": "object",
                "properties": {
                    "zone_id": {"type": "string"},
                    "name": {"type": "string", "description": "Domain name"},
                },
            },
        ),
        Tool(
            name="dns_zone_create",
            description="Create a new DNS zone (requires confirm=true)",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Domain name"},
                    "ttl": {"type": "integer", "default": 3600},
                    "confirm": {"type": "boolean"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="dns_zone_delete",
            description="Delete a DNS zone (requires confirm=true)",
            inputSchema={
                "type": "object",
                "properties": {
                    "zone_id": {"type": "string"},
                    "confirm": {"type": "boolean"},
                },
                "required": ["zone_id"],
            },
        ),
        # =====================================================================
        # DNS RECORD TOOLS (Phase 3.2)
        # =====================================================================
        Tool(
            name="dns_record_list",
            description="List DNS records in a zone",
            inputSchema={
                "type": "object",
                "properties": {
                    "zone_id": {"type": "string"},
                    "domain": {"type": "string", "description": "Domain name (alternative)"},
                },
            },
        ),
        Tool(
            name="dns_record_get",
            description="Get DNS record details",
            inputSchema={
                "type": "object",
                "properties": {
                    "record_id": {"type": "string"},
                },
                "required": ["record_id"],
            },
        ),
        Tool(
            name="dns_record_create",
            description="Create a new DNS record",
            inputSchema={
                "type": "object",
                "properties": {
                    "zone_id": {"type": "string"},
                    "domain": {"type": "string"},
                    "name": {"type": "string", "default": "@"},
                    "type": {"type": "string", "enum": ["A", "AAAA", "CNAME", "MX", "TXT", "NS", "SRV"]},
                    "value": {"type": "string"},
                    "ttl": {"type": "integer", "default": 3600},
                },
                "required": ["value"],
            },
        ),
        Tool(
            name="dns_record_update",
            description="Update a DNS record",
            inputSchema={
                "type": "object",
                "properties": {
                    "record_id": {"type": "string"},
                    "zone_id": {"type": "string"},
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "value": {"type": "string"},
                    "ttl": {"type": "integer", "default": 3600},
                },
                "required": ["record_id", "zone_id", "name", "type", "value"],
            },
        ),
        Tool(
            name="dns_record_delete",
            description="Delete a DNS record (requires confirm=true)",
            inputSchema={
                "type": "object",
                "properties": {
                    "record_id": {"type": "string"},
                    "confirm": {"type": "boolean"},
                },
                "required": ["record_id"],
            },
        ),
        Tool(
            name="dns_find_records",
            description="Find DNS records by name and/or type",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "name": {"type": "string"},
                    "record_type": {"type": "string"},
                },
                "required": ["domain"],
            },
        ),
        Tool(
            name="dns_set_a_record",
            description="Set an A record (create or update)",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "subdomain": {"type": "string"},
                    "ip": {"type": "string"},
                    "ttl": {"type": "integer", "default": 3600},
                },
                "required": ["domain", "subdomain", "ip"],
            },
        ),
        Tool(
            name="dns_set_cname_record",
            description="Set a CNAME record (create or update)",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "subdomain": {"type": "string"},
                    "value": {"type": "string"},
                    "ttl": {"type": "integer", "default": 3600},
                },
                "required": ["domain", "subdomain", "value"],
            },
        ),
    ]

    if _ALLOWLIST is None:
        return tools

    return [t for t in tools if t.name in _ALLOWLIST]


async def handle_tool_call(name: str, arguments: dict[str, Any]) -> str:
    """Handle tool call and return result."""
    import json

    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return json.dumps({"success": False, "error": f"Unknown tool: {name}"})

    try:
        result = await handler(**arguments)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        logger.exception(f"Tool error: {name}")
        return json.dumps({"success": False, "error": str(e)})


async def run_server() -> None:
    """Run the MCP server."""
    server = Server("deployment-mcp")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return get_tool_definitions()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        result = await handle_tool_call(name, arguments)
        return [TextContent(type="text", text=result)]

    logger.info("Starting Deployment MCP Server with %d tools", len(TOOL_HANDLERS))

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    """Main entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
