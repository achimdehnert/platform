"""Specialized search indexes"""

from .document_index import DocumentSearchIndex
from .tool_index import ToolSearchIndex

__all__ = ["ToolSearchIndex", "DocumentSearchIndex"]
