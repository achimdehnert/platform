"""Tests for temporal decay scoring."""

from datetime import datetime, timedelta, timezone

import pytest

from platform_search.decay import apply_temporal_decay
from platform_search.service import SearchResult


class TestTemporalDecay:
    """Tests for apply_temporal_decay."""

    def test_should_boost_recent_results(self) -> None:
        now = datetime.now(tz=timezone.utc)
        results = [
            SearchResult(
                chunk_id="old", source_type="ch",
                source_id="a", content="Old", score=0.9,
            ),
            SearchResult(
                chunk_id="new", source_type="ch",
                source_id="a", content="New", score=0.9,
            ),
        ]
        timestamps = {
            "old": now - timedelta(days=365),
            "new": now - timedelta(days=1),
        }
        reranked = apply_temporal_decay(
            results, timestamps, decay_weight=0.5
        )
        assert reranked[0].chunk_id == "new"

    def test_should_handle_missing_timestamps(self) -> None:
        results = [
            SearchResult(
                chunk_id="1", source_type="ch",
                source_id="a", content="A", score=0.9,
            ),
        ]
        reranked = apply_temporal_decay(results, {})
        assert len(reranked) == 1
        assert reranked[0].score == 0.9

    def test_should_handle_empty_results(self) -> None:
        reranked = apply_temporal_decay([], {})
        assert reranked == []
