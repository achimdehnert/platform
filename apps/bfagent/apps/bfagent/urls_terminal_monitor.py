# -*- coding: utf-8 -*-
"""
URL configuration for Terminal Error Monitor.
"""
from django.urls import path
from . import views_terminal_monitor as views

urlpatterns = [
    # Dashboard
    path('', views.terminal_dashboard, name='dashboard'),
    
    # Error Queue
    path('errors/', views.error_queue, name='error_queue'),
    path('errors/<uuid:error_id>/', views.error_detail, name='error_detail'),
    
    # Actions
    path('errors/<uuid:error_id>/analyze/', views.analyze_error, name='analyze_error'),
    path('errors/<uuid:error_id>/mark-fixed/', views.mark_fixed, name='mark_fixed'),
    path('errors/<uuid:error_id>/mark-ignored/', views.mark_ignored, name='mark_ignored'),
    path('errors/<uuid:error_id>/verify/', views.verify_fix, name='verify_fix'),
    
    # HTMX Partials
    path('errors/<uuid:error_id>/ai-solution/', views.ai_solution_partial, name='ai_solution_partial'),
    
    # Manual Capture
    path('capture/', views.capture_input, name='capture_input'),
    
    # API
    path('api/capture/', views.api_capture_error, name='api_capture_error'),
]
