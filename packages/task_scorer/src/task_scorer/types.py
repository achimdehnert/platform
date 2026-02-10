"""
Type definitions for task_scorer.

All public types used by the scoring engine. Uses stdlib-only
dataclasses (no Pydantic) to maintain zero-dependency constraint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Tier(Enum):
    """Complexity tier for a scored task."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ScoringConfig:
    """Configuration for the scoring engine.

    All fields have sensible defaults. Override individual fields
    to customize scoring behavior (e.g. inject DB-driven keywords).

    Attributes:
        keywords: Mapping of task_type -> list of keywords.
            Each keyword is matched as a substring in the description.
        weights: Mapping of task_type -> weight multiplier.
            Higher weight = stronger signal when keywords match.
        tier_boundaries: (low_max, medium_max) score thresholds.
            score <= low_max -> LOW, score <= medium_max -> MEDIUM, else HIGH.
        confidence_steepness: Sigmoid steepness for confidence calibration.
            Higher = sharper transition between confident/uncertain.
        confidence_threshold: Below this confidence, result is flagged
            as ambiguous (result.is_ambiguous = True).
    """

    keywords: dict[str, list[str]] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)
    tier_boundaries: tuple[float, float] = (1.0, 4.0)
    confidence_steepness: float = 8.0
    confidence_threshold: float = 0.65

    def __post_init__(self) -> None:
        """Apply defaults for missing keywords/weights."""
        if not self.keywords:
            # frozen=True requires object.__setattr__
            object.__setattr__(self, "keywords", DEFAULT_KEYWORDS.copy())
        if not self.weights:
            object.__setattr__(self, "weights", DEFAULT_WEIGHTS.copy())


@dataclass(frozen=True)
class ScoringResult:
    """Result of scoring a task description.

    Attributes:
        scores: All type scores: {"security": 1.5, "bug": 0.3, ...}.
        top_type: Highest scoring type (e.g. "security").
        tier: Mapped complexity tier (LOW/MEDIUM/HIGH).
        confidence: Sigmoid confidence [0.0, 1.0] based on score gap.
        signals: Debug signals showing which keywords matched.
        is_ambiguous: True if confidence < threshold.
        raw_score: The winning type's raw weighted score.
    """

    scores: dict[str, float]
    top_type: str
    tier: Tier
    confidence: float
    signals: list[str]
    is_ambiguous: bool
    raw_score: float


# ============================================================================
# DEFAULT CONFIGURATION
# Unified keyword set from BFAgent + Orchestrator + ClawRouter analysis.
# See ADR-023 Appendix A for divergence analysis.
# ============================================================================

DEFAULT_KEYWORDS: dict[str, list[str]] = {
    "architecture": [
        "architecture", "architektur", "design", "adr", "strategy",
        "integration", "pattern", "diagram",
    ],
    "security": [
        "security", "auth", "authentication", "authorization",
        "permission", "credential", "secret", "vulnerability", "cve",
    ],
    "breaking_change": [
        "breaking", "migrate", "migration", "deprecate", "remove",
        "drop support", "incompatible",
    ],
    "feature": [
        "feature", "add", "implement", "create", "new",
        "build", "introduce",
    ],
    "bug": [
        "bug", "fix", "issue", "error", "broken",
        "crash", "regression", "fails",
    ],
    "refactor": [
        "refactor", "clean", "improve", "optimize", "optimization",
        "simplify", "extract", "reorganize", "caching", "performance",
    ],
    "test": [
        "test", "spec", "coverage", "pytest", "assert",
        "mock", "fixture", "integration",
    ],
    "docs": [
        "doc", "readme", "comment", "docstring", "documentation",
        "sphinx", "changelog",
    ],
    "lint": [
        "lint", "format", "formatting", "style", "ruff", "flake8",
    ],
    "typo": [
        "typo", "spelling", "minor", "whitespace", "css",
        "label", "text", "button", "spacing", "icon",
    ],
}

DEFAULT_WEIGHTS: dict[str, float] = {
    "architecture": 1.5,
    "security": 1.5,
    "breaking_change": 1.4,
    "feature": 1.0,
    "bug": 1.0,
    "refactor": 0.9,
    "test": 0.8,
    "docs": 0.7,
    "lint": 0.6,
    "typo": 0.5,
}
