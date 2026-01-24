"""
Research Hub - URL Configuration
"""

from django.urls import path
from . import views

app_name = 'research'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Outline Generator
    path('outline/', views.outline_generator_view, name='outline_generator'),
    path('outline/generate/', views.generate_outline_view, name='generate_outline'),
    path('outline/export/', views.export_outline_view, name='export_outline'),
    path('outline/frameworks/', views.list_frameworks_view, name='list_frameworks'),
    
    # Projects
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('projects/<int:pk>/delete/', views.project_delete, name='project_delete'),
    
    # Research Actions
    path('projects/<int:pk>/search/', views.perform_search, name='perform_search'),
    path('projects/<int:pk>/fact-check/', views.perform_fact_check, name='perform_fact_check'),
    path('projects/<int:pk>/summarize/', views.generate_summary, name='generate_summary'),
    
    # Quick Search (AJAX)
    path('api/quick-search/', views.api_quick_search, name='api_quick_search'),
    path('api/fact-check/', views.api_fact_check, name='api_fact_check'),
    
    # Export
    path('projects/<int:pk>/export/<str:format>/', views.project_export, name='project_export'),
]
