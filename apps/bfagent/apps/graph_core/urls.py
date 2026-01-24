"""
Graph Core URL Configuration
"""

from django.urls import path
from . import views

app_name = 'graph_core'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Frameworks
    path('frameworks/', views.framework_list, name='framework-list'),
    path('frameworks/<slug:slug>/', views.framework_detail, name='framework-detail'),
    path('frameworks/<slug:slug>/apply/<int:project_id>/', views.framework_apply, name='framework-apply'),
    
    # Graph Explorer
    path('explorer/<int:project_id>/', views.graph_explorer, name='explorer'),
    path('explorer/<int:project_id>/data/', views.graph_data, name='graph-data'),
    
    # Node CRUD
    path('explorer/<int:project_id>/node/create/', views.node_create, name='node-create'),
    path('explorer/<int:project_id>/node/<int:node_id>/update/', views.node_update, name='node-update'),
    path('explorer/<int:project_id>/node/<int:node_id>/delete/', views.node_delete, name='node-delete'),
    
    # Edge CRUD
    path('explorer/<int:project_id>/edge/create/', views.edge_create, name='edge-create'),
    path('explorer/<int:project_id>/edge/<int:edge_id>/delete/', views.edge_delete, name='edge-delete'),
    
    # Project Workflow (Integrated View)
    path('workflow/<int:project_id>/', views.project_workflow, name='project-workflow'),
    path('workflow/<int:project_id>/select-framework/', views.select_framework, name='select-framework'),
    path('workflow/toggle-step/<int:project_framework_id>/<int:step_id>/', views.toggle_step, name='toggle-step'),
    path('workflow/update-notes/<int:project_framework_id>/<int:step_id>/', views.update_step_notes, name='update-step-notes'),
]
