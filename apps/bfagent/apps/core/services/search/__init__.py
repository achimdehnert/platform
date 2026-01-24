"""
Core Search Service - Unified Semantic Search

Production-ready semantic search service for BF Agent apps.

Quick Start:
    from apps.core.services.search import get_search_engine

    # Create search engine
    search = get_search_engine(namespace="my_tools")

    # Add items
    search.add_item(
        id="parser_1",
        text="DWG/DXF Parser: Parse AutoCAD files and extract geometry",
        metadata={"category": "input", "version": "1.0.0"}
    )

    # Build index
    search.build_index()

    # Search
    results = search.search("parse DXF files", top_k=5)

    for result in results:
        print(f"{result.id}: {result.title} (score: {result.score:.2f})")

Features:
    - FAISS-based semantic search
    - Multi-index support (namespace isolation)
    - Document chunking for long texts
    - Advanced metadata filtering
    - Async operations support
    - Caching with hash-based invalidation
    - German language support

Architecture:
    - BaseSearchEngine: Abstract base for all backends
    - FAISSSearchEngine: FAISS implementation
    - AsyncFAISSSearchEngine: Async wrapper
    - ToolSearchIndex: Specialized for tools/handlers
    - DocumentSearchIndex: Specialized for documents with chunking
"""

# ==================== Backends ====================
from .backends import FAISSSearchEngine

# ==================== Base Classes ====================
from .base import BaseSearchEngine, SearchIndex

# ==================== Factory ====================
from .factory import get_async_search_engine, get_search_engine

try:
    from .backends import AsyncFAISSSearchEngine

    _has_async = True
except ImportError:
    _has_async = False

# ==================== Utilities ====================
from .chunking import DocumentChunker

# ==================== Exceptions ====================
from .exceptions import (
    InvalidSearchQuery,
    NamespaceNotFound,
    SearchBackendNotAvailable,
    SearchException,
    SearchIndexCorrupted,
    SearchIndexNotBuilt,
)
from .filtering import FilterBuilder, MetadataFilter

# ==================== Specialized Indexes ====================
from .indexes import DocumentSearchIndex, ToolSearchIndex

# ==================== Models ====================
from .models import (
    Chunk,
    EmbeddingModel,
    IndexItem,
    SearchAnalytics,
    SearchBackend,
    SearchConfig,
    SearchRequest,
    SearchResponse,
    SearchResult,
)

# ==================== Public API ====================

__all__ = [
    # Factory
    "get_search_engine",
    "get_async_search_engine",
    # Base Classes
    "BaseSearchEngine",
    "SearchIndex",
    # Backends
    "FAISSSearchEngine",
    # Indexes
    "ToolSearchIndex",
    "DocumentSearchIndex",
    # Models
    "SearchBackend",
    "EmbeddingModel",
    "SearchConfig",
    "SearchResult",
    "SearchRequest",
    "SearchResponse",
    "IndexItem",
    "Chunk",
    "SearchAnalytics",
    # Utilities
    "DocumentChunker",
    "MetadataFilter",
    "FilterBuilder",
    # Exceptions
    "SearchException",
    "SearchBackendNotAvailable",
    "SearchIndexNotBuilt",
    "SearchIndexCorrupted",
    "InvalidSearchQuery",
    "NamespaceNotFound",
]

# Add async support if available
if _has_async:
    __all__.append("AsyncFAISSSearchEngine")

__version__ = "1.0.0"


# ==================== Convenience Functions ====================


def is_available() -> bool:
    """
    Check if semantic search dependencies are available

    Returns:
        True if FAISS and Sentence Transformers are installed
    """
    try:
        import faiss
        from sentence_transformers import SentenceTransformer

        return True
    except ImportError:
        return False


def get_backends() -> list:
    """
    Get list of available backends

    Returns:
        List of backend names
    """
    backends = ["faiss"]
    return backends


__all__.extend(["is_available", "get_backends"])
