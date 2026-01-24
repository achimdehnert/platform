# -*- coding: utf-8 -*-
"""
Views für Usage Tracking Dashboard.

Zeigt:
- Django Generation Errors
- Tool/Agent Usage Statistiken
- Error Fix Patterns
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Avg, Q
from datetime import timedelta

from .models_usage_tracking import (
    DjangoGenerationError,
    ToolUsageLog,
    ErrorFixPattern,
)
from .services.usage_tracker import get_usage_tracker
from .services.mcp_error_fixer import analyze_error, COMMON_ERROR_FIXES


@login_required
def usage_dashboard(request):
    """
    Haupt-Dashboard für Usage Tracking.
    
    Zeigt Übersicht über Errors und Tool-Nutzung.
    """
    days = int(request.GET.get('days', 30))
    since = timezone.now() - timedelta(days=days)
    
    # Error Stats
    errors = DjangoGenerationError.objects.filter(timestamp__gte=since)
    error_stats = {
        'total': errors.count(),
        'by_type': list(
            errors.values('error_type')
            .annotate(count=Count('id'), occurrences=Sum('occurrence_count'))
            .order_by('-occurrences')
        ),
        'unresolved': errors.filter(resolved=False).count(),
        'auto_fixable': errors.filter(auto_fixable=True, resolved=False).count(),
    }
    
    # Tool Usage Stats
    tool_logs = ToolUsageLog.objects.filter(timestamp__gte=since)
    tool_stats = {
        'total_calls': tool_logs.count(),
        'by_caller': list(
            tool_logs.values('caller_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        ),
        'by_tool': list(
            tool_logs.values('tool_name')
            .annotate(
                count=Count('id'),
                avg_time=Avg('execution_time_ms'),
                success_count=Count('id', filter=Q(success=True))
            )
            .order_by('-count')[:10]
        ),
        'success_rate': (
            tool_logs.filter(success=True).count() / tool_logs.count() * 100
            if tool_logs.count() > 0 else 100
        ),
    }
    
    # Recent Errors
    recent_errors = errors.order_by('-timestamp')[:10]
    
    # Recent Tool Usage
    recent_tools = tool_logs.order_by('-timestamp')[:10]
    
    # Top Error Patterns
    top_errors = list(
        errors.values('error_type', 'error_message')
        .annotate(total=Sum('occurrence_count'))
        .order_by('-total')[:5]
    )
    
    context = {
        'page_title': 'Usage Tracking Dashboard',
        'days': days,
        'error_stats': error_stats,
        'tool_stats': tool_stats,
        'recent_errors': recent_errors,
        'recent_tools': recent_tools,
        'top_errors': top_errors,
        'caller_icons': {
            'user': '👤',
            'cascade': '🤖',
            'mcp': '🔧',
            'api': '🌐',
            'scheduled': '⏰',
            'system': '⚙️',
        },
        'error_type_colors': {
            'template': 'info',
            'view': 'success',
            'url': 'warning',
            'model': 'danger',
            'import': 'secondary',
            'syntax': 'primary',
            'migration': 'dark',
            'other': 'light',
        },
    }
    
    return render(request, 'bfagent/usage_tracking/dashboard.html', context)


@login_required
def error_list(request):
    """Liste aller Django Generation Errors."""
    # Filter
    error_type = request.GET.get('type', '')
    severity = request.GET.get('severity', '')
    resolved = request.GET.get('resolved', '')
    source = request.GET.get('source', '')
    search = request.GET.get('q', '')
    
    errors = DjangoGenerationError.objects.all()
    
    if error_type:
        errors = errors.filter(error_type=error_type)
    if severity:
        errors = errors.filter(severity=severity)
    if resolved == 'yes':
        errors = errors.filter(resolved=True)
    elif resolved == 'no':
        errors = errors.filter(resolved=False)
    if source:
        errors = errors.filter(source=source)
    if search:
        errors = errors.filter(
            Q(error_message__icontains=search) |
            Q(file_path__icontains=search) |
            Q(error_code__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(errors.order_by('-timestamp'), 25)
    page = request.GET.get('page', 1)
    errors_page = paginator.get_page(page)
    
    context = {
        'page_title': 'Django Generation Errors',
        'errors': errors_page,
        'error_types': DjangoGenerationError.ERROR_TYPES,
        'severity_choices': DjangoGenerationError.SEVERITY_CHOICES,
        'source_choices': DjangoGenerationError.SOURCE_CHOICES,
        'filters': {
            'type': error_type,
            'severity': severity,
            'resolved': resolved,
            'source': source,
            'q': search,
        },
        'total_count': paginator.count,
    }
    
    return render(request, 'bfagent/usage_tracking/error_list.html', context)


@login_required
def error_detail(request, pk):
    """Detail-Ansicht eines Errors."""
    error = get_object_or_404(DjangoGenerationError, pk=pk)
    
    # Analyze error for fix suggestions
    analysis = analyze_error(
        error.error_message,
        error.file_path,
        error.code_snippet
    )
    
    # Find similar errors
    similar = DjangoGenerationError.objects.filter(
        error_type=error.error_type,
        error_hash=error.error_hash
    ).exclude(pk=pk)[:5]
    
    context = {
        'page_title': f'Error #{error.id}',
        'error': error,
        'analysis': analysis,
        'similar_errors': similar,
    }
    
    return render(request, 'bfagent/usage_tracking/error_detail.html', context)


@login_required
def error_resolve(request, pk):
    """Markiert einen Error als resolved."""
    error = get_object_or_404(DjangoGenerationError, pk=pk)
    
    if request.method == 'POST':
        error.resolved = True
        error.resolution = request.POST.get('resolution', '')
        error.save()
        messages.success(request, f'Error #{pk} als resolved markiert.')
    
    return redirect('bfagent:error_detail', pk=pk)


@login_required
def tool_usage_list(request):
    """Liste der Tool-Nutzungen."""
    # Filter
    tool_name = request.GET.get('tool', '')
    caller_type = request.GET.get('caller', '')
    success = request.GET.get('success', '')
    app_label = request.GET.get('app', '')
    
    logs = ToolUsageLog.objects.all()
    
    if tool_name:
        logs = logs.filter(tool_name=tool_name)
    if caller_type:
        logs = logs.filter(caller_type=caller_type)
    if success == 'yes':
        logs = logs.filter(success=True)
    elif success == 'no':
        logs = logs.filter(success=False)
    if app_label:
        logs = logs.filter(app_label=app_label)
    
    # Pagination
    paginator = Paginator(logs.order_by('-timestamp'), 50)
    page = request.GET.get('page', 1)
    logs_page = paginator.get_page(page)
    
    # Available tools for filter
    available_tools = list(
        ToolUsageLog.objects.values_list('tool_name', flat=True).distinct()
    )
    available_apps = list(
        ToolUsageLog.objects.filter(app_label__isnull=False)
        .values_list('app_label', flat=True).distinct()
    )
    
    context = {
        'page_title': 'Tool Usage Log',
        'logs': logs_page,
        'caller_types': ToolUsageLog.CALLER_TYPES,
        'available_tools': available_tools,
        'available_apps': available_apps,
        'filters': {
            'tool': tool_name,
            'caller': caller_type,
            'success': success,
            'app': app_label,
        },
        'total_count': paginator.count,
    }
    
    return render(request, 'bfagent/usage_tracking/tool_usage_list.html', context)


@login_required
def tool_statistics(request):
    """Statistiken zur Tool-Nutzung."""
    days = int(request.GET.get('days', 30))
    since = timezone.now() - timedelta(days=days)
    
    logs = ToolUsageLog.objects.filter(timestamp__gte=since)
    
    # By Caller Type
    by_caller = list(
        logs.values('caller_type')
        .annotate(
            count=Count('id'),
            success_count=Count('id', filter=Q(success=True)),
            avg_time=Avg('execution_time_ms')
        )
        .order_by('-count')
    )
    
    # By Tool
    by_tool = list(
        logs.values('tool_name')
        .annotate(
            count=Count('id'),
            success_count=Count('id', filter=Q(success=True)),
            avg_time=Avg('execution_time_ms'),
            total_time=Sum('execution_time_ms')
        )
        .order_by('-count')
    )
    
    # By App
    by_app = list(
        logs.filter(app_label__isnull=False)
        .values('app_label')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    
    # Daily trend
    daily_trend = []
    for i in range(min(days, 14)):
        day = timezone.now() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = logs.filter(timestamp__gte=day_start, timestamp__lt=day_end).count()
        daily_trend.append({
            'date': day_start.strftime('%d.%m'),
            'count': count
        })
    daily_trend.reverse()
    
    context = {
        'page_title': 'Tool Usage Statistics',
        'days': days,
        'total_calls': logs.count(),
        'by_caller': by_caller,
        'by_tool': by_tool,
        'by_app': by_app,
        'daily_trend': daily_trend,
        'caller_icons': {
            'user': '👤',
            'cascade': '🤖',
            'mcp': '🔧',
            'api': '🌐',
            'scheduled': '⏰',
            'system': '⚙️',
        },
    }
    
    return render(request, 'bfagent/usage_tracking/tool_statistics.html', context)


@login_required
def error_patterns(request):
    """Error Fix Patterns verwalten."""
    patterns = ErrorFixPattern.objects.all().order_by('-times_applied')
    
    # Built-in patterns
    builtin_patterns = [
        {
            'name': name,
            'description': info['description'],
            'error_type': info.get('fix_type', 'unknown'),
            'pattern': info['pattern'],
        }
        for name, info in COMMON_ERROR_FIXES.items()
    ]
    
    context = {
        'page_title': 'Error Fix Patterns',
        'patterns': patterns,
        'builtin_patterns': builtin_patterns,
    }
    
    return render(request, 'bfagent/usage_tracking/error_patterns.html', context)


@login_required
def api_error_analyze(request):
    """API: Analysiert einen Error und gibt Fixes zurück."""
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        
        result = analyze_error(
            error_message=data.get('error_message', ''),
            file_path=data.get('file_path'),
            code_snippet=data.get('code_snippet'),
        )
        
        return JsonResponse(result)
    
    return JsonResponse({'error': 'POST required'}, status=400)


@login_required
def api_usage_stats(request):
    """API: Gibt Usage Stats als JSON zurück."""
    days = int(request.GET.get('days', 30))
    tracker = get_usage_tracker()
    
    return JsonResponse({
        'error_stats': tracker.get_error_stats(days),
        'usage_stats': tracker.get_usage_stats(days),
    })


@login_required  
def api_log_error(request):
    """API: Loggt einen neuen Error."""
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        
        tracker = get_usage_tracker()
        error_id = tracker.log_django_error(
            error_type=data.get('error_type', 'other'),
            error_message=data.get('error_message', ''),
            file_path=data.get('file_path'),
            line_number=data.get('line_number'),
            code_snippet=data.get('code_snippet'),
            auto_fixable=data.get('auto_fixable', False),
            fix_suggestion=data.get('fix_suggestion'),
        )
        
        return JsonResponse({
            'success': error_id is not None,
            'error_id': error_id,
        })
    
    return JsonResponse({'error': 'POST required'}, status=400)


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def api_log_tool(request):
    """API: Loggt Tool-Usage (für MCP Server - kein Login erforderlich)."""
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            
            tracker = get_usage_tracker()
            tracker.set_session(
                session_id=data.get('session_id', 'mcp'),
                caller_type=data.get('caller_type', 'mcp'),
                caller_id=data.get('caller_id', 'mcp_server')
            )
            
            log_id = tracker.log_tool_usage(
                tool_name=data.get('tool_name', 'unknown'),
                input_params=data.get('input_params', {}),
                execution_time_ms=data.get('execution_time_ms', 0),
                success=data.get('success', True),
                result_summary=data.get('result_summary'),
                error_message=data.get('error_message'),
                app_label=data.get('app_label'),
            )
            
            return JsonResponse({
                'success': log_id is not None,
                'log_id': log_id,
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'POST required'}, status=400)
