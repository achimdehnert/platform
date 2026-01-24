"""Search backends"""

from .faiss_backend import FAISSSearchEngine

try:
    from .async_faiss_backend import AsyncFAISSSearchEngine

    __all__ = ["FAISSSearchEngine", "AsyncFAISSSearchEngine"]
except ImportError:
    __all__ = ["FAISSSearchEngine"]
