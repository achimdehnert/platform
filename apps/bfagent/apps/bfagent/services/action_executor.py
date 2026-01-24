"""
Action Executor - Handler Pipeline Execution Engine
Executes ActionHandler pipelines with error handling, retries, and metrics tracking
"""

import time
import traceback
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db import transaction

from apps.bfagent.models_handlers import Handler, ActionHandler, HandlerExecution
from apps.bfagent.models import AgentAction, BookProjects


class ActionExecutionError(Exception):
    """Raised when action execution fails"""
    pass


class ActionExecutor:
    """
    Executes AgentAction by running its configured handler pipeline
    
    Features:
    - Dynamic handler loading
    - Phase-based execution (input → processing → output)
    - Error handling (stop/skip/retry/fallback)
    - Conditional execution
    - Performance tracking
    - Metrics updates
    """
    
    def __init__(self, action: AgentAction, project: BookProjects, user=None):
        """
        Initialize executor
        
        Args:
            action: AgentAction to execute
            project: BookProjects instance
            user: User executing the action (optional)
        """
        self.action = action
        self.project = project
        self.user = user
        self.context = {
            'project': project,
            'project_id': project.id,
            'user': user
        }
        self.executions = []  # Track all handler executions
    
    def execute(self, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the action's handler pipeline
        
        Args:
            initial_context: Additional context to merge
            
        Returns:
            Final context with all handler outputs
            
        Raises:
            ActionExecutionError: If execution fails
        """
        # Merge initial context
        if initial_context:
            self.context.update(initial_context)
        
        # Get all handlers for this action, ordered by phase and order
        action_handlers = self.action.action_handlers.filter(
            is_active=True
        ).select_related('handler', 'fallback_handler').order_by('phase', 'order')
        
        if not action_handlers.exists():
            raise ActionExecutionError(
                f"No active handlers configured for action {self.action.name}"
            )
        
        # Execute handlers by phase
        for phase in ['input', 'processing', 'output']:
            phase_handlers = [ah for ah in action_handlers if ah.phase == phase]
            
            if phase_handlers:
                self._execute_phase(phase, phase_handlers)
        
        return self.context
    
    def _execute_phase(self, phase_name: str, action_handlers: List[ActionHandler]):
        """
        Execute all handlers in a phase
        
        Args:
            phase_name: Phase name (input/processing/output)
            action_handlers: List of ActionHandler instances for this phase
        """
        for action_handler in action_handlers:
            # Check if handler should execute based on condition
            if not action_handler.should_execute(self.context):
                self._skip_handler(action_handler, "Condition not met")
                continue
            
            # Execute handler with error handling
            try:
                self._execute_handler(action_handler)
            except Exception as e:
                self._handle_execution_error(action_handler, e)
    
    def _execute_handler(self, action_handler: ActionHandler):
        """
        Execute a single handler
        
        Args:
            action_handler: ActionHandler instance to execute
        """
        handler = action_handler.handler
        
        # Create execution record
        execution = HandlerExecution.objects.create(
            action_handler=action_handler,
            project=self.project,
            status='running',
            input_data=self._sanitize_context(self.context),
            executed_by=self.user
        )
        self.executions.append(execution)
        
        start_time = time.time()
        
        try:
            # Dynamically load handler class
            handler_class = handler.get_implementation()
            
            # Instantiate handler
            handler_instance = handler_class()
            
            # Execute handler
            result = handler_instance.execute(
                context=self.context,
                config=action_handler.config
            )
            
            # Update context with result
            if isinstance(result, dict):
                self.context.update(result)
            
            # Mark success
            execution_time_ms = int((time.time() - start_time) * 1000)
            execution.mark_success(result if isinstance(result, dict) else {'result': result})
            execution.execution_time_ms = execution_time_ms
            execution.save()
            
        except Exception as e:
            # Mark failed
            execution_time_ms = int((time.time() - start_time) * 1000)
            execution.mark_failed(
                error_message=str(e),
                error_traceback=traceback.format_exc()
            )
            
            # Re-raise for error handling
            raise
    
    def _handle_execution_error(self, action_handler: ActionHandler, error: Exception):
        """
        Handle handler execution error based on configured strategy
        
        Args:
            action_handler: ActionHandler that failed
            error: Exception that was raised
        """
        strategy = action_handler.on_error
        
        if strategy == 'stop':
            # Stop entire execution
            raise ActionExecutionError(
                f"Handler {action_handler.handler.handler_id} failed: {error}"
            ) from error
        
        elif strategy == 'skip':
            # Skip this handler and continue
            self._skip_handler(action_handler, f"Skipped due to error: {error}")
        
        elif strategy == 'retry':
            # Retry handler
            self._retry_handler(action_handler, error)
        
        elif strategy == 'fallback':
            # Use fallback handler
            self._use_fallback(action_handler, error)
    
    def _retry_handler(self, action_handler: ActionHandler, original_error: Exception):
        """
        Retry handler execution
        
        Args:
            action_handler: ActionHandler to retry
            original_error: Original error that triggered retry
        """
        max_retries = action_handler.retry_count
        retry_delay_ms = action_handler.retry_delay_ms
        
        for attempt in range(1, max_retries + 1):
            try:
                # Wait before retry
                if retry_delay_ms > 0:
                    time.sleep(retry_delay_ms / 1000.0)
                
                # Update last execution to show retry
                if self.executions:
                    self.executions[-1].retry_attempt = attempt
                    self.executions[-1].status = 'retrying'
                    self.executions[-1].save()
                
                # Try to execute again
                self._execute_handler(action_handler)
                return  # Success!
                
            except Exception as e:
                if attempt == max_retries:
                    # All retries exhausted
                    raise ActionExecutionError(
                        f"Handler {action_handler.handler.handler_id} failed after {max_retries} retries"
                    ) from e
    
    def _use_fallback(self, action_handler: ActionHandler, original_error: Exception):
        """
        Use fallback handler when primary fails
        
        Args:
            action_handler: ActionHandler that failed
            original_error: Original error
        """
        if not action_handler.fallback_handler:
            raise ActionExecutionError(
                f"Handler {action_handler.handler.handler_id} failed and no fallback configured"
            ) from original_error
        
        # Create temporary ActionHandler for fallback
        fallback_ah = ActionHandler(
            action=action_handler.action,
            handler=action_handler.fallback_handler,
            phase=action_handler.phase,
            order=action_handler.order,
            config=action_handler.config,  # Use same config
            on_error='stop'  # Don't cascade fallbacks
        )
        
        try:
            self._execute_handler(fallback_ah)
        except Exception as e:
            raise ActionExecutionError(
                f"Fallback handler {action_handler.fallback_handler.handler_id} also failed"
            ) from e
    
    def _skip_handler(self, action_handler: ActionHandler, reason: str):
        """
        Skip handler execution
        
        Args:
            action_handler: ActionHandler to skip
            reason: Reason for skipping
        """
        execution = HandlerExecution.objects.create(
            action_handler=action_handler,
            project=self.project,
            status='skipped',
            input_data=self._sanitize_context(self.context),
            executed_by=self.user
        )
        execution.mark_skipped(reason)
        self.executions.append(execution)
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize context for storage (remove non-serializable objects)
        
        Args:
            context: Context dictionary
            
        Returns:
            Sanitized context safe for JSON storage
        """
        sanitized = {}
        
        for key, value in context.items():
            # Skip Django model instances
            if hasattr(value, '_meta'):
                sanitized[key] = f"<{value.__class__.__name__}: {str(value)}>"
            # Skip functions
            elif callable(value):
                continue
            # Keep serializable values
            elif isinstance(value, (str, int, float, bool, list, dict, type(None))):
                sanitized[key] = value
            else:
                sanitized[key] = str(value)
        
        return sanitized
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get summary of execution
        
        Returns:
            Dictionary with execution statistics
        """
        total = len(self.executions)
        success = sum(1 for e in self.executions if e.status == 'success')
        failed = sum(1 for e in self.executions if e.status == 'failed')
        skipped = sum(1 for e in self.executions if e.status == 'skipped')
        total_time_ms = sum(e.execution_time_ms or 0 for e in self.executions)
        
        return {
            'total_handlers': total,
            'successful': success,
            'failed': failed,
            'skipped': skipped,
            'total_execution_time_ms': total_time_ms,
            'executions': [
                {
                    'handler': e.action_handler.handler.handler_id,
                    'status': e.status,
                    'execution_time_ms': e.execution_time_ms,
                    'error': e.error_message if e.error_message else None
                }
                for e in self.executions
            ]
        }


# Convenience function for quick execution
def execute_action(
    action: AgentAction,
    project: BookProjects,
    context: Optional[Dict[str, Any]] = None,
    user=None
) -> Dict[str, Any]:
    """
    Execute an action with its handler pipeline
    
    Args:
        action: AgentAction to execute
        project: BookProjects instance
        context: Initial context (optional)
        user: User executing (optional)
        
    Returns:
        Final execution context
    """
    executor = ActionExecutor(action, project, user)
    return executor.execute(context)
