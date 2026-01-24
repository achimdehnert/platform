"""
Cache Service Exceptions

Comprehensive exception hierarchy for cache operations.
Part of the consolidated Core Cache Service.
"""

from typing import Any, Dict, Optional


class CacheException(Exception):
    """
    Base exception for all cache-related errors.

    Attributes:
        message: Error message
        key: Cache key involved (if applicable)
        backend: Cache backend that raised the error
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        key: Optional[str] = None,
        backend: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.key = key
        self.backend = backend
        self.details = details or {}
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format the exception message with context."""
        parts = [self.message]
        if self.key:
            parts.append(f"key={self.key}")
        if self.backend:
            parts.append(f"backend={self.backend}")
        return " | ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/reporting."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "key": self.key,
            "backend": self.backend,
            "details": self.details,
        }


# =============================================================================
# Connection Errors
# =============================================================================


class CacheConnectionError(CacheException):
    """
    Raised when cache backend connection fails.

    Examples:
        - Redis server unreachable
        - Memcached timeout
        - Database cache table missing
    """

    pass


class CacheTimeoutError(CacheException):
    """
    Raised when cache operation times out.

    Examples:
        - Long-running query
        - Network latency
        - Lock timeout
    """

    def __init__(
        self,
        message: str = "Cache operation timed out",
        timeout_seconds: Optional[float] = None,
        **kwargs,
    ):
        self.timeout_seconds = timeout_seconds
        if timeout_seconds:
            kwargs.setdefault("details", {})["timeout_seconds"] = timeout_seconds
        super().__init__(message, **kwargs)


# =============================================================================
# Key Errors
# =============================================================================


class CacheKeyError(CacheException):
    """
    Raised for cache key-related errors.

    Examples:
        - Invalid key format
        - Key too long
        - Reserved key prefix
    """

    pass


class CacheKeyNotFoundError(CacheKeyError):
    """
    Raised when a required cache key is not found.

    Note: This is for cases where a key MUST exist.
    Normal cache misses don't raise exceptions.
    """

    def __init__(self, key: str, **kwargs):
        super().__init__(message=f"Required cache key not found: {key}", key=key, **kwargs)


class CacheKeyExistsError(CacheKeyError):
    """
    Raised when trying to add a key that already exists.

    Used with add() operations that should not overwrite.
    """

    def __init__(self, key: str, **kwargs):
        super().__init__(message=f"Cache key already exists: {key}", key=key, **kwargs)


class InvalidCacheKeyError(CacheKeyError):
    """
    Raised when cache key format is invalid.

    Examples:
        - Contains forbidden characters
        - Empty key
        - Key exceeds maximum length
    """

    def __init__(self, key: str, reason: str = "Invalid format", **kwargs):
        self.reason = reason
        super().__init__(message=f"Invalid cache key: {reason}", key=key, **kwargs)


# =============================================================================
# Value Errors
# =============================================================================


class CacheValueError(CacheException):
    """
    Raised for cache value-related errors.

    Examples:
        - Value too large
        - Non-serializable value
        - Corrupted cached value
    """

    pass


class CacheSerializationError(CacheValueError):
    """
    Raised when value serialization fails.

    Examples:
        - Non-JSON-serializable object
        - Pickle error
        - Compression error
    """

    def __init__(
        self,
        message: str = "Failed to serialize cache value",
        value_type: Optional[str] = None,
        **kwargs,
    ):
        self.value_type = value_type
        if value_type:
            kwargs.setdefault("details", {})["value_type"] = value_type
        super().__init__(message, **kwargs)


class CacheDeserializationError(CacheValueError):
    """
    Raised when value deserialization fails.

    Examples:
        - Corrupted data
        - Version mismatch
        - Missing class definition (pickle)
    """

    def __init__(self, message: str = "Failed to deserialize cache value", **kwargs):
        super().__init__(message, **kwargs)


class CacheValueTooLargeError(CacheValueError):
    """
    Raised when value exceeds size limits.

    Examples:
        - Memcached 1MB limit
        - Redis max string size
        - Custom limits
    """

    def __init__(self, key: str, size_bytes: int, max_bytes: int, **kwargs):
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes
        kwargs.setdefault("details", {}).update(
            {
                "size_bytes": size_bytes,
                "max_bytes": max_bytes,
            }
        )
        super().__init__(
            message=f"Cache value too large: {size_bytes} bytes (max: {max_bytes})",
            key=key,
            **kwargs,
        )


# =============================================================================
# Backend Errors
# =============================================================================


class CacheBackendError(CacheException):
    """
    Raised for backend-specific errors.

    Examples:
        - Backend not configured
        - Backend-specific feature not supported
        - Backend version incompatible
    """

    pass


class CacheBackendNotAvailableError(CacheBackendError):
    """
    Raised when cache backend is not available.

    Examples:
        - Redis not installed
        - Django cache not configured
        - Required dependencies missing
    """

    def __init__(self, backend: str, reason: str = "Not available", **kwargs):
        self.reason = reason
        super().__init__(
            message=f"Cache backend '{backend}' not available: {reason}", backend=backend, **kwargs
        )


class CacheBackendNotConfiguredError(CacheBackendError):
    """
    Raised when cache backend is not properly configured.

    Examples:
        - Missing Redis URL
        - Invalid cache settings
        - Missing required options
    """

    def __init__(self, backend: str, missing_config: Optional[str] = None, **kwargs):
        self.missing_config = missing_config
        message = f"Cache backend '{backend}' not configured"
        if missing_config:
            message += f": missing {missing_config}"
        super().__init__(message=message, backend=backend, **kwargs)


# =============================================================================
# Operation Errors
# =============================================================================


class CacheOperationError(CacheException):
    """
    Raised for general cache operation failures.

    Examples:
        - Atomic operation failed
        - Lock acquisition failed
        - Transaction rollback
    """

    pass


class CacheLockError(CacheOperationError):
    """
    Raised for lock-related errors.

    Examples:
        - Lock acquisition timeout
        - Lock already held
        - Lock release failed
    """

    def __init__(
        self, message: str = "Cache lock error", lock_name: Optional[str] = None, **kwargs
    ):
        self.lock_name = lock_name
        if lock_name:
            kwargs.setdefault("details", {})["lock_name"] = lock_name
        super().__init__(message, **kwargs)


class CacheLockTimeoutError(CacheLockError):
    """
    Raised when lock acquisition times out.
    """

    def __init__(self, lock_name: str, timeout_seconds: float, **kwargs):
        super().__init__(
            message=f"Failed to acquire lock '{lock_name}' within {timeout_seconds}s",
            lock_name=lock_name,
            **kwargs,
        )


class CacheVersionError(CacheOperationError):
    """
    Raised for version-related errors in optimistic locking.

    Examples:
        - Version mismatch during CAS operation
        - Concurrent modification detected
    """

    def __init__(self, key: str, expected_version: int, actual_version: int, **kwargs):
        self.expected_version = expected_version
        self.actual_version = actual_version
        kwargs.setdefault("details", {}).update(
            {
                "expected_version": expected_version,
                "actual_version": actual_version,
            }
        )
        super().__init__(message=f"Cache version mismatch for key '{key}'", key=key, **kwargs)


# =============================================================================
# Configuration Errors
# =============================================================================


class CacheConfigurationError(CacheException):
    """
    Raised for cache configuration errors.

    Examples:
        - Invalid TTL value
        - Conflicting options
        - Missing required settings
    """

    pass


class InvalidTTLError(CacheConfigurationError):
    """
    Raised when TTL value is invalid.

    Examples:
        - Negative TTL
        - TTL exceeds maximum
        - Non-numeric TTL
    """

    def __init__(self, ttl: Any, reason: str = "Invalid value", **kwargs):
        self.ttl = ttl
        super().__init__(message=f"Invalid TTL '{ttl}': {reason}", **kwargs)


# =============================================================================
# Helper Functions
# =============================================================================


def is_cache_error(exception: Exception) -> bool:
    """Check if an exception is a cache-related error."""
    return isinstance(exception, CacheException)


def is_retriable_error(exception: Exception) -> bool:
    """
    Check if a cache error should be retried.

    Retriable errors:
        - Connection errors
        - Timeout errors
        - Lock timeout errors

    Non-retriable errors:
        - Key errors
        - Serialization errors
        - Configuration errors
    """
    retriable_types = (
        CacheConnectionError,
        CacheTimeoutError,
        CacheLockTimeoutError,
    )
    return isinstance(exception, retriable_types)


def wrap_backend_error(
    exception: Exception, backend: str, key: Optional[str] = None, operation: Optional[str] = None
) -> CacheException:
    """
    Wrap a backend-specific exception in a CacheException.

    Args:
        exception: Original exception
        backend: Backend name
        key: Cache key (if applicable)
        operation: Operation being performed

    Returns:
        Appropriate CacheException subclass
    """
    details = {
        "original_type": type(exception).__name__,
        "original_message": str(exception),
    }
    if operation:
        details["operation"] = operation

    # Handle common exception types
    exc_str = str(exception).lower()

    if "connection" in exc_str or "connect" in exc_str:
        return CacheConnectionError(
            message=f"Backend connection error: {exception}",
            backend=backend,
            key=key,
            details=details,
        )

    if "timeout" in exc_str:
        return CacheTimeoutError(
            message=f"Backend timeout: {exception}",
            backend=backend,
            key=key,
            details=details,
        )

    if "serial" in exc_str or "encode" in exc_str or "decode" in exc_str:
        return CacheSerializationError(
            message=f"Serialization error: {exception}",
            key=key,
            details=details,
        )

    # Default to generic operation error
    return CacheOperationError(
        message=f"Cache operation failed: {exception}",
        backend=backend,
        key=key,
        details=details,
    )
