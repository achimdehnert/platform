"""Tests for MMR diversity filter."""

import pytest

from platform_search.mmr import maximal_marginal_relevance
from platform_search.service import SearchResult


class TestMMR:
    """Tests for maximal_marginal_relevance."""

    def test_should_return_top_k_results(self) -> None:
        results = [
            SearchResult(
                chunk_id=str(i), source_type="ch",
                source_id="a", content=f"Doc {i}", score=0.9 - i * 0.1,
            )
            for i in range(5)
        ]
        query_emb = [1.0, 0.0, 0.0]
        doc_embs = [
            [1.0, 0.0, 0.0],
            [0.9, 0.1, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.5, 0.5, 0.0],
        ]
        reranked = maximal_marginal_relevance(
            query_emb, doc_embs, results, top_k=3
        )
        assert len(reranked) == 3

    def test_should_handle_empty_results(self) -> None:
        reranked = maximal_marginal_relevance(
            [1.0, 0.0], [], [], top_k=5
        )
        assert reranked == []

    def test_should_promote_diversity(self) -> None:
        results = [
            SearchResult(
                chunk_id="1", source_type="ch",
                source_id="a", content="Similar A", score=0.9,
            ),
            SearchResult(
                chunk_id="2", source_type="ch",
                source_id="a", content="Similar B", score=0.85,
            ),
            SearchResult(
                chunk_id="3", source_type="ch",
                source_id="a", content="Different", score=0.7,
            ),
        ]
        query_emb = [1.0, 0.0]
        doc_embs = [
            [0.99, 0.01],
            [0.98, 0.02],
            [0.1, 0.9],
        ]
        reranked = maximal_marginal_relevance(
            query_emb, doc_embs, results,
            lambda_param=0.3, top_k=3,
        )
        assert reranked[1].chunk_id == "3"
