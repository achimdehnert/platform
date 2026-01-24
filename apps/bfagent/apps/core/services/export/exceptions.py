"""
Export Service Exceptions

Exception hierarchy for export operations.
Part of the consolidated Core Export Service.
"""

from typing import Any, Dict, Optional


class ExportException(Exception):
    """
    Base exception for all export-related errors.

    Attributes:
        message: Error message
        format: Export format involved
        path: File path involved
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        format: Optional[str] = None,
        path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.format = format
        self.path = path
        self.details = details or {}
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format exception message with context."""
        parts = [self.message]
        if self.format:
            parts.append(f"format={self.format}")
        if self.path:
            parts.append(f"path={self.path}")
        return " | ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/API responses."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "format": self.format,
            "path": self.path,
            "details": self.details,
        }


# =============================================================================
# Format Errors
# =============================================================================


class UnsupportedFormatError(ExportException):
    """Raised when export format is not supported."""

    def __init__(self, format: str, supported: Optional[list] = None, **kwargs):
        self.supported = supported
        msg = f"Unsupported export format: {format}"
        if supported:
            msg += f" (supported: {', '.join(supported)})"
        super().__init__(message=msg, format=format, **kwargs)


class FormatConversionError(ExportException):
    """Raised when format conversion fails."""

    def __init__(self, source_format: str, target_format: str, reason: str = "", **kwargs):
        self.source_format = source_format
        self.target_format = target_format
        msg = f"Failed to convert {source_format} to {target_format}"
        if reason:
            msg += f": {reason}"
        super().__init__(message=msg, format=target_format, **kwargs)


# =============================================================================
# Content Errors
# =============================================================================


class ContentError(ExportException):
    """Base class for content-related errors."""

    pass


class EmptyContentError(ContentError):
    """Raised when content to export is empty."""

    def __init__(self, content_type: str = "content", **kwargs):
        super().__init__(message=f"Cannot export empty {content_type}", **kwargs)


class InvalidContentError(ContentError):
    """Raised when content is invalid for export."""

    def __init__(self, reason: str, **kwargs):
        super().__init__(message=f"Invalid content: {reason}", **kwargs)


class ContentParseError(ContentError):
    """Raised when content parsing fails."""

    def __init__(self, content_type: str, reason: str = "", **kwargs):
        msg = f"Failed to parse {content_type}"
        if reason:
            msg += f": {reason}"
        super().__init__(message=msg, **kwargs)


# =============================================================================
# File Errors
# =============================================================================


class FileError(ExportException):
    """Base class for file-related errors."""

    pass


class OutputPathError(FileError):
    """Raised when output path is invalid."""

    def __init__(self, path: str, reason: str = "", **kwargs):
        msg = f"Invalid output path: {path}"
        if reason:
            msg += f" ({reason})"
        super().__init__(message=msg, path=path, **kwargs)


class FileExistsError(FileError):
    """Raised when output file already exists."""

    def __init__(self, path: str, **kwargs):
        super().__init__(message=f"Output file already exists: {path}", path=path, **kwargs)


class WriteError(FileError):
    """Raised when file writing fails."""

    def __init__(self, path: str, reason: str = "", **kwargs):
        msg = f"Failed to write file"
        if reason:
            msg += f": {reason}"
        super().__init__(message=msg, path=path, **kwargs)


class PermissionError(FileError):
    """Raised when lacking file permissions."""

    def __init__(self, path: str, operation: str = "access", **kwargs):
        super().__init__(
            message=f"Permission denied: cannot {operation} {path}", path=path, **kwargs
        )


# =============================================================================
# Dependency Errors
# =============================================================================


class DependencyError(ExportException):
    """Base class for dependency-related errors."""

    pass


class MissingDependencyError(DependencyError):
    """Raised when required dependency is not installed."""

    def __init__(self, dependency: str, format: str = "", install_cmd: str = "", **kwargs):
        self.dependency = dependency
        self.install_cmd = install_cmd

        msg = f"Missing required dependency: {dependency}"
        if install_cmd:
            msg += f". Install with: {install_cmd}"

        super().__init__(message=msg, format=format, **kwargs)


class DependencyVersionError(DependencyError):
    """Raised when dependency version is incompatible."""

    def __init__(self, dependency: str, required: str, installed: str, **kwargs):
        super().__init__(
            message=f"{dependency} version {installed} is incompatible (requires {required})",
            **kwargs,
        )


# =============================================================================
# Template Errors
# =============================================================================


class TemplateError(ExportException):
    """Base class for template-related errors."""

    pass


class TemplateNotFoundError(TemplateError):
    """Raised when template file is not found."""

    def __init__(self, template_path: str, **kwargs):
        super().__init__(
            message=f"Template not found: {template_path}", path=template_path, **kwargs
        )


class TemplateRenderError(TemplateError):
    """Raised when template rendering fails."""

    def __init__(self, template: str, reason: str = "", **kwargs):
        msg = f"Failed to render template: {template}"
        if reason:
            msg += f" ({reason})"
        super().__init__(message=msg, **kwargs)


# =============================================================================
# Exporter Errors
# =============================================================================


class ExporterError(ExportException):
    """Base class for exporter-specific errors."""

    pass


class ExporterNotFoundError(ExporterError):
    """Raised when exporter is not registered."""

    def __init__(self, exporter_name: str, **kwargs):
        super().__init__(message=f"Exporter not found: {exporter_name}", **kwargs)


class ExporterConfigError(ExporterError):
    """Raised when exporter configuration is invalid."""

    def __init__(self, exporter: str, reason: str, **kwargs):
        super().__init__(message=f"Invalid configuration for {exporter}: {reason}", **kwargs)


# =============================================================================
# Helper Functions
# =============================================================================


def is_export_error(exception: Exception) -> bool:
    """Check if exception is export-related."""
    return isinstance(exception, ExportException)


def wrap_library_error(exception: Exception, format: str, library: str) -> ExportException:
    """
    Wrap library-specific errors in ExportException.

    Args:
        exception: Original exception
        format: Export format
        library: Library name

    Returns:
        Appropriate ExportException subclass
    """
    error_msg = str(exception)

    # Common library error patterns
    if "not installed" in error_msg.lower() or "no module" in error_msg.lower():
        return MissingDependencyError(library, format=format)

    if "permission" in error_msg.lower():
        return PermissionError("", operation="export")

    return ExportException(
        message=f"{library} error: {error_msg}",
        format=format,
        details={"original_error": str(exception)},
    )
