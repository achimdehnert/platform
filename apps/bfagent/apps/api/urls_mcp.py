"""
URL Configuration for MCP Orchestration API
"""

from django.urls import path

from .mcp_orchestration import (
    create_workflow_context,
    delete_workflow_context,
    execute_mcp_tool,
    get_tool_info,
    get_workflow_context,
    list_mcp_servers,
    list_mcp_tools,
)

urlpatterns = [
    # Server & Tool Discovery
    path("servers", list_mcp_servers, name="mcp_list_servers"),
    path("tools", list_mcp_tools, name="mcp_list_tools"),
    path("tool/<str:server>/<str:tool>", get_tool_info, name="mcp_get_tool_info"),
    # Tool Execution
    path("execute", execute_mcp_tool, name="mcp_execute_tool"),
    # Workflow Context Management
    path("context", create_workflow_context, name="mcp_create_context"),
    path("context/<str:context_id>", get_workflow_context, name="mcp_get_context"),
    path("context/<str:context_id>/delete", delete_workflow_context, name="mcp_delete_context"),
]
