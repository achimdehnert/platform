"""
Core Search Service - Factory Functions

Factory functions for creating search engines.
"""

from typing import Optional

from .backends.faiss_backend import FAISSSearchEngine
from .base import BaseSearchEngine
from .exceptions import SearchBackendNotAvailable
from .models import SearchBackend, SearchConfig


def get_search_engine(
    backend: str = None,
    namespace: str = "default",
    model: str = None,
    config: SearchConfig = None,
    **kwargs,
) -> BaseSearchEngine:
    """
    Get a search engine instance

    Factory function that returns the appropriate search engine
    based on backend type.

    Args:
        backend: Backend type ("faiss", "postgres_vector", etc.)
        namespace: Index namespace for isolation
        model: Embedding model name
        config: Search configuration
        **kwargs: Additional backend-specific options

    Returns:
        Configured search engine instance

    Example:
        # Auto-detect from settings
        search = get_search_engine()

        # Specific backend
        search = get_search_engine(
            backend="faiss",
            namespace="writing_chapters",
            model="all-MiniLM-L6-v2"
        )

        # German-optimized
        search = get_search_engine(
            model="deutsche-telekom/gbert-large-paraphrase-cosine"
        )
    """
    # Try to get defaults from Django settings
    if backend is None or model is None:
        try:
            from django.conf import settings

            if backend is None:
                backend = getattr(settings, "SEARCH_BACKEND", "faiss")

            if model is None:
                model = getattr(settings, "SEARCH_EMBEDDING_MODEL", "all-MiniLM-L6-v2")

        except Exception:
            backend = backend or "faiss"
            model = model or "all-MiniLM-L6-v2"

    backend = (backend or "faiss").lower()

    if config is None:
        config = SearchConfig(backend=SearchBackend(backend), model=model)

    if backend == "faiss":
        return FAISSSearchEngine(
            namespace=namespace, config=config, embedding_model=model, **kwargs
        )
    elif backend == "postgres_vector":
        # Future implementation
        raise SearchBackendNotAvailable("postgres_vector", ["psycopg2-binary", "pgvector"])
    elif backend == "elasticsearch":
        # Future implementation
        raise SearchBackendNotAvailable("elasticsearch", ["elasticsearch"])
    else:
        # Default to FAISS
        return FAISSSearchEngine(
            namespace=namespace, config=config, embedding_model=model, **kwargs
        )


def get_async_search_engine(
    backend: str = None,
    namespace: str = "default",
    model: str = None,
    config: SearchConfig = None,
    **kwargs,
) -> BaseSearchEngine:
    """
    Get an async search engine instance

    Args:
        backend: Backend type
        namespace: Index namespace
        model: Embedding model
        config: Search configuration
        **kwargs: Additional options

    Returns:
        Async search engine instance
    """
    from .backends.async_faiss_backend import AsyncFAISSSearchEngine

    backend = (backend or "faiss").lower()

    if config is None:
        config = SearchConfig(backend=SearchBackend(backend), model=model or "all-MiniLM-L6-v2")

    if backend == "faiss":
        return AsyncFAISSSearchEngine(
            namespace=namespace, config=config, embedding_model=model, **kwargs
        )
    else:
        # Default to async FAISS
        return AsyncFAISSSearchEngine(
            namespace=namespace, config=config, embedding_model=model, **kwargs
        )


__all__ = ["get_search_engine", "get_async_search_engine"]
