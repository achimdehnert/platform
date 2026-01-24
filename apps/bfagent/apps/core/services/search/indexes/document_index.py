"""
Core Search Service - Document Search Index

Specialized index for documents with chunking support.
"""

from typing import Any, Dict, List

from ..base import SearchIndex
from ..chunking import DocumentChunker
from ..models import IndexItem, SearchConfig


class DocumentSearchIndex(SearchIndex):
    """Search index for documents with chunking"""

    def __init__(
        self,
        namespace: str = "documents",
        search_engine=None,
        config: SearchConfig = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        chunking_strategy: str = "semantic",
    ):
        super().__init__(namespace, search_engine, config)

        self.chunker = DocumentChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            strategy=chunking_strategy,
        )

    def add_document(
        self,
        id: str,
        title: str,
        content: str,
        metadata: Dict[str, Any] = None,
        use_chunking: bool = True,
    ) -> None:
        """
        Add document to index

        Args:
            id: Document ID
            title: Document title
            content: Document content
            metadata: Document metadata
            use_chunking: Whether to chunk the document
        """
        meta = metadata or {}

        if not use_chunking or len(content.split()) < self.chunker.chunk_size:
            # Add as single item
            self.add_item(
                id=id,
                title=title,
                description="",
                content=content,
                metadata=meta,
            )
        else:
            # Chunk and add each chunk
            chunks = self.chunker.chunk_text(content, metadata=meta)

            for chunk in chunks:
                chunk_id = f"{id}_chunk_{chunk.idx}"
                chunk_meta = {
                    **meta,
                    "parent_id": id,
                    "chunk_idx": chunk.idx,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                }

                self.add_item(
                    id=chunk_id,
                    title=title,
                    description=f"Chunk {chunk.idx + 1}",
                    content=chunk.text,
                    metadata=chunk_meta,
                )

    def build_corpus(self) -> List[IndexItem]:
        """Build corpus from indexed documents"""
        return self._items


__all__ = ["DocumentSearchIndex"]
