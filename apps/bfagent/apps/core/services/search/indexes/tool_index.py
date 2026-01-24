"""
Core Search Service - Tool Search Index

Specialized index for tools/handlers discovery.
"""

from typing import Any, Dict, List

from ..base import SearchIndex
from ..models import IndexItem, SearchConfig


class ToolSearchIndex(SearchIndex):
    """Search index for tools and handlers"""

    def __init__(self, namespace: str = "tools", search_engine=None, config: SearchConfig = None):
        super().__init__(namespace, search_engine, config)

    def add_tool(
        self,
        code: str,
        title: str,
        description: str,
        category: str,
        version: str = "1.0.0",
        requires_external: List[str] = None,
        is_experimental: bool = False,
        **metadata,
    ) -> None:
        """
        Add tool to index

        Args:
            code: Unique tool code
            title: Tool title
            description: Tool description
            category: Tool category
            version: Tool version
            requires_external: External dependencies
            is_experimental: Experimental flag
            **metadata: Additional metadata
        """
        meta = {
            "category": category,
            "version": version,
            "requires_external": requires_external or [],
            "is_experimental": is_experimental,
            **metadata,
        }

        self.add_item(
            id=code,
            title=title,
            description=description,
            content=f"{title}: {description} Category: {category}",
            metadata=meta,
        )

    def build_corpus(self) -> List[IndexItem]:
        """Build corpus from registered tools"""
        return self._items


__all__ = ["ToolSearchIndex"]
