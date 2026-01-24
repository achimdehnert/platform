"""
MCP Dashboard Celery Tasks
==========================

Async tasks for:
- Data synchronization
- Refactoring sessions
- Cleanup operations

All tasks emit progress updates for SSE consumption.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()


# =============================================================================
# SYNC DATA TASK
# =============================================================================

@shared_task(
    bind=True,
    name='mcp.sync_data',
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=360,
)
def sync_mcp_data_task(self, triggered_by: int = None) -> Dict[str, Any]:
    """
    Synchronize MCP data from various sources.
    
    This task:
    1. Scans project structure for domains
    2. Updates domain configurations
    3. Refreshes protected paths
    4. Updates component registry
    
    Args:
        triggered_by: User ID who triggered the sync
    
    Returns:
        Dict with sync results
    """
    from bfagent_mcp.services.sync_service import MCPSyncService
    
    logger.info(f"MCP sync task started (task_id: {self.request.id})")
    
    results = {
        'task_id': self.request.id,
        'started_at': timezone.now().isoformat(),
        'triggered_by': triggered_by,
        'domains_synced': 0,
        'paths_updated': 0,
        'errors': [],
    }
    
    try:
        # Initialize sync service
        sync_service = MCPSyncService()
        
        # Step 1: Sync domains
        self.update_state(state='PROGRESS', meta={'step': 'domains', 'progress': 20})
        domain_results = sync_service.sync_domains()
        results['domains_synced'] = domain_results.get('synced', 0)
        
        # Step 2: Sync protected paths
        self.update_state(state='PROGRESS', meta={'step': 'paths', 'progress': 50})
        path_results = sync_service.sync_protected_paths()
        results['paths_updated'] = path_results.get('updated', 0)
        
        # Step 3: Sync components
        self.update_state(state='PROGRESS', meta={'step': 'components', 'progress': 80})
        sync_service.sync_components()
        
        # Step 4: Update naming conventions
        self.update_state(state='PROGRESS', meta={'step': 'conventions', 'progress': 95})
        sync_service.sync_naming_conventions()
        
        results['status'] = 'success'
        results['ended_at'] = timezone.now().isoformat()
        
        logger.info(f"MCP sync completed: {results}")
        
        return results
        
    except Exception as e:
        logger.error(f"MCP sync failed: {e}", exc_info=True)
        results['status'] = 'failed'
        results['errors'].append(str(e))
        results['ended_at'] = timezone.now().isoformat()
        
        # Retry on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return results


# =============================================================================
# REFACTOR SESSION TASK
# =============================================================================

@shared_task(
    bind=True,
    name='mcp.start_refactor_session',
    max_retries=0,  # No automatic retry for refactoring
    soft_time_limit=1800,  # 30 minutes
    time_limit=2000,
)
def start_refactor_session_task(
    self,
    session_id: int,
    user_id: int = None
) -> Dict[str, Any]:
    """
    Execute a refactoring session.
    
    This task:
    1. Loads session configuration
    2. Creates backup of target files
    3. Applies refactoring rules
    4. Validates changes
    5. Updates session status
    
    Args:
        session_id: MCPRefactorSession ID
        user_id: User who triggered the session
    
    Returns:
        Dict with session results
    """
    from bfagent_mcp.models_mcp import MCPRefactorSession, MCPSessionFileChange
    from bfagent_mcp.services.refactor_service import MCPRefactorService
    
    logger.info(f"Refactor session {session_id} started (task_id: {self.request.id})")
    
    results = {
        'task_id': self.request.id,
        'session_id': session_id,
        'started_at': timezone.now().isoformat(),
        'files_changed': 0,
        'lines_added': 0,
        'lines_removed': 0,
        'errors': [],
    }
    
    try:
        # Load session
        session = MCPRefactorSession.objects.select_related(
            'domain_config__domain',
            'domain_config__risk_level'
        ).get(id=session_id)
        
        # Update status to in_progress
        session.status = 'in_progress'
        session.started_at = timezone.now()
        session.save(update_fields=['status', 'started_at'])
        
        # Initialize refactor service
        refactor_service = MCPRefactorService(session=session)
        
        # Step 1: Create backup
        self.update_state(state='PROGRESS', meta={
            'session_id': session_id,
            'step': 'backup',
            'progress': 10,
            'message': 'Creating backup...'
        })
        backup_path = refactor_service.create_backup()
        session.backup_path = backup_path
        session.save(update_fields=['backup_path'])
        
        # Step 2: Analyze files
        self.update_state(state='PROGRESS', meta={
            'session_id': session_id,
            'step': 'analyze',
            'progress': 25,
            'message': 'Analyzing files...'
        })
        files_to_process = refactor_service.analyze_files()
        
        # Step 3: Apply refactoring
        total_files = len(files_to_process)
        for idx, file_info in enumerate(files_to_process):
            progress = 25 + int((idx / total_files) * 60)
            
            self.update_state(state='PROGRESS', meta={
                'session_id': session_id,
                'step': 'refactor',
                'progress': progress,
                'current_file': file_info['path'],
                'files_processed': idx + 1,
                'total_files': total_files,
            })
            
            try:
                change_result = refactor_service.refactor_file(file_info)
                
                if change_result['changed']:
                    # Record file change
                    MCPSessionFileChange.objects.create(
                        session=session,
                        file_path=file_info['path'],
                        change_type=change_result['change_type'],
                        lines_added=change_result.get('lines_added', 0),
                        lines_removed=change_result.get('lines_removed', 0),
                        diff_content=change_result.get('diff', ''),
                    )
                    
                    results['files_changed'] += 1
                    results['lines_added'] += change_result.get('lines_added', 0)
                    results['lines_removed'] += change_result.get('lines_removed', 0)
                    
            except Exception as e:
                logger.warning(f"Failed to refactor {file_info['path']}: {e}")
                results['errors'].append({
                    'file': file_info['path'],
                    'error': str(e)
                })
        
        # Step 4: Validate changes
        self.update_state(state='PROGRESS', meta={
            'session_id': session_id,
            'step': 'validate',
            'progress': 90,
            'message': 'Validating changes...'
        })
        
        validation_result = refactor_service.validate_changes()
        
        if not validation_result['valid']:
            # Rollback if validation fails
            self.update_state(state='PROGRESS', meta={
                'session_id': session_id,
                'step': 'rollback',
                'progress': 95,
                'message': 'Rolling back changes...'
            })
            refactor_service.rollback()
            
            session.status = 'failed'
            session.error_message = 'Validation failed: ' + str(validation_result['errors'])
            results['status'] = 'failed'
            results['validation_errors'] = validation_result['errors']
        else:
            session.status = 'completed'
            results['status'] = 'success'
        
        # Finalize session
        session.ended_at = timezone.now()
        session.files_changed = results['files_changed']
        session.lines_added = results['lines_added']
        session.lines_removed = results['lines_removed']
        session.save()
        
        results['ended_at'] = timezone.now().isoformat()
        
        logger.info(f"Refactor session {session_id} completed: {results['status']}")
        
        return results
        
    except MCPRefactorSession.DoesNotExist:
        logger.error(f"Session {session_id} not found")
        results['status'] = 'failed'
        results['errors'].append(f'Session {session_id} not found')
        return results
        
    except Exception as e:
        logger.error(f"Refactor session {session_id} failed: {e}", exc_info=True)
        
        # Update session status
        try:
            session = MCPRefactorSession.objects.get(id=session_id)
            session.status = 'failed'
            session.error_message = str(e)
            session.ended_at = timezone.now()
            session.save()
        except Exception:
            pass
        
        results['status'] = 'failed'
        results['errors'].append(str(e))
        results['ended_at'] = timezone.now().isoformat()
        
        return results


# =============================================================================
# CLEANUP TASK
# =============================================================================

@shared_task(
    name='mcp.cleanup_old_sessions',
    soft_time_limit=300,
)
def cleanup_old_sessions_task(days: int = 30) -> Dict[str, Any]:
    """
    Cleanup old refactor sessions and their backups.
    
    Args:
        days: Delete sessions older than this many days
    
    Returns:
        Dict with cleanup results
    """
    from bfagent_mcp.models_mcp import MCPRefactorSession
    import shutil
    import os
    
    logger.info(f"Cleanup task started: removing sessions older than {days} days")
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    old_sessions = MCPRefactorSession.objects.filter(
        started_at__lt=cutoff_date,
        status__in=['completed', 'failed', 'cancelled']
    )
    
    results = {
        'sessions_deleted': 0,
        'backups_removed': 0,
        'errors': [],
    }
    
    for session in old_sessions:
        try:
            # Remove backup directory if exists
            if session.backup_path and os.path.exists(session.backup_path):
                shutil.rmtree(session.backup_path)
                results['backups_removed'] += 1
            
            # Delete session (cascades to file changes)
            session.delete()
            results['sessions_deleted'] += 1
            
        except Exception as e:
            logger.warning(f"Failed to cleanup session {session.id}: {e}")
            results['errors'].append({
                'session_id': session.id,
                'error': str(e)
            })
    
    logger.info(f"Cleanup completed: {results}")
    
    return results


# =============================================================================
# MONITORING TASK
# =============================================================================

@shared_task(
    name='mcp.check_stalled_sessions',
    soft_time_limit=60,
)
def check_stalled_sessions_task() -> Dict[str, Any]:
    """
    Check for stalled sessions and mark them as failed.
    
    A session is considered stalled if it's been in_progress for > 1 hour.
    """
    from bfagent_mcp.models_mcp import MCPRefactorSession
    
    stall_threshold = timezone.now() - timedelta(hours=1)
    
    stalled_sessions = MCPRefactorSession.objects.filter(
        status='in_progress',
        started_at__lt=stall_threshold
    )
    
    results = {
        'stalled_sessions': 0,
        'sessions_marked_failed': [],
    }
    
    for session in stalled_sessions:
        session.status = 'failed'
        session.error_message = 'Session stalled (timeout)'
        session.ended_at = timezone.now()
        session.save()
        
        results['stalled_sessions'] += 1
        results['sessions_marked_failed'].append(session.id)
        
        logger.warning(f"Session {session.id} marked as failed (stalled)")
    
    return results


# =============================================================================
# CELERY BEAT SCHEDULE (add to settings.py)
# =============================================================================

"""
# settings.py

CELERY_BEAT_SCHEDULE = {
    # ... existing schedules ...
    
    'mcp-cleanup-old-sessions': {
        'task': 'mcp.cleanup_old_sessions',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
        'kwargs': {'days': 30},
    },
    'mcp-check-stalled-sessions': {
        'task': 'mcp.check_stalled_sessions',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
}
"""
