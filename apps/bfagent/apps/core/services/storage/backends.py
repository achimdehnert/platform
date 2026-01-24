"""
Storage Backend Implementations

Concrete implementations of storage backends:
- LocalStorageBackend: Local filesystem
- MediaStorageBackend: Django MEDIA_ROOT integration
- S3StorageBackend: AWS S3 / S3-compatible storage

Part of the consolidated Core Storage Service.
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from .base import BaseStorageBackend
    from .exceptions import (
        BackendNotAvailableError,
        BackendNotConfiguredError,
        DirectoryNotFoundError,
        FileExistsError,
        FileNotFoundError,
        StorageException,
        wrap_os_error,
    )
    from .models import FileMetadata, ProjectStructure, StorageBackend, StorageConfig
except ImportError:
    from base import BaseStorageBackend
    from exceptions import (
        BackendNotAvailableError,
        BackendNotConfiguredError,
        DirectoryNotFoundError,
        FileExistsError,
        FileNotFoundError,
        StorageException,
        wrap_os_error,
    )
    from models import FileMetadata, ProjectStructure, StorageBackend, StorageConfig


logger = logging.getLogger(__name__)


# =============================================================================
# Local Filesystem Backend
# =============================================================================


class LocalStorageBackend(BaseStorageBackend):
    """
    Local filesystem storage backend.

    Stores files on the local filesystem with full path support.

    Features:
        - Full filesystem operations
        - Automatic directory creation
        - Symlink support
        - File metadata from filesystem

    Example:
        storage = LocalStorageBackend(StorageConfig(
            base_path="/var/data/myapp"
        ))
        storage.write("docs/readme.md", "# Hello")
    """

    def __init__(self, config: Optional[StorageConfig] = None):
        super().__init__(config)
        self.base_path = self.config.get_base_path()

        if self.config.auto_create_dirs:
            self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, path: str) -> Path:
        """Resolve relative path to absolute."""
        return self.base_path / path

    def _read(self, path: str) -> bytes:
        full_path = self._resolve_path(path)
        return full_path.read_bytes()

    def _write(self, path: str, content: bytes) -> bool:
        full_path = self._resolve_path(path)

        # Ensure directory exists
        if self.config.auto_create_dirs:
            full_path.parent.mkdir(parents=True, exist_ok=True)

        full_path.write_bytes(content)
        return True

    def _delete(self, path: str) -> bool:
        full_path = self._resolve_path(path)

        if full_path.is_dir():
            shutil.rmtree(full_path)
        else:
            full_path.unlink()

        return True

    def _exists(self, path: str) -> bool:
        return self._resolve_path(path).exists()

    def _list(self, path: str = "") -> List[str]:
        full_path = self._resolve_path(path)

        if not full_path.exists():
            return []

        if full_path.is_file():
            return [path]

        return [str(p.relative_to(self.base_path)) for p in full_path.iterdir()]

    def _copy(self, source: str, destination: str) -> bool:
        src_path = self._resolve_path(source)
        dst_path = self._resolve_path(destination)

        if self.config.auto_create_dirs:
            dst_path.parent.mkdir(parents=True, exist_ok=True)

        if src_path.is_dir():
            shutil.copytree(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)

        return True

    def _move(self, source: str, destination: str) -> bool:
        src_path = self._resolve_path(source)
        dst_path = self._resolve_path(destination)

        if self.config.auto_create_dirs:
            dst_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(src_path), str(dst_path))
        return True

    def _mkdir(self, path: str) -> bool:
        full_path = self._resolve_path(path)
        full_path.mkdir(parents=True, exist_ok=True)
        return True

    def _get_metadata(self, path: str) -> Optional[FileMetadata]:
        full_path = self._resolve_path(path)

        if not full_path.exists():
            return None

        return FileMetadata.from_path(full_path, relative_to=self.base_path)

    def list_recursive(self, path: str = "", pattern: str = "*") -> List[str]:
        """List files recursively with glob pattern."""
        full_path = self._resolve_path(path)

        if not full_path.exists():
            return []

        return [str(p.relative_to(self.base_path)) for p in full_path.rglob(pattern) if p.is_file()]

    def get_size(self, path: str) -> int:
        """Get file or directory size in bytes."""
        full_path = self._resolve_path(path)

        if full_path.is_file():
            return full_path.stat().st_size

        total = 0
        for p in full_path.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
        return total


# =============================================================================
# Django Media Storage Backend
# =============================================================================


class MediaStorageBackend(BaseStorageBackend):
    """
    Django MEDIA_ROOT storage backend.

    Integrates with Django's file handling and serves files
    via MEDIA_URL.

    Features:
        - Django settings integration
        - Automatic MEDIA_URL generation
        - Works with Django's staticfiles

    Example:
        storage = MediaStorageBackend()
        storage.write("uploads/document.pdf", pdf_bytes)
        url = storage.get_url("uploads/document.pdf")
        # Returns: "/media/uploads/document.pdf"
    """

    def __init__(self, config: Optional[StorageConfig] = None):
        super().__init__(config)

        try:
            from django.conf import settings

            self.media_root = Path(settings.MEDIA_ROOT)
            self.media_url = settings.MEDIA_URL
        except ImportError:
            raise BackendNotAvailableError("media", reason="Django not installed")
        except Exception as e:
            raise BackendNotConfiguredError("media", missing="MEDIA_ROOT setting")

        if self.config.auto_create_dirs:
            self.media_root.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, path: str) -> Path:
        """Resolve relative path to absolute within MEDIA_ROOT."""
        return self.media_root / path

    def _read(self, path: str) -> bytes:
        return self._resolve_path(path).read_bytes()

    def _write(self, path: str, content: bytes) -> bool:
        full_path = self._resolve_path(path)

        if self.config.auto_create_dirs:
            full_path.parent.mkdir(parents=True, exist_ok=True)

        full_path.write_bytes(content)
        return True

    def _delete(self, path: str) -> bool:
        full_path = self._resolve_path(path)

        if full_path.is_dir():
            shutil.rmtree(full_path)
        else:
            full_path.unlink()

        return True

    def _exists(self, path: str) -> bool:
        return self._resolve_path(path).exists()

    def _list(self, path: str = "") -> List[str]:
        full_path = self._resolve_path(path)

        if not full_path.exists():
            return []

        if full_path.is_file():
            return [path]

        return [str(p.relative_to(self.media_root)) for p in full_path.iterdir()]

    def _get_url(self, path: str) -> Optional[str]:
        """Get MEDIA_URL for file."""
        return f"{self.media_url.rstrip('/')}/{path}"

    def _get_metadata(self, path: str) -> Optional[FileMetadata]:
        full_path = self._resolve_path(path)

        if not full_path.exists():
            return None

        metadata = FileMetadata.from_path(full_path, relative_to=self.media_root)
        metadata.storage_url = self._get_url(path)
        return metadata

    def _mkdir(self, path: str) -> bool:
        full_path = self._resolve_path(path)
        full_path.mkdir(parents=True, exist_ok=True)
        return True


# =============================================================================
# S3 Storage Backend
# =============================================================================


class S3StorageBackend(BaseStorageBackend):
    """
    AWS S3 / S3-compatible storage backend.

    Supports AWS S3, MinIO, DigitalOcean Spaces, etc.

    Features:
        - Presigned URLs for downloads
        - Multipart uploads for large files
        - Server-side encryption
        - Custom endpoints (MinIO, etc.)

    Example:
        storage = S3StorageBackend(StorageConfig(
            bucket_name="my-bucket",
            region="us-east-1",
            access_key="...",
            secret_key="..."
        ))
        storage.write("docs/file.pdf", pdf_bytes)
        url = storage.get_presigned_url("docs/file.pdf")
    """

    def __init__(self, config: Optional[StorageConfig] = None):
        super().__init__(config)
        self._client = None
        self._resource = None

    @property
    def client(self):
        """Lazy load boto3 client."""
        if self._client is None:
            try:
                import boto3
            except ImportError:
                raise BackendNotAvailableError(
                    "s3", reason="boto3 not installed. Run: pip install boto3"
                )

            if not self.config.bucket_name:
                raise BackendNotConfiguredError("s3", missing="bucket_name")

            session_kwargs = {}
            if self.config.access_key:
                session_kwargs["aws_access_key_id"] = self.config.access_key
            if self.config.secret_key:
                session_kwargs["aws_secret_access_key"] = self.config.secret_key
            if self.config.region:
                session_kwargs["region_name"] = self.config.region

            client_kwargs = {}
            if self.config.endpoint_url:
                client_kwargs["endpoint_url"] = self.config.endpoint_url

            self._client = boto3.client("s3", **session_kwargs, **client_kwargs)

        return self._client

    @property
    def bucket(self) -> str:
        """Get bucket name."""
        return self.config.bucket_name

    def _read(self, path: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=path)
        return response["Body"].read()

    def _write(self, path: str, content: bytes) -> bool:
        import io

        content_type = None
        try:
            from .models import get_content_type

            content_type = get_content_type(path)
        except:
            import mimetypes

            content_type, _ = mimetypes.guess_type(path)

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        self.client.put_object(Bucket=self.bucket, Key=path, Body=content, **extra_args)
        return True

    def _delete(self, path: str) -> bool:
        self.client.delete_object(Bucket=self.bucket, Key=path)
        return True

    def _exists(self, path: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=path)
            return True
        except self.client.exceptions.ClientError:
            return False
        except Exception:
            return False

    def _list(self, path: str = "") -> List[str]:
        prefix = path.rstrip("/") + "/" if path else ""

        response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix, Delimiter="/")

        files = []

        # Files
        for obj in response.get("Contents", []):
            files.append(obj["Key"])

        # Directories (common prefixes)
        for prefix in response.get("CommonPrefixes", []):
            files.append(prefix["Prefix"].rstrip("/"))

        return files

    def _get_url(self, path: str) -> Optional[str]:
        """Get S3 URL."""
        if self.config.endpoint_url:
            return f"{self.config.endpoint_url}/{self.bucket}/{path}"
        return f"https://{self.bucket}.s3.amazonaws.com/{path}"

    def _get_metadata(self, path: str) -> Optional[FileMetadata]:
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=path)

            return FileMetadata(
                path=path,
                filename=Path(path).name,
                size_bytes=response.get("ContentLength", 0),
                content_type=response.get("ContentType"),
                checksum=response.get("ETag", "").strip('"'),
                modified_at=response.get("LastModified", datetime.now()),
                storage_backend=StorageBackend.S3,
                storage_url=self._get_url(path),
                metadata=response.get("Metadata", {}),
            )
        except Exception:
            return None

    def get_presigned_url(
        self, path: str, expires_in: int = 3600, method: str = "get_object"
    ) -> str:
        """
        Generate presigned URL for file access.

        Args:
            path: File path
            expires_in: URL expiration in seconds
            method: S3 method (get_object, put_object)

        Returns:
            Presigned URL
        """
        return self.client.generate_presigned_url(
            method, Params={"Bucket": self.bucket, "Key": path}, ExpiresIn=expires_in
        )

    def upload_fileobj(
        self, fileobj, path: str, content_type: Optional[str] = None
    ) -> FileMetadata:
        """
        Upload file-like object (efficient for large files).

        Args:
            fileobj: File-like object
            path: Destination path
            content_type: MIME type

        Returns:
            File metadata
        """
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        self.client.upload_fileobj(fileobj, self.bucket, path, ExtraArgs=extra_args or None)

        return self.get_metadata(path)


# =============================================================================
# Project Storage (High-Level API)
# =============================================================================


class ProjectStorage:
    """
    High-level storage API for project-based content.

    Provides structured storage for projects with chapters,
    characters, assets, and exports.

    Example:
        storage = ProjectStorage("my-novel")
        storage.save_chapter(1, "Chapter content...", metadata={...})
        storage.save_character("protagonist", {...})
        storage.save_metadata({...})
    """

    def __init__(
        self,
        project_slug: str,
        backend: Optional[BaseStorageBackend] = None,
        base_path: Optional[str] = None,
    ):
        """
        Initialize project storage.

        Args:
            project_slug: Project identifier
            backend: Storage backend (defaults to LocalStorageBackend)
            base_path: Base path for storage
        """
        self.project_slug = project_slug

        if backend:
            self.backend = backend
        else:
            config = StorageConfig(base_path=base_path or str(Path.home() / "domains"))
            self.backend = LocalStorageBackend(config)

        self.structure = ProjectStructure(
            project_slug=project_slug, base_path=self.backend.config.get_base_path()
        )
        self.structure.ensure_dirs()

    # =========================================================================
    # Chapter Operations
    # =========================================================================

    def save_chapter(
        self,
        chapter_number: int,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        version: Optional[int] = None,
    ) -> str:
        """
        Save chapter content.

        Args:
            chapter_number: Chapter number
            content: Chapter content (markdown)
            metadata: Optional metadata
            version: Optional version number

        Returns:
            Path to saved file
        """
        # Build path
        rel_path = f"{self.project_slug}/chapters/chapter_{chapter_number:02d}"
        if version:
            rel_path += f"_v{version}"
        rel_path += ".md"

        # Format content with metadata header
        if metadata:
            header = "---\n"
            for key, value in metadata.items():
                header += f"{key}: {value}\n"
            header += "---\n\n"
            content = header + content

        self.backend.write(rel_path, content)

        # Save metadata separately
        if metadata:
            meta_path = rel_path.replace(".md", "_metadata.json")
            metadata["saved_at"] = datetime.now().isoformat()
            self.backend.write_json(meta_path, metadata)

        logger.info(f"Saved chapter {chapter_number} to {rel_path}")
        return rel_path

    def load_chapter(self, chapter_number: int, version: Optional[int] = None) -> Optional[str]:
        """Load chapter content."""
        rel_path = f"{self.project_slug}/chapters/chapter_{chapter_number:02d}"
        if version:
            rel_path += f"_v{version}"
        rel_path += ".md"

        if not self.backend.exists(rel_path):
            return None

        return self.backend.read_text(rel_path)

    def chapter_exists(self, chapter_number: int, version: Optional[int] = None) -> bool:
        """Check if chapter exists."""
        rel_path = f"{self.project_slug}/chapters/chapter_{chapter_number:02d}"
        if version:
            rel_path += f"_v{version}"
        rel_path += ".md"
        return self.backend.exists(rel_path)

    def list_chapters(self) -> List[int]:
        """List all chapter numbers."""
        import re

        chapter_path = f"{self.project_slug}/chapters"
        if not self.backend.exists(chapter_path):
            return []

        files = self.backend.list(chapter_path)
        chapters = []

        for f in files:
            match = re.match(r"chapter_(\d+)\.md$", Path(f).name)
            if match:
                chapters.append(int(match.group(1)))

        return sorted(chapters)

    # =========================================================================
    # Character Operations
    # =========================================================================

    def save_character(self, name: str, data: Dict[str, Any]) -> str:
        """Save character data."""
        from django.utils.text import slugify

        rel_path = f"{self.project_slug}/characters/{slugify(name)}.json"
        data["saved_at"] = datetime.now().isoformat()

        self.backend.write_json(rel_path, data)
        logger.info(f"Saved character '{name}' to {rel_path}")
        return rel_path

    def load_character(self, name: str) -> Optional[Dict[str, Any]]:
        """Load character data."""
        from django.utils.text import slugify

        rel_path = f"{self.project_slug}/characters/{slugify(name)}.json"

        if not self.backend.exists(rel_path):
            return None

        return self.backend.read_json(rel_path)

    # =========================================================================
    # Metadata Operations
    # =========================================================================

    def save_metadata(self, metadata: Dict[str, Any]) -> str:
        """Save project metadata."""
        rel_path = f"{self.project_slug}/metadata.json"
        metadata["last_updated"] = datetime.now().isoformat()

        self.backend.write_json(rel_path, metadata)
        return rel_path

    def load_metadata(self) -> Optional[Dict[str, Any]]:
        """Load project metadata."""
        rel_path = f"{self.project_slug}/metadata.json"

        if not self.backend.exists(rel_path):
            return None

        return self.backend.read_json(rel_path)

    # =========================================================================
    # Export Operations
    # =========================================================================

    def get_export_path(self, format: str, version: Optional[str] = None) -> str:
        """Get path for export file."""
        filename = self.project_slug
        if version:
            filename += f"_{version}"
        return f"{self.project_slug}/exports/{filename}.{format}"


# =============================================================================
# Backend Factory
# =============================================================================


def create_backend(
    backend_type: StorageBackend, config: Optional[StorageConfig] = None, **kwargs
) -> BaseStorageBackend:
    """
    Factory function to create storage backends.

    Args:
        backend_type: Type of backend
        config: Storage configuration
        **kwargs: Additional arguments

    Returns:
        Storage backend instance
    """
    backends = {
        StorageBackend.LOCAL: LocalStorageBackend,
        StorageBackend.MEDIA: MediaStorageBackend,
        StorageBackend.S3: S3StorageBackend,
    }

    backend_class = backends.get(backend_type)
    if backend_class is None:
        raise ValueError(f"Unknown storage backend: {backend_type}")

    return backend_class(config, **kwargs)
