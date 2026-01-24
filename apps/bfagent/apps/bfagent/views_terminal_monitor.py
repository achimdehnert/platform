# -*- coding: utf-8 -*-
"""
Terminal Error Monitor Views.

MVP: Manual error capture + KI-Lösungsvorschläge.
"""
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Count, Q
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .models_terminal import TerminalSession, TerminalError, TerminalErrorFixAttempt
from .services.terminal_capture import get_terminal_capture_service


@login_required
def terminal_dashboard(request):
    """Dashboard für Terminal Error Monitor."""
    # Statistiken
    total_errors = TerminalError.objects.count()
    new_errors = TerminalError.objects.filter(status='new').count()
    ready_errors = TerminalError.objects.filter(status='ready').count()
    fixed_errors = TerminalError.objects.filter(status__in=['fixed', 'verified']).count()
    
    # Fehler nach Typ
    errors_by_type = TerminalError.objects.values('error_type').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Fehler nach Severity
    errors_by_severity = TerminalError.objects.values('severity').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Neueste Fehler
    recent_errors = TerminalError.objects.filter(
        status__in=['new', 'ready', 'analyzing']
    ).order_by('-last_seen')[:10]
    
    # Sessions
    recent_sessions = TerminalSession.objects.order_by('-started_at')[:5]
    
    context = {
        'total_errors': total_errors,
        'new_errors': new_errors,
        'ready_errors': ready_errors,
        'fixed_errors': fixed_errors,
        'errors_by_type': errors_by_type,
        'errors_by_severity': errors_by_severity,
        'recent_errors': recent_errors,
        'recent_sessions': recent_sessions,
    }
    
    return render(request, 'bfagent/terminal_monitor/dashboard.html', context)


@login_required
def error_queue(request):
    """Error Queue - Alle offenen Fehler."""
    # Filter
    status_filter = request.GET.get('status', 'open')
    error_type = request.GET.get('type', '')
    severity = request.GET.get('severity', '')
    search = request.GET.get('q', '')
    
    # Query
    errors = TerminalError.objects.all()
    
    if status_filter == 'open':
        errors = errors.filter(status__in=['new', 'ready', 'analyzing', 'in_progress'])
    elif status_filter == 'fixed':
        errors = errors.filter(status__in=['fixed', 'verified'])
    elif status_filter == 'ignored':
        errors = errors.filter(status__in=['ignored', 'wont_fix'])
    elif status_filter != 'all':
        errors = errors.filter(status=status_filter)
    
    if error_type:
        errors = errors.filter(error_type=error_type)
    
    if severity:
        errors = errors.filter(severity=severity)
    
    if search:
        errors = errors.filter(
            Q(message__icontains=search) |
            Q(file_path__icontains=search) |
            Q(error_class__icontains=search)
        )
    
    errors = errors.order_by('-last_seen')
    
    # Pagination
    paginator = Paginator(errors, 20)
    page = request.GET.get('page', 1)
    errors_page = paginator.get_page(page)
    
    # Filter-Optionen
    error_types = TerminalError.ERROR_TYPE_CHOICES
    severities = TerminalError.SEVERITY_CHOICES
    statuses = TerminalError.STATUS_CHOICES
    
    context = {
        'errors': errors_page,
        'error_types': error_types,
        'severities': severities,
        'statuses': statuses,
        'current_filters': {
            'status': status_filter,
            'type': error_type,
            'severity': severity,
            'q': search,
        },
    }
    
    return render(request, 'bfagent/terminal_monitor/error_queue.html', context)


@login_required
def error_detail(request, error_id):
    """Detail-Ansicht eines Fehlers mit KI-Lösung."""
    error = get_object_or_404(TerminalError, id=error_id)
    
    # Fix-Versuche
    fix_attempts = error.fix_attempts.order_by('-attempted_at')
    
    context = {
        'error': error,
        'fix_attempts': fix_attempts,
    }
    
    return render(request, 'bfagent/terminal_monitor/error_detail.html', context)


@login_required
@require_POST
def analyze_error(request, error_id):
    """Startet KI-Analyse für einen Fehler."""
    error = get_object_or_404(TerminalError, id=error_id)
    
    # Status aktualisieren
    error.status = 'analyzing'
    error.save(update_fields=['status'])
    
    # KI-Analyse
    service = get_terminal_capture_service()
    result = service.get_ai_solution(str(error_id))
    
    if result.get('success'):
        return JsonResponse({
            'success': True,
            'analysis': result.get('analysis'),
            'solution_steps': result.get('solution_steps'),
            'confidence': result.get('confidence'),
            'cached': result.get('cached', False),
        })
    else:
        return JsonResponse({
            'success': False,
            'error': result.get('error', 'Analysis failed'),
        }, status=500)


@login_required
@require_POST
def mark_fixed(request, error_id):
    """Markiert Fehler als behoben."""
    error = get_object_or_404(TerminalError, id=error_id)
    
    data = json.loads(request.body) if request.body else {}
    
    # Fix-Attempt dokumentieren
    TerminalErrorFixAttempt.objects.create(
        error=error,
        user=request.user,
        description=data.get('description', 'Manuell als behoben markiert'),
        files_changed=data.get('files_changed', []),
        used_ai_suggestion=data.get('used_ai_suggestion', False),
        ai_step_followed=data.get('ai_step_followed'),
        result='success',
    )
    
    # Status aktualisieren
    error.status = 'fixed'
    error.resolved_by = request.user
    error.resolved_at = timezone.now()
    error.save()
    
    return JsonResponse({'success': True})


@login_required
@require_POST
def mark_ignored(request, error_id):
    """Markiert Fehler als ignoriert."""
    error = get_object_or_404(TerminalError, id=error_id)
    
    data = json.loads(request.body) if request.body else {}
    
    error.status = 'ignored'
    error.notes = data.get('reason', '')
    error.save()
    
    return JsonResponse({'success': True})


@login_required
@require_POST
def verify_fix(request, error_id):
    """Verifiziert einen Fix."""
    error = get_object_or_404(TerminalError, id=error_id)
    
    data = json.loads(request.body) if request.body else {}
    
    error.status = 'verified'
    error.save(update_fields=['status'])
    
    # Letzten Fix-Attempt aktualisieren
    last_attempt = error.fix_attempts.first()
    if last_attempt:
        last_attempt.verified = True
        last_attempt.verified_at = timezone.now()
        last_attempt.verification_method = data.get('method', 'manual')
        last_attempt.save()
    
    return JsonResponse({'success': True})


@login_required
def capture_input(request):
    """Seite zum manuellen Einfügen von Terminal-Output."""
    if request.method == 'POST':
        text = request.POST.get('terminal_output', '')
        source = request.POST.get('source', 'manual')
        
        if text.strip():
            service = get_terminal_capture_service()
            results = service.process_text_input(text, source)
            
            return render(request, 'bfagent/terminal_monitor/capture_result.html', {
                'results': results,
                'input_text': text,
            })
    
    return render(request, 'bfagent/terminal_monitor/capture_input.html')


@csrf_exempt
def api_capture_error(request):
    """API-Endpoint für externes Error-Capturing."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        text = data.get('output', '')
        source = data.get('source', 'api')
        
        if not text:
            return JsonResponse({'error': 'No output provided'}, status=400)
        
        service = get_terminal_capture_service()
        results = service.process_text_input(text, source)
        
        return JsonResponse({
            'success': True,
            'errors_found': len(results),
            'errors': results,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def ai_solution_partial(request, error_id):
    """HTMX-Partial für KI-Lösungsvorschlag."""
    error = get_object_or_404(TerminalError, id=error_id)
    
    # Bereits analysiert?
    if error.ai_solution_steps and error.ai_analyzed_at:
        return render(request, 'bfagent/terminal_monitor/partials/ai_solution.html', {
            'error': error,
            'cached': True,
        })
    
    # Neue Analyse
    service = get_terminal_capture_service()
    result = service.get_ai_solution(str(error_id))
    
    # Error neu laden (wurde in Service aktualisiert)
    error.refresh_from_db()
    
    return render(request, 'bfagent/terminal_monitor/partials/ai_solution.html', {
        'error': error,
        'success': result.get('success', False),
        'error_message': result.get('error'),
        'cached': False,
    })
