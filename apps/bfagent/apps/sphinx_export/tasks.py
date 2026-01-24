"""
Sphinx Export Celery Tasks
==========================

Periodische Tasks für Sphinx-Dokumentations-Synchronisation.

Setup in settings:
    CELERY_BEAT_SCHEDULE = {
        'sphinx-sync-daily': {
            'task': 'apps.sphinx_export.tasks.sphinx_sync_check',
            'schedule': crontab(hour=6, minute=0),  # Täglich um 6:00
        },
    }
"""

from celery import shared_task
from django.conf import settings
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1)
def sphinx_sync_check(self, notify: bool = True) -> dict:
    """
    Prüft Sphinx-Dokumentation auf Änderungen.
    
    Kann als Celery Task oder direkt aufgerufen werden.
    
    Args:
        notify: Wenn True, sendet Benachrichtigung bei Änderungen
        
    Returns:
        Dict mit Sync-Ergebnis
    """
    from .sync_service import get_sphinx_sync_service
    
    try:
        service = get_sphinx_sync_service()
        report = service.check_changes()
        
        result = {
            'success': True,
            'has_changes': report.has_changes,
            'total_issues': report.total_issues,
            'python_changes': len(report.python_changes),
            'doc_changes': len(report.doc_changes),
            'missing_docs': len(report.missing_docs),
            'undocumented': len(report.undocumented_items),
        }
        
        if report.has_changes and notify:
            _send_sync_notification(report)
        
        logger.info(f"Sphinx sync check completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Sphinx sync check failed: {e}")
        return {
            'success': False,
            'error': str(e),
        }


@shared_task(bind=True, max_retries=1)
def sphinx_full_sync(self, generate_stubs: bool = True, rebuild: bool = True) -> dict:
    """
    Führt vollständige Sphinx-Synchronisation durch.
    
    Args:
        generate_stubs: Fehlende Stubs generieren
        rebuild: Dokumentation neu bauen
        
    Returns:
        Dict mit Sync-Ergebnis
    """
    from .sync_service import get_sphinx_sync_service
    
    try:
        service = get_sphinx_sync_service()
        
        # 1. Check
        report = service.check_changes()
        
        # 2. Generate stubs
        stubs_generated = []
        if generate_stubs and report.missing_docs:
            stubs_generated = service.generate_missing_stubs(dry_run=False)
        
        # 3. Rebuild
        build_success = True
        build_output = ""
        if rebuild:
            build_success, build_output = service.rebuild_docs()
        
        result = {
            'success': True,
            'check': {
                'has_changes': report.has_changes,
                'total_issues': report.total_issues,
            },
            'stubs_generated': len(stubs_generated),
            'build_success': build_success,
        }
        
        logger.info(f"Sphinx full sync completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Sphinx full sync failed: {e}")
        return {
            'success': False,
            'error': str(e),
        }


@shared_task
def sphinx_generate_report(output_path: str = None) -> dict:
    """
    Generiert Sphinx Sync Report als Markdown.
    
    Args:
        output_path: Ausgabepfad (optional)
        
    Returns:
        Dict mit Report-Pfad
    """
    from .sync_service import get_sphinx_sync_service
    from datetime import datetime
    
    try:
        service = get_sphinx_sync_service()
        report = service.check_changes()
        
        markdown = report.to_markdown()
        
        if output_path:
            path = Path(output_path)
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            path = Path(settings.BASE_DIR) / 'docs' / f'sync_report_{timestamp}.md'
        
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding='utf-8')
        
        return {
            'success': True,
            'report_path': str(path),
            'total_issues': report.total_issues,
        }
        
    except Exception as e:
        logger.error(f"Sphinx report generation failed: {e}")
        return {
            'success': False,
            'error': str(e),
        }


def _send_sync_notification(report):
    """Sendet Benachrichtigung über Sphinx-Änderungen."""
    try:
        # Hier könnte Email, Slack, etc. integriert werden
        logger.warning(
            f"Sphinx Sync: {report.total_issues} Issues gefunden - "
            f"{len(report.python_changes)} Python, "
            f"{len(report.missing_docs)} fehlende Doku"
        )
    except Exception as e:
        logger.error(f"Failed to send sync notification: {e}")
