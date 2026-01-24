"""
MCP Hub URL Configuration
"""

from django.urls import path
from . import views

app_name = 'mcp_hub'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Server Management
    path('servers/', views.server_list, name='server-list'),
    path('servers/<uuid:pk>/', views.server_detail, name='server-detail'),
    path('servers/<uuid:pk>/toggle/', views.toggle_server, name='server-toggle'),
    path('servers/<uuid:pk>/restart/', views.restart_server, name='server-restart'),
    path('servers/restart-all/', views.restart_all_servers, name='restart-all-servers'),
    
    # Tool Management
    path('tools/', views.tool_list, name='tool-list'),
    path('tools/<uuid:pk>/', views.tool_detail, name='tool-detail'),
    path('tools/<uuid:pk>/toggle/', views.toggle_tool, name='tool-toggle'),
    
    # Config Sync
    path('sync/', views.sync_from_config, name='sync-from-config'),
]
