"""Temporal decay scoring for search results (ADR-087).

Boosts recent results via exponential decay.
Reference: OpenClaw src/memory/temporal-decay.ts
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from platform_search.service import SearchResult


def apply_temporal_decay(
    results: list[SearchResult],
    timestamps: dict[str, datetime],
    half_life_days: float = 90.0,
    decay_weight: float = 0.1,
) -> list[SearchResult]:
    """Boost recent results via exponential decay.

    decay = exp(-ln(2) * age_days / half_life)
    final_score = (1 - decay_weight) * score + decay_weight * decay

    Args:
        results: Search results to re-score.
        timestamps: Mapping of chunk_id to creation/update datetime.
        half_life_days: Half-life for decay in days.
        decay_weight: Weight of temporal decay in final score.

    Returns:
        Re-scored and re-sorted results.
    """
    now = datetime.now(tz=timezone.utc)
    decay_constant = math.log(2) / half_life_days

    scored: list[tuple[float, SearchResult]] = []
    for result in results:
        ts = timestamps.get(result.chunk_id)
        if ts is None:
            scored.append((result.score, result))
            continue

        age_days = (now - ts).total_seconds() / 86400.0
        decay = math.exp(-decay_constant * age_days)
        final_score = (
            (1 - decay_weight) * result.score + decay_weight * decay
        )

        scored.append((
            final_score,
            SearchResult(
                chunk_id=result.chunk_id,
                source_type=result.source_type,
                source_id=result.source_id,
                content=result.content,
                score=final_score,
                vector_rank=result.vector_rank,
                text_rank=result.text_rank,
            ),
        ))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored]
