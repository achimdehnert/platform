"""
Cascade Autonomous Work Session API

Provides endpoints for starting, monitoring, and stopping autonomous Cascade work sessions.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils import timezone
import json

from apps.bfagent.models import TestRequirement
from apps.bfagent.models_cascade import CascadeWorkSession, CascadeWorkLog


@login_required
@require_http_methods(["POST"])
def session_start(request):
    """
    Start a new autonomous Cascade work session
    
    POST /api/cascade/session/start/
    {
        "requirement_id": "uuid",
        "max_iterations": 10  (optional, default 10)
    }
    """
    print("=" * 60)
    print("[CASCADE API] session_start CALLED!")
    print("=" * 60)
    
    try:
        data = json.loads(request.body) if request.body else {}
        requirement_id = data.get('requirement_id') or request.POST.get('requirement_id')
        print(f"[CASCADE API] requirement_id: {requirement_id}")
        max_iterations = data.get('max_iterations', 10)
        
        if not requirement_id:
            return JsonResponse({'success': False, 'error': 'requirement_id is required'}, status=400)
        
        force_restart = data.get('force_restart', False)
        requirement = get_object_or_404(TestRequirement, pk=requirement_id)
        
        # Check if there's already an active session
        active_session = CascadeWorkSession.objects.filter(
            requirement=requirement,
            status__in=['pending', 'running']
        ).first()
        
        if active_session:
            # Check if session is stale (no activity for 5 minutes)
            from datetime import timedelta
            stale_threshold = timezone.now() - timedelta(minutes=5)
            
            # Get last activity from session logs or updated_at
            last_activity = active_session.updated_at
            if hasattr(active_session, 'logs'):
                last_log = active_session.logs.order_by('-timestamp').first()
                if last_log and last_log.timestamp > last_activity:
                    last_activity = last_log.timestamp
            
            is_stale = last_activity < stale_threshold
            
            if is_stale or force_restart:
                # Auto-close stale session and continue
                active_session.status = 'cancelled'
                active_session.save()
                active_session.add_log('warning', f'Session automatisch beendet ({"force_restart" if force_restart else "inaktiv > 5 Min"})')
            else:
                # Session is still active - offer to force restart
                minutes_active = int((timezone.now() - active_session.created_at).total_seconds() / 60)
                return JsonResponse({
                    'success': False,
                    'error': f'Aktive Session läuft seit {minutes_active} Min. Klicke erneut mit force_restart=true um neu zu starten.',
                    'session_id': str(active_session.id),
                    'is_stale': is_stale,
                    'can_force_restart': True
                }, status=409)
        
        # Generate initial context (same as cascadeWorkOn)
        context = f"""## 🎯 Cascade Task: {requirement.name}

**Requirement ID:** `{requirement.id}`
**Domain:** {requirement.domain}
**Category:** {requirement.category}
**Priority:** {requirement.priority}
**Status:** {requirement.status}
"""
        if requirement.category == 'bug_fix':
            if requirement.url:
                context += f"\n**Bug gefunden auf:** {requirement.url}\n"
            if requirement.actual_behavior:
                context += f"\n### ❌ Aktuelles Verhalten:\n{requirement.actual_behavior}\n"
            if requirement.expected_behavior:
                context += f"\n### ✅ Erwartetes Verhalten:\n{requirement.expected_behavior}\n"
        
        if requirement.description:
            context += f"\n### Beschreibung:\n{requirement.description}\n"
        
        # Include Initiative content if linked
        if requirement.initiative:
            initiative = requirement.initiative
            context += f"\n### 📋 Übergeordnete Initiative: {initiative.title}\n"
            if initiative.description:
                context += f"\n**Initiative-Beschreibung:**\n{initiative.description}\n"
            if initiative.analysis:
                context += f"\n**Analyse:**\n{initiative.analysis}\n"
            if initiative.concept:
                context += f"\n**Konzept:**\n{initiative.concept}\n"
            context += f"\n**Initiative-Status:** {initiative.get_status_display()}\n"
            context += f"**Workflow-Phase:** {initiative.get_workflow_phase_display()}\n"
        
        context += f"\n---\n\n**Bitte arbeite autonom an diesem {'Bug' if requirement.category == 'bug_fix' else 'Feature'}.**\n"
        
        # Create session
        session = CascadeWorkSession.objects.create(
            requirement=requirement,
            initial_context=context,
            max_iterations=max_iterations,
            created_by=request.user,
            status='pending'
        )
        
        # Update requirement status
        was_already_in_progress = requirement.status == 'in_progress'
        requirement.status = 'in_progress'
        requirement.save()
        
        # Add feedback for activity dashboard
        from apps.bfagent.models_testing import RequirementFeedback
        
        # ALWAYS explicitly trigger Celery task (don't rely on signal)
        celery_task_id = None
        from django.conf import settings
        celery_enabled = getattr(settings, 'CELERY_BROKER_URL', None)
        print(f"[DEBUG] CELERY_BROKER_URL: {celery_enabled}")
        if celery_enabled:
            try:
                from apps.bfagent.tasks import process_requirement_task
                print(f"[DEBUG] Triggering Celery task for requirement: {requirement.pk}")
                result = process_requirement_task.delay(str(requirement.pk))
                celery_task_id = result.id
                print(f"[DEBUG] Celery task triggered! ID: {celery_task_id}")
                import structlog
                structlog.get_logger().info(
                    "cascade_celery_task_triggered",
                    requirement_id=str(requirement.pk),
                    celery_task_id=celery_task_id
                )
            except Exception as e:
                print(f"[DEBUG] Celery task FAILED: {e}")
                import structlog
                structlog.get_logger().error("cascade_celery_task_failed", error=str(e))
        else:
            print("[DEBUG] CELERY_BROKER_URL not set - task not triggered")
        
        RequirementFeedback.objects.create(
            requirement=requirement,
            feedback_type='progress',
            content=f"🤖 **Cascade Autonom gestartet**\n\nSession ID: `{session.id}`\nCelery Task: `{celery_task_id or 'nicht gestartet'}`",
            is_from_cascade=True,
            author=request.user
        )
        
        # Add initial log
        session.add_log('info', f'Session gestartet für: {requirement.name}')
        
        return JsonResponse({
            'success': True,
            'session_id': str(session.id),
            'context': context,
            'message': f'Session started for "{requirement.name}"'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def session_status(request, session_id):
    """
    Get status of a Cascade work session
    
    GET /api/cascade/session/{session_id}/
    """
    session = get_object_or_404(CascadeWorkSession, pk=session_id)
    
    return JsonResponse({
        'success': True,
        'session': {
            'id': str(session.id),
            'requirement_id': str(session.requirement.id),
            'requirement_name': session.requirement.name,
            'status': session.status,
            'status_display': session.get_status_display(),
            'current_iteration': session.current_iteration,
            'max_iterations': session.max_iterations,
            'progress_percentage': session.progress_percentage,
            'is_active': session.is_active,
            'started_at': session.started_at.isoformat() if session.started_at else None,
            'completed_at': session.completed_at.isoformat() if session.completed_at else None,
            'error_count': session.error_count,
            'files_changed': session.files_changed,
        }
    })


@login_required
@require_http_methods(["POST"])
def session_stop(request, session_id):
    """
    Stop a running Cascade work session
    
    POST /api/cascade/session/{session_id}/stop/
    """
    session = get_object_or_404(CascadeWorkSession, pk=session_id)
    
    if not session.is_active:
        return JsonResponse({
            'success': False,
            'error': f'Session is already {session.status}'
        }, status=400)
    
    session.stop('stopped')
    session.add_log('warning', 'Session manuell gestoppt')
    
    return JsonResponse({
        'success': True,
        'message': 'Session stopped',
        'session_id': str(session.id)
    })


@login_required
@require_http_methods(["GET"])
def session_logs(request, session_id):
    """
    Get logs for a Cascade work session (with optional since filter for polling)
    
    GET /api/cascade/session/{session_id}/logs/
    GET /api/cascade/session/{session_id}/logs/?since=2025-01-10T08:00:00
    """
    session = get_object_or_404(CascadeWorkSession, pk=session_id)
    
    logs = session.logs.all()
    
    # Filter by timestamp if 'since' provided
    since = request.GET.get('since')
    if since:
        from django.utils.dateparse import parse_datetime
        since_dt = parse_datetime(since)
        if since_dt:
            logs = logs.filter(timestamp__gt=since_dt)
    
    # Limit results
    limit = int(request.GET.get('limit', 100))
    logs = logs[:limit]
    
    return JsonResponse({
        'success': True,
        'session_id': str(session.id),
        'session_status': session.status,
        'is_active': session.is_active,
        'logs': [
            {
                'id': str(log.id),
                'log_type': log.log_type,
                'icon': log.icon,
                'iteration': log.iteration,
                'message': log.message,
                'details': log.details,
                'timestamp': log.timestamp.isoformat(),
            }
            for log in logs
        ]
    })


@login_required
@require_http_methods(["POST"])
def session_log_add(request, session_id):
    """
    Add a log entry to a session (for external integrations)
    
    POST /api/cascade/session/{session_id}/log/
    {
        "log_type": "info|action|stdout|stderr|success|error|warning|file_change|test_result",
        "message": "Log message",
        "details": {}  (optional)
    }
    """
    session = get_object_or_404(CascadeWorkSession, pk=session_id)
    
    try:
        data = json.loads(request.body) if request.body else {}
        log_type = data.get('log_type', 'info')
        message = data.get('message', '')
        details = data.get('details', {})
        
        if not message:
            return JsonResponse({'success': False, 'error': 'message is required'}, status=400)
        
        log = session.add_log(log_type, message, details)
        
        # Track errors
        if log_type in ['error', 'stderr']:
            session.error_count += 1
            session.save()
        
        # Track file changes
        if log_type == 'file_change' and 'file' in details:
            files = session.files_changed or []
            if details['file'] not in files:
                files.append(details['file'])
                session.files_changed = files
                session.save()
        
        return JsonResponse({
            'success': True,
            'log_id': str(log.id),
            'timestamp': log.timestamp.isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)


@login_required
@require_http_methods(["POST"])
def session_iterate(request, session_id):
    """
    Move to next iteration (called after each work cycle)
    
    POST /api/cascade/session/{session_id}/iterate/
    {
        "success_check": true/false,
        "summary": "What was done this iteration"  (optional)
    }
    """
    session = get_object_or_404(CascadeWorkSession, pk=session_id)
    
    if not session.is_active:
        return JsonResponse({
            'success': False,
            'error': f'Session is not active (status: {session.status})'
        }, status=400)
    
    try:
        data = json.loads(request.body) if request.body else {}
        success_check = data.get('success_check', False)
        summary = data.get('summary', '')
        
        # Start session if pending
        if session.status == 'pending':
            session.start()
        
        # Add iteration log
        session.add_log('action', f'Iteration {session.current_iteration + 1} abgeschlossen: {summary or "Keine Details"}')
        
        # Check for success
        if success_check:
            session.mark_success(summary)
            return JsonResponse({
                'success': True,
                'completed': True,
                'status': 'success',
                'message': 'Bug/Feature erfolgreich gelöst!'
            })
        
        # Move to next iteration
        new_iteration = session.increment_iteration()
        
        # Check if max iterations reached
        if session.status == 'max_iterations':
            return JsonResponse({
                'success': True,
                'completed': True,
                'status': 'max_iterations',
                'message': f'Max iterations ({session.max_iterations}) erreicht',
                'iteration': new_iteration
            })
        
        return JsonResponse({
            'success': True,
            'completed': False,
            'status': session.status,
            'iteration': new_iteration,
            'remaining': session.max_iterations - new_iteration
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)


@login_required
@require_http_methods(["GET"])
def active_sessions(request):
    """
    Get all active sessions (for dashboard/monitoring)
    
    GET /api/cascade/sessions/active/
    """
    sessions = CascadeWorkSession.objects.filter(
        status__in=['pending', 'running']
    ).select_related('requirement', 'created_by')
    
    return JsonResponse({
        'success': True,
        'count': sessions.count(),
        'sessions': [
            {
                'id': str(s.id),
                'requirement_id': str(s.requirement.id),
                'requirement_name': s.requirement.name,
                'status': s.status,
                'progress_percentage': s.progress_percentage,
                'current_iteration': s.current_iteration,
                'max_iterations': s.max_iterations,
                'created_by': s.created_by.username if s.created_by else None,
                'started_at': s.started_at.isoformat() if s.started_at else None,
            }
            for s in sessions
        ]
    })
