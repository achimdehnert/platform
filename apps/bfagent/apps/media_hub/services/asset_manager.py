"""
Asset Manager Service
=====================

Manages asset storage, retrieval, and file operations.
"""
import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List, BinaryIO
from datetime import datetime

from django.conf import settings
from django.core.files.storage import default_storage
import structlog

logger = structlog.get_logger(__name__)


class AssetManager:
    """
    Manages Media Hub assets and their file variants.
    
    Responsibilities:
    - File storage/retrieval
    - Thumbnail generation
    - Asset metadata extraction
    - Cleanup of orphaned files
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize asset manager."""
        self.base_path = Path(base_path or settings.MEDIA_ROOT) / 'media_hub' / 'assets'
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.log = logger.bind(service="AssetManager")
    
    def get_asset_path(self, asset_id: int, file_type: str = 'original') -> Path:
        """Get storage path for an asset file."""
        # Organize by asset ID (sharded)
        shard = str(asset_id % 1000).zfill(3)
        return self.base_path / shard / str(asset_id) / file_type
    
    def save_file(self, asset_id: int, file_data: bytes, 
                  filename: str, file_type: str = 'original') -> Dict[str, Any]:
        """
        Save a file for an asset.
        
        Returns dict with path, size, checksum, mime_type.
        """
        # Create directory structure
        asset_dir = self.get_asset_path(asset_id, file_type)
        asset_dir.mkdir(parents=True, exist_ok=True)
        
        # Full path
        filepath = asset_dir / filename
        
        # Write file
        filepath.write_bytes(file_data)
        
        # Calculate metadata
        checksum = hashlib.sha256(file_data).hexdigest()
        mime_type, _ = mimetypes.guess_type(filename)
        
        self.log.info("file_saved", 
                     asset_id=asset_id, 
                     path=str(filepath),
                     size=len(file_data))
        
        return {
            'path': str(filepath),
            'relative_path': str(filepath.relative_to(settings.MEDIA_ROOT)),
            'size': len(file_data),
            'checksum': checksum,
            'mime_type': mime_type or 'application/octet-stream',
        }
    
    def get_file(self, storage_path: str) -> Optional[bytes]:
        """Read file contents from storage path."""
        path = Path(storage_path)
        if not path.is_absolute():
            path = Path(settings.MEDIA_ROOT) / storage_path
        
        if path.exists():
            return path.read_bytes()
        return None
    
    def delete_file(self, storage_path: str) -> bool:
        """Delete a file from storage."""
        path = Path(storage_path)
        if not path.is_absolute():
            path = Path(settings.MEDIA_ROOT) / storage_path
        
        if path.exists():
            path.unlink()
            self.log.info("file_deleted", path=str(path))
            return True
        return False
    
    def create_thumbnail(self, asset_id: int, 
                         original_path: str,
                         max_size: tuple = (256, 256)) -> Optional[Dict[str, Any]]:
        """
        Create a thumbnail for an image asset.
        
        Requires PIL/Pillow.
        """
        try:
            from PIL import Image
        except ImportError:
            self.log.warning("pillow_not_installed", msg="Thumbnail creation requires Pillow")
            return None
        
        path = Path(original_path)
        if not path.exists():
            return None
        
        try:
            with Image.open(path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Create thumbnail
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save
                thumb_filename = f"thumb_{path.stem}.jpg"
                thumb_data = bytearray()
                
                from io import BytesIO
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                thumb_bytes = buffer.getvalue()
                
                return self.save_file(asset_id, thumb_bytes, thumb_filename, 'thumbnail')
                
        except Exception as e:
            self.log.error("thumbnail_failed", error=str(e), path=str(path))
            return None
    
    def get_asset_url(self, storage_path: str) -> str:
        """Get public URL for an asset file."""
        # Convert storage path to URL
        if storage_path.startswith(str(settings.MEDIA_ROOT)):
            relative = storage_path[len(str(settings.MEDIA_ROOT)):].lstrip('/')
        else:
            relative = storage_path
        
        return f"{settings.MEDIA_URL}{relative}"
    
    def cleanup_orphaned_files(self, dry_run: bool = True) -> List[str]:
        """
        Find and optionally delete files not linked to any asset.
        
        Returns list of orphaned file paths.
        """
        from apps.media_hub.models import AssetFile
        
        # Get all referenced paths
        referenced = set(AssetFile.objects.values_list('storage_path', flat=True))
        
        # Find all files in storage
        orphaned = []
        for filepath in self.base_path.rglob('*'):
            if filepath.is_file():
                str_path = str(filepath)
                if str_path not in referenced:
                    orphaned.append(str_path)
                    if not dry_run:
                        filepath.unlink()
        
        if orphaned:
            self.log.info("orphaned_files", 
                         count=len(orphaned), 
                         dry_run=dry_run)
        
        return orphaned
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics for Media Hub assets."""
        from apps.media_hub.models import Asset, AssetFile
        
        total_files = AssetFile.objects.count()
        total_size = AssetFile.objects.filter(
            file_size__isnull=False
        ).values_list('file_size', flat=True)
        
        by_type = {}
        for file_type in ['original', 'thumbnail', 'preview', 'optimized']:
            count = AssetFile.objects.filter(file_type=file_type).count()
            if count:
                by_type[file_type] = count
        
        return {
            'total_assets': Asset.objects.count(),
            'total_files': total_files,
            'total_size_bytes': sum(s for s in total_size if s),
            'by_file_type': by_type,
            'storage_path': str(self.base_path),
        }
