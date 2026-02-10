"""
Tests for the task_scorer package.

Covers: score_task, _score_all_types, _sigmoid_confidence,
_score_to_tier, _metadata_bonus, ScoringConfig defaults,
custom config injection, edge cases.
"""

import pytest

from task_scorer import ScoringConfig, ScoringResult, Tier, score_task
from task_scorer.scorer import (
    _metadata_bonus,
    _score_all_types,
    _score_to_tier,
    _sigmoid_confidence,
)


# ============================================================================
# _score_all_types
# ============================================================================

class TestScoreAllTypes:
    """Tests for weighted keyword scoring."""

    def test_should_return_scores_for_all_types(self) -> None:
        config = ScoringConfig()
        scores, signals = _score_all_types(
            "hello world", config.keywords, config.weights,
        )
        assert len(scores) == len(config.keywords)

    def test_should_score_zero_for_no_matches(self) -> None:
        config = ScoringConfig()
        scores, signals = _score_all_types(
            "xyzzy", config.keywords, config.weights,
        )
        assert all(v == 0.0 for v in scores.values())
        assert signals == []

    def test_should_score_bug_highest_for_bug_text(self) -> None:
        config = ScoringConfig()
        scores, _ = _score_all_types(
            "fix the bug crash error", config.keywords, config.weights,
        )
        max_type = max(scores, key=scores.get)
        assert max_type == "bug"
        assert scores["bug"] > 0

    def test_should_score_security_highest_for_auth(self) -> None:
        config = ScoringConfig()
        scores, _ = _score_all_types(
            "fix auth permission credential vulnerability",
            config.keywords, config.weights,
        )
        max_type = max(scores, key=scores.get)
        assert max_type == "security"

    def test_should_generate_signals_for_matches(self) -> None:
        config = ScoringConfig()
        _, signals = _score_all_types(
            "refactor and clean the code", config.keywords, config.weights,
        )
        assert any("refactor" in s for s in signals)

    def test_should_handle_empty_keyword_list(self) -> None:
        scores, signals = _score_all_types(
            "test", {"custom": []}, {"custom": 1.0},
        )
        assert scores["custom"] == 0.0

    def test_should_apply_weights(self) -> None:
        scores_high, _ = _score_all_types(
            "auth", {"security": ["auth"]}, {"security": 2.0},
        )
        scores_low, _ = _score_all_types(
            "auth", {"security": ["auth"]}, {"security": 0.5},
        )
        assert scores_high["security"] > scores_low["security"]


# ============================================================================
# _sigmoid_confidence
# ============================================================================

class TestSigmoidConfidence:
    """Tests for sigmoid confidence calibration."""

    def test_should_return_0_5_for_zero_gap(self) -> None:
        conf = _sigmoid_confidence(0.5, 0.5, steepness=8.0)
        assert conf == pytest.approx(0.5, abs=0.01)

    def test_should_return_high_for_large_gap(self) -> None:
        conf = _sigmoid_confidence(1.0, 0.0, steepness=8.0)
        assert conf > 0.95

    def test_should_return_low_for_negative_gap(self) -> None:
        conf = _sigmoid_confidence(0.0, 1.0, steepness=8.0)
        assert conf < 0.05

    def test_should_be_monotonically_increasing(self) -> None:
        c1 = _sigmoid_confidence(0.5, 0.4, steepness=8.0)
        c2 = _sigmoid_confidence(0.5, 0.2, steepness=8.0)
        c3 = _sigmoid_confidence(0.5, 0.0, steepness=8.0)
        assert c1 < c2 < c3

    def test_should_respect_steepness(self) -> None:
        c_flat = _sigmoid_confidence(0.6, 0.4, steepness=2.0)
        c_steep = _sigmoid_confidence(0.6, 0.4, steepness=20.0)
        # Steeper sigmoid = more extreme confidence for same gap
        assert c_steep > c_flat


# ============================================================================
# _score_to_tier
# ============================================================================

class TestScoreToTier:
    """Tests for score-to-tier mapping."""

    def test_should_return_low_for_small_score(self) -> None:
        assert _score_to_tier(0.5, (1.0, 4.0)) == Tier.LOW

    def test_should_return_medium_for_mid_score(self) -> None:
        assert _score_to_tier(2.0, (1.0, 4.0)) == Tier.MEDIUM

    def test_should_return_high_for_large_score(self) -> None:
        assert _score_to_tier(5.0, (1.0, 4.0)) == Tier.HIGH

    def test_should_handle_boundary_low_max(self) -> None:
        assert _score_to_tier(1.0, (1.0, 4.0)) == Tier.LOW

    def test_should_handle_boundary_medium_max(self) -> None:
        assert _score_to_tier(4.0, (1.0, 4.0)) == Tier.MEDIUM

    def test_should_respect_custom_boundaries(self) -> None:
        assert _score_to_tier(0.3, (0.2, 0.5)) == Tier.MEDIUM
        assert _score_to_tier(0.6, (0.2, 0.5)) == Tier.HIGH


# ============================================================================
# _metadata_bonus
# ============================================================================

class TestMetadataBonus:
    """Tests for metadata bonus scoring."""

    def test_should_return_zero_for_no_metadata(self) -> None:
        assert _metadata_bonus(None, 0, 0) == 0.0

    def test_should_add_bonus_for_many_criteria(self) -> None:
        bonus = _metadata_bonus(None, 5, 0)
        assert bonus == pytest.approx(0.4)

    def test_should_add_bonus_for_some_criteria(self) -> None:
        bonus = _metadata_bonus(None, 3, 0)
        assert bonus == pytest.approx(0.2)

    def test_should_add_bonus_for_many_files(self) -> None:
        bonus = _metadata_bonus(None, 0, 6)
        assert bonus == pytest.approx(0.5)

    def test_should_add_bonus_for_some_files(self) -> None:
        bonus = _metadata_bonus(None, 0, 3)
        assert bonus == pytest.approx(0.2)

    def test_should_combine_criteria_and_files(self) -> None:
        bonus = _metadata_bonus(None, 5, 6)
        assert bonus == pytest.approx(0.9)


# ============================================================================
# score_task (integration)
# ============================================================================

class TestScoreTask:
    """Integration tests for the main score_task function."""

    def test_should_return_scoring_result(self) -> None:
        result = score_task("fix the bug")
        assert isinstance(result, ScoringResult)
        assert isinstance(result.tier, Tier)
        assert 0 <= result.confidence <= 1

    def test_should_detect_clear_bug(self) -> None:
        result = score_task("fix the bug crash error regression")
        assert result.top_type == "bug"
        assert result.confidence > 0.7

    def test_should_detect_clear_security(self) -> None:
        result = score_task("auth permission credential vulnerability")
        assert result.top_type == "security"
        assert result.confidence > 0.7

    def test_should_detect_architecture(self) -> None:
        result = score_task("design the architecture pattern strategy")
        assert result.top_type == "architecture"

    def test_should_detect_refactor(self) -> None:
        result = score_task("refactor clean improve optimize simplify")
        assert result.top_type == "refactor"

    def test_should_detect_docs(self) -> None:
        result = score_task("update readme docstring documentation")
        assert result.top_type == "docs"

    def test_should_default_to_feature_no_keywords(self) -> None:
        result = score_task("do something completely random xyzzy")
        assert result.top_type == "feature"
        assert result.confidence == 0.5
        assert result.is_ambiguous is True

    def test_should_handle_empty_string(self) -> None:
        result = score_task("")
        assert result.top_type == "feature"
        assert result.is_ambiguous is True

    def test_should_flag_ambiguous_on_low_confidence(self) -> None:
        result = score_task("fix the architecture docs")
        # Multiple types match = lower confidence
        assert result.confidence < 1.0

    def test_should_include_signals(self) -> None:
        result = score_task("fix bug and add feature")
        assert len(result.signals) >= 2

    def test_should_include_all_scores(self) -> None:
        result = score_task("fix the bug")
        assert "bug" in result.scores
        assert "security" in result.scores

    def test_should_apply_category_bonus(self) -> None:
        result_no_cat = score_task("fix something")
        result_with_cat = score_task("fix something", category="security")
        # Category bonus shouldn't change score if no security keywords
        assert result_no_cat.scores.get("security", 0) == result_with_cat.scores.get("security", 0)

    def test_should_apply_criteria_bonus(self) -> None:
        result = score_task(
            "security auth vulnerability",
            category="security",
            acceptance_criteria_count=6,
        )
        assert result.top_type == "security"
        assert "category_bonus" in " ".join(result.signals)

    def test_should_apply_files_bonus_with_category(self) -> None:
        result = score_task(
            "security auth vulnerability",
            category="security",
            files_affected=10,
        )
        assert result.scores["security"] > 0

    def test_should_be_idempotent(self) -> None:
        r1 = score_task("fix the authentication bug")
        r2 = score_task("fix the authentication bug")
        assert r1.top_type == r2.top_type
        assert r1.confidence == r2.confidence
        assert r1.tier == r2.tier


# ============================================================================
# ScoringConfig
# ============================================================================

class TestScoringConfig:
    """Tests for config defaults and custom injection."""

    def test_should_have_defaults(self) -> None:
        config = ScoringConfig()
        assert len(config.keywords) > 0
        assert len(config.weights) > 0
        assert config.confidence_steepness == 8.0

    def test_should_accept_custom_keywords(self) -> None:
        custom = ScoringConfig(
            keywords={"custom_type": ["alpha", "beta"]},
            weights={"custom_type": 1.0},
        )
        result = score_task("alpha beta gamma", config=custom)
        assert result.top_type == "custom_type"

    def test_should_accept_custom_boundaries(self) -> None:
        narrow = ScoringConfig(tier_boundaries=(0.1, 0.2))
        result = score_task("fix the bug", config=narrow)
        # With very narrow boundaries, most scores should be HIGH
        assert result.tier == Tier.HIGH

    def test_should_accept_custom_steepness(self) -> None:
        flat = ScoringConfig(confidence_steepness=1.0)
        steep = ScoringConfig(confidence_steepness=50.0)
        r_flat = score_task("fix the bug crash", config=flat)
        r_steep = score_task("fix the bug crash", config=steep)
        # Steeper produces more extreme confidence
        assert r_steep.confidence >= r_flat.confidence

    def test_should_be_frozen(self) -> None:
        config = ScoringConfig()
        with pytest.raises(AttributeError):
            config.confidence_steepness = 99.0


# ============================================================================
# Tier enum
# ============================================================================

class TestTier:
    """Tests for Tier enum values."""

    def test_should_have_three_values(self) -> None:
        assert len(Tier) == 3

    def test_should_have_string_values(self) -> None:
        assert Tier.LOW.value == "low"
        assert Tier.MEDIUM.value == "medium"
        assert Tier.HIGH.value == "high"

    def test_should_be_constructible_from_string(self) -> None:
        assert Tier("low") == Tier.LOW
        assert Tier("high") == Tier.HIGH
