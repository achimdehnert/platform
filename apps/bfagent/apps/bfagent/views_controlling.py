# -*- coding: utf-8 -*-
"""
Views für Agent/LLM Controlling Dashboard.
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count, Avg
from datetime import timedelta
from decimal import Decimal
import json

from .models_controlling import (
    LLMUsageLog,
    AgentValidationLog,
    ControllingBaseline,
    ControllingAlert,
    OrchestrationCall,
)


@login_required
def controlling_dashboard(request):
    """
    Haupt-Dashboard für Agent/LLM Controlling.
    
    Zeigt:
    - Kosten-Übersicht (nach Provider, Agent)
    - Qualitäts-Metriken (DjangoAgent)
    - Performance-Metriken
    - Aktive Alerts
    """
    days = int(request.GET.get('days', 30))
    since = timezone.now() - timedelta(days=days)
    
    # LLM Usage Stats
    llm_logs = LLMUsageLog.objects.filter(timestamp__gte=since)
    cost_summary = LLMUsageLog.get_cost_summary(days=days)
    
    # Agent Validation Stats
    validation_logs = AgentValidationLog.objects.filter(timestamp__gte=since)
    quality_summary = AgentValidationLog.get_quality_summary(days=days)
    
    # Baseline Comparison
    django_baseline = ControllingBaseline.get_latest('django_errors')
    
    # Unacknowledged Alerts
    active_alerts = ControllingAlert.objects.filter(acknowledged=False).order_by('-created_at')[:5]
    
    # Recent Activity
    recent_llm = llm_logs.order_by('-timestamp')[:10]
    recent_validations = validation_logs.order_by('-timestamp')[:10]
    
    # Token summary
    token_summary = llm_logs.aggregate(
        total_in=Sum('tokens_in'),
        total_out=Sum('tokens_out')
    )
    total_tokens = (token_summary['total_in'] or 0) + (token_summary['total_out'] or 0)
    
    # By Task breakdown
    by_task = llm_logs.values('task').annotate(
        calls=Count('id'),
        cost=Sum('cost_usd'),
        tokens_in=Sum('tokens_in'),
        tokens_out=Sum('tokens_out'),
    ).order_by('-cost')[:10]
    
    # Success rate
    success_count = llm_logs.filter(success=True).count()
    total_count = llm_logs.count()
    llm_success_rate = (success_count / total_count * 100) if total_count > 0 else 100
    
    # Recent Orchestration Sessions
    recent_sessions = []
    session_ids = OrchestrationCall.objects.filter(
        started_at__gte=since,
        parent__isnull=True
    ).values_list('session_id', flat=True).distinct()[:5]
    
    for session_id in session_ids:
        calls = OrchestrationCall.objects.filter(session_id=session_id).order_by('depth', 'sequence')
        if calls.exists():
            root = calls.first()
            status_colors = {'success': 'success', 'failed': 'danger', 'running': 'primary', 'pending': 'secondary'}
            recent_sessions.append({
                'session_id': session_id,
                'name': root.name,
                'description': root.description[:100] if root.description else '',
                'status': root.status,
                'status_color': status_colors.get(root.status, 'secondary'),
                'started_at': root.started_at,
                'calls': list(calls[:10]),
            })
    
    context = {
        'page_title': 'Agent/LLM Controlling',
        'days': days,
        
        # Kosten
        'cost_summary': cost_summary,
        'total_cost': cost_summary['summary']['total_cost'] or Decimal('0'),
        'total_calls': cost_summary['summary']['total_calls'] or 0,
        'total_tokens': total_tokens,
        'by_provider': cost_summary['by_provider'],
        'by_agent': cost_summary['by_agent'],
        'by_task': by_task,
        
        # Qualität
        'quality_summary': quality_summary,
        'total_validations': quality_summary['summary']['total_validations'] or 0,
        'errors_prevented': quality_summary['summary']['total_errors_prevented'] or 0,
        'success_rate': llm_success_rate,
        'top_error_types': quality_summary['top_error_types'][:5],
        
        # Performance
        'avg_latency': cost_summary['summary']['avg_latency'] or 0,
        'cache_hits': llm_logs.filter(cached=True).count(),
        'cache_rate': (
            llm_logs.filter(cached=True).count() / llm_logs.count() * 100
            if llm_logs.count() > 0 else 0
        ),
        'fallback_count': llm_logs.filter(fallback_used=True).count(),
        
        # Baseline
        'django_baseline': django_baseline,
        
        # Alerts
        'active_alerts': active_alerts,
        'alert_count': active_alerts.count(),
        
        # Recent
        'recent_llm': recent_llm,
        'recent_validations': recent_validations,
        'recent_sessions': recent_sessions,
    }
    
    return render(request, 'bfagent/controlling/dashboard.html', context)


@login_required
def controlling_api_summary(request):
    """API Endpoint für Dashboard-Daten (für HTMX Refresh)."""
    days = int(request.GET.get('days', 30))
    
    cost_summary = LLMUsageLog.get_cost_summary(days=days)
    quality_summary = AgentValidationLog.get_quality_summary(days=days)
    
    return JsonResponse({
        'cost': {
            'total': float(cost_summary['summary']['total_cost'] or 0),
            'calls': cost_summary['summary']['total_calls'] or 0,
            'by_provider': cost_summary['by_provider'],
        },
        'quality': {
            'validations': quality_summary['summary']['total_validations'] or 0,
            'errors_prevented': quality_summary['summary']['total_errors_prevented'] or 0,
            'success_rate': quality_summary['summary']['success_rate'],
        },
        'performance': {
            'avg_latency_ms': cost_summary['summary']['avg_latency'] or 0,
        }
    })


@login_required
def controlling_baseline_compare(request):
    """Vergleicht aktuelle Daten mit Baseline."""
    from .models_testing import TestRequirement
    
    # Aktuelle Django-Fehler messen
    days = 30
    since = timezone.now() - timedelta(days=days)
    reqs = TestRequirement.objects.filter(created_at__gte=since)
    
    current_data = {
        "total_requirements": reqs.count(),
        "django_errors": {
            "template": reqs.filter(description__icontains='template').count(),
            "url": reqs.filter(description__icontains='url').count(),
            "import": reqs.filter(description__icontains='import').count(),
            "static": reqs.filter(description__icontains='static').count(),
            "total": (
                reqs.filter(description__icontains='template').count() +
                reqs.filter(description__icontains='url').count() +
                reqs.filter(description__icontains='import').count() +
                reqs.filter(description__icontains='static').count()
            ),
        }
    }
    
    comparison = ControllingBaseline.compare_with_current('django_errors', current_data)
    
    return JsonResponse(comparison)


@login_required
@require_POST
def controlling_interpret(request):
    """LLM-basierte Interpretation der Controlling-Daten."""
    interpretation_type = request.GET.get('type', 'cost')
    days = 30
    since = timezone.now() - timedelta(days=days)
    
    # Sammle Daten für Interpretation
    llm_logs = LLMUsageLog.objects.filter(timestamp__gte=since)
    cost_summary = LLMUsageLog.get_cost_summary(days=days)
    
    by_task = list(llm_logs.values('task').annotate(
        calls=Count('id'),
        cost=Sum('cost_usd'),
        tokens=Sum('tokens_in') + Sum('tokens_out'),
    ).order_by('-cost')[:5])
    
    by_provider = list(llm_logs.values('provider').annotate(
        calls=Count('id'),
        cost=Sum('cost_usd'),
    ).order_by('-cost'))
    
    error_logs = llm_logs.filter(success=False)
    
    # Build context for LLM
    data_context = {
        "period_days": days,
        "total_cost_usd": float(cost_summary['summary']['total_cost'] or 0),
        "total_calls": cost_summary['summary']['total_calls'] or 0,
        "avg_latency_ms": cost_summary['summary']['avg_latency'] or 0,
        "by_task": [{"task": t['task'], "calls": t['calls'], "cost": float(t['cost'] or 0)} for t in by_task],
        "by_provider": [{"provider": p['provider'], "calls": p['calls'], "cost": float(p['cost'] or 0)} for p in by_provider],
        "error_count": error_logs.count(),
        "success_rate": ((llm_logs.count() - error_logs.count()) / llm_logs.count() * 100) if llm_logs.count() > 0 else 100,
    }
    
    # Build prompt based on type
    prompts = {
        'cost': f"""Analysiere diese LLM-Nutzungsdaten und gib eine kurze Kosten-Zusammenfassung:

Daten (letzte {days} Tage):
- Gesamtkosten: ${data_context['total_cost_usd']:.4f}
- Aufrufe: {data_context['total_calls']}
- Ø Latenz: {data_context['avg_latency_ms']:.0f}ms
- Top Tasks: {json.dumps(data_context['by_task'], indent=2)}
- Provider: {json.dumps(data_context['by_provider'], indent=2)}

Antworte auf Deutsch, kurz und prägnant (max 3-4 Sätze). Fokus auf Kosten-Effizienz.""",

        'optimization': f"""Basierend auf diesen LLM-Nutzungsdaten, schlage Optimierungen vor:

Daten:
- Kosten: ${data_context['total_cost_usd']:.4f} für {data_context['total_calls']} Aufrufe
- Top Tasks nach Kosten: {json.dumps(data_context['by_task'], indent=2)}
- Provider-Verteilung: {json.dumps(data_context['by_provider'], indent=2)}

Antworte auf Deutsch mit 2-3 konkreten Optimierungsvorschlägen.""",

        'anomaly': f"""Prüfe diese LLM-Daten auf Anomalien oder Probleme:

Daten:
- Erfolgsrate: {data_context['success_rate']:.1f}%
- Fehler: {data_context['error_count']}
- Ø Latenz: {data_context['avg_latency_ms']:.0f}ms
- Tasks: {json.dumps(data_context['by_task'], indent=2)}

Antworte auf Deutsch. Wenn alles normal aussieht, sag das. Sonst beschreibe die Anomalien."""
    }
    
    prompt = prompts.get(interpretation_type, prompts['cost'])
    
    try:
        # Use WorkerLLMClient for interpretation
        from .services.orchestration_service import WorkerLLMClient
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        import asyncio
        
        async def get_interpretation():
            client = WorkerLLMClient(model_name='gpt4o-mini', task='controlling_interpret')
            result = await client.generate(
                prompt=prompt,
                system_prompt="Du bist ein Datenanalyst für LLM-Kosten und Performance. Antworte präzise auf Deutsch.",
                max_tokens=300,
                temperature=0.3
            )
            return result
        
        result = asyncio.run(get_interpretation())
        
        if result.get('success'):
            interpretation = result.get('content', 'Keine Interpretation verfügbar.')
            return JsonResponse({
                'success': True,
                'html': f'<div class="alert alert-light border">{interpretation}</div>',
                'tokens_used': result.get('total_tokens', 0),
                'cost': result.get('estimated_cost', 0),
            })
        else:
            return JsonResponse({
                'success': False,
                'html': f'<div class="alert alert-warning">⚠️ {result.get("error", "Fehler")}</div>',
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'html': f'<div class="alert alert-danger">❌ Fehler: {str(e)}</div>',
        })


@login_required
def llm_usage_list(request):
    """Liste aller LLM-Aufrufe mit Filter."""
    days = int(request.GET.get('days', 30))
    session_id = request.GET.get('session')
    task_filter = request.GET.get('task')
    since = timezone.now() - timedelta(days=days)
    
    logs = LLMUsageLog.objects.filter(timestamp__gte=since)
    
    # Filter by session
    if session_id:
        logs = logs.filter(session_id=session_id)
    
    # Filter by task
    if task_filter:
        logs = logs.filter(task__icontains=task_filter)
    
    logs = logs.order_by('-timestamp')
    
    context = {
        'page_title': 'LLM Usage Log',
        'logs': logs[:100],
        'total_count': logs.count(),
        'days': days,
        'session_id': session_id,
        'task_filter': task_filter,
    }
    return render(request, 'bfagent/controlling/llm_usage_list.html', context)


@login_required
def orchestration_list(request):
    """Liste aller Orchestrierungs-Sessions."""
    days = int(request.GET.get('days', 30))
    since = timezone.now() - timedelta(days=days)
    
    sessions = []
    session_ids = OrchestrationCall.objects.filter(
        started_at__gte=since,
        parent__isnull=True
    ).values_list('session_id', flat=True).distinct()
    
    for session_id in session_ids:
        calls = OrchestrationCall.objects.filter(session_id=session_id).order_by('depth', 'sequence')
        if calls.exists():
            root = calls.first()
            sessions.append({
                'session_id': session_id,
                'root': root,
                'calls': list(calls),
                'call_count': calls.count(),
            })
    
    context = {
        'page_title': 'Orchestration Sessions',
        'sessions': sessions,
        'days': days,
    }
    return render(request, 'bfagent/controlling/orchestration_list.html', context)


@login_required
@require_POST
def alert_acknowledge(request, alert_id):
    """Alert als bestätigt markieren."""
    alert = get_object_or_404(ControllingAlert, id=alert_id)
    alert.acknowledge(by=request.user.username)
    return JsonResponse({'success': True, 'html': ''})


@login_required
def llm_usage_detail(request, log_id):
    """Detail-Ansicht eines einzelnen LLM-Aufrufs."""
    log = get_object_or_404(LLMUsageLog, id=log_id)
    
    # Find related calls in same time window (±5 seconds)
    time_window_start = log.timestamp - timedelta(seconds=5)
    time_window_end = log.timestamp + timedelta(seconds=5)
    related_logs = LLMUsageLog.objects.filter(
        timestamp__gte=time_window_start,
        timestamp__lte=time_window_end
    ).exclude(id=log_id).order_by('timestamp')[:5]
    
    # Cost breakdown
    cost_per_token_in = float(log.cost_usd) / log.tokens_in if log.tokens_in > 0 else 0
    cost_per_token_out = float(log.cost_usd) / log.tokens_out if log.tokens_out > 0 else 0
    
    # Provider stats for comparison
    provider_avg = LLMUsageLog.objects.filter(
        provider=log.provider,
        timestamp__gte=timezone.now() - timedelta(days=30)
    ).aggregate(
        avg_latency=Avg('latency_ms'),
        avg_tokens_in=Avg('tokens_in'),
        avg_tokens_out=Avg('tokens_out'),
        avg_cost=Avg('cost_usd'),
    )
    
    context = {
        'page_title': f'LLM Call Detail #{log.id}',
        'log': log,
        'related_logs': related_logs,
        'cost_per_token_in': cost_per_token_in,
        'cost_per_token_out': cost_per_token_out,
        'provider_avg': provider_avg,
    }
    return render(request, 'bfagent/controlling/llm_usage_detail.html', context)


@login_required
def orchestration_detail(request, session_id):
    """Detail-Ansicht einer Orchestrierungs-Session."""
    calls = OrchestrationCall.objects.filter(session_id=session_id).order_by('depth', 'sequence')
    
    if not calls.exists():
        from django.http import Http404
        raise Http404("Session not found")
    
    root = calls.first()
    
    # Calculate session metrics
    total_duration = 0
    total_tokens_in = 0
    total_tokens_out = 0
    total_cost = Decimal('0')
    llm_calls = []
    failed_calls = []
    
    for call in calls:
        if call.duration_ms:
            total_duration += call.duration_ms
        if call.tokens_in:
            total_tokens_in += call.tokens_in
        if call.tokens_out:
            total_tokens_out += call.tokens_out
        if call.cost_usd:
            total_cost += call.cost_usd
        if call.call_type == 'llm_call':
            llm_calls.append(call)
        if call.status == 'failed':
            failed_calls.append(call)
    
    # Build timeline data for visualization
    timeline = []
    for call in calls:
        timeline.append({
            'name': call.name,
            'type': call.call_type,
            'depth': call.depth,
            'status': call.status,
            'start': call.started_at.isoformat() if call.started_at else None,
            'end': call.ended_at.isoformat() if call.ended_at else None,
            'duration_ms': call.duration_ms,
        })
    
    context = {
        'page_title': f'Session {session_id}',
        'session_id': session_id,
        'root': root,
        'calls': calls,
        'call_count': calls.count(),
        'total_duration': total_duration,
        'total_tokens_in': total_tokens_in,
        'total_tokens_out': total_tokens_out,
        'total_cost': total_cost,
        'llm_calls': llm_calls,
        'failed_calls': failed_calls,
        'timeline_json': json.dumps(timeline),
    }
    return render(request, 'bfagent/controlling/orchestration_detail.html', context)
