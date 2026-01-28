"""
Retry strategies for LLM calls.

Uses tenacity for robust retry logic with exponential backoff.
"""

import asyncio
from typing import Any, Callable, TypeVar

from ..schemas.llm_config import RetryConfig
from ..exceptions import LLMError

# Try to import tenacity, provide fallback if not available
try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception,
        RetryCallState,
    )

    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

T = TypeVar("T")


class RetryStrategy:
    """
    Configurable retry strategy for LLM calls.

    Wraps tenacity with sensible defaults for LLM API calls.
    """

    def __init__(self, config: RetryConfig | None = None):
        """
        Initialize retry strategy.

        Args:
            config: Retry configuration (uses defaults if not provided)
        """
        self.config = config or RetryConfig()

    def should_retry(self, exception: BaseException) -> bool:
        """
        Determine if an exception should trigger a retry.

        Args:
            exception: The exception that was raised

        Returns:
            True if should retry
        """
        if isinstance(exception, LLMError):
            # Check if error is marked as retryable
            if exception.retryable:
                return True
            # Check status code
            if exception.status_code in self.config.retry_on_status_codes:
                return True
            return False

        # Retry on common transient errors
        if isinstance(exception, (asyncio.TimeoutError, ConnectionError)):
            return True

        return False

    def get_wait_time(self, attempt: int) -> float:
        """
        Calculate wait time for a given attempt.

        Uses exponential backoff with jitter.

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Wait time in seconds
        """
        delay = self.config.initial_delay_seconds * (
            self.config.exponential_base ** (attempt - 1)
        )
        return min(delay, self.config.max_delay_seconds)


def create_retry_strategy(config: RetryConfig | None = None) -> RetryStrategy:
    """
    Create a retry strategy from configuration.

    Args:
        config: Optional retry configuration

    Returns:
        Configured RetryStrategy
    """
    return RetryStrategy(config)


async def with_retry(
    func: Callable[..., T],
    config: RetryConfig | None = None,
    on_retry: Callable[[int, BaseException], None] | None = None,
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Execute an async function with retry logic.

    Args:
        func: Async function to execute
        config: Retry configuration
        on_retry: Optional callback on each retry (attempt, exception)
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Result of func

    Raises:
        The last exception if all retries fail
    """
    strategy = RetryStrategy(config)
    last_exception: BaseException | None = None

    for attempt in range(1, strategy.config.max_attempts + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            last_exception = e

            if not strategy.should_retry(e):
                raise

            if attempt >= strategy.config.max_attempts:
                raise

            # Call retry callback if provided
            if on_retry:
                on_retry(attempt, e)

            # Wait before retry
            wait_time = strategy.get_wait_time(attempt)
            await asyncio.sleep(wait_time)

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry loop completed without result or exception")


def create_tenacity_retry(config: RetryConfig | None = None):
    """
    Create a tenacity retry decorator.

    Only available if tenacity is installed.

    Args:
        config: Retry configuration

    Returns:
        Tenacity retry decorator

    Raises:
        ImportError: If tenacity is not installed
    """
    if not TENACITY_AVAILABLE:
        raise ImportError(
            "tenacity is required for create_tenacity_retry. "
            "Install with: pip install tenacity"
        )

    config = config or RetryConfig()
    strategy = RetryStrategy(config)

    return retry(
        stop=stop_after_attempt(config.max_attempts),
        wait=wait_exponential(
            multiplier=config.initial_delay_seconds,
            max=config.max_delay_seconds,
            exp_base=config.exponential_base,
        ),
        retry=retry_if_exception(strategy.should_retry),
        reraise=True,
    )
