"""
LLM Service Exceptions
======================

Exception hierarchy for LLM operations.

Usage:
    from apps.core.services.llm import (
        LLMException,
        LLMConnectionError,
        LLMRateLimitError,
        LLMValidationError
    )
"""

from typing import Any, Optional


class LLMException(Exception):
    """
    Base exception for all LLM errors.

    Attributes:
        message: Human-readable error message
        provider: LLM provider that raised the error
        model: Model that was being used
        original_error: The original exception if this wraps another
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        self.message = message
        self.provider = provider
        self.model = model
        self.original_error = original_error
        super().__init__(message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "provider": self.provider,
            "model": self.model,
            "original_error": str(self.original_error) if self.original_error else None,
        }


class LLMConnectionError(LLMException):
    """
    Raised when connection to LLM API fails.

    This includes:
    - Network errors
    - DNS resolution failures
    - SSL/TLS errors
    - Timeouts
    """

    pass


class LLMAuthenticationError(LLMException):
    """
    Raised when authentication fails.

    This includes:
    - Invalid API key
    - Expired API key
    - Missing API key
    """

    pass


class LLMRateLimitError(LLMException):
    """
    Raised when rate limit is exceeded.

    Attributes:
        retry_after: Suggested wait time in seconds before retry
    """

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["retry_after"] = self.retry_after
        return result


class LLMQuotaExceededError(LLMException):
    """
    Raised when usage quota is exceeded.

    This typically means the billing limit has been reached
    and requires account action.
    """

    pass


class LLMValidationError(LLMException):
    """
    Raised when response validation fails.

    This includes:
    - Structured output schema validation failures
    - Malformed JSON responses
    - Missing required fields

    Attributes:
        content: The raw content that failed validation
        validation_errors: Detailed validation error info
    """

    def __init__(
        self,
        message: str,
        content: Optional[str] = None,
        validation_errors: Optional[list] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.content = content
        self.validation_errors = validation_errors or []

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["content"] = self.content
        result["validation_errors"] = self.validation_errors
        return result


class LLMContentFilterError(LLMException):
    """
    Raised when content is blocked by safety filters.

    Attributes:
        filter_type: Type of filter that triggered (if known)
        flagged_categories: Categories that were flagged
    """

    def __init__(
        self,
        message: str,
        filter_type: Optional[str] = None,
        flagged_categories: Optional[list] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.filter_type = filter_type
        self.flagged_categories = flagged_categories or []

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["filter_type"] = self.filter_type
        result["flagged_categories"] = self.flagged_categories
        return result


class LLMContextLengthError(LLMException):
    """
    Raised when input exceeds context window.

    Attributes:
        max_tokens: Maximum allowed tokens
        actual_tokens: Actual token count
    """

    def __init__(
        self,
        message: str,
        max_tokens: Optional[int] = None,
        actual_tokens: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.max_tokens = max_tokens
        self.actual_tokens = actual_tokens

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["max_tokens"] = self.max_tokens
        result["actual_tokens"] = self.actual_tokens
        return result


class LLMModelNotFoundError(LLMException):
    """
    Raised when requested model doesn't exist.
    """

    pass


class LLMTimeoutError(LLMException):
    """
    Raised when request times out.

    Attributes:
        timeout_seconds: The timeout value that was exceeded
    """

    def __init__(self, message: str, timeout_seconds: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.timeout_seconds = timeout_seconds

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["timeout_seconds"] = self.timeout_seconds
        return result


class LLMConfigurationError(LLMException):
    """
    Raised when client configuration is invalid.

    This includes:
    - Missing required configuration
    - Invalid parameter values
    - Incompatible settings
    """

    pass
