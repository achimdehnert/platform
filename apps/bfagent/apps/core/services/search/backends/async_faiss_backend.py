"""
Core Search Service - Async FAISS Backend

Async wrapper for FAISS search engine using ThreadPoolExecutor.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

from ..models import IndexItem, SearchConfig, SearchResult
from .faiss_backend import FAISSSearchEngine


class AsyncFAISSSearchEngine(FAISSSearchEngine):
    """Async FAISS search engine"""

    def __init__(
        self,
        namespace: str = "default",
        config: SearchConfig = None,
        embedding_model: str = None,
        max_workers: int = 4,
    ):
        super().__init__(namespace, config, embedding_model)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def search_async(
        self, query: str, top_k: int = 10, filters: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """Async search"""
        loop = asyncio.get_event_loop()

        results = await loop.run_in_executor(
            self.executor, self._search_sync, query, top_k, filters
        )

        return results

    def _search_sync(
        self, query: str, top_k: int, filters: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """Internal sync search"""
        return self.search(query, top_k, filters)

    async def batch_search_async(
        self, queries: List[str], top_k: int = 10, filters: Dict[str, Any] = None
    ) -> List[List[SearchResult]]:
        """Batch search multiple queries"""
        tasks = [self.search_async(query, top_k, filters) for query in queries]

        return await asyncio.gather(*tasks)

    async def add_items_async(self, items: List[IndexItem]) -> None:
        """Async bulk add"""
        loop = asyncio.get_event_loop()

        await loop.run_in_executor(self.executor, self._add_items_sync, items)

    def _add_items_sync(self, items: List[IndexItem]) -> None:
        """Internal sync add"""
        self.add_items(items)

    async def build_index_async(self) -> bool:
        """Async index building"""
        loop = asyncio.get_event_loop()

        result = await loop.run_in_executor(self.executor, self.build_index)

        return result

    def __del__(self):
        """Cleanup executor on deletion"""
        if hasattr(self, "executor"):
            self.executor.shutdown(wait=False)


__all__ = ["AsyncFAISSSearchEngine"]
