"""
Decorators for handler pipeline - COMPLETE IMPLEMENTATION
"""

import time
import functools
import hashlib
import json
from typing import Callable, Any
from django.core.cache import cache
import structlog

logger = structlog.get_logger()


def with_logging(func: Callable) -> Callable:
    """
    Add structured logging to handler methods.
    
    Logs method start, completion, duration, and errors.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        bound_logger = logger.bind(
            handler=self.handler_name,
            version=self.handler_version,
            method=func.__name__
        )
        
        bound_logger.info("handler_method_started")
        start_time = time.time()
        
        try:
            result = func(self, *args, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)
            bound_logger.info(
                "handler_method_completed",
                duration_ms=duration_ms
            )
            return result
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Import here to avoid circular dependency
            from .exceptions import HandlerException
            
            if isinstance(e, HandlerException):
                bound_logger.error(
                    "handler_method_failed",
                    duration_ms=duration_ms,
                    error=e.to_dict()
                )
            else:
                bound_logger.error(
                    "handler_method_unexpected_error",
                    duration_ms=duration_ms,
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
            raise
    
    return wrapper


def with_performance_monitoring(func: Callable) -> Callable:
    """
    Monitor handler performance metrics.
    
    Tracks execution time and success/failure.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        success = False
        error_type = None
        
        try:
            result = func(self, *args, **kwargs)
            success = True
            return result
            
        except Exception as e:
            error_type = type(e).__name__
            raise
            
        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                "handler_performance_metric",
                handler=self.handler_name,
                handler_version=self.handler_version,
                method=func.__name__,
                duration_ms=duration_ms,
                success=success,
                error_type=error_type
            )
    
    return wrapper


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    exclude_exceptions: tuple = ()
):
    """
    Retry handler execution on failure with exponential backoff.
    
    Args:
        max_attempts: Maximum retry attempts
        delay: Initial delay in seconds
        backoff: Backoff multiplier
        exceptions: Tuple of exceptions to retry on
        exclude_exceptions: Tuple of exceptions to NOT retry on
    
    Example:
        @retry_on_failure(max_attempts=3, delay=1.0, backoff=2.0)
        def collect(self, context):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            attempt = 0
            current_delay = delay
            last_exception = None
            
            while attempt < max_attempts:
                try:
                    return func(self, *args, **kwargs)
                    
                except exclude_exceptions:
                    # Don't retry these
                    raise
                    
                except exceptions as e:
                    attempt += 1
                    last_exception = e
                    
                    # Import here to avoid circular dependency
                    from .exceptions import HandlerException, HandlerErrorSeverity
                    
                    # Don't retry critical errors
                    if isinstance(e, HandlerException) and e.severity == HandlerErrorSeverity.CRITICAL:
                        raise
                    
                    if attempt >= max_attempts:
                        break
                    
                    logger.warning(
                        "handler_retry",
                        handler=self.handler_name,
                        method=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay_seconds=current_delay,
                        error_type=type(e).__name__
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            # All retries exhausted
            logger.error(
                "handler_retries_exhausted",
                handler=self.handler_name,
                method=func.__name__,
                max_attempts=max_attempts
            )
            raise last_exception
        
        return wrapper
    return decorator


def with_caching(
    cache_key_prefix: str = None,
    ttl: int = 300,
    key_func: Callable = None
):
    """
    Cache handler results.
    
    Args:
        cache_key_prefix: Prefix for cache keys
        ttl: Time to live in seconds
        key_func: Function to generate cache key from args
    
    Example:
        @with_caching(cache_key_prefix="chapter_data", ttl=300)
        def collect(self, context):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Check if caching is enabled for this handler
            if not getattr(self, 'cache_enabled', False):
                return func(self, *args, **kwargs)
            
            # Generate cache key
            if key_func:
                cache_suffix = key_func(*args, **kwargs)
            else:
                # Default: hash the arguments
                args_str = json.dumps(
                    {"args": str(args), "kwargs": str(kwargs)},
                    sort_keys=True
                )
                cache_suffix = hashlib.md5(args_str.encode()).hexdigest()[:8]
            
            prefix = cache_key_prefix or f"{self.handler_name}_{func.__name__}"
            cache_key = f"handler:{prefix}:{cache_suffix}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.info(
                    "handler_cache_hit",
                    handler=self.handler_name,
                    method=func.__name__,
                    cache_key=cache_key
                )
                return cached_result
            
            # Execute function
            result = func(self, *args, **kwargs)
            
            # Cache result
            cache_ttl = ttl or getattr(self, 'cache_ttl', 300)
            cache.set(cache_key, result, cache_ttl)
            
            logger.info(
                "handler_cache_set",
                handler=self.handler_name,
                method=func.__name__,
                cache_key=cache_key,
                ttl=cache_ttl
            )
            
            return result
        
        return wrapper
    return decorator


def validate_context(required_keys: list):
    """
    Validate required keys in context.
    
    Args:
        required_keys: List of required key names
    
    Example:
        @validate_context(["project", "agent"])
        def collect(self, context):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, context, *args, **kwargs):
            from .exceptions import InputHandlerException
            
            missing_keys = [key for key in required_keys if key not in context]
            
            if missing_keys:
                raise InputHandlerException(
                    f"Missing required context keys: {', '.join(missing_keys)}",
                    handler_name=self.handler_name,
                    context={
                        "required": required_keys,
                        "provided": list(context.keys()),
                        "missing": missing_keys
                    }
                )
            
            return func(self, context, *args, **kwargs)
        
        return wrapper
    return decorator


def measure_tokens(func: Callable) -> Callable:
    """
    Measure token usage for LLM handlers.
    
    Logs prompt and completion token counts.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        
        # Extract token info from result
        if isinstance(result, dict):
            tokens_used = result.get('tokens_used', 0)
            prompt_tokens = result.get('prompt_tokens', 0)
            completion_tokens = result.get('completion_tokens', 0)
            cost = result.get('generation_cost', 0)
            
            logger.info(
                "llm_token_usage",
                handler=self.handler_name,
                method=func.__name__,
                tokens_used=tokens_used,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=float(cost) if cost else 0
            )
        
        return result
    
    return wrapper


# Export all decorators
__all__ = [
    "with_logging",
    "with_performance_monitoring",
    "retry_on_failure",
    "with_caching",
    "validate_context",
    "measure_tokens",
]