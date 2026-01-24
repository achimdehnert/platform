"""
MCP Dashboard URLs
==================

HTMX-native URL patterns with proper namespacing.
"""

from django.urls import path

from . import views_mcp

# MCP Dashboard URL patterns
mcp_urlpatterns = [
    # =========================================================================
    # MAIN VIEWS
    # =========================================================================
    path(
        'mcp/',
        views_mcp.MCPDashboardView.as_view(),
        name='mcp-dashboard'
    ),
    path(
        'mcp/domains/',
        views_mcp.MCPDomainListView.as_view(),
        name='mcp-domains'
    ),
    path(
        'mcp/domain/<str:domain_id>/',
        views_mcp.MCPDomainDetailView.as_view(),
        name='mcp-domain-detail'
    ),
    path(
        'mcp/protected/',
        views_mcp.MCPProtectedPathsView.as_view(),
        name='mcp-protected-paths'
    ),
    path(
        'mcp/sessions/',
        views_mcp.MCPSessionListView.as_view(),
        name='mcp-sessions'
    ),
    path(
        'mcp/session/<int:session_id>/',
        views_mcp.MCPSessionDetailView.as_view(),
        name='mcp-session-detail'
    ),
    path(
        'mcp/conventions/',
        views_mcp.MCPConventionsView.as_view(),
        name='mcp-conventions'
    ),
    
    # =========================================================================
    # HTMX ACTIONS
    # =========================================================================
    path(
        'mcp/api/sync/',
        views_mcp.MCPSyncDataView.as_view(),
        name='mcp-sync-data'
    ),
    path(
        'mcp/api/start-session/',
        views_mcp.MCPStartSessionView.as_view(),
        name='mcp-start-session'
    ),
    path(
        'mcp/api/cancel-session/<int:session_id>/',
        views_mcp.MCPCancelSessionView.as_view(),
        name='mcp-cancel-session'
    ),
    
    # =========================================================================
    # SSE (Server-Sent Events)
    # =========================================================================
    path(
        'mcp/sse/sessions/',
        views_mcp.MCPSessionSSEView.as_view(),
        name='mcp-sse-sessions'
    ),
    path(
        'mcp/sse/stats/',
        views_mcp.MCPStatsSSEView.as_view(),
        name='mcp-sse-stats'
    ),
]


# Integration in main urls.py:
# 
# from apps.control_center.urls_mcp import mcp_urlpatterns
# 
# urlpatterns = [
#     # ... existing patterns ...
# ] + mcp_urlpatterns
