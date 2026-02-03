"""
Base storage backend interface.

Defines the abstract interface for all storage backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.
    
    All storage implementations must inherit from this class
    and implement the required methods.
    """
    
    @abstractmethod
    def save(self, path: str, content: bytes) -> str:
        """
        Save content to storage.
        
        Args:
            path: Relative path within storage
            content: Binary content to save
            
        Returns:
            Full storage path/URL
        """
        ...
    
    @abstractmethod
    def read(self, path: str) -> bytes | None:
        """
        Read content from storage.
        
        Args:
            path: Path to read from
            
        Returns:
            Binary content or None if not found
        """
        ...
    
    @abstractmethod
    def delete(self, path: str) -> bool:
        """
        Delete file from storage.
        
        Args:
            path: Path to delete
            
        Returns:
            True if deleted, False otherwise
        """
        ...
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        """
        Check if file exists in storage.
        
        Args:
            path: Path to check
            
        Returns:
            True if exists, False otherwise
        """
        ...
    
    @abstractmethod
    def get_url(self, path: str, expires_in: int = 3600) -> str:
        """
        Get URL for accessing the file.
        
        Args:
            path: Path to file
            expires_in: URL expiration time in seconds (for pre-signed URLs)
            
        Returns:
            URL string
        """
        ...
    
    def save_file(self, path: str, file: BinaryIO) -> str:
        """
        Save file object to storage.
        
        Args:
            path: Relative path within storage
            file: File-like object
            
        Returns:
            Full storage path/URL
        """
        content = file.read()
        return self.save(path, content)
    
    def copy(self, source_path: str, dest_path: str) -> str:
        """
        Copy file within storage.
        
        Args:
            source_path: Source path
            dest_path: Destination path
            
        Returns:
            Destination storage path/URL
        """
        content = self.read(source_path)
        if content is None:
            raise FileNotFoundError(f"Source file not found: {source_path}")
        return self.save(dest_path, content)
    
    def move(self, source_path: str, dest_path: str) -> str:
        """
        Move file within storage.
        
        Args:
            source_path: Source path
            dest_path: Destination path
            
        Returns:
            Destination storage path/URL
        """
        result = self.copy(source_path, dest_path)
        self.delete(source_path)
        return result
