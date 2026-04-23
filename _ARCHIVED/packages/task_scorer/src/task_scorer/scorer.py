"""
Core scoring engine for task complexity estimation.

Implements weighted multi-dimension keyword scoring with sigmoid
confidence calibration. Inspired by ClawRouter's 14-dimension
scoring approach, adapted for server-side Python use.

This module is the single entry point for scoring. It has zero
external dependencies (stdlib math only).
"""

from __future__ import annotations

import math

from .types import ScoringConfig, ScoringResult, Tier


def score_task(
    description: str,
    config: ScoringConfig | None = None,
    category: str | None = None,
    acceptance_criteria_count: int = 0,
    files_affected: int = 0,
) -> ScoringResult:
    """Score a task description and return complexity assessment.

    This is the main public API. It scores the description against
    all configured task types using weighted keyword matching, then
    maps the result to a complexity tier with confidence.

    Args:
        description: Task description text to score.
        config: Optional custom scoring config. Uses defaults if None.
        category: Optional task category (e.g. 'security', 'refactor').
            Adds bonus score if it matches a task type.
        acceptance_criteria_count: Number of acceptance criteria.
            More criteria = higher complexity signal.
        files_affected: Number of files likely affected.
            More files = higher complexity signal.

    Returns:
        ScoringResult with scores, tier, confidence, and signals.
    """
    if config is None:
        config = ScoringConfig()

    scores, signals = _score_all_types(
        description=description,
        keywords=config.keywords,
        weights=config.weights,
    )

    # Bonus signals from structured metadata
    bonus = _metadata_bonus(
        category=category,
        acceptance_criteria_count=acceptance_criteria_count,
        files_affected=files_affected,
    )

    # Apply metadata bonus to matching task type
    if category and category in scores:
        scores[category] += bonus
        if bonus > 0:
            signals.append(f"category_bonus({category}={bonus:.1f})")

    # Find winner and runner-up
    sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    winner_type, winner_score = sorted_types[0]
    runner_up_score = sorted_types[1][1] if len(sorted_types) > 1 else 0.0

    # Handle no-match case
    if winner_score == 0.0:
        return ScoringResult(
            scores=scores,
            top_type="feature",
            tier=Tier.LOW,
            confidence=0.5,
            signals=["no keywords matched"],
            is_ambiguous=True,
            raw_score=0.0,
        )

    # Compute confidence via sigmoid on score gap
    confidence = _sigmoid_confidence(
        winner_score=winner_score,
        runner_up_score=runner_up_score,
        steepness=config.confidence_steepness,
    )

    # Map raw score to tier
    tier = _score_to_tier(winner_score, config.tier_boundaries)

    # Check ambiguity
    is_ambiguous = confidence < config.confidence_threshold

    return ScoringResult(
        scores=scores,
        top_type=winner_type,
        tier=tier,
        confidence=round(confidence, 4),
        signals=signals,
        is_ambiguous=is_ambiguous,
        raw_score=round(winner_score, 4),
    )


def _score_all_types(
    description: str,
    keywords: dict[str, list[str]],
    weights: dict[str, float],
) -> tuple[dict[str, float], list[str]]:
    """Score description against all task types.

    For each task type, computes:
        hit_ratio = matched_keywords / total_keywords
        weighted_score = hit_ratio * type_weight

    Returns (scores_dict, signals_list).
    """
    desc_lower = description.lower()
    scores: dict[str, float] = {}
    signals: list[str] = []

    for task_type, kw_list in keywords.items():
        if not kw_list:
            scores[task_type] = 0.0
            continue

        matches = [kw for kw in kw_list if kw in desc_lower]

        if not matches:
            scores[task_type] = 0.0
            continue

        hit_ratio = len(matches) / len(kw_list)
        type_weight = weights.get(task_type, 1.0)
        score = hit_ratio * type_weight

        scores[task_type] = round(score, 4)
        signals.append(f"{task_type}({', '.join(matches[:3])})")

    return scores, signals


def _sigmoid_confidence(
    winner_score: float,
    runner_up_score: float,
    steepness: float,
) -> float:
    """Compute confidence via sigmoid on score gap.

    Maps the gap between winner and runner-up through a sigmoid
    function to produce a value in (0, 1). A large gap = high
    confidence; small gap = low confidence (~0.5).

    Args:
        winner_score: Score of the winning task type.
        runner_up_score: Score of the second-place task type.
        steepness: Sigmoid curve steepness (default 8.0).

    Returns:
        Confidence value in (0.0, 1.0).
    """
    gap = winner_score - runner_up_score
    return 1.0 / (1.0 + math.exp(-steepness * gap))


def _score_to_tier(
    score: float,
    boundaries: tuple[float, float],
) -> Tier:
    """Map a raw weighted score to a complexity tier.

    Args:
        score: The winning type's weighted score.
        boundaries: (low_max, medium_max) thresholds.

    Returns:
        Tier.LOW, Tier.MEDIUM, or Tier.HIGH.
    """
    low_max, medium_max = boundaries

    if score <= low_max:
        return Tier.LOW
    if score <= medium_max:
        return Tier.MEDIUM
    return Tier.HIGH


def _metadata_bonus(
    category: str | None,
    acceptance_criteria_count: int,
    files_affected: int,
) -> float:
    """Compute bonus score from structured task metadata.

    Mirrors the heuristic signals from BFAgent's TestRequirement
    and LLMRouter that use category, criteria count, and file
    count as scoring dimensions beyond keyword matching.

    Returns a bonus value to add to the matching task type score.
    """
    bonus = 0.0

    if acceptance_criteria_count >= 5:
        bonus += 0.4
    elif acceptance_criteria_count >= 2:
        bonus += 0.2

    if files_affected > 5:
        bonus += 0.5
    elif files_affected > 2:
        bonus += 0.2

    return bonus
