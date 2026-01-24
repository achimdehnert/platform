"""
Celery Tasks für Autorouting System
====================================

Background-Tasks für asynchrone Verarbeitung von Autorouting-Runs.
"""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='bfagent.autorouting.process_requirement',
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=600,  # 10 Minuten
    time_limit=660,       # 11 Minuten hard limit
)
def process_requirement_async(self, requirement_id: str, user_id: int = None, llm_id: int = None):
    """
    Verarbeitet ein Requirement asynchron im Background.
    
    Args:
        requirement_id: UUID des Requirements
        user_id: Optional User ID
        llm_id: Optional LLM ID für Override
        
    Returns:
        dict mit Ergebnis
    """
    from ..models_testing import TestRequirement
    from ..models_autocoding import AutocodingRun
    from ..services.autorouting_orchestrator import AutoroutingOrchestrator
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    logger.info(f"[CELERY-AUTOROUTING] Start Task für Requirement {requirement_id}")
    
    try:
        requirement = TestRequirement.objects.get(id=requirement_id)
        user = User.objects.get(id=user_id) if user_id else None
        
        orchestrator = AutoroutingOrchestrator()
        result = orchestrator.process_requirement(
            requirement=requirement,
            user=user,
            llm_id=llm_id
        )
        
        logger.info(f"[CELERY-AUTOROUTING] Ergebnis: success={result.success}, "
                   f"tasks={result.tasks_extracted}, sessions={len(result.sessions)}")
        
        return {
            'success': result.success,
            'run_id': str(result.run.id),
            'status': result.run.status,
            'tasks_extracted': result.tasks_extracted,
            'sessions_created': len(result.sessions),
            'error': result.error
        }
        
    except TestRequirement.DoesNotExist:
        logger.error(f"[CELERY-AUTOROUTING] Requirement {requirement_id} nicht gefunden")
        return {'success': False, 'error': 'Requirement nicht gefunden'}
        
    except Exception as e:
        logger.exception(f"[CELERY-AUTOROUTING] Fehler: {e}")
        
        # Bei Retry-fähigen Fehlern
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {'success': False, 'error': str(e)}


@shared_task(
    name='bfagent.autorouting.cancel_run',
    soft_time_limit=30,
)
def cancel_run_async(run_id: str):
    """
    Bricht einen laufenden Run ab.
    """
    from ..models_autocoding import AutocodingRun
    from ..services.autorouting_orchestrator import AutoroutingOrchestrator
    
    logger.info(f"[CELERY-AUTOROUTING] Cancel Run {run_id}")
    
    try:
        orchestrator = AutoroutingOrchestrator()
        success = orchestrator.cancel_run(run_id)
        return {'success': success}
    except Exception as e:
        logger.exception(f"[CELERY-AUTOROUTING] Cancel Fehler: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(
    name='bfagent.autorouting.cleanup_old_runs',
    soft_time_limit=300,
)
def cleanup_old_runs(days: int = 30):
    """
    Bereinigt alte Runs und deren Artifacts.
    
    Args:
        days: Runs älter als X Tage werden gelöscht
    """
    from ..models_autocoding import AutocodingRun
    from datetime import timedelta
    
    logger.info(f"[CELERY-AUTOROUTING] Cleanup Runs älter als {days} Tage")
    
    cutoff = timezone.now() - timedelta(days=days)
    
    # Nur abgeschlossene/fehlgeschlagene Runs
    old_runs = AutocodingRun.objects.filter(
        created_at__lt=cutoff,
        status__in=['completed', 'failed', 'cancelled']
    )
    
    count = old_runs.count()
    old_runs.delete()
    
    logger.info(f"[CELERY-AUTOROUTING] {count} alte Runs gelöscht")
    return {'deleted': count}


@shared_task(
    name='bfagent.autorouting.retry_failed_run',
    soft_time_limit=600,
)
def retry_failed_run(run_id: str):
    """
    Wiederholt einen fehlgeschlagenen Run.
    """
    from ..models_autocoding import AutocodingRun
    from ..services.autorouting_orchestrator import AutoroutingOrchestrator
    
    logger.info(f"[CELERY-AUTOROUTING] Retry Run {run_id}")
    
    try:
        run = AutocodingRun.objects.get(id=run_id)
        
        if run.status != 'failed':
            return {'success': False, 'error': 'Run ist nicht fehlgeschlagen'}
        
        # Reset Status
        run.status = 'created'
        run.error_message = ''
        run.current_iteration = 0
        run.save()
        
        # Erneut verarbeiten
        orchestrator = AutoroutingOrchestrator()
        result = orchestrator._execute_run(run)
        
        return {
            'success': result.success,
            'status': run.status,
            'error': result.error
        }
        
    except AutocodingRun.DoesNotExist:
        return {'success': False, 'error': 'Run nicht gefunden'}
    except Exception as e:
        logger.exception(f"[CELERY-AUTOROUTING] Retry Fehler: {e}")
        return {'success': False, 'error': str(e)}
