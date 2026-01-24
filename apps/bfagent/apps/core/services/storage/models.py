"""
Storage Service Models

Typed dataclasses for storage configuration, file metadata, and paths.
Part of the consolidated Core Storage Service.
"""

import hashlib
import mimetypes
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class StorageBackend(str, Enum):
    """Supported storage backends."""

    LOCAL = "local"  # Local filesystem
    MEDIA = "media"  # Django MEDIA_ROOT
    S3 = "s3"  # AWS S3 / compatible
    GCS = "gcs"  # Google Cloud Storage
    AZURE = "azure"  # Azure Blob Storage


class StorageType(str, Enum):
    """Types of stored content."""

    DOCUMENT = "document"  # Text documents (md, txt, json)
    MEDIA = "media"  # Media files (images, audio, video)
    EXPORT = "export"  # Generated exports (docx, pdf, epub)
    UPLOAD = "upload"  # User uploads
    TEMP = "temp"  # Temporary files
    ASSET = "asset"  # Static assets


@dataclass
class StorageConfig:
    """
    Storage configuration settings.

    Attributes:
        backend: Storage backend to use
        base_path: Base path for local storage
        media_root: Django MEDIA_ROOT (for media backend)
        bucket_name: Cloud storage bucket name
        region: Cloud storage region
        access_key: Cloud storage access key
        secret_key: Cloud storage secret key
        endpoint_url: Custom endpoint (for S3-compatible)
        public_url_base: Base URL for public file access
        max_file_size: Maximum file size in bytes
        allowed_extensions: List of allowed file extensions
        auto_create_dirs: Automatically create directories
    """

    backend: StorageBackend = StorageBackend.LOCAL
    base_path: Optional[str] = None
    media_root: Optional[str] = None
    bucket_name: Optional[str] = None
    region: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    endpoint_url: Optional[str] = None
    public_url_base: Optional[str] = None
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_extensions: Optional[List[str]] = None
    auto_create_dirs: bool = True

    @classmethod
    def from_django_settings(cls) -> "StorageConfig":
        """Create config from Django settings."""
        try:
            from django.conf import settings

            return cls(
                backend=StorageBackend(getattr(settings, "STORAGE_BACKEND", "local")),
                base_path=getattr(settings, "STORAGE_BASE_PATH", None),
                media_root=getattr(settings, "MEDIA_ROOT", None),
                bucket_name=getattr(settings, "AWS_STORAGE_BUCKET_NAME", None),
                region=getattr(settings, "AWS_S3_REGION_NAME", None),
                access_key=getattr(settings, "AWS_ACCESS_KEY_ID", None),
                secret_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
                endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None),
                public_url_base=getattr(settings, "MEDIA_URL", "/media/"),
                max_file_size=getattr(settings, "FILE_UPLOAD_MAX_MEMORY_SIZE", 100 * 1024 * 1024),
            )
        except ImportError:
            return cls()

    def get_base_path(self) -> Path:
        """Get resolved base path."""
        if self.base_path:
            return Path(self.base_path)
        if self.media_root:
            return Path(self.media_root)
        return Path.home() / "storage"


@dataclass
class FileMetadata:
    """
    Metadata for a stored file.

    Attributes:
        path: Relative path within storage
        filename: Original filename
        size_bytes: File size in bytes
        content_type: MIME type
        checksum: File checksum (MD5)
        created_at: Creation timestamp
        modified_at: Last modification timestamp
        storage_backend: Backend where file is stored
        storage_url: Public/internal URL
        metadata: Additional custom metadata
    """

    path: str
    filename: str
    size_bytes: int = 0
    content_type: Optional[str] = None
    checksum: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    storage_backend: StorageBackend = StorageBackend.LOCAL
    storage_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def extension(self) -> str:
        """Get file extension."""
        return Path(self.filename).suffix.lower()

    @property
    def size_human(self) -> str:
        """Get human-readable file size."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if self.size_bytes < 1024:
                return f"{self.size_bytes:.1f} {unit}"
            self.size_bytes /= 1024
        return f"{self.size_bytes:.1f} PB"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "content_type": self.content_type,
            "checksum": self.checksum,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "storage_backend": self.storage_backend.value,
            "storage_url": self.storage_url,
            "metadata": self.metadata,
        }

    @classmethod
    def from_path(cls, file_path: Path, relative_to: Optional[Path] = None) -> "FileMetadata":
        """Create metadata from file path."""
        stat = file_path.stat()

        rel_path = str(file_path)
        if relative_to:
            try:
                rel_path = str(file_path.relative_to(relative_to))
            except ValueError:
                pass

        content_type, _ = mimetypes.guess_type(str(file_path))

        return cls(
            path=rel_path,
            filename=file_path.name,
            size_bytes=stat.st_size,
            content_type=content_type,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
        )


@dataclass
class ProjectStructure:
    """
    Standard project directory structure.

    Provides consistent paths for different content types
    within a project folder.
    """

    project_slug: str
    base_path: Path

    @property
    def root(self) -> Path:
        """Project root directory."""
        return self.base_path / self.project_slug

    @property
    def chapters(self) -> Path:
        """Chapters directory."""
        return self.root / "chapters"

    @property
    def characters(self) -> Path:
        """Characters directory."""
        return self.root / "characters"

    @property
    def assets(self) -> Path:
        """Assets directory (images, etc.)."""
        return self.root / "assets"

    @property
    def exports(self) -> Path:
        """Exports directory (docx, pdf, etc.)."""
        return self.root / "exports"

    @property
    def metadata_file(self) -> Path:
        """Project metadata file."""
        return self.root / "metadata.json"

    @property
    def outline_file(self) -> Path:
        """Project outline file."""
        return self.root / "outline.md"

    def ensure_dirs(self) -> None:
        """Create all directories if they don't exist."""
        for path in [self.root, self.chapters, self.characters, self.assets, self.exports]:
            path.mkdir(parents=True, exist_ok=True)

    def chapter_file(self, chapter_number: int, version: Optional[int] = None) -> Path:
        """Get path for a chapter file."""
        filename = f"chapter_{chapter_number:02d}"
        if version:
            filename += f"_v{version}"
        return self.chapters / f"{filename}.md"

    def character_file(self, character_name: str) -> Path:
        """Get path for a character file."""
        from django.utils.text import slugify

        return self.characters / f"{slugify(character_name)}.json"

    def export_file(self, format: str, version: Optional[str] = None) -> Path:
        """Get path for an export file."""
        filename = self.project_slug
        if version:
            filename += f"_{version}"
        return self.exports / f"{filename}.{format}"


def generate_file_path(
    filename: str, prefix: Optional[str] = None, date_based: bool = True, unique: bool = True
) -> str:
    """
    Generate a storage path for a file.

    Args:
        filename: Original filename
        prefix: Path prefix (e.g., "uploads/images")
        date_based: Include date in path
        unique: Add unique suffix to prevent collisions

    Returns:
        Generated path string

    Example:
        path = generate_file_path("photo.jpg", prefix="uploads")
        # Returns: "uploads/2024/01/photo_a1b2c3.jpg"
    """
    import uuid
    from datetime import datetime

    parts = []

    if prefix:
        parts.append(prefix)

    if date_based:
        now = datetime.now()
        parts.extend([str(now.year), f"{now.month:02d}"])

    name, ext = os.path.splitext(filename)

    if unique:
        suffix = uuid.uuid4().hex[:8]
        name = f"{name}_{suffix}"

    parts.append(f"{name}{ext}")

    return "/".join(parts)


def calculate_checksum(file_path: Union[str, Path], algorithm: str = "md5") -> str:
    """
    Calculate file checksum.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256)

    Returns:
        Hex digest string
    """
    hash_func = hashlib.new(algorithm)

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)

    return hash_func.hexdigest()


def validate_file_extension(
    filename: str, allowed: Optional[List[str]] = None, blocked: Optional[List[str]] = None
) -> bool:
    """
    Validate file extension.

    Args:
        filename: Filename to check
        allowed: List of allowed extensions (with or without dot)
        blocked: List of blocked extensions

    Returns:
        True if valid
    """
    ext = Path(filename).suffix.lower().lstrip(".")

    if blocked:
        blocked_clean = [e.lstrip(".").lower() for e in blocked]
        if ext in blocked_clean:
            return False

    if allowed:
        allowed_clean = [e.lstrip(".").lower() for e in allowed]
        return ext in allowed_clean

    return True


def get_content_type(filename: str) -> str:
    """Get MIME type for a filename."""
    content_type, _ = mimetypes.guess_type(filename)
    return content_type or "application/octet-stream"
