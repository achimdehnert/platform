"""
Core Handler Decorators
=======================

Decorators for enhancing handler functionality:
- Logging
- Performance monitoring
- Retry logic
- Caching
- Context validation

Migrated from apps/bfagent/services/handlers/decorators.py

Usage:
    from apps.core.handlers.decorators import (
        with_logging,
        with_performance_monitoring,
        retry_on_failure,
        with_caching,
        validate_context
    )

    class MyHandler(BaseHandler):
        @with_logging
        @with_performance_monitoring
        def execute(self, context):
            ...
"""

import functools
import hashlib
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Type

from .exceptions import RetryableError, ValidationError

# Try to import structlog, fall back to standard logging
try:
    import structlog

    logger = structlog.get_logger()
    USE_STRUCTLOG = True
except ImportError:
    logger = logging.getLogger(__name__)
    USE_STRUCTLOG = False


def with_logging(func: Callable) -> Callable:
    """
    Decorator to add structured logging to handler methods.

    Logs:
    - Method entry with context summary
    - Method exit with result summary
    - Exceptions with full context

    Example:
        class MyHandler(BaseHandler):
            @with_logging
            def execute(self, context):
                return {'success': True}
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        handler_name = getattr(self, "handler_name", self.__class__.__name__)
        method_name = func.__name__

        # Log entry
        if USE_STRUCTLOG:
            logger.info(
                f"{handler_name}.{method_name}_started",
                handler=handler_name,
                method=method_name,
                args_count=len(args),
                kwargs_keys=list(kwargs.keys()),
            )
        else:
            logger.info(f"[{handler_name}] {method_name} started")

        try:
            result = func(self, *args, **kwargs)

            # Log success
            if USE_STRUCTLOG:
                logger.info(
                    f"{handler_name}.{method_name}_completed",
                    handler=handler_name,
                    method=method_name,
                    success=True,
                )
            else:
                logger.info(f"[{handler_name}] {method_name} completed successfully")

            return result

        except Exception as e:
            # Log error
            if USE_STRUCTLOG:
                logger.error(
                    f"{handler_name}.{method_name}_failed",
                    handler=handler_name,
                    method=method_name,
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
            else:
                logger.error(f"[{handler_name}] {method_name} failed: {e}")
            raise

    return wrapper


def with_performance_monitoring(func: Callable) -> Callable:
    """
    Decorator to measure and log execution time.

    Adds timing metrics to handler execution and logs
    performance data for monitoring.

    Example:
        class MyHandler(BaseHandler):
            @with_performance_monitoring
            def execute(self, context):
                return {'success': True}
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        handler_name = getattr(self, "handler_name", self.__class__.__name__)
        method_name = func.__name__

        start_time = time.perf_counter()

        try:
            result = func(self, *args, **kwargs)

            # Calculate duration
            duration = time.perf_counter() - start_time
            duration_ms = round(duration * 1000, 2)

            # Log performance
            if USE_STRUCTLOG:
                logger.info(
                    f"{handler_name}.{method_name}_performance",
                    handler=handler_name,
                    method=method_name,
                    duration_ms=duration_ms,
                    duration_s=round(duration, 3),
                )
            else:
                logger.info(f"[{handler_name}] {method_name} took {duration_ms}ms")

            # Add timing to result if it's a dict
            if isinstance(result, dict):
                result["_execution_time_ms"] = duration_ms

            return result

        except Exception as e:
            duration = time.perf_counter() - start_time
            duration_ms = round(duration * 1000, 2)

            if USE_STRUCTLOG:
                logger.error(
                    f"{handler_name}.{method_name}_performance_failed",
                    handler=handler_name,
                    method=method_name,
                    duration_ms=duration_ms,
                    error=str(e),
                )
            else:
                logger.error(f"[{handler_name}] {method_name} failed after {duration_ms}ms")
            raise

    return wrapper


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (RetryableError, ConnectionError, TimeoutError),
) -> Callable:
    """
    Decorator to retry handler methods on failure.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exception types to retry on

    Example:
        class MyHandler(BaseHandler):
            @retry_on_failure(max_retries=3, delay=2.0)
            def call_external_api(self, data):
                return api_client.call(data)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            handler_name = getattr(self, "handler_name", self.__class__.__name__)
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(self, *args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        if USE_STRUCTLOG:
                            logger.warning(
                                f"{handler_name}_retry",
                                handler=handler_name,
                                attempt=attempt + 1,
                                max_retries=max_retries,
                                delay=current_delay,
                                error=str(e),
                            )
                        else:
                            logger.warning(
                                f"[{handler_name}] Retry {attempt + 1}/{max_retries} "
                                f"after {current_delay}s: {e}"
                            )

                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        if USE_STRUCTLOG:
                            logger.error(
                                f"{handler_name}_retry_exhausted",
                                handler=handler_name,
                                max_retries=max_retries,
                                error=str(e),
                            )
                        else:
                            logger.error(f"[{handler_name}] Max retries ({max_retries}) exhausted")

            raise last_exception

        return wrapper

    return decorator


def with_caching(ttl: int = 300, key_func: Optional[Callable] = None) -> Callable:
    """
    Decorator to cache handler results.

    Args:
        ttl: Cache time-to-live in seconds
        key_func: Function to generate cache key from args/kwargs

    Example:
        class MyHandler(BaseHandler):
            @with_caching(ttl=600)
            def fetch_data(self, project_id):
                return expensive_operation(project_id)
    """
    cache: Dict[str, tuple] = {}  # {key: (result, expiry_time)}

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: hash of function name + args + kwargs
                key_data = {
                    "func": func.__name__,
                    "args": str(args),
                    "kwargs": json.dumps(kwargs, sort_keys=True, default=str),
                }
                cache_key = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

            # Check cache
            if cache_key in cache:
                result, expiry_time = cache[cache_key]
                if time.time() < expiry_time:
                    if USE_STRUCTLOG:
                        logger.debug(
                            "cache_hit",
                            handler=getattr(self, "handler_name", "unknown"),
                            method=func.__name__,
                        )
                    return result

            # Execute and cache
            result = func(self, *args, **kwargs)
            cache[cache_key] = (result, time.time() + ttl)

            if USE_STRUCTLOG:
                logger.debug(
                    "cache_miss",
                    handler=getattr(self, "handler_name", "unknown"),
                    method=func.__name__,
                    ttl=ttl,
                )

            return result

        # Add cache management methods
        wrapper.cache_clear = lambda: cache.clear()
        wrapper.cache_info = lambda: {"size": len(cache), "keys": list(cache.keys())}

        return wrapper

    return decorator


def validate_context(required_keys: List[str]) -> Callable:
    """
    Decorator to validate required context keys.

    Args:
        required_keys: List of keys that must be present in context

    Example:
        class MyHandler(BaseHandler):
            @validate_context(['project_id', 'user_id'])
            def execute(self, context):
                # project_id and user_id guaranteed to exist
                return {'success': True}

    Raises:
        ValidationError: If any required key is missing
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, context: Dict[str, Any], *args, **kwargs):
            handler_name = getattr(self, "handler_name", self.__class__.__name__)

            # Check for missing keys
            missing_keys = [key for key in required_keys if key not in context]

            if missing_keys:
                raise ValidationError(
                    f"Missing required context keys: {', '.join(missing_keys)}",
                    handler_name=handler_name,
                    context={
                        "required_keys": required_keys,
                        "missing_keys": missing_keys,
                        "received_keys": list(context.keys()),
                    },
                )

            return func(self, context, *args, **kwargs)

        return wrapper

    return decorator


def measure_tokens(func: Callable) -> Callable:
    """
    Decorator to estimate token usage for LLM operations.

    Adds approximate token counts to the result for cost tracking.
    Uses rough estimation: ~4 characters per token.

    Example:
        class LLMHandler(BaseHandler):
            @measure_tokens
            def generate(self, prompt):
                return llm.complete(prompt)
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        handler_name = getattr(self, "handler_name", self.__class__.__name__)

        # Estimate input tokens
        input_text = " ".join(str(arg) for arg in args)
        input_text += " ".join(str(v) for v in kwargs.values())
        input_tokens = len(input_text) // 4

        # Execute
        result = func(self, *args, **kwargs)

        # Estimate output tokens
        output_text = str(result)
        output_tokens = len(output_text) // 4

        # Log token usage
        if USE_STRUCTLOG:
            logger.info(
                f"{handler_name}_token_usage",
                handler=handler_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            )
        else:
            logger.info(
                f"[{handler_name}] Tokens: {input_tokens} in, "
                f"{output_tokens} out, {input_tokens + output_tokens} total"
            )

        # Add to result if dict
        if isinstance(result, dict):
            result["_token_usage"] = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            }

        return result

    return wrapper


def deprecated(message: str = "This handler is deprecated") -> Callable:
    """
    Decorator to mark handlers as deprecated.

    Logs a warning when the handler is used.

    Example:
        @deprecated("Use NewHandler instead")
        class OldHandler(BaseHandler):
            ...
    """

    def decorator(cls_or_func):
        if isinstance(cls_or_func, type):
            # Decorating a class
            original_init = cls_or_func.__init__

            @functools.wraps(original_init)
            def new_init(self, *args, **kwargs):
                logger.warning(f"DEPRECATED: {cls_or_func.__name__} - {message}")
                original_init(self, *args, **kwargs)

            cls_or_func.__init__ = new_init
            return cls_or_func
        else:
            # Decorating a function
            @functools.wraps(cls_or_func)
            def wrapper(*args, **kwargs):
                logger.warning(f"DEPRECATED: {cls_or_func.__name__} - {message}")
                return cls_or_func(*args, **kwargs)

            return wrapper

    return decorator
