"""
Local filesystem storage backend.
"""

from __future__ import annotations

from pathlib import Path

import structlog

from pptx_hub.core.storage.base import StorageBackend

logger = structlog.get_logger(__name__)


class LocalStorage(StorageBackend):
    """
    Local filesystem storage backend.
    
    Stores files on the local filesystem with configurable base path.
    
    Example:
        storage = LocalStorage(base_path="/data/presentations")
        storage.save("org/123/file.pptx", content)
    """
    
    def __init__(self, base_path: str | Path) -> None:
        """
        Initialize local storage.
        
        Args:
            base_path: Root directory for storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.log = logger.bind(storage="local", base_path=str(self.base_path))
    
    def _full_path(self, path: str) -> Path:
        """Get full filesystem path."""
        return self.base_path / path
    
    def save(self, path: str, content: bytes) -> str:
        """Save content to local filesystem."""
        full_path = self._full_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)
        self.log.debug("file_saved", path=path, size=len(content))
        return str(full_path)
    
    def read(self, path: str) -> bytes | None:
        """Read content from local filesystem."""
        full_path = self._full_path(path)
        if full_path.exists():
            return full_path.read_bytes()
        return None
    
    def delete(self, path: str) -> bool:
        """Delete file from local filesystem."""
        full_path = self._full_path(path)
        if full_path.exists():
            full_path.unlink()
            self.log.debug("file_deleted", path=path)
            return True
        return False
    
    def exists(self, path: str) -> bool:
        """Check if file exists on local filesystem."""
        return self._full_path(path).exists()
    
    def get_url(self, path: str, expires_in: int = 3600) -> str:
        """
        Get URL for local file.
        
        Note: For local storage, this returns the filesystem path.
        In a web context, you'd typically serve these through Django's
        media URL configuration.
        """
        return str(self._full_path(path))
    
    def list_files(self, prefix: str = "") -> list[str]:
        """
        List files with given prefix.
        
        Args:
            prefix: Path prefix to filter by
            
        Returns:
            List of relative paths
        """
        base = self._full_path(prefix) if prefix else self.base_path
        
        if not base.exists():
            return []
        
        files = []
        for path in base.rglob("*"):
            if path.is_file():
                rel_path = path.relative_to(self.base_path)
                files.append(str(rel_path))
        
        return files
    
    def get_size(self, path: str) -> int | None:
        """Get file size in bytes."""
        full_path = self._full_path(path)
        if full_path.exists():
            return full_path.stat().st_size
        return None
