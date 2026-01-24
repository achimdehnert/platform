"""
Handler Metrics & Analytics Views - Phase 3A Session 3

Provides metrics aggregation and visualization data for:
- Handler performance over time
- Success/failure rates
- Execution time trends
- Top performers
- Error analysis
"""

from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Avg, Count, Sum, Q
from apps.bfagent.models_handlers import Handler, ActionHandler
from apps.bfagent.models import AgentAction
import json


@require_http_methods(["GET"])
def metrics_dashboard_tab(request: HttpRequest) -> HttpResponse:
    """
    Metrics Dashboard Tab - Main metrics overview with charts
    """
    # Get overall statistics
    handlers = Handler.objects.filter(is_active=True)
    
    total_handlers = handlers.count()
    total_executions = sum(h.total_executions or 0 for h in handlers)
    avg_success_rate = sum(h.success_rate or 0 for h in handlers) / max(total_handlers, 1)
    avg_execution_time = sum(h.avg_execution_time_ms or 0 for h in handlers) / max(total_handlers, 1)
    
    # Get top handlers by execution count
    top_handlers = list(handlers.order_by('-total_executions')[:5])
    
    # Get handlers with low success rate (potential issues)
    problematic_handlers = list(handlers.filter(
        success_rate__lt=80, 
        total_executions__gt=0
    ).order_by('success_rate')[:5])
    
    # Get active mappings count
    active_mappings = ActionHandler.objects.filter(is_active=True).count()
    
    context = {
        'total_handlers': total_handlers,
        'total_executions': int(total_executions),
        'avg_success_rate': round(avg_success_rate, 1),
        'avg_execution_time': round(avg_execution_time, 1),
        'active_mappings': active_mappings,
        'top_handlers': top_handlers,
        'problematic_handlers': problematic_handlers,
    }
    
    return render(request, 'bfagent/partials/metrics_dashboard.html', context)


@require_http_methods(["GET"])
def metrics_api_chart_data(request: HttpRequest) -> JsonResponse:
    """
    API endpoint for chart data (JSON)
    Returns performance data for Chart.js
    """
    handlers = Handler.objects.filter(is_active=True, total_executions__gt=0)
    
    # Handler Performance Chart Data
    handler_labels = [h.display_name[:30] for h in handlers[:10]]
    success_rates = [h.success_rate or 0 for h in handlers[:10]]
    execution_times = [h.avg_execution_time_ms or 0 for h in handlers[:10]]
    execution_counts = [h.total_executions or 0 for h in handlers[:10]]
    
    # Phase Distribution (from ActionHandler)
    phase_counts = {
        'input': ActionHandler.objects.filter(phase='input', is_active=True).count(),
        'processing': ActionHandler.objects.filter(phase='processing', is_active=True).count(),
        'output': ActionHandler.objects.filter(phase='output', is_active=True).count(),
    }
    
    chart_data = {
        'handlerPerformance': {
            'labels': handler_labels,
            'datasets': [
                {
                    'label': 'Success Rate (%)',
                    'data': success_rates,
                    'backgroundColor': 'rgba(75, 192, 192, 0.6)',
                    'borderColor': 'rgba(75, 192, 192, 1)',
                    'borderWidth': 2,
                },
            ]
        },
        'executionTimes': {
            'labels': handler_labels,
            'datasets': [
                {
                    'label': 'Avg Execution Time (ms)',
                    'data': execution_times,
                    'backgroundColor': 'rgba(255, 159, 64, 0.6)',
                    'borderColor': 'rgba(255, 159, 64, 1)',
                    'borderWidth': 2,
                },
            ]
        },
        'executionCounts': {
            'labels': handler_labels,
            'datasets': [
                {
                    'label': 'Total Executions',
                    'data': execution_counts,
                    'backgroundColor': 'rgba(153, 102, 255, 0.6)',
                    'borderColor': 'rgba(153, 102, 255, 1)',
                    'borderWidth': 2,
                },
            ]
        },
        'phaseDistribution': {
            'labels': ['Input', 'Processing', 'Output'],
            'datasets': [
                {
                    'label': 'Active Mappings by Phase',
                    'data': [phase_counts['input'], phase_counts['processing'], phase_counts['output']],
                    'backgroundColor': [
                        'rgba(54, 162, 235, 0.6)',
                        'rgba(255, 206, 86, 0.6)',
                        'rgba(75, 192, 192, 0.6)',
                    ],
                    'borderColor': [
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(75, 192, 192, 1)',
                    ],
                    'borderWidth': 2,
                },
            ]
        },
    }
    
    return JsonResponse(chart_data)


@require_http_methods(["GET"])
def metrics_api_top_handlers(request: HttpRequest) -> JsonResponse:
    """
    API endpoint for top handlers list
    """
    handlers = Handler.objects.filter(
        is_active=True, 
        total_executions__gt=0
    ).order_by('-total_executions')[:10]
    
    data = {
        'topHandlers': [
            {
                'id': h.pk,
                'handler_id': h.handler_id,
                'display_name': h.display_name,
                'total_executions': h.total_executions or 0,
                'success_rate': h.success_rate or 0,
                'avg_execution_time': h.avg_execution_time_ms or 0,
                'category': h.category,
            }
            for h in handlers
        ]
    }
    
    return JsonResponse(data)
