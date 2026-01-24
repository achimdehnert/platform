"""
Task Executor Service
=====================

Executes delegated tasks using the LLM Router.
Designed to work both synchronously and with Celery (future).

Usage:
    from apps.bfagent.services.task_executor import TaskExecutor
    
    executor = TaskExecutor()
    result = executor.execute_task(task_id)
    
    # Or create and execute in one step
    result = executor.create_and_execute(
        name="Fix typo in button",
        prompt="Fix the typo...",
        complexity='low',
        task_type='coding'
    )
"""

import logging
from typing import Any, Dict, Optional
from django.utils import timezone
from django.db import transaction

from .llm_router import get_router, ComplexityLevel

logger = logging.getLogger(__name__)


class TaskExecutor:
    """
    Executor for delegated LLM tasks.
    
    Handles:
    - Task creation with automatic routing
    - Synchronous execution (current)
    - Celery task queueing (future)
    - Result tracking and logging
    """
    
    def __init__(self):
        self.router = get_router()
    
    def create_task(self,
                   name: str,
                   prompt: str,
                   system_prompt: str = "",
                   description: str = "",
                   complexity: str = 'auto',
                   task_type: str = 'coding',
                   requirement_id: str = None,
                   llm_override_id: int = None,
                   user=None) -> 'DelegatedTask':
        """
        Create a new delegated task with routing decision.
        
        Args:
            name: Task name
            prompt: The prompt to execute
            system_prompt: Optional system prompt
            description: Task description for complexity estimation
            complexity: 'auto', 'low', 'medium', 'high'
            task_type: 'coding', 'writing', 'analysis', etc.
            requirement_id: Optional linked requirement UUID
            llm_override_id: Optional specific LLM to use
            user: User creating the task
        
        Returns:
            DelegatedTask instance (not yet executed)
        """
        from apps.bfagent.models_tasks import DelegatedTask
        
        # Get routing decision
        routing = self.router.get_routing_decision(
            complexity=complexity,
            task_type=task_type,
            description=description or prompt[:500],
            llm_override_id=llm_override_id
        )
        
        # Determine estimated complexity if auto
        complexity_estimated = ''
        if complexity == 'auto':
            estimated = self.router.estimate_complexity(description or prompt[:500])
            complexity_estimated = estimated.value
        
        # Create task
        task = DelegatedTask(
            name=name,
            description=description,
            task_type=task_type,
            complexity=complexity,
            complexity_estimated=complexity_estimated,
            prompt=prompt,
            system_prompt=system_prompt,
            routing_reason=routing.reason,
            requires_cascade=routing.requires_cascade,
            estimated_cost=routing.estimated_cost,
            created_by=user
        )
        
        # Set LLM if not requiring Cascade
        if not routing.requires_cascade and routing.llm_id:
            from apps.bfagent.models import Llms
            try:
                task.llm_selected = Llms.objects.get(id=routing.llm_id)
            except Llms.DoesNotExist:
                pass
        
        # Link requirement if provided
        if requirement_id:
            from apps.bfagent.models_testing import TestRequirement
            try:
                task.requirement = TestRequirement.objects.get(id=requirement_id)
            except TestRequirement.DoesNotExist:
                pass
        
        task.save()
        
        # Log creation
        self._log_event(task, 'created', {
            'routing': routing.__dict__,
            'complexity_estimated': complexity_estimated
        })
        
        return task
    
    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """
        Execute a task synchronously.
        
        Args:
            task_id: UUID of the task
        
        Returns:
            Dict with execution result
        """
        from apps.bfagent.models_tasks import DelegatedTask
        
        try:
            task = DelegatedTask.objects.get(id=task_id)
        except DelegatedTask.DoesNotExist:
            return {'ok': False, 'error': f'Task {task_id} not found'}
        
        return self._execute(task)
    
    def _execute(self, task: 'DelegatedTask') -> Dict[str, Any]:
        """Internal execution logic"""
        from apps.bfagent.models_tasks import DelegatedTask
        
        # Check if requires Cascade
        if task.requires_cascade:
            return {
                'ok': False,
                'task_id': str(task.id),
                'requires_cascade': True,
                'message': f"Task requires Cascade: {task.routing_reason}",
                'complexity': task.complexity_estimated or task.complexity
            }
        
        # Mark as running
        task.mark_started()
        self._log_event(task, 'started', {'llm': task.llm_selected.name if task.llm_selected else 'unknown'})
        
        try:
            # Execute via router
            result = self.router.execute(
                prompt=task.prompt,
                system_prompt=task.system_prompt,
                complexity=task.complexity_estimated or task.complexity,
                task_type=task.task_type,
                llm_override_id=task.llm_selected.id if task.llm_selected else None
            )
            
            if result.get('ok'):
                task.mark_completed(
                    result_text=result.get('text', ''),
                    tokens=result.get('tokens_used', 0),
                    latency=result.get('latency_ms', 0)
                )
                self._log_event(task, 'completed', {
                    'tokens': result.get('tokens_used', 0),
                    'latency_ms': result.get('latency_ms', 0)
                })
                
                return {
                    'ok': True,
                    'task_id': str(task.id),
                    'result': result.get('text'),
                    'llm_used': task.llm_selected.name if task.llm_selected else 'unknown',
                    'latency_ms': result.get('latency_ms', 0),
                    'requires_cascade': False
                }
            else:
                error = result.get('error', 'Unknown error')
                task.mark_failed(error)
                self._log_event(task, 'failed', {'error': error})
                
                return {
                    'ok': False,
                    'task_id': str(task.id),
                    'error': error,
                    'requires_cascade': result.get('requires_cascade', False)
                }
                
        except Exception as e:
            logger.exception(f"Task execution failed: {task.id}")
            task.mark_failed(str(e))
            self._log_event(task, 'failed', {'error': str(e), 'exception': type(e).__name__})
            
            return {
                'ok': False,
                'task_id': str(task.id),
                'error': str(e),
                'requires_cascade': False
            }
    
    def create_and_execute(self,
                          name: str,
                          prompt: str,
                          system_prompt: str = "",
                          description: str = "",
                          complexity: str = 'auto',
                          task_type: str = 'coding',
                          requirement_id: str = None,
                          llm_override_id: int = None,
                          user=None) -> Dict[str, Any]:
        """
        Create and immediately execute a task.
        
        Convenience method that combines create_task and execute_task.
        
        Returns:
            Dict with task_id and execution result
        """
        task = self.create_task(
            name=name,
            prompt=prompt,
            system_prompt=system_prompt,
            description=description,
            complexity=complexity,
            task_type=task_type,
            requirement_id=requirement_id,
            llm_override_id=llm_override_id,
            user=user
        )
        
        result = self._execute(task)
        result['task_id'] = str(task.id)
        
        return result
    
    def queue_task(self, task_id: str) -> Dict[str, Any]:
        """
        Queue a task for background execution (Celery).
        
        Currently runs synchronously. When Celery is enabled,
        this will queue the task instead.
        
        Args:
            task_id: UUID of the task
        
        Returns:
            Dict with queue status
        """
        # TODO: When Celery is enabled, use:
        # from apps.bfagent.tasks import execute_delegated_task
        # result = execute_delegated_task.delay(task_id)
        # return {'queued': True, 'celery_task_id': result.id}
        
        # For now, execute synchronously
        logger.info(f"Celery not enabled, executing task {task_id} synchronously")
        return self.execute_task(task_id)
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get current status of a task"""
        from apps.bfagent.models_tasks import DelegatedTask
        
        try:
            task = DelegatedTask.objects.get(id=task_id)
            return {
                'task_id': str(task.id),
                'name': task.name,
                'status': task.status,
                'complexity': task.complexity_estimated or task.complexity,
                'llm_used': task.llm_selected.name if task.llm_selected else None,
                'requires_cascade': task.requires_cascade,
                'created_at': task.created_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'duration_seconds': task.duration_seconds,
                'has_result': bool(task.result_text),
                'has_error': bool(task.error_message),
            }
        except DelegatedTask.DoesNotExist:
            return {'error': f'Task {task_id} not found'}
    
    def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """Get full result of a completed task"""
        from apps.bfagent.models_tasks import DelegatedTask
        
        try:
            task = DelegatedTask.objects.get(id=task_id)
            return {
                'task_id': str(task.id),
                'status': task.status,
                'result': task.result_text if task.status == 'completed' else None,
                'error': task.error_message if task.status == 'failed' else None,
                'requires_cascade': task.requires_cascade,
                'routing_reason': task.routing_reason,
                'llm_used': task.llm_selected.name if task.llm_selected else None,
                'tokens_used': task.tokens_used,
                'latency_ms': task.latency_ms,
                'duration_seconds': task.duration_seconds,
            }
        except DelegatedTask.DoesNotExist:
            return {'error': f'Task {task_id} not found'}
    
    def _log_event(self, task: 'DelegatedTask', event: str, details: dict):
        """Log a task execution event"""
        from apps.bfagent.models_tasks import TaskExecutionLog
        
        try:
            TaskExecutionLog.objects.create(
                task=task,
                event=event,
                details=details
            )
        except Exception as e:
            logger.warning(f"Failed to log task event: {e}")


# Singleton instance
_executor_instance = None

def get_executor() -> TaskExecutor:
    """Get singleton executor instance"""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = TaskExecutor()
    return _executor_instance
