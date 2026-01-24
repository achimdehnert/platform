"""
File Extractor Exceptions

Exception hierarchy for file extraction operations.
Part of the consolidated Core File Extractor Service.
"""

from typing import Any, Dict, Optional


class ExtractorException(Exception):
    """
    Base exception for all extractor-related errors.

    Attributes:
        message: Error message
        file_path: Path to file being extracted
        file_type: Type of file
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        file_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.file_path = file_path
        self.file_type = file_type
        self.details = details or {}
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format exception message with context."""
        parts = [self.message]
        if self.file_type:
            parts.append(f"type={self.file_type}")
        if self.file_path:
            parts.append(f"path={self.file_path}")
        return " | ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/API responses."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "details": self.details,
        }


# =============================================================================
# File Errors
# =============================================================================


class FileNotFoundError(ExtractorException):
    """Raised when file does not exist."""

    def __init__(self, file_path: str, **kwargs):
        super().__init__(message=f"File not found: {file_path}", file_path=file_path, **kwargs)


class FileReadError(ExtractorException):
    """Raised when file cannot be read."""

    def __init__(self, file_path: str, reason: str = "", **kwargs):
        msg = f"Failed to read file: {file_path}"
        if reason:
            msg += f" ({reason})"
        super().__init__(message=msg, file_path=file_path, **kwargs)


class FileTooLargeError(ExtractorException):
    """Raised when file exceeds size limit."""

    def __init__(self, file_path: str, size: int, max_size: int, **kwargs):
        super().__init__(
            message=f"File too large: {size} bytes (max: {max_size})",
            file_path=file_path,
            details={"size": size, "max_size": max_size},
            **kwargs,
        )


class FileCorruptedError(ExtractorException):
    """Raised when file is corrupted."""

    def __init__(self, file_path: str, reason: str = "", **kwargs):
        msg = f"File appears corrupted: {file_path}"
        if reason:
            msg += f" ({reason})"
        super().__init__(message=msg, file_path=file_path, **kwargs)


# =============================================================================
# Format Errors
# =============================================================================


class UnsupportedFormatError(ExtractorException):
    """Raised when file format is not supported."""

    def __init__(self, file_type: str, supported: Optional[list] = None, **kwargs):
        msg = f"Unsupported file format: {file_type}"
        if supported:
            msg += f" (supported: {', '.join(supported)})"
        super().__init__(message=msg, file_type=file_type, **kwargs)


class InvalidFormatError(ExtractorException):
    """Raised when file content doesn't match expected format."""

    def __init__(self, expected: str, actual: str = "", **kwargs):
        msg = f"Invalid file format: expected {expected}"
        if actual:
            msg += f", got {actual}"
        super().__init__(message=msg, **kwargs)


# =============================================================================
# Extraction Errors
# =============================================================================


class ExtractionError(ExtractorException):
    """Base class for extraction-specific errors."""

    pass


class TextExtractionError(ExtractionError):
    """Raised when text extraction fails."""

    def __init__(self, reason: str, **kwargs):
        super().__init__(message=f"Text extraction failed: {reason}", **kwargs)


class TableExtractionError(ExtractionError):
    """Raised when table extraction fails."""

    def __init__(self, reason: str, **kwargs):
        super().__init__(message=f"Table extraction failed: {reason}", **kwargs)


class MetadataExtractionError(ExtractionError):
    """Raised when metadata extraction fails."""

    def __init__(self, reason: str, **kwargs):
        super().__init__(message=f"Metadata extraction failed: {reason}", **kwargs)


class OCRError(ExtractionError):
    """Raised when OCR processing fails."""

    def __init__(self, reason: str, **kwargs):
        super().__init__(message=f"OCR failed: {reason}", **kwargs)


# =============================================================================
# Dependency Errors
# =============================================================================


class DependencyError(ExtractorException):
    """Base class for dependency-related errors."""

    pass


class MissingDependencyError(DependencyError):
    """Raised when required dependency is not installed."""

    def __init__(self, dependency: str, file_type: str = "", install_cmd: str = "", **kwargs):
        self.dependency = dependency
        self.install_cmd = install_cmd

        msg = f"Missing required dependency: {dependency}"
        if install_cmd:
            msg += f". Install with: {install_cmd}"

        super().__init__(message=msg, file_type=file_type, **kwargs)


# =============================================================================
# Page/Sheet Errors
# =============================================================================


class PageNotFoundError(ExtractorException):
    """Raised when requested page doesn't exist."""

    def __init__(self, page: int, total_pages: int, **kwargs):
        super().__init__(
            message=f"Page {page} not found (total: {total_pages})",
            details={"page": page, "total_pages": total_pages},
            **kwargs,
        )


class SheetNotFoundError(ExtractorException):
    """Raised when requested sheet doesn't exist."""

    def __init__(self, sheet: str, available: list, **kwargs):
        super().__init__(
            message=f"Sheet '{sheet}' not found (available: {', '.join(available)})",
            details={"sheet": sheet, "available": available},
            **kwargs,
        )


# =============================================================================
# Encoding Errors
# =============================================================================


class EncodingError(ExtractorException):
    """Raised when file encoding is invalid."""

    def __init__(self, encoding: str, file_path: str = "", **kwargs):
        super().__init__(message=f"Invalid encoding: {encoding}", file_path=file_path, **kwargs)


# =============================================================================
# Password/Security Errors
# =============================================================================


class PasswordRequiredError(ExtractorException):
    """Raised when file is password-protected."""

    def __init__(self, file_path: str = "", **kwargs):
        super().__init__(message="File is password-protected", file_path=file_path, **kwargs)


class InvalidPasswordError(ExtractorException):
    """Raised when provided password is incorrect."""

    def __init__(self, file_path: str = "", **kwargs):
        super().__init__(message="Invalid password", file_path=file_path, **kwargs)


# =============================================================================
# Helper Functions
# =============================================================================


def is_extractor_error(exception: Exception) -> bool:
    """Check if exception is extractor-related."""
    return isinstance(exception, ExtractorException)


def wrap_library_error(exception: Exception, file_type: str, library: str) -> ExtractorException:
    """
    Wrap library-specific errors in ExtractorException.

    Args:
        exception: Original exception
        file_type: File type being processed
        library: Library name

    Returns:
        Appropriate ExtractorException subclass
    """
    error_msg = str(exception).lower()

    # Common patterns
    if "not installed" in error_msg or "no module" in error_msg:
        return MissingDependencyError(library, file_type=file_type)

    if "password" in error_msg or "encrypted" in error_msg:
        return PasswordRequiredError()

    if "corrupt" in error_msg or "invalid" in error_msg:
        return FileCorruptedError("", reason=str(exception))

    return ExtractionError(reason=f"{library} error: {exception}", file_type=file_type)
