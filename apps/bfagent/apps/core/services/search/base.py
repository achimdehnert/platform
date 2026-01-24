"""
Core Search Service - Base Classes

Abstract base classes for search engines and indexes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import IndexItem, SearchConfig, SearchRequest, SearchResult


class BaseSearchEngine(ABC):
    """Base class for all search backends"""

    def __init__(self, config: SearchConfig = None):
        self.config = config or SearchConfig()
        self._is_built = False

    @abstractmethod
    def add_item(self, id: str, text: str, metadata: Dict[str, Any] = None) -> None:
        """Add single item to index"""
        pass

    @abstractmethod
    def add_items(self, items: List[IndexItem]) -> None:
        """Add multiple items to index"""
        pass

    @abstractmethod
    def search(
        self, query: str, top_k: int = 10, filters: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """Search for items"""
        pass

    @abstractmethod
    def build_index(self) -> bool:
        """Build/rebuild search index"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if backend dependencies are available"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all indexed items"""
        pass

    def is_built(self) -> bool:
        """Check if index is built"""
        return self._is_built


class SearchIndex(ABC):
    """Base class for specialized search indexes"""

    def __init__(
        self,
        namespace: str,
        search_engine: BaseSearchEngine = None,
        config: SearchConfig = None,
    ):
        self.namespace = namespace
        self.config = config or SearchConfig()
        self.search_engine = search_engine
        self._items: List[IndexItem] = []

        # Namespace-specific paths
        cache_dir = Path(self.config.cache_dir or Path.home() / ".bfagent" / "search")
        self.index_dir = cache_dir / namespace
        self.index_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def build_corpus(self) -> List[IndexItem]:
        """Build corpus for this index type"""
        pass

    def add_item(
        self,
        id: str,
        title: str = "",
        description: str = "",
        content: str = "",
        metadata: Dict[str, Any] = None,
    ) -> None:
        """Add item to index"""
        text = self._build_search_text(title, description, content)

        item = IndexItem(
            id=id,
            text=text,
            title=title,
            description=description,
            metadata=metadata or {},
        )

        self._items.append(item)

    def add_items(self, items: List[Dict[str, Any]]) -> None:
        """Add multiple items"""
        for item_data in items:
            self.add_item(**item_data)

    def build(self) -> bool:
        """Build search index"""
        if not self.search_engine:
            raise ValueError("Search engine not set")

        # Clear existing
        self.search_engine.clear()

        # Add items
        self.search_engine.add_items(self._items)

        # Build index
        return self.search_engine.build_index()

    def search(
        self, query: str, top_k: int = 10, filters: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """Search this index"""
        if not self.search_engine:
            raise ValueError("Search engine not set")

        return self.search_engine.search(query, top_k, filters)

    def clear(self) -> None:
        """Clear all items"""
        self._items.clear()
        if self.search_engine:
            self.search_engine.clear()

    def _build_search_text(self, title: str, description: str, content: str) -> str:
        """Build combined search text"""
        parts = []
        if title:
            parts.append(f"Title: {title}")
        if description:
            parts.append(f"Description: {description}")
        if content:
            parts.append(content)

        return " ".join(parts)


__all__ = ["BaseSearchEngine", "SearchIndex"]
