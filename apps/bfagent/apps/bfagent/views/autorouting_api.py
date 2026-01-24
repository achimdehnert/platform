"""
Autorouting API Endpoints
=========================

API-Endpoints für das Autorouting-System im Test Studio.

Endpoints:
    POST /api/autorouting/start/           - Startet Autorouting-Run
    GET  /api/autorouting/run/<id>/        - Run-Status abrufen
    POST /api/autorouting/run/<id>/cancel/ - Run abbrechen
    GET  /api/autorouting/runs/            - Liste aller Runs für Requirement
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from ..models_testing import TestRequirement
from ..models_autocoding import AutocodingRun, ToolCall, Artifact
from ..services.autorouting_orchestrator import AutoroutingOrchestrator

logger = logging.getLogger(__name__)

# Flag für async Execution
USE_CELERY = True


# =============================================================================
# API Endpoints
# =============================================================================

@login_required
@require_http_methods(["POST"])
def start_autorouting(request):
    """
    Startet einen Autorouting-Run für ein Requirement.
    
    POST Body:
        {
            "requirement_id": 123,
            "llm_id": null,  // optional
            "async": false   // optional - true für Background-Execution
        }
    
    Returns:
        {
            "success": true,
            "run_id": "uuid...",
            "status": "analyzing"
        }
    """
    try:
        data = json.loads(request.body)
        requirement_id = data.get('requirement_id')
        llm_id = data.get('llm_id')
        run_async = data.get('async', False)
        
        if not requirement_id:
            return JsonResponse({
                'success': False,
                'error': 'requirement_id ist erforderlich'
            }, status=400)
        
        requirement = get_object_or_404(TestRequirement, id=requirement_id)
        
        logger.info(f"[AUTOROUTING-API] Start für Requirement {requirement_id} (async={run_async})")
        
        # Async via Celery
        if run_async and USE_CELERY:
            try:
                from ..tasks.autorouting_tasks import process_requirement_async
                task = process_requirement_async.delay(
                    requirement_id=str(requirement_id),
                    user_id=request.user.id,
                    llm_id=llm_id
                )
                return JsonResponse({
                    'success': True,
                    'async': True,
                    'task_id': task.id,
                    'status': 'queued',
                    'status_display': 'In Warteschlange'
                })
            except Exception as e:
                logger.warning(f"[AUTOROUTING-API] Celery nicht verfügbar, sync Fallback: {e}")
        
        # Synchron
        orchestrator = AutoroutingOrchestrator()
        result = orchestrator.process_requirement(
            requirement=requirement,
            user=request.user,
            llm_id=llm_id
        )
        
        return JsonResponse({
            'success': result.success,
            'async': False,
            'run_id': str(result.run.id),
            'status': result.run.status,
            'status_display': result.run.get_status_display(),
            'tasks_extracted': result.tasks_extracted,
            'sessions_created': len(result.sessions),
            'error': result.error if not result.success else None
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Ungültiges JSON'
        }, status=400)
    except Exception as e:
        logger.exception(f"[AUTOROUTING-API] Fehler: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_run_status(request, run_id):
    """
    Gibt den Status eines Autorouting-Runs zurück.
    
    Returns:
        {
            "success": true,
            "run": { ... }
        }
    """
    try:
        run = get_object_or_404(AutocodingRun, id=run_id)
        
        return JsonResponse({
            'success': True,
            'run': _serialize_run(run)
        })
        
    except Exception as e:
        logger.exception(f"[AUTOROUTING-API] Fehler bei get_run_status: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def cancel_run(request, run_id):
    """
    Bricht einen laufenden Run ab.
    """
    try:
        run = get_object_or_404(AutocodingRun, id=run_id)
        
        if run.status in ['completed', 'failed', 'cancelled']:
            return JsonResponse({
                'success': False,
                'error': f'Run kann nicht abgebrochen werden (Status: {run.status})'
            }, status=400)
        
        orchestrator = AutoroutingOrchestrator()
        success = orchestrator.cancel_run(str(run_id))
        
        return JsonResponse({
            'success': success,
            'status': run.status if not success else 'cancelled'
        })
        
    except Exception as e:
        logger.exception(f"[AUTOROUTING-API] Fehler bei cancel_run: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def list_runs(request):
    """
    Listet alle Runs für ein Requirement.
    
    Query Params:
        requirement_id: int (required)
        limit: int (default 10)
    """
    try:
        requirement_id = request.GET.get('requirement_id')
        limit = int(request.GET.get('limit', 10))
        
        if not requirement_id:
            return JsonResponse({
                'success': False,
                'error': 'requirement_id ist erforderlich'
            }, status=400)
        
        runs = AutocodingRun.objects.filter(
            requirement_id=requirement_id
        ).order_by('-created_at')[:limit]
        
        return JsonResponse({
            'success': True,
            'runs': [_serialize_run(run, include_details=False) for run in runs],
            'total': AutocodingRun.objects.filter(requirement_id=requirement_id).count()
        })
        
    except Exception as e:
        logger.exception(f"[AUTOROUTING-API] Fehler bei list_runs: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_run_artifacts(request, run_id):
    """
    Gibt alle Artifacts eines Runs zurück.
    """
    try:
        run = get_object_or_404(AutocodingRun, id=run_id)
        artifacts = run.artifacts.all()
        
        return JsonResponse({
            'success': True,
            'artifacts': [_serialize_artifact(a) for a in artifacts]
        })
        
    except Exception as e:
        logger.exception(f"[AUTOROUTING-API] Fehler bei get_run_artifacts: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# =============================================================================
# Serialization Helpers
# =============================================================================

def _serialize_run(run: AutocodingRun, include_details: bool = True) -> dict:
    """Serialisiert einen AutocodingRun."""
    data = {
        'id': str(run.id),
        'requirement_id': run.requirement_id,
        'status': run.status,
        'status_display': run.get_status_display(),
        'complexity': run.complexity,
        'risk': run.risk,
        'current_iteration': run.current_iteration,
        'max_iterations': run.max_iterations,
        'total_tokens': run.total_tokens,
        'total_cost': float(run.total_cost),
        'created_at': run.created_at.isoformat() if run.created_at else None,
        'duration_seconds': run.duration_seconds,
        'llm_name': run.llm.name if run.llm else None,
    }
    
    if include_details:
        data.update({
            'task_text': run.task_text[:500] if run.task_text else '',
            'routing_reason': run.routing_reason,
            'error_message': run.error_message,
            'tasks_extracted': run.tasks_extracted,
            'tool_calls_count': run.tool_calls.count(),
            'artifacts_count': run.artifacts.count(),
        })
    
    return data


def _serialize_artifact(artifact: Artifact) -> dict:
    """Serialisiert ein Artifact."""
    return {
        'id': str(artifact.id),
        'kind': artifact.kind,
        'kind_display': artifact.get_kind_display(),
        'file_path': artifact.file_path,
        'size_bytes': artifact.size_bytes,
        'sha256': artifact.sha256[:12] + '...' if artifact.sha256 else None,
        'has_refactor_session': artifact.refactor_session_id is not None,
        'refactor_session_id': str(artifact.refactor_session_id) if artifact.refactor_session_id else None,
        'created_at': artifact.created_at.isoformat() if artifact.created_at else None,
    }
