"""
API URL Configuration for Workflow Builder
"""

from django.urls import path
from . import workflow_api

urlpatterns = [
    # Handler Catalog
    path('handlers/', workflow_api.list_handlers, name='handler-list'),
    path('handlers/<str:handler_id>/', workflow_api.handler_detail, name='handler-detail'),
    
    # Domains (NEW V2)
    path('domains/', workflow_api.list_domains, name='domain-list'),
    
    # Projects API (for dropdowns)
    path('projects/list/', workflow_api.list_projects_api, name='projects-api-list'),
    
    # Workflow Templates
    path('workflows/templates/', workflow_api.list_workflow_templates, name='workflow-template-list'),
    path('workflows/templates/<str:template_id>/', workflow_api.workflow_template_detail, name='workflow-template-detail'),
    
    # Workflow Execution
    path('workflows/execute/', workflow_api.execute_workflow_api, name='workflow-execute'),
    path('workflows/save/', workflow_api.save_custom_workflow, name='workflow-save'),
    
    # Converters (React Flow ↔ Pipeline)
    path('convert/to-pipeline/', workflow_api.convert_react_flow_to_pipeline, name='convert-to-pipeline'),
    path('convert/to-reactflow/', workflow_api.convert_pipeline_to_react_flow, name='convert-to-reactflow'),
]
