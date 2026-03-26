"""iil-dvelop-client — Python client for the d.velop DMS REST API."""

from dvelop_client.client import DvelopClient
from dvelop_client.exceptions import (
    DvelopAuthError,
    DvelopError,
    DvelopNotFoundError,
    DvelopRateLimitError,
)
from dvelop_client.models import BlobRef, Category, DmsObject, Repository

__all__ = [
    "DvelopClient",
    "DvelopError",
    "DvelopAuthError",
    "DvelopNotFoundError",
    "DvelopRateLimitError",
    "Repository",
    "DmsObject",
    "BlobRef",
    "Category",
]

__version__ = "0.1.0"
