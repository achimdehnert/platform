"""
Workflow Dashboard URLs
URL routing for Multi-Hub Framework workflow views
"""

from django.urls import path
from apps.bfagent.views.workflow_dashboard import (
    workflow_dashboard,
    workflow_builder,
    workflow_visualizer,
    workflow_phase_detail,
    workflow_execute,
    workflow_api_info,
)

urlpatterns = [
    # Main dashboard
    path(
        '',
        workflow_dashboard,
        name='workflow_dashboard'
    ),
    
    # Workflow builder
    path(
        'builder/<str:domain_art>/<str:domain_type>/',
        workflow_builder,
        name='workflow_builder'
    ),
    
    # Workflow visualizer
    path(
        'visualizer/<str:domain_art>/<str:domain_type>/',
        workflow_visualizer,
        name='workflow_visualizer'
    ),
    
    # Phase detail
    path(
        'phase/<int:phase_id>/',
        workflow_phase_detail,
        name='workflow_phase_detail'
    ),
    
    # API endpoints
    path(
        'api/execute/',
        workflow_execute,
        name='workflow_execute'
    ),
    path(
        'api/info/',
        workflow_api_info,
        name='workflow_api_info'
    ),
]