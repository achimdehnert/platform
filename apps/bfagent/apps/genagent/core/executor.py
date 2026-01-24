"""
GenAgent Action Executor - ACID Transaction Safety
Implements transaction-safe action execution with automatic rollback.
"""

import time
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.genagent.models import Action, ExecutionLog
from apps.genagent.core.handler_registry import HandlerRegistry, HandlerNotFoundError

logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Raised when action execution fails."""
    pass


class ValidationError(Exception):
    """Raised when result validation fails."""
    pass


class ActionExecutor:
    """
    Transaction-safe Action Executor with ACID guarantees.
    
    Features:
    - Atomic transaction execution
    - Automatic rollback on failure
    - Context snapshot creation
    - Result validation
    - Execution logging
    - Performance tracking
    """
    
    @staticmethod
    def execute_action(
        action_id: int,
        context: Dict[str, Any],
        validate_result: bool = True
    ) -> Dict[str, Any]:
        """
        Execute an action with ACID guarantees.
        
        Args:
            action_id: ID of action to execute
            context: Execution context dictionary
            validate_result: Whether to validate result against schema
            
        Returns:
            Dictionary with execution result
            
        Raises:
            ExecutionError: If execution fails
            ValidationError: If result validation fails
            HandlerNotFoundError: If handler not found
        """
        
        try:
            with transaction.atomic():
                # 1. Lock Action for update (prevents concurrent execution)
                action = Action.objects.select_for_update().get(id=action_id)
                
                # 2. Create snapshot before execution
                snapshot = ActionExecutor._create_snapshot(context, action)
                
                # 3. Validate handler availability
                HandlerRegistry.validate_availability(action.handler_class)
                
                # 4. Execute handler
                start_time = time.time()
                logger.info(f"Executing action {action.id}: {action.handler_class}")
                
                handler_class = HandlerRegistry.get_handler_class(action.handler_class)
                handler = handler_class()
                
                # Merge action config with context
                execution_context = {**context, **action.config}
                
                result = handler.process(execution_context)
                duration = time.time() - start_time
                
                logger.info(
                    f"Action {action.id} completed in {duration:.2f}s"
                )
                
                # 5. Validate result if requested
                if validate_result:
                    ActionExecutor._validate_result(result, action)
                
                # 6. Persist execution log
                execution_log = ExecutionLog.objects.create(
                    action=action,
                    output_data=result,
                    duration_seconds=duration,
                    status="success",
                    input_data=snapshot,
                    error_message=""
                )
                
                logger.info(
                    f"Execution log created: {execution_log.id}"
                )
                
                # 7. Emit success event (placeholder for future event system)
                ActionExecutor._emit_action_completed(action, result, duration)
                
                return {
                    "success": True,
                    "result": result,
                    "duration": duration,
                    "execution_log_id": execution_log.id,
                    "timestamp": timezone.now().isoformat()
                }
                
        except HandlerNotFoundError as e:
            error_msg = f"Handler not found: {str(e)}"
            logger.error(error_msg)
            ActionExecutor._log_failure(action_id, snapshot, error_msg)
            raise ExecutionError(error_msg) from e
            
        except ValidationError as e:
            error_msg = f"Result validation failed: {str(e)}"
            logger.error(error_msg)
            # Rollback happens automatically due to transaction.atomic()
            ActionExecutor._log_failure(action_id, snapshot, error_msg)
            raise
            
        except Exception as e:
            error_msg = f"Execution failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Rollback happens automatically due to transaction.atomic()
            ActionExecutor._log_failure(action_id, snapshot, error_msg)
            raise ExecutionError(error_msg) from e
    
    @staticmethod
    def _create_snapshot(context: Dict[str, Any], action: Action) -> Dict[str, Any]:
        """
        Create execution context snapshot.
        
        Args:
            context: Current execution context
            action: Action being executed
            
        Returns:
            Snapshot dictionary with context, config, and metadata
        """
        return {
            "context": ActionExecutor._sanitize_for_json(context.copy()),
            "action_config": ActionExecutor._sanitize_for_json(action.config),
            "action_handler": action.handler_class,
            "timestamp": timezone.now().isoformat(),
            "action_id": action.id
        }
    
    @staticmethod
    def _sanitize_for_json(data: Any) -> Any:
        """
        Sanitize data for JSON serialization.
        
        Handles datetime objects, complex types, etc.
        """
        if isinstance(data, dict):
            return {k: ActionExecutor._sanitize_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [ActionExecutor._sanitize_for_json(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        elif hasattr(data, '__dict__'):
            # Convert objects to dict (for model instances, etc.)
            return str(data)
        else:
            return data
    
    @staticmethod
    def _validate_result(result: Dict[str, Any], action: Action) -> bool:
        """
        Validate result against action's output schema.
        
        Args:
            result: Execution result
            action: Action with potential output_schema
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        # Basic validation - result must be a dictionary
        if not isinstance(result, dict):
            raise ValidationError(
                f"Result must be a dictionary, got {type(result).__name__}"
            )
        
        # Check for success indicator
        if "success" in result and not result["success"]:
            raise ValidationError(
                f"Handler indicated failure: {result.get('error', 'Unknown error')}"
            )
        
        # Future: Pydantic schema validation (Feature 4)
        # if hasattr(action, 'output_schema') and action.output_schema:
        #     schema_class = action.output_schema
        #     schema_class(**result)  # Raises ValidationError if invalid
        
        return True
    
    @staticmethod
    def _log_failure(
        action_id: int,
        snapshot: Dict[str, Any],
        error_message: str
    ) -> None:
        """
        Log execution failure.
        
        Args:
            action_id: ID of failed action
            snapshot: Context snapshot
            error_message: Error description
        """
        try:
            action = Action.objects.get(id=action_id)
            ExecutionLog.objects.create(
                action=action,
                status="failed",
                error_message=error_message,
                input_data=snapshot,
                output_data={},
                duration_seconds=0.0
            )
        except Exception as e:
            logger.error(f"Failed to log failure: {e}")
    
    @staticmethod
    def _emit_action_completed(
        action: Action,
        result: Dict[str, Any],
        duration: float
    ) -> None:
        """
        Emit action completed event.
        
        Placeholder for future event system (Feature 7).
        
        Args:
            action: Completed action
            result: Execution result
            duration: Execution duration in seconds
        """
        # Future: Event bus integration
        logger.debug(
            f"Event: action_completed - {action.handler_class} in {duration:.2f}s"
        )
    
    @staticmethod
    def get_execution_history(
        action_id: int,
        limit: int = 10
    ) -> list:
        """
        Get execution history for an action.
        
        Args:
            action_id: Action ID
            limit: Maximum number of records to return
            
        Returns:
            List of execution log dictionaries
        """
        logs = ExecutionLog.objects.filter(
            action_id=action_id
        ).order_by('-created_at')[:limit]
        
        return [
            {
                "id": log.id,
                "status": log.status,
                "duration": log.duration_seconds,
                "timestamp": log.created_at.isoformat(),
                "error": log.error_message,
                "has_result": bool(log.output_data)
            }
            for log in logs
        ]
    
    @staticmethod
    def get_execution_stats(action_id: int) -> Dict[str, Any]:
        """
        Get execution statistics for an action.
        
        Args:
            action_id: Action ID
            
        Returns:
            Dictionary with execution statistics
        """
        logs = ExecutionLog.objects.filter(action_id=action_id)
        
        total = logs.count()
        if total == 0:
            return {
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0.0,
                "avg_duration": 0.0
            }
        
        successful = logs.filter(status="success").count()
        failed = logs.filter(status="failed").count()
        
        # Calculate average duration for successful executions
        completed_logs = logs.filter(status="success")
        avg_duration = 0.0
        if completed_logs.exists():
            durations = [log.duration_seconds for log in completed_logs if log.duration_seconds is not None]
            if durations:
                avg_duration = sum(durations) / len(durations)
        
        return {
            "total_executions": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0.0,
            "avg_duration": avg_duration,
            "last_execution": logs.first().created_at.isoformat() if logs.exists() else None
        }
