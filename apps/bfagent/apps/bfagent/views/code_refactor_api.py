"""
Code Refactor API Endpoints

REST API für LLM-gestütztes Code-Refactoring.
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from apps.bfagent.models_testing import CodeRefactorSession, TestRequirement
from apps.bfagent.services.code_refactor import CodeRefactorService

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def create_session(request):
    """
    Erstellt eine neue Refactoring-Session.
    
    POST /api/refactor/session/create/
    {
        "requirement_id": "uuid",
        "file_path": "apps/bfagent/services/llm_client.py",
        "instruction": "Verbessere Error-Handling"
    }
    """
    try:
        data = json.loads(request.body)
        
        requirement_id = data.get('requirement_id')
        file_path = data.get('file_path')
        instruction = data.get('instruction')
        
        if not all([requirement_id, file_path, instruction]):
            return JsonResponse({
                'success': False,
                'error': 'requirement_id, file_path und instruction sind erforderlich'
            }, status=400)
        
        # Requirement laden
        try:
            requirement = TestRequirement.objects.get(pk=requirement_id)
        except TestRequirement.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Requirement {requirement_id} nicht gefunden'
            }, status=404)
        
        # Session erstellen
        service = CodeRefactorService()
        session = service.create_session(
            requirement=requirement,
            file_path=file_path,
            instruction=instruction,
            user=request.user
        )
        
        return JsonResponse({
            'success': True,
            'session': _serialize_session(session)
        })
        
    except FileNotFoundError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=404)
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.exception(f"Error creating refactor session: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def generate_proposal(request, session_id):
    """
    Generiert Refactoring-Vorschlag mit LLM.
    
    POST /api/refactor/session/<uuid>/generate/
    {
        "llm_id": 8,             // optional, LLM ID aus DB
        "model": "gpt-4o-mini",  // optional, Model Override
        "temperature": 0.3       // optional
    }
    """
    try:
        session = CodeRefactorSession.objects.get(pk=session_id)
        
        data = json.loads(request.body) if request.body else {}
        llm_id = data.get('llm_id')
        model = data.get('model')
        temperature = data.get('temperature')
        
        service = CodeRefactorService()
        session = service.generate(
            session=session,
            llm_id=llm_id,
            model=model,
            temperature=temperature
        )
        
        return JsonResponse({
            'success': True,
            'session': _serialize_session(session)
        })
        
    except CodeRefactorSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Session {session_id} nicht gefunden'
        }, status=404)
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.exception(f"Error generating proposal: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def approve_proposal(request, session_id):
    """
    Genehmigt einen Vorschlag.
    
    POST /api/refactor/session/<uuid>/approve/
    {
        "notes": "Sieht gut aus"  // optional
    }
    """
    try:
        session = CodeRefactorSession.objects.get(pk=session_id)
        
        data = json.loads(request.body) if request.body else {}
        notes = data.get('notes', '')
        
        service = CodeRefactorService()
        session = service.approve(
            session=session,
            user=request.user,
            notes=notes
        )
        
        return JsonResponse({
            'success': True,
            'session': _serialize_session(session)
        })
        
    except CodeRefactorSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Session {session_id} nicht gefunden'
        }, status=404)
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.exception(f"Error approving proposal: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def reject_proposal(request, session_id):
    """
    Lehnt einen Vorschlag ab.
    
    POST /api/refactor/session/<uuid>/reject/
    {
        "notes": "Nicht was ich wollte"  // optional
    }
    """
    try:
        session = CodeRefactorSession.objects.get(pk=session_id)
        
        data = json.loads(request.body) if request.body else {}
        notes = data.get('notes', '')
        
        service = CodeRefactorService()
        session = service.reject(
            session=session,
            user=request.user,
            notes=notes
        )
        
        return JsonResponse({
            'success': True,
            'session': _serialize_session(session)
        })
        
    except CodeRefactorSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Session {session_id} nicht gefunden'
        }, status=404)
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.exception(f"Error rejecting proposal: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def apply_proposal(request, session_id):
    """
    Wendet die Änderung an.
    
    POST /api/refactor/session/<uuid>/apply/
    """
    try:
        session = CodeRefactorSession.objects.get(pk=session_id)
        
        service = CodeRefactorService()
        session = service.apply(
            session=session,
            user=request.user
        )
        
        return JsonResponse({
            'success': True,
            'session': _serialize_session(session),
            'message': f'Änderung erfolgreich angewendet auf {session.file_path}'
        })
        
    except CodeRefactorSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Session {session_id} nicht gefunden'
        }, status=404)
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.exception(f"Error applying proposal: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def revert_proposal(request, session_id):
    """
    Setzt die Änderung zurück.
    
    POST /api/refactor/session/<uuid>/revert/
    """
    try:
        session = CodeRefactorSession.objects.get(pk=session_id)
        
        service = CodeRefactorService()
        session = service.revert(
            session=session,
            user=request.user
        )
        
        return JsonResponse({
            'success': True,
            'session': _serialize_session(session),
            'message': f'Änderung erfolgreich zurückgesetzt auf {session.file_path}'
        })
        
    except CodeRefactorSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Session {session_id} nicht gefunden'
        }, status=404)
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.exception(f"Error reverting proposal: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_session(request, session_id):
    """
    Lädt Session-Details.
    
    GET /api/refactor/session/<uuid>/
    """
    try:
        session = CodeRefactorSession.objects.select_related(
            'requirement', 'created_by', 'reviewed_by', 'applied_by'
        ).get(pk=session_id)
        
        return JsonResponse({
            'success': True,
            'session': _serialize_session(session, include_content=True)
        })
        
    except CodeRefactorSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Session {session_id} nicht gefunden'
        }, status=404)


@login_required
@require_http_methods(["GET"])
def list_sessions(request, requirement_id):
    """
    Listet alle Sessions für ein Requirement.
    
    GET /api/refactor/requirement/<uuid>/sessions/
    """
    try:
        sessions = CodeRefactorSession.objects.filter(
            requirement_id=requirement_id
        ).select_related('created_by').order_by('-created_at')
        
        return JsonResponse({
            'success': True,
            'sessions': [_serialize_session(s) for s in sessions]
        })
        
    except Exception as e:
        logger.exception(f"Error listing sessions: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_diff(request, session_id):
    """
    Lädt nur den Diff einer Session.
    
    GET /api/refactor/session/<uuid>/diff/
    """
    try:
        session = CodeRefactorSession.objects.get(pk=session_id)
        
        return JsonResponse({
            'success': True,
            'diff': session.unified_diff,
            'file_path': session.file_path,
            'lines_added': session.lines_added,
            'lines_removed': session.lines_removed
        })
        
    except CodeRefactorSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Session {session_id} nicht gefunden'
        }, status=404)


def _serialize_session(session: CodeRefactorSession, include_content: bool = False) -> dict:
    """Serialisiert eine Session für JSON-Response."""
    data = {
        'id': str(session.id),
        'requirement_id': str(session.requirement_id),
        'file_path': session.file_path,
        'instruction': session.instruction,
        'status': session.status,
        'status_display': session.get_status_display(),
        'error_message': session.error_message,
        'llm_model': session.llm_model,
        'llm_tokens_input': session.llm_tokens_input,
        'llm_tokens_output': session.llm_tokens_output,
        'llm_tokens_total': session.tokens_total,
        'llm_duration_ms': session.llm_duration_ms,
        'lines_added': session.lines_added,
        'lines_removed': session.lines_removed,
        'can_apply': session.can_apply,
        'can_revert': session.can_revert,
        'created_at': session.created_at.isoformat() if session.created_at else None,
        'created_by': session.created_by.username if session.created_by else None,
        'reviewed_at': session.reviewed_at.isoformat() if session.reviewed_at else None,
        'reviewed_by': session.reviewed_by.username if session.reviewed_by else None,
        'review_notes': session.review_notes,
        'applied_at': session.applied_at.isoformat() if session.applied_at else None,
        'applied_by': session.applied_by.username if session.applied_by else None,
        'reverted_at': session.reverted_at.isoformat() if session.reverted_at else None,
    }
    
    if include_content:
        data['original_content'] = session.original_content
        data['proposed_content'] = session.proposed_content
        data['unified_diff'] = session.unified_diff
    
    return data
