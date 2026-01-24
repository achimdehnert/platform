"""
Core Storage Service

Unified file storage system with multiple backend support.

Features:
    - Multiple backends: Local, Django Media, S3
    - Consistent API across all backends
    - Project-based content organization
    - File metadata tracking
    - Checksum verification

Quick Start:
    from apps.core.services.storage import storage, ProjectStorage

    # Simple file operations
    storage.write("docs/readme.md", "# Hello")
    content = storage.read("docs/readme.md")

    # Project-based storage
    project = ProjectStorage("my-novel")
    project.save_chapter(1, "Chapter content...")
    project.save_metadata({"title": "My Novel", "genre": "Fiction"})

Backends:
    - LOCAL: Local filesystem
    - MEDIA: Django MEDIA_ROOT
    - S3: AWS S3 / compatible (MinIO, DigitalOcean Spaces)

Configuration:
    # Django settings
    STORAGE_BACKEND = "local"  # or "media", "s3"
    STORAGE_BASE_PATH = "/var/data/myapp"

    # S3 settings
    AWS_STORAGE_BUCKET_NAME = "my-bucket"
    AWS_S3_REGION_NAME = "us-east-1"
    AWS_ACCESS_KEY_ID = "..."
    AWS_SECRET_ACCESS_KEY = "..."

Migration from existing code:
    # Old: from apps.core.services.storage import StorageService
    # New: from apps.core.services.storage import ProjectStorage

    # Old: from apps.core.services.storage import ContentStorageService
    # New: from apps.core.services.storage import ProjectStorage
"""

from typing import Any, Optional

from .backends import (
    LocalStorageBackend,
    MediaStorageBackend,
    ProjectStorage,
    S3StorageBackend,
    create_backend,
)
from .base import BaseStorageBackend
from .exceptions import (
    BackendConnectionError,
    BackendError,
    BackendNotAvailableError,
    BackendNotConfiguredError,
    BackendPermissionError,
    ChecksumMismatchError,
    CopyError,
    DirectoryExistsError,
    DirectoryNotEmptyError,
    DirectoryNotFoundError,
    DownloadError,
    FileDeleteError,
    FileExistsError,
    FileNotFoundError,
    FileReadError,
    FileSizeError,
    FileWriteError,
    InvalidContentTypeError,
    InvalidExtensionError,
    MoveError,
    StorageException,
    UploadError,
    ValidationError,
    is_storage_error,
    wrap_os_error,
)
from .models import (
    FileMetadata,
    ProjectStructure,
    StorageBackend,
    StorageConfig,
    StorageType,
    calculate_checksum,
    generate_file_path,
    get_content_type,
    validate_file_extension,
)

# =============================================================================
# Global Storage Instance
# =============================================================================

_default_storage: Optional[BaseStorageBackend] = None
_storage_lock = __import__("threading").Lock()


def get_storage(
    backend: Optional[str] = None, config: Optional[StorageConfig] = None, **kwargs
) -> BaseStorageBackend:
    """
    Get or create a storage backend instance.

    Args:
        backend: Backend type ("local", "media", "s3")
        config: Storage configuration
        **kwargs: Additional backend arguments

    Returns:
        Storage backend instance

    Example:
        # Auto-detect from Django settings
        storage = get_storage()

        # Explicit backend
        storage = get_storage("s3", config=StorageConfig(
            bucket_name="my-bucket"
        ))
    """
    global _default_storage

    if backend is None and config is None and not kwargs:
        if _default_storage is not None:
            return _default_storage

        with _storage_lock:
            if _default_storage is None:
                _default_storage = _create_default_storage()
            return _default_storage

    return _create_storage(backend, config, **kwargs)


def _detect_backend() -> StorageBackend:
    """Auto-detect best available storage backend."""
    try:
        from django.conf import settings

        backend_name = getattr(settings, "STORAGE_BACKEND", None)
        if backend_name:
            return StorageBackend(backend_name)

        # Check for S3 config
        if getattr(settings, "AWS_STORAGE_BUCKET_NAME", None):
            return StorageBackend.S3

        # Check for MEDIA_ROOT
        if getattr(settings, "MEDIA_ROOT", None):
            return StorageBackend.MEDIA
    except ImportError:
        pass

    return StorageBackend.LOCAL


def _create_default_storage() -> BaseStorageBackend:
    """Create default storage from settings."""
    backend_type = _detect_backend()
    config = StorageConfig.from_django_settings()
    return create_backend(backend_type, config)


def _create_storage(
    backend: Optional[str], config: Optional[StorageConfig], **kwargs
) -> BaseStorageBackend:
    """Create a storage backend instance."""
    if backend is None:
        backend_type = _detect_backend()
    else:
        backend_type = StorageBackend(backend)

    if config is None:
        config = StorageConfig.from_django_settings()

    return create_backend(backend_type, config, **kwargs)


def reset_storage() -> None:
    """Reset the global storage instance."""
    global _default_storage
    with _storage_lock:
        _default_storage = None


# =============================================================================
# Convenience Functions
# =============================================================================


def read(path: str) -> bytes:
    """Read file from default storage."""
    return get_storage().read(path)


def read_text(path: str, encoding: str = "utf-8") -> str:
    """Read text file from default storage."""
    return get_storage().read_text(path, encoding)


def write(path: str, content: Any, **kwargs) -> FileMetadata:
    """Write file to default storage."""
    return get_storage().write(path, content, **kwargs)


def delete(path: str, missing_ok: bool = False) -> bool:
    """Delete file from default storage."""
    return get_storage().delete(path, missing_ok)


def exists(path: str) -> bool:
    """Check if file exists in default storage."""
    return get_storage().exists(path)


# =============================================================================
# Storage Proxy
# =============================================================================


class _StorageProxy:
    """Proxy for lazy storage access."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_storage(), name)


# Global storage instance (lazy loaded)
storage = _StorageProxy()


# =============================================================================
# Backward Compatibility Aliases
# =============================================================================

# Alias for old code that imports ContentStorageService
ContentStorageService = ProjectStorage
StorageService = ProjectStorage


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Main interface
    "storage",
    "get_storage",
    "reset_storage",
    # Backward compatibility
    "ContentStorageService",
    "StorageService",
    # Convenience functions
    "read",
    "read_text",
    "write",
    "delete",
    "exists",
    # High-level API
    "ProjectStorage",
    # Models
    "StorageConfig",
    "StorageBackend",
    "StorageType",
    "FileMetadata",
    "ProjectStructure",
    "generate_file_path",
    "calculate_checksum",
    "validate_file_extension",
    "get_content_type",
    # Backend classes
    "BaseStorageBackend",
    "LocalStorageBackend",
    "MediaStorageBackend",
    "S3StorageBackend",
    "create_backend",
    # Exceptions
    "StorageException",
    "FileNotFoundError",
    "FileExistsError",
    "FileReadError",
    "FileWriteError",
    "FileDeleteError",
    "DirectoryNotFoundError",
    "DirectoryExistsError",
    "DirectoryNotEmptyError",
    "ValidationError",
    "FileSizeError",
    "InvalidExtensionError",
    "InvalidContentTypeError",
    "ChecksumMismatchError",
    "BackendError",
    "BackendNotAvailableError",
    "BackendNotConfiguredError",
    "BackendConnectionError",
    "BackendPermissionError",
    "CopyError",
    "MoveError",
    "UploadError",
    "DownloadError",
    "is_storage_error",
    "wrap_os_error",
]
