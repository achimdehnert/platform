"""
Storage Service Base Classes

Abstract base class for storage backends.
Part of the consolidated Core Storage Service.
"""

import io
import json
import logging
import os
import shutil
import tempfile
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Callable, Dict, Generator, Iterator, List, Optional, Tuple, Union

try:
    from .exceptions import (
        FileExistsError,
        FileNotFoundError,
        FileReadError,
        FileSizeError,
        FileWriteError,
        InvalidExtensionError,
        StorageException,
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
    )
except ImportError:
    from exceptions import (
        FileExistsError,
        FileNotFoundError,
        FileReadError,
        FileSizeError,
        FileWriteError,
        InvalidExtensionError,
        StorageException,
        wrap_os_error,
    )
    from models import (
        FileMetadata,
        ProjectStructure,
        StorageBackend,
        StorageConfig,
        StorageType,
        calculate_checksum,
        generate_file_path,
        get_content_type,
    )


logger = logging.getLogger(__name__)


class BaseStorageBackend(ABC):
    """
    Abstract base class for storage backends.

    All storage backends must implement the abstract methods.
    Provides common functionality for path handling, validation,
    and file operations.

    Abstract Methods (must implement):
        - _read(path) -> bytes
        - _write(path, content) -> bool
        - _delete(path) -> bool
        - _exists(path) -> bool
        - _list(path) -> List[str]

    Optional Methods (can override):
        - _copy(src, dst) -> bool
        - _move(src, dst) -> bool
        - _get_metadata(path) -> FileMetadata
    """

    def __init__(self, config: Optional[StorageConfig] = None):
        """
        Initialize storage backend.

        Args:
            config: Storage configuration
        """
        self.config = config or StorageConfig()

    @property
    def name(self) -> str:
        """Get backend name."""
        return self.__class__.__name__

    # =========================================================================
    # Abstract Methods (MUST implement)
    # =========================================================================

    @abstractmethod
    def _read(self, path: str) -> bytes:
        """
        Read file content as bytes.

        Args:
            path: Relative path within storage

        Returns:
            File content as bytes
        """
        pass

    @abstractmethod
    def _write(self, path: str, content: bytes) -> bool:
        """
        Write content to file.

        Args:
            path: Relative path within storage
            content: Content to write

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def _delete(self, path: str) -> bool:
        """
        Delete a file.

        Args:
            path: Relative path within storage

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    def _exists(self, path: str) -> bool:
        """
        Check if path exists.

        Args:
            path: Relative path within storage

        Returns:
            True if exists
        """
        pass

    @abstractmethod
    def _list(self, path: str = "") -> List[str]:
        """
        List files in directory.

        Args:
            path: Directory path

        Returns:
            List of file/directory names
        """
        pass

    # =========================================================================
    # Optional Methods (can override)
    # =========================================================================

    def _copy(self, source: str, destination: str) -> bool:
        """
        Copy a file.

        Default implementation reads and writes.
        Override for backends that support native copy.
        """
        content = self._read(source)
        return self._write(destination, content)

    def _move(self, source: str, destination: str) -> bool:
        """
        Move a file.

        Default implementation copies then deletes.
        Override for backends that support native move.
        """
        if self._copy(source, destination):
            return self._delete(source)
        return False

    def _get_metadata(self, path: str) -> Optional[FileMetadata]:
        """
        Get file metadata.

        Default returns basic metadata.
        Override for backends with rich metadata support.
        """
        if not self._exists(path):
            return None

        content = self._read(path)
        return FileMetadata(
            path=path,
            filename=Path(path).name,
            size_bytes=len(content),
            content_type=get_content_type(path),
            storage_backend=self.config.backend,
        )

    def _mkdir(self, path: str) -> bool:
        """
        Create directory.

        Default is no-op (most backends don't need explicit dirs).
        Override for local filesystem backends.
        """
        return True

    def _get_url(self, path: str) -> Optional[str]:
        """
        Get public URL for file.

        Returns None if not applicable.
        Override for backends that support public URLs.
        """
        if self.config.public_url_base:
            return f"{self.config.public_url_base.rstrip('/')}/{path}"
        return None

    # =========================================================================
    # Public API - Reading
    # =========================================================================

    def read(self, path: str) -> bytes:
        """
        Read file content as bytes.

        Args:
            path: File path

        Returns:
            File content

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not self.exists(path):
            raise FileNotFoundError(path, backend=self.name)

        try:
            return self._read(path)
        except Exception as e:
            if isinstance(e, StorageException):
                raise
            raise FileReadError(path, reason=str(e), backend=self.name)

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """
        Read file content as text.

        Args:
            path: File path
            encoding: Text encoding

        Returns:
            File content as string
        """
        return self.read(path).decode(encoding)

    def read_json(self, path: str) -> Any:
        """
        Read and parse JSON file.

        Args:
            path: File path

        Returns:
            Parsed JSON data
        """
        content = self.read_text(path)
        return json.loads(content)

    def stream(self, path: str, chunk_size: int = 8192) -> Iterator[bytes]:
        """
        Stream file content in chunks.

        Args:
            path: File path
            chunk_size: Chunk size in bytes

        Yields:
            File content chunks
        """
        content = self.read(path)
        for i in range(0, len(content), chunk_size):
            yield content[i : i + chunk_size]

    # =========================================================================
    # Public API - Writing
    # =========================================================================

    def write(
        self,
        path: str,
        content: Union[bytes, str, BinaryIO],
        overwrite: bool = True,
        encoding: str = "utf-8",
    ) -> FileMetadata:
        """
        Write content to file.

        Args:
            path: File path
            content: Content to write (bytes, str, or file-like)
            overwrite: Allow overwriting existing files
            encoding: Encoding for string content

        Returns:
            File metadata

        Raises:
            FileExistsError: If file exists and overwrite=False
            FileSizeError: If content exceeds max size
        """
        # Check if exists
        if not overwrite and self.exists(path):
            raise FileExistsError(path, backend=self.name)

        # Convert content to bytes
        if isinstance(content, str):
            content_bytes = content.encode(encoding)
        elif hasattr(content, "read"):
            content_bytes = content.read()
            if isinstance(content_bytes, str):
                content_bytes = content_bytes.encode(encoding)
        else:
            content_bytes = content

        # Validate size
        if len(content_bytes) > self.config.max_file_size:
            raise FileSizeError(
                path,
                size_bytes=len(content_bytes),
                max_bytes=self.config.max_file_size,
                backend=self.name,
            )

        # Validate extension
        if self.config.allowed_extensions:
            ext = Path(path).suffix.lower().lstrip(".")
            allowed = [e.lstrip(".").lower() for e in self.config.allowed_extensions]
            if ext and ext not in allowed:
                raise InvalidExtensionError(path, ext, allowed=allowed, backend=self.name)

        # Write
        try:
            self._write(path, content_bytes)
        except Exception as e:
            if isinstance(e, StorageException):
                raise
            raise FileWriteError(path, reason=str(e), backend=self.name)

        # Return metadata
        return FileMetadata(
            path=path,
            filename=Path(path).name,
            size_bytes=len(content_bytes),
            content_type=get_content_type(path),
            storage_backend=self.config.backend,
            storage_url=self._get_url(path),
        )

    def write_text(
        self, path: str, content: str, encoding: str = "utf-8", **kwargs
    ) -> FileMetadata:
        """Write text content to file."""
        return self.write(path, content, encoding=encoding, **kwargs)

    def write_json(self, path: str, data: Any, indent: int = 2, **kwargs) -> FileMetadata:
        """Write JSON data to file."""
        content = json.dumps(data, indent=indent, default=str)
        return self.write(path, content, **kwargs)

    # =========================================================================
    # Public API - File Operations
    # =========================================================================

    def delete(self, path: str, missing_ok: bool = False) -> bool:
        """
        Delete a file.

        Args:
            path: File path
            missing_ok: Don't raise error if file doesn't exist

        Returns:
            True if deleted
        """
        if not self.exists(path):
            if missing_ok:
                return False
            raise FileNotFoundError(path, backend=self.name)

        return self._delete(path)

    def exists(self, path: str) -> bool:
        """Check if file/directory exists."""
        return self._exists(path)

    def copy(self, source: str, destination: str) -> FileMetadata:
        """
        Copy a file.

        Args:
            source: Source path
            destination: Destination path

        Returns:
            Destination file metadata
        """
        if not self.exists(source):
            raise FileNotFoundError(source, backend=self.name)

        self._copy(source, destination)
        return self.get_metadata(destination)

    def move(self, source: str, destination: str) -> FileMetadata:
        """
        Move a file.

        Args:
            source: Source path
            destination: Destination path

        Returns:
            Destination file metadata
        """
        if not self.exists(source):
            raise FileNotFoundError(source, backend=self.name)

        self._move(source, destination)
        return self.get_metadata(destination)

    def rename(self, path: str, new_name: str) -> FileMetadata:
        """
        Rename a file (keeping same directory).

        Args:
            path: Current path
            new_name: New filename

        Returns:
            New file metadata
        """
        directory = str(Path(path).parent)
        new_path = f"{directory}/{new_name}" if directory != "." else new_name
        return self.move(path, new_path)

    # =========================================================================
    # Public API - Directory Operations
    # =========================================================================

    def list(
        self, path: str = "", pattern: Optional[str] = None, recursive: bool = False
    ) -> List[str]:
        """
        List files in directory.

        Args:
            path: Directory path
            pattern: Glob pattern to filter
            recursive: Include subdirectories

        Returns:
            List of file paths
        """
        files = self._list(path)

        if pattern:
            import fnmatch

            files = [f for f in files if fnmatch.fnmatch(f, pattern)]

        return files

    def mkdir(self, path: str, exist_ok: bool = True) -> bool:
        """
        Create directory.

        Args:
            path: Directory path
            exist_ok: Don't raise error if exists

        Returns:
            True if created
        """
        return self._mkdir(path)

    # =========================================================================
    # Public API - Metadata
    # =========================================================================

    def get_metadata(self, path: str) -> FileMetadata:
        """
        Get file metadata.

        Args:
            path: File path

        Returns:
            File metadata
        """
        if not self.exists(path):
            raise FileNotFoundError(path, backend=self.name)

        metadata = self._get_metadata(path)
        if metadata:
            return metadata

        # Fallback
        return FileMetadata(
            path=path,
            filename=Path(path).name,
            storage_backend=self.config.backend,
        )

    def get_url(self, path: str) -> Optional[str]:
        """
        Get public URL for file.

        Args:
            path: File path

        Returns:
            URL or None
        """
        return self._get_url(path)

    def get_checksum(self, path: str, algorithm: str = "md5") -> str:
        """
        Calculate file checksum.

        Args:
            path: File path
            algorithm: Hash algorithm

        Returns:
            Checksum hex string
        """
        import hashlib

        content = self.read(path)
        return hashlib.new(algorithm, content).hexdigest()

    # =========================================================================
    # Utility Methods
    # =========================================================================

    @contextmanager
    def open(self, path: str, mode: str = "rb") -> Generator[BinaryIO, None, None]:
        """
        Open file as context manager.

        Args:
            path: File path
            mode: Open mode ('rb', 'wb', etc.)

        Yields:
            File-like object
        """
        if "r" in mode:
            content = self.read(path)
            yield io.BytesIO(content)
        else:
            buffer = io.BytesIO()
            try:
                yield buffer
            finally:
                buffer.seek(0)
                self.write(path, buffer.read())

    def health_check(self) -> bool:
        """
        Check if backend is healthy.

        Returns:
            True if backend is working
        """
        try:
            test_path = "_health_check_test"
            test_content = b"ok"

            self.write(test_path, test_content)
            result = self.read(test_path)
            self.delete(test_path)

            return result == test_content
        except Exception:
            return False
