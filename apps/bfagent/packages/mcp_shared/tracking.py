"""
MCP Usage Tracking
==================

Zentrale Tracking-Funktion für ALLE MCP Server.
Loggt jeden Tool-Call in die MCPUsageLog Tabelle.
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("mcp_shared.tracking")


def _setup_django():
    """Setup Django if not already done."""
    project_root = os.environ.get("BFAGENT_PROJECT_ROOT", "/home/dehnert/github/bfagent")
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    
    import django
    if not django.apps.apps.ready:
        django.setup()


def _smart_truncate(text: str, max_length: int = 500) -> str:
    """Truncate text smartly."""
    if not text or len(text) <= max_length:
        return text or ""
    return text[:max_length - 3] + "..."


def _categorize_tool(tool_name: str) -> str:
    """Categorize tool by name prefix."""
    prefixes = {
        'bfagent_': 'bfagent',
        'db_': 'database',
        'analyze_': 'code_quality',
        'check_': 'code_quality',
        'list_': 'code_quality',
        'suggest_': 'code_quality',
        'validate_': 'code_quality',
        'generate_': 'test_generator',
        'run_': 'test_generator',
        'get_': 'general',
        'server_': 'deployment',
        'firewall_': 'deployment',
        'container_': 'deployment',
        'compose_': 'deployment',
        'ssl_': 'deployment',
        'dns_': 'deployment',
        'env_': 'deployment',
        'secret_': 'deployment',
    }
    
    for prefix, category in prefixes.items():
        if tool_name.startswith(prefix):
            return category
    
    return 'general'


def log_mcp_call_sync(
    tool_name: str,
    server_name: str,
    arguments: Dict[str, Any],
    result: str = "",
    status: str = "success",
    error_message: str = "",
    duration_ms: int = 0,
    session_id: str = ""
):
    """
    Synchrones Logging eines MCP Tool Calls.
    
    Verwendet MCPUsageLog für einheitliches Tracking über alle MCP Server.
    """
    try:
        _setup_django()
        
        from apps.bfagent.models_testing import MCPUsageLog
        from django.utils import timezone
        
        # Determine category
        category = _categorize_tool(tool_name)
        
        # Create log entry
        MCPUsageLog.objects.create(
            tool_name=f"{server_name}:{tool_name}",
            tool_category=category,
            arguments={k: str(v)[:200] for k, v in arguments.items()} if arguments else {},
            result_summary=_smart_truncate(result, 500),
            status=status,
            error_message=error_message[:1000] if error_message else "",
            session_id=session_id or f"mcp-{timezone.now():%Y%m%d-%H%M%S}",
            duration_ms=duration_ms,
        )
        
    except Exception as e:
        logger.warning(f"Failed to log MCP call: {e}")


async def log_mcp_call(
    tool_name: str,
    server_name: str,
    arguments: Dict[str, Any],
    result: str = "",
    status: str = "success",
    error_message: str = "",
    duration_ms: int = 0,
    session_id: str = ""
):
    """
    Async Logging eines MCP Tool Calls.
    
    Fire-and-forget - blockiert Tool-Ausführung nicht.
    """
    try:
        _setup_django()
        
        from asgiref.sync import sync_to_async
        from apps.bfagent.models_testing import MCPUsageLog
        from django.utils import timezone
        
        category = _categorize_tool(tool_name)
        
        @sync_to_async
        def save_log():
            return MCPUsageLog.objects.create(
                tool_name=f"{server_name}:{tool_name}",
                tool_category=category,
                arguments={k: str(v)[:200] for k, v in arguments.items()} if arguments else {},
                result_summary=_smart_truncate(result, 500),
                status=status,
                error_message=error_message[:1000] if error_message else "",
                session_id=session_id or f"mcp-{timezone.now():%Y%m%d-%H%M%S}",
                duration_ms=duration_ms,
            )
        
        await save_log()
        
    except Exception as e:
        logger.warning(f"Failed to log MCP call async: {e}")


class MCPTracker:
    """
    Context manager for tracking MCP tool calls.
    
    Usage:
        async with MCPTracker("db_list_tables", "bfagent_db", {"schema": "public"}) as tracker:
            result = do_work()
            tracker.set_result(result)
    """
    
    def __init__(self, tool_name: str, server_name: str, arguments: Dict[str, Any]):
        self.tool_name = tool_name
        self.server_name = server_name
        self.arguments = arguments
        self.start_time = None
        self.result = ""
        self.status = "success"
        self.error_message = ""
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration_ms = int((time.time() - self.start_time) * 1000)
        
        if exc_type is not None:
            self.status = "error"
            self.error_message = str(exc_val)
        
        # Fire and forget
        asyncio.create_task(log_mcp_call(
            tool_name=self.tool_name,
            server_name=self.server_name,
            arguments=self.arguments,
            result=self.result,
            status=self.status,
            error_message=self.error_message,
            duration_ms=duration_ms
        ))
        
        return False  # Don't suppress exceptions
    
    def set_result(self, result: str):
        self.result = result
    
    def set_error(self, error: str):
        self.status = "error"
        self.error_message = error
