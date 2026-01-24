# -*- coding: utf-8 -*-
"""
Usage Tracker Service.

Provides centralized logging for:
- Django generation errors
- Tool/Agent usage tracking
- Error pattern analysis
"""
import logging
import time
import hashlib
import traceback
from typing import Optional, Dict, List, Any, Callable
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Singleton instance
_tracker_instance = None


class UsageTracker:
    """
    Centralized usage tracking service.
    
    Usage:
        tracker = get_usage_tracker()
        
        # Log an error
        tracker.log_django_error(
            error_type='view',
            error_message='NameError: name xyz is not defined',
            file_path='apps/myapp/views.py'
        )
        
        # Log tool usage
        tracker.log_tool_usage(
            tool_name='code_quality_check',
            caller_type='cascade',
            input_params={'file': 'views.py'}
        )
        
        # Use as decorator
        @tracker.track_tool('my_tool')
        def my_function():
            ...
    """
    
    def __init__(self):
        self._session_id: Optional[str] = None
        self._caller_type: str = 'system'
        self._caller_id: Optional[str] = None
    
    def set_session(
        self,
        session_id: str,
        caller_type: str = 'cascade',
        caller_id: str = None
    ):
        """Set the current session context."""
        self._session_id = session_id
        self._caller_type = caller_type
        self._caller_id = caller_id
    
    def clear_session(self):
        """Clear the current session context."""
        self._session_id = None
        self._caller_type = 'system'
        self._caller_id = None
    
    # ==================== Error Logging ====================
    
    def log_django_error(
        self,
        error_type: str,
        error_message: str,
        file_path: str = None,
        line_number: int = None,
        code_snippet: str = None,
        stack_trace: str = None,
        error_code: str = None,
        function_name: str = None,
        severity: str = 'error',
        auto_fixable: bool = False,
        fix_suggestion: str = None,
    ) -> Optional[int]:
        """
        Log a Django generation error.
        
        Returns the error ID if logged successfully.
        """
        try:
            from ..models_usage_tracking import DjangoGenerationError
            
            error = DjangoGenerationError.log_error(
                error_type=error_type,
                error_message=error_message,
                file_path=file_path,
                line_number=line_number,
                code_snippet=code_snippet,
                stack_trace=stack_trace,
                error_code=error_code,
                function_name=function_name,
                severity=severity,
                source=self._caller_type,
                session_id=self._session_id,
                auto_fixable=auto_fixable,
                fix_suggestion=fix_suggestion,
            )
            
            logger.info(f"Logged Django error: {error_type} - {error_message[:50]}")
            return error.id
            
        except Exception as e:
            logger.error(f"Failed to log Django error: {e}")
            return None
    
    def log_exception(
        self,
        exception: Exception,
        error_type: str = 'other',
        file_path: str = None,
        code_snippet: str = None,
    ) -> Optional[int]:
        """Log an exception as a Django error."""
        return self.log_django_error(
            error_type=error_type,
            error_message=str(exception),
            file_path=file_path,
            code_snippet=code_snippet,
            stack_trace=traceback.format_exc(),
            severity='error',
        )
    
    def log_template_error(
        self,
        error_message: str,
        template_path: str = None,
        line_number: int = None,
        **kwargs
    ) -> Optional[int]:
        """Shortcut for logging template errors."""
        return self.log_django_error(
            error_type='template',
            error_message=error_message,
            file_path=template_path,
            line_number=line_number,
            **kwargs
        )
    
    def log_view_error(
        self,
        error_message: str,
        view_path: str = None,
        function_name: str = None,
        **kwargs
    ) -> Optional[int]:
        """Shortcut for logging view errors."""
        return self.log_django_error(
            error_type='view',
            error_message=error_message,
            file_path=view_path,
            function_name=function_name,
            **kwargs
        )
    
    def log_url_error(
        self,
        error_message: str,
        urls_path: str = None,
        **kwargs
    ) -> Optional[int]:
        """Shortcut for logging URL configuration errors."""
        return self.log_django_error(
            error_type='url',
            error_message=error_message,
            file_path=urls_path,
            **kwargs
        )
    
    def log_import_error(
        self,
        error_message: str,
        file_path: str = None,
        **kwargs
    ) -> Optional[int]:
        """Shortcut for logging import errors."""
        return self.log_django_error(
            error_type='import',
            error_message=error_message,
            file_path=file_path,
            **kwargs
        )
    
    # ==================== Tool Usage Logging ====================
    
    def log_tool_usage(
        self,
        tool_name: str,
        caller_type: str = None,
        caller_id: str = None,
        app_label: str = None,
        input_params: dict = None,
        execution_time_ms: float = 0.0,
        success: bool = True,
        result_summary: str = None,
        error_message: str = None,
        request_url: str = None,
        tool_version: str = None,
        tool_category: str = None,
    ) -> Optional[int]:
        """
        Log a tool usage.
        
        Returns the log ID if successful.
        """
        try:
            from ..models_usage_tracking import ToolUsageLog
            
            log = ToolUsageLog.log_usage(
                tool_name=tool_name,
                caller_type=caller_type or self._caller_type,
                caller_id=caller_id or self._caller_id,
                app_label=app_label,
                input_params=input_params,
                execution_time_ms=execution_time_ms,
                success=success,
                result_summary=result_summary,
                error_message=error_message,
                request_url=request_url,
                tool_version=tool_version,
                tool_category=tool_category,
                session_id=self._session_id,
            )
            
            logger.debug(f"Logged tool usage: {tool_name}")
            return log.id
            
        except Exception as e:
            logger.error(f"Failed to log tool usage: {e}")
            return None
    
    # ==================== Decorators ====================
    
    def track_tool(
        self,
        tool_name: str,
        tool_category: str = None,
        log_params: bool = True
    ) -> Callable:
        """
        Decorator to automatically track tool usage.
        
        Usage:
            @tracker.track_tool('my_tool')
            def my_function(param1, param2):
                return result
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                error_msg = None
                result = None
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error_msg = str(e)
                    raise
                finally:
                    execution_time = (time.time() - start_time) * 1000
                    
                    params = None
                    if log_params:
                        params = {
                            'args_count': len(args),
                            **{k: str(v)[:100] for k, v in kwargs.items()}
                        }
                    
                    self.log_tool_usage(
                        tool_name=tool_name,
                        tool_category=tool_category,
                        input_params=params,
                        execution_time_ms=execution_time,
                        success=success,
                        error_message=error_msg,
                        result_summary=str(result)[:200] if result else None,
                    )
            
            return wrapper
        return decorator
    
    @contextmanager
    def track_operation(
        self,
        tool_name: str,
        tool_category: str = None,
        input_params: dict = None
    ):
        """
        Context manager to track an operation.
        
        Usage:
            with tracker.track_operation('my_operation') as ctx:
                # do work
                ctx['result'] = 'success'
        """
        ctx = {'result': None, 'error': None}
        start_time = time.time()
        
        try:
            yield ctx
        except Exception as e:
            ctx['error'] = str(e)
            raise
        finally:
            execution_time = (time.time() - start_time) * 1000
            
            self.log_tool_usage(
                tool_name=tool_name,
                tool_category=tool_category,
                input_params=input_params,
                execution_time_ms=execution_time,
                success=ctx['error'] is None,
                error_message=ctx['error'],
                result_summary=str(ctx['result'])[:200] if ctx['result'] else None,
            )
    
    # ==================== Statistics ====================
    
    def get_error_stats(self, days: int = 30) -> Dict:
        """Get error statistics."""
        try:
            from ..models_usage_tracking import DjangoGenerationError
            return {
                "common_errors": DjangoGenerationError.get_common_errors(days),
                "fixable_count": DjangoGenerationError.objects.filter(
                    auto_fixable=True, resolved=False
                ).count(),
            }
        except Exception as e:
            logger.error(f"Failed to get error stats: {e}")
            return {}
    
    def get_usage_stats(self, days: int = 30) -> Dict:
        """Get usage statistics."""
        try:
            from ..models_usage_tracking import ToolUsageLog
            return ToolUsageLog.get_usage_stats(days)
        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            return {}
    
    def get_fixable_errors(self) -> List[Dict]:
        """Get list of auto-fixable errors."""
        try:
            from ..models_usage_tracking import DjangoGenerationError
            errors = DjangoGenerationError.get_fixable_errors()
            return [
                {
                    "id": e.id,
                    "type": e.error_type,
                    "message": e.error_message,
                    "file": e.file_path,
                    "fix": e.fix_suggestion,
                    "occurrences": e.occurrence_count,
                }
                for e in errors
            ]
        except Exception as e:
            logger.error(f"Failed to get fixable errors: {e}")
            return []


def get_usage_tracker() -> UsageTracker:
    """Get the singleton UsageTracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = UsageTracker()
    return _tracker_instance


# ==================== Middleware Integration ====================

class UsageTrackingMiddleware:
    """
    Django middleware to track requests and errors.
    
    Add to MIDDLEWARE in settings.py:
        'apps.bfagent.services.usage_tracker.UsageTrackingMiddleware',
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.tracker = get_usage_tracker()
    
    def __call__(self, request):
        # Set session context
        session_id = request.session.session_key if hasattr(request, 'session') else None
        user_id = str(request.user.id) if request.user.is_authenticated else None
        
        self.tracker.set_session(
            session_id=session_id or 'anonymous',
            caller_type='user' if user_id else 'system',
            caller_id=user_id
        )
        
        response = self.get_response(request)
        
        # Clear session context
        self.tracker.clear_session()
        
        return response
    
    def process_exception(self, request, exception):
        """Log unhandled exceptions."""
        self.tracker.log_exception(
            exception=exception,
            error_type='view',
            file_path=request.path,
        )
        return None


# ==================== Signal Handlers ====================

def setup_error_signals():
    """Setup Django signals to capture errors."""
    from django.core.signals import got_request_exception
    
    def handle_exception(sender, request=None, **kwargs):
        tracker = get_usage_tracker()
        exc_info = kwargs.get('exc_info')
        if exc_info:
            tracker.log_exception(exc_info[1])
    
    got_request_exception.connect(handle_exception)
