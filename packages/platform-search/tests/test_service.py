"""Tests for SearchService and Reciprocal Rank Fusion."""

import pytest

from platform_search.service import SearchResult, reciprocal_rank_fusion


class TestReciprocalRankFusion:
    """Tests for reciprocal_rank_fusion."""

    def test_should_merge_vector_and_text_results(self) -> None:
        vector = [
            SearchResult(
                chunk_id="1", source_type="ch",
                source_id="a", content="A", score=0.9,
            ),
            SearchResult(
                chunk_id="2", source_type="ch",
                source_id="a", content="B", score=0.8,
            ),
        ]
        text = [
            SearchResult(
                chunk_id="2", source_type="ch",
                source_id="a", content="B", score=5.0,
            ),
            SearchResult(
                chunk_id="3", source_type="ch",
                source_id="a", content="C", score=3.0,
            ),
        ]
        results = reciprocal_rank_fusion(vector, text)
        ids = [r.chunk_id for r in results]
        assert ids[0] == "2"
        assert len(results) == 3

    def test_should_handle_empty_inputs(self) -> None:
        results = reciprocal_rank_fusion([], [])
        assert results == []

    def test_should_respect_weights(self) -> None:
        vector = [
            SearchResult(
                chunk_id="1", source_type="ch",
                source_id="a", content="A", score=0.9,
            ),
        ]
        text = [
            SearchResult(
                chunk_id="2", source_type="ch",
                source_id="a", content="B", score=5.0,
            ),
        ]
        results = reciprocal_rank_fusion(
            vector, text, vector_weight=1.0, text_weight=0.0
        )
        assert results[0].chunk_id == "1"

    def test_should_produce_deterministic_scores(self) -> None:
        vector = [
            SearchResult(
                chunk_id="1", source_type="ch",
                source_id="a", content="A", score=0.9,
            ),
        ]
        r1 = reciprocal_rank_fusion(vector, [])
        r2 = reciprocal_rank_fusion(vector, [])
        assert r1[0].score == r2[0].score
