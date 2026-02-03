"""
Storage backends for PPTX-Hub.

Provides abstraction over different storage backends (local, S3, etc.)
"""

from pptx_hub.core.storage.base import StorageBackend
from pptx_hub.core.storage.local import LocalStorage

__all__ = [
    "StorageBackend",
    "LocalStorage",
]

# Optional S3 import
try:
    from pptx_hub.core.storage.s3 import S3Storage
    __all__.append("S3Storage")
except ImportError:
    pass
