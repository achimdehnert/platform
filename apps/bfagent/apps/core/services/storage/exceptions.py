"""
Storage Service Exceptions

Exception hierarchy for storage operations.
Part of the consolidated Core Storage Service.
"""

from pathlib import Path
from typing import Any, Dict, Optional


class StorageException(Exception):
    """
    Base exception for all storage-related errors.

    Attributes:
        message: Error message
        path: File/directory path involved
        backend: Storage backend that raised the error
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        backend: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.path = path
        self.backend = backend
        self.details = details or {}
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format exception message with context."""
        parts = [self.message]
        if self.path:
            parts.append(f"path={self.path}")
        if self.backend:
            parts.append(f"backend={self.backend}")
        return " | ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/API responses."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "path": self.path,
            "backend": self.backend,
            "details": self.details,
        }


# =============================================================================
# File Errors
# =============================================================================


class FileNotFoundError(StorageException):
    """Raised when a file is not found."""

    def __init__(self, path: str, **kwargs):
        super().__init__(message=f"File not found: {path}", path=path, **kwargs)


class FileExistsError(StorageException):
    """Raised when trying to create a file that already exists."""

    def __init__(self, path: str, **kwargs):
        super().__init__(message=f"File already exists: {path}", path=path, **kwargs)


class FileReadError(StorageException):
    """Raised when file reading fails."""

    def __init__(self, path: str, reason: str = "Unknown error", **kwargs):
        self.reason = reason
        super().__init__(message=f"Failed to read file: {reason}", path=path, **kwargs)


class FileWriteError(StorageException):
    """Raised when file writing fails."""

    def __init__(self, path: str, reason: str = "Unknown error", **kwargs):
        self.reason = reason
        super().__init__(message=f"Failed to write file: {reason}", path=path, **kwargs)


class FileDeleteError(StorageException):
    """Raised when file deletion fails."""

    def __init__(self, path: str, reason: str = "Unknown error", **kwargs):
        self.reason = reason
        super().__init__(message=f"Failed to delete file: {reason}", path=path, **kwargs)


# =============================================================================
# Directory Errors
# =============================================================================


class DirectoryNotFoundError(StorageException):
    """Raised when a directory is not found."""

    def __init__(self, path: str, **kwargs):
        super().__init__(message=f"Directory not found: {path}", path=path, **kwargs)


class DirectoryExistsError(StorageException):
    """Raised when trying to create a directory that already exists."""

    def __init__(self, path: str, **kwargs):
        super().__init__(message=f"Directory already exists: {path}", path=path, **kwargs)


class DirectoryNotEmptyError(StorageException):
    """Raised when trying to delete a non-empty directory."""

    def __init__(self, path: str, **kwargs):
        super().__init__(message=f"Directory not empty: {path}", path=path, **kwargs)


# =============================================================================
# Validation Errors
# =============================================================================


class ValidationError(StorageException):
    """Base class for validation errors."""

    pass


class FileSizeError(ValidationError):
    """Raised when file exceeds size limit."""

    def __init__(self, path: str, size_bytes: int, max_bytes: int, **kwargs):
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes
        kwargs.setdefault("details", {}).update(
            {
                "size_bytes": size_bytes,
                "max_bytes": max_bytes,
            }
        )
        super().__init__(
            message=f"File too large: {size_bytes} bytes (max: {max_bytes})", path=path, **kwargs
        )


class InvalidExtensionError(ValidationError):
    """Raised when file has invalid extension."""

    def __init__(self, filename: str, extension: str, allowed: Optional[list] = None, **kwargs):
        self.extension = extension
        self.allowed = allowed
        msg = f"Invalid file extension: {extension}"
        if allowed:
            msg += f" (allowed: {', '.join(allowed)})"
        super().__init__(message=msg, path=filename, **kwargs)


class InvalidContentTypeError(ValidationError):
    """Raised when file has invalid content type."""

    def __init__(self, filename: str, content_type: str, expected: Optional[str] = None, **kwargs):
        self.content_type = content_type
        self.expected = expected
        msg = f"Invalid content type: {content_type}"
        if expected:
            msg += f" (expected: {expected})"
        super().__init__(message=msg, path=filename, **kwargs)


class ChecksumMismatchError(ValidationError):
    """Raised when file checksum doesn't match."""

    def __init__(self, path: str, expected: str, actual: str, **kwargs):
        self.expected = expected
        self.actual = actual
        kwargs.setdefault("details", {}).update(
            {
                "expected": expected,
                "actual": actual,
            }
        )
        super().__init__(message=f"Checksum mismatch", path=path, **kwargs)


# =============================================================================
# Backend Errors
# =============================================================================


class BackendError(StorageException):
    """Base class for backend-specific errors."""

    pass


class BackendNotAvailableError(BackendError):
    """Raised when storage backend is not available."""

    def __init__(self, backend: str, reason: str = "Not available", **kwargs):
        self.reason = reason
        super().__init__(
            message=f"Storage backend '{backend}' not available: {reason}",
            backend=backend,
            **kwargs,
        )


class BackendNotConfiguredError(BackendError):
    """Raised when storage backend is not configured."""

    def __init__(self, backend: str, missing: Optional[str] = None, **kwargs):
        self.missing = missing
        msg = f"Storage backend '{backend}' not configured"
        if missing:
            msg += f": missing {missing}"
        super().__init__(message=msg, backend=backend, **kwargs)


class BackendConnectionError(BackendError):
    """Raised when connection to backend fails."""

    def __init__(self, backend: str, reason: str = "Connection failed", **kwargs):
        self.reason = reason
        super().__init__(message=f"Backend connection error: {reason}", backend=backend, **kwargs)


class BackendPermissionError(BackendError):
    """Raised when backend operation lacks permissions."""

    def __init__(self, backend: str, operation: str, **kwargs):
        self.operation = operation
        super().__init__(message=f"Permission denied for {operation}", backend=backend, **kwargs)


# =============================================================================
# Operation Errors
# =============================================================================


class OperationError(StorageException):
    """Base class for operation errors."""

    pass


class CopyError(OperationError):
    """Raised when file copy fails."""

    def __init__(self, source: str, destination: str, reason: str = "", **kwargs):
        self.source = source
        self.destination = destination
        kwargs.setdefault("details", {}).update(
            {
                "source": source,
                "destination": destination,
            }
        )
        super().__init__(message=f"Failed to copy file: {reason}", path=source, **kwargs)


class MoveError(OperationError):
    """Raised when file move fails."""

    def __init__(self, source: str, destination: str, reason: str = "", **kwargs):
        self.source = source
        self.destination = destination
        kwargs.setdefault("details", {}).update(
            {
                "source": source,
                "destination": destination,
            }
        )
        super().__init__(message=f"Failed to move file: {reason}", path=source, **kwargs)


class UploadError(OperationError):
    """Raised when file upload fails."""

    def __init__(self, filename: str, reason: str = "", **kwargs):
        super().__init__(message=f"Upload failed: {reason}", path=filename, **kwargs)


class DownloadError(OperationError):
    """Raised when file download fails."""

    def __init__(self, path: str, reason: str = "", **kwargs):
        super().__init__(message=f"Download failed: {reason}", path=path, **kwargs)


# =============================================================================
# Helper Functions
# =============================================================================


def is_storage_error(exception: Exception) -> bool:
    """Check if exception is storage-related."""
    return isinstance(exception, StorageException)


def wrap_os_error(
    exception: OSError, path: Optional[str] = None, backend: Optional[str] = None
) -> StorageException:
    """
    Wrap an OSError in appropriate StorageException.

    Args:
        exception: Original OSError
        path: File path involved
        backend: Backend name

    Returns:
        Appropriate StorageException subclass
    """
    import errno

    path = path or str(getattr(exception, "filename", ""))

    if exception.errno == errno.ENOENT:
        return FileNotFoundError(path, backend=backend)
    elif exception.errno == errno.EEXIST:
        return FileExistsError(path, backend=backend)
    elif exception.errno == errno.EACCES:
        return BackendPermissionError(backend or "local", operation="access", path=path)
    elif exception.errno == errno.ENOSPC:
        return FileWriteError(path, reason="No space left on device", backend=backend)
    elif exception.errno == errno.EISDIR:
        return FileReadError(path, reason="Is a directory", backend=backend)
    elif exception.errno == errno.ENOTDIR:
        return DirectoryNotFoundError(path, backend=backend)
    elif exception.errno == errno.ENOTEMPTY:
        return DirectoryNotEmptyError(path, backend=backend)
    else:
        return StorageException(
            message=str(exception), path=path, backend=backend, details={"errno": exception.errno}
        )
