"""
Retry Utilities for Handler Execution
Provides decorators for automatic retry logic with exponential backoff
"""

import time
import logging
from functools import wraps
from typing import Callable, Tuple, Type

logger = logging.getLogger(__name__)


def retry_on_failure(
    max_retries: int = 3,
    delay_seconds: float = 2.0,
    exponential_backoff: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for retrying functions that may fail transiently
    
    Args:
        max_retries: Maximum number of retry attempts
        delay_seconds: Base delay between retries in seconds
        exponential_backoff: If True, delay doubles with each retry
        exceptions: Tuple of exception types to catch and retry
    
    Example:
        @retry_on_failure(max_retries=3, delay_seconds=2)
        def call_external_api():
            return requests.get('https://api.example.com')
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay_seconds
            
            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    
                    # Log success if this was a retry
                    if attempt > 0:
                        logger.info(
                            f"✅ {func.__name__} succeeded on attempt {attempt + 1}/{max_retries}"
                        )
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"⚠️  {func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        
                        # Exponential backoff
                        if exponential_backoff:
                            current_delay *= 2
                    else:
                        logger.error(
                            f"❌ {func.__name__} failed after {max_retries} attempts: {e}"
                        )
            
            # All retries exhausted
            raise last_exception
        
        return wrapper
    return decorator


def retry_with_timeout(
    timeout_seconds: float = 30.0,
    max_retries: int = 3,
    delay_seconds: float = 2.0
):
    """
    Decorator combining timeout and retry logic
    
    Args:
        timeout_seconds: Maximum time to wait for function completion
        max_retries: Maximum number of retry attempts
        delay_seconds: Delay between retries in seconds
    
    Example:
        @retry_with_timeout(timeout_seconds=30, max_retries=3)
        def slow_llm_call():
            return llm.generate()
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError(
                    f"{func.__name__} exceeded timeout of {timeout_seconds}s"
                )
            
            # Apply retry logic
            @retry_on_failure(max_retries=max_retries, delay_seconds=delay_seconds)
            def with_timeout():
                # Set timeout
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(timeout_seconds))
                
                try:
                    result = func(*args, **kwargs)
                    signal.alarm(0)  # Cancel alarm
                    return result
                except TimeoutError:
                    signal.alarm(0)
                    raise
            
            return with_timeout()
        
        return wrapper
    return decorator
