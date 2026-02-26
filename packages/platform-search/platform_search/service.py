"""Hybrid search service (ADR-087).

Combines pgvector vector search with PostgreSQL full-text search,
merged via Reciprocal Rank Fusion (RRF).
"""

import json
import logging
from dataclasses import dataclass

from django.db import connections

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResult:
    """A single search result from hybrid search."""

    chunk_id: str
    source_type: str
    source_id: str
    content: str
    score: float
    vector_rank: int | None = None
    text_rank: int | None = None


class SearchService:
    """Platform-wide hybrid search service.

    All methods are sync — safe for Django views and Celery tasks.
    Uses content_store DB connection (ADR-062).
    """

    DB_ALIAS = "content_store"

    @classmethod
    def search(
        cls,
        query: str,
        tenant_id: str,
        source_types: list[str] | None = None,
        top_k: int = 10,
        vector_weight: float = 0.6,
        text_weight: float = 0.4,
    ) -> list[SearchResult]:
        """Sync hybrid search — safe for Django views."""
        vector_results = cls._vector_search(
            query, tenant_id, source_types, top_k
        )
        text_results = cls._text_search(
            query, tenant_id, source_types, top_k
        )
        return reciprocal_rank_fusion(
            vector_results,
            text_results,
            vector_weight=vector_weight,
            text_weight=text_weight,
        )

    @classmethod
    def _vector_search(
        cls,
        query: str,
        tenant_id: str,
        source_types: list[str] | None,
        top_k: int,
    ) -> list[SearchResult]:
        """Embed query and find nearest neighbors via pgvector."""
        try:
            from platform_search.embeddings import embed_texts

            query_embedding = embed_texts([query])[0]
        except Exception:
            logger.warning(
                "Embedding API unavailable, skipping vector search",
                exc_info=True,
            )
            return []

        params: list = [str(query_embedding), tenant_id]
        source_filter = ""
        if source_types:
            source_filter = "AND source_type = ANY(%s) "
            params.append(source_types)
        params.append(top_k)

        sql = (
            "SELECT id, source_type, source_id, content, "
            "embedding <=> %s::vector AS distance "
            "FROM search_chunks WHERE tenant_id = %s "
            + source_filter
            + "ORDER BY distance LIMIT %s"
        )

        try:
            with connections[cls.DB_ALIAS].cursor() as cursor:
                cursor.execute(sql, params)
                return [
                    SearchResult(
                        chunk_id=str(row[0]),
                        source_type=row[1],
                        source_id=str(row[2]),
                        content=row[3],
                        score=1.0 - row[4],
                    )
                    for row in cursor.fetchall()
                ]
        except Exception:
            logger.warning(
                "Vector search failed, returning empty results",
                exc_info=True,
            )
            return []

    @classmethod
    def _text_search(
        cls,
        query: str,
        tenant_id: str,
        source_types: list[str] | None,
        top_k: int,
    ) -> list[SearchResult]:
        """Full-text search via PostgreSQL tsvector."""
        params: list = [query, tenant_id, query]
        source_filter = ""
        if source_types:
            source_filter = "AND source_type = ANY(%s) "
            params.append(source_types)
        params.append(top_k)

        sql = (
            "SELECT id, source_type, source_id, content, "
            "ts_rank(search_vector, plainto_tsquery('german', %s)) AS rank "
            "FROM search_chunks WHERE tenant_id = %s "
            "AND search_vector @@ plainto_tsquery('german', %s) "
            + source_filter
            + "ORDER BY rank DESC LIMIT %s"
        )

        try:
            with connections[cls.DB_ALIAS].cursor() as cursor:
                cursor.execute(sql, params)
                return [
                    SearchResult(
                        chunk_id=str(row[0]),
                        source_type=row[1],
                        source_id=str(row[2]),
                        content=row[3],
                        score=row[4],
                    )
                    for row in cursor.fetchall()
                ]
        except Exception:
            logger.warning(
                "Text search failed, returning empty results",
                exc_info=True,
            )
            return []

    @classmethod
    def index_chunks(
        cls,
        tenant_id: str,
        source_type: str,
        source_id: str,
        chunks: list[str],
        metadata: dict | None = None,
    ) -> int:
        """Index text chunks for search.

        Deletes existing chunks for the source, then inserts new ones
        with embeddings.

        Returns:
            Number of chunks indexed.
        """
        from platform_search.embeddings import embed_texts

        if not chunks:
            return 0

        embeddings = embed_texts(chunks)
        meta_json = json.dumps(metadata or {})

        with connections[cls.DB_ALIAS].cursor() as cursor:
            cursor.execute(
                "DELETE FROM search_chunks "
                "WHERE tenant_id = %s AND source_type = %s "
                "AND source_id = %s",
                [tenant_id, source_type, source_id],
            )
            for i, (chunk, embedding) in enumerate(
                zip(chunks, embeddings, strict=True)
            ):
                cursor.execute(
                    "INSERT INTO search_chunks "
                    "(tenant_id, source_type, source_id, chunk_index, "
                    "content, embedding, metadata) "
                    "VALUES (%s, %s, %s, %s, %s, %s::vector, %s::jsonb)",
                    [
                        tenant_id,
                        source_type,
                        source_id,
                        i,
                        chunk,
                        str(embedding),
                        meta_json,
                    ],
                )

        return len(chunks)

    @classmethod
    def delete_chunks(
        cls,
        tenant_id: str,
        source_type: str,
        source_id: str,
    ) -> int:
        """Delete all chunks for a source."""
        with connections[cls.DB_ALIAS].cursor() as cursor:
            cursor.execute(
                "DELETE FROM search_chunks "
                "WHERE tenant_id = %s AND source_type = %s "
                "AND source_id = %s",
                [tenant_id, source_type, source_id],
            )
            return cursor.rowcount

    @classmethod
    def health_check(cls) -> dict[str, bool | str]:
        """Check pgvector availability for /healthz/ endpoint."""
        try:
            with connections[cls.DB_ALIAS].cursor() as cursor:
                cursor.execute(
                    "SELECT extversion FROM pg_extension "
                    "WHERE extname = 'vector'"
                )
                row = cursor.fetchone()
                if row:
                    return {"healthy": True, "pgvector_version": row[0]}
                return {
                    "healthy": False,
                    "error": "pgvector extension not installed",
                }
        except Exception as exc:
            return {"healthy": False, "error": str(exc)}


def reciprocal_rank_fusion(
    vector_results: list[SearchResult],
    text_results: list[SearchResult],
    vector_weight: float = 0.6,
    text_weight: float = 0.4,
    k: int = 60,
) -> list[SearchResult]:
    """Merge vector + text results via Reciprocal Rank Fusion.

    Score = vector_weight * 1/(k + rank) + text_weight * 1/(k + rank)

    Reference: Cormack et al. (2009), OpenClaw src/memory/hybrid.ts
    """
    scores: dict[str, float] = {}
    results_map: dict[str, SearchResult] = {}

    for rank, result in enumerate(vector_results, 1):
        scores[result.chunk_id] = scores.get(result.chunk_id, 0.0)
        scores[result.chunk_id] += vector_weight * (1.0 / (k + rank))
        results_map[result.chunk_id] = result

    for rank, result in enumerate(text_results, 1):
        scores[result.chunk_id] = scores.get(result.chunk_id, 0.0)
        scores[result.chunk_id] += text_weight * (1.0 / (k + rank))
        results_map[result.chunk_id] = result

    sorted_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    return [
        SearchResult(
            chunk_id=cid,
            source_type=results_map[cid].source_type,
            source_id=results_map[cid].source_id,
            content=results_map[cid].content,
            score=scores[cid],
        )
        for cid in sorted_ids
    ]
