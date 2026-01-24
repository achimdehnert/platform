"""
Context Enrichment Service Package

Database-driven context enrichment for processing handlers.
"""

from .exceptions import (
    EnrichmentError,
    SchemaNotFoundError,
    SourceResolutionError,
    ValidationError,
)

__all__ = [
    'EnrichmentError',
    'SchemaNotFoundError',
    'SourceResolutionError',
    'ValidationError',
]
