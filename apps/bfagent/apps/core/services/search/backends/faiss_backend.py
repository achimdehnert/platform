"""
Core Search Service - FAISS Backend

FAISS-based semantic search with caching and multi-index support.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import BaseSearchEngine
from ..exceptions import SearchBackendNotAvailable, SearchIndexNotBuilt
from ..filtering import MetadataFilter
from ..models import IndexItem, SearchConfig, SearchResult

log = logging.getLogger(__name__)


class FAISSSearchEngine(BaseSearchEngine):
    """FAISS-based semantic search engine"""

    def __init__(
        self,
        namespace: str = "default",
        config: SearchConfig = None,
        embedding_model: str = None,
    ):
        super().__init__(config)

        self.namespace = namespace
        self.embedding_model = embedding_model or self.config.model

        # Storage paths
        cache_dir = Path(self.config.cache_dir or Path.home() / ".bfagent" / "search")
        self.index_dir = cache_dir / namespace
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self.index_file = self.index_dir / "index.faiss"
        self.meta_file = self.index_dir / "index.meta.json"

        # Runtime state
        self.faiss_index: Optional[Any] = None
        self.sentence_model: Optional[Any] = None
        self.items: List[IndexItem] = []
        self.dimension: Optional[int] = None

    def is_available(self) -> bool:
        """Check if FAISS and Sentence Transformers are available"""
        try:
            import faiss
            from sentence_transformers import SentenceTransformer

            return True
        except ImportError:
            return False

    def add_item(self, id: str, text: str, metadata: Dict[str, Any] = None) -> None:
        """Add single item to index"""
        item = IndexItem(
            id=id,
            text=text,
            title=metadata.get("title", "") if metadata else "",
            description=metadata.get("description", "") if metadata else "",
            metadata=metadata or {},
        )
        self.items.append(item)

    def add_items(self, items: List[IndexItem]) -> None:
        """Add multiple items"""
        self.items.extend(items)

    def build_index(self) -> bool:
        """Build FAISS index from items"""
        if not self.is_available():
            raise SearchBackendNotAvailable("faiss", ["sentence-transformers", "faiss-cpu"])

        if not self.items:
            log.warning("No items to index")
            return False

        log.info(f"Building FAISS index for namespace '{self.namespace}'...")
        log.info(f"  Items: {len(self.items)}")
        log.info(f"  Model: {self.embedding_model}")

        try:
            # Initialize model
            self._initialize_model()

            # Check cache
            current_hash = self._compute_catalog_hash()
            if self._load_cached_index(current_hash):
                log.info("✅ Loaded from cache")
                self._is_built = True
                return True

            # Build new index
            self._build_new_index(current_hash)
            self._is_built = True

            log.info(f"✅ Index built: {len(self.items)} items")
            return True

        except Exception as e:
            log.error(f"Failed to build index: {e}")
            return False

    def search(
        self, query: str, top_k: int = 10, filters: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """Search for similar items"""
        if not self._is_built:
            raise SearchIndexNotBuilt(self.namespace)

        if not query or not query.strip():
            return []

        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)

            # Search FAISS
            import numpy as np

            faiss_lib = self._import_faiss()
            faiss_lib.normalize_L2(query_embedding.reshape(1, -1))

            distances, indices = self.faiss_index.search(
                query_embedding.reshape(1, -1).astype("float32"), min(top_k * 2, len(self.items))
            )

            # Convert to results
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1 or idx >= len(self.items):
                    continue

                item = self.items[idx]

                # Apply filters
                if filters:
                    filter_obj = self._build_filter(filters)
                    if not filter_obj.matches(item.metadata):
                        continue

                # Convert distance to similarity score (cosine)
                score = float(1.0 - dist)

                # Skip low scores
                if score < self.config.min_score:
                    continue

                results.append(
                    SearchResult(
                        id=item.id,
                        score=score,
                        title=item.title,
                        description=item.description,
                        content=item.text,
                        metadata=item.metadata,
                    )
                )

                if len(results) >= top_k:
                    break

            # Apply relative threshold
            if results and len(results) > 1:
                top_score = results[0].score
                threshold = top_score * self.config.relative_threshold
                results = [r for r in results if r.score >= threshold]

            return results

        except Exception as e:
            log.error(f"Search failed: {e}")
            return []

    def clear(self) -> None:
        """Clear all items"""
        self.items.clear()
        self.faiss_index = None
        self._is_built = False

    def _initialize_model(self) -> None:
        """Initialize sentence transformer model"""
        if self.sentence_model is not None:
            return

        from sentence_transformers import SentenceTransformer

        log.info(f"  Loading model: {self.embedding_model}")
        self.sentence_model = SentenceTransformer(
            self.embedding_model,
            cache_folder=str(self.index_dir.parent / ".models"),
        )

        # Auto-detect dimension
        if self.dimension is None:
            test_embedding = self.sentence_model.encode("test", convert_to_numpy=True)
            self.dimension = len(test_embedding)
            log.info(f"  Dimension: {self.dimension}")

    def _generate_embedding(self, text: str):
        """Generate embedding for text"""
        import numpy as np

        if self.sentence_model is None:
            self._initialize_model()

        return self.sentence_model.encode(text, convert_to_numpy=True, show_progress_bar=False)

    def _compute_catalog_hash(self) -> str:
        """Compute hash of catalog for cache invalidation"""
        catalog_data = {
            "model": self.embedding_model,
            "items": [{"id": item.id, "text": item.text} for item in self.items],
        }
        serialized = json.dumps(catalog_data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def _load_cached_index(self, expected_hash: str) -> bool:
        """Try to load cached index"""
        if not (self.meta_file.exists() and self.index_file.exists()):
            return False

        try:
            # Load metadata
            with open(self.meta_file, "r") as f:
                metadata = json.load(f)

            # Validate
            if (
                metadata.get("catalog_hash") == expected_hash
                and metadata.get("model") == self.embedding_model
            ):
                faiss_lib = self._import_faiss()
                self.faiss_index = faiss_lib.read_index(str(self.index_file))
                self.dimension = metadata.get("dimension")
                log.info(f"  Loaded cached index: {self.faiss_index.ntotal} vectors")
                return True

        except Exception as e:
            log.warning(f"  Cache invalid: {e}")

        return False

    def _build_new_index(self, catalog_hash: str) -> None:
        """Build new FAISS index"""
        import numpy as np

        faiss_lib = self._import_faiss()

        # Generate embeddings
        log.info("  Generating embeddings...")
        texts = [item.text for item in self.items]
        embeddings = self.sentence_model.encode(
            texts, show_progress_bar=True, convert_to_numpy=True
        )
        embeddings = np.array(embeddings).astype("float32")

        # Normalize for cosine similarity
        faiss_lib.normalize_L2(embeddings)

        # Build index
        log.info(f"  Building index (dimension: {embeddings.shape[1]})...")
        self.dimension = embeddings.shape[1]
        self.faiss_index = faiss_lib.IndexFlatIP(self.dimension)
        self.faiss_index.add(embeddings)

        # Save to disk
        faiss_lib.write_index(self.faiss_index, str(self.index_file))

        # Save metadata
        metadata = {
            "catalog_hash": catalog_hash,
            "model": self.embedding_model,
            "dimension": self.dimension,
            "item_count": len(self.items),
        }
        with open(self.meta_file, "w") as f:
            json.dump(metadata, f, indent=2)

        log.info(f"  Saved to: {self.index_file}")

    def _import_faiss(self):
        """Import FAISS library"""
        try:
            import faiss

            return faiss
        except ImportError:
            raise SearchBackendNotAvailable("faiss", ["faiss-cpu"])

    def _build_filter(self, filters: Dict[str, Any]) -> MetadataFilter:
        """Build MetadataFilter from dict"""
        filter_obj = MetadataFilter()
        for key, value in filters.items():
            if isinstance(value, dict):
                # Complex filter: {"operator": "eq", "value": "something"}
                op = value.get("operator", "eq")
                val = value.get("value")
                filter_obj.add_filter(key, op, val)
            else:
                # Simple equality filter
                filter_obj.add_filter(key, "eq", value)
        return filter_obj


__all__ = ["FAISSSearchEngine"]
