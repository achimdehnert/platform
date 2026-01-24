# -*- coding: utf-8 -*-
"""
URL configuration for Usage Tracking.
"""
from django.urls import path
from . import views_usage_tracking as views

urlpatterns = [
    # Dashboard
    path('', views.usage_dashboard, name='usage_dashboard'),
    
    # Error Management
    path('errors/', views.error_list, name='error_list'),
    path('errors/<int:pk>/', views.error_detail, name='error_detail'),
    path('errors/<int:pk>/resolve/', views.error_resolve, name='error_resolve'),
    
    # Tool Usage
    path('tools/', views.tool_usage_list, name='tool_usage_list'),
    path('tools/statistics/', views.tool_statistics, name='tool_statistics'),
    
    # Error Patterns
    path('patterns/', views.error_patterns, name='error_patterns'),
    
    # API Endpoints
    path('api/analyze/', views.api_error_analyze, name='api_error_analyze'),
    path('api/stats/', views.api_usage_stats, name='api_usage_stats'),
    path('api/log-error/', views.api_log_error, name='api_log_error'),
    path('api/log-tool/', views.api_log_tool, name='api_log_tool'),
]
