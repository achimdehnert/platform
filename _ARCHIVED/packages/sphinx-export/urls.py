"""
Sphinx Export URLs
==================
"""

from django.urls import path
from . import views

app_name = 'sphinx_export'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('export/', views.export_project, name='export'),
    path('download/', views.download_export, name='download'),
    path('download/file/', views.download_file, name='download_file'),
    
    # Sync URLs
    path('sync/', views.run_sync, name='sync'),
    path('sync/report/', views.sync_report, name='sync_report'),
    
    # API endpoints
    path('api/documents/', views.list_documents, name='api_documents'),
    path('api/validate/', views.validate_project, name='api_validate'),
    path('api/sync-status/', views.sync_status, name='api_sync_status'),
]
