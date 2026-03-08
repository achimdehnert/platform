"""
orchestrator_mcp/agent_team/evaluator.py

QualityEvaluator + QualityScore per ADR-108.
Computes composite quality score and determines rollback level.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RollbackLevel(str, Enum):
    NONE = "none"        # Score >= 0.85
    SOFT = "soft"        # Score 0.70–0.84 — retry with feedback
    HARD = "hard"        # Score 0.50–0.69 — revert to last known good
    ESCALATE = "escalate"  # Score < 0.50  — human intervention required


# Token budgets per task complexity
TOKEN_BUDGETS: dict[str, int] = {
    "trivial": 10_000,
    "simple": 25_000,
    "moderate": 60_000,
    "complex": 120_000,
    "architectural": 200_000,
}

# Hard limits (never exceed regardless of complexity)
TOKEN_HARD_LIMIT = 250_000
ITERATION_HARD_LIMIT = 10


@dataclass
class QualityScore:
    """Composite quality score for a completed agent task."""

    # Sub-scores (0.0 – 1.0 each)
    completion_score: float = 0.0       # TaskCompletionChecker result
    guardian_score: float = 0.0         # Guardian agent sign-off (0 or 1)
    adr_compliance_score: float = 0.0   # platform-context check result
    iteration_score: float = 1.0        # Penalised per extra iteration
    token_score: float = 1.0            # Penalised per % over budget

    # Raw metrics
    iterations_used: int = 0
    tokens_used: int = 0
    token_budget: int = 60_000
    complexity: str = "moderate"

    # Derived
    composite: float = field(init=False, default=0.0)
    rollback_level: RollbackLevel = field(init=False, default=RollbackLevel.NONE)

    # Weights
    _WEIGHTS: dict[str, float] = field(init=False, default_factory=lambda: {
        "completion": 0.35,
        "guardian": 0.25,
        "adr_compliance": 0.20,
        "iteration": 0.10,
        "token": 0.10,
    })

    def __post_init__(self) -> None:
        self._compute()

    def _compute(self) -> None:
        w = self._WEIGHTS
        self.composite = (
            self.completion_score * w["completion"]
            + self.guardian_score * w["guardian"]
            + self.adr_compliance_score * w["adr_compliance"]
            + self.iteration_score * w["iteration"]
            + self.token_score * w["token"]
        )
        self.rollback_level = self._determine_rollback()

    def _determine_rollback(self) -> RollbackLevel:
        if self.composite >= 0.85:
            return RollbackLevel.NONE
        if self.composite >= 0.70:
            return RollbackLevel.SOFT
        if self.composite >= 0.50:
            return RollbackLevel.HARD
        return RollbackLevel.ESCALATE


class QualityEvaluator:
    """
    Evaluates a completed agent task and produces a QualityScore.

    Usage:
        evaluator = QualityEvaluator()
        score = evaluator.evaluate(
            completion_score=0.9,
            guardian_passed=True,
            adr_violations=0,
            iterations_used=3,
            tokens_used=45_000,
            complexity="moderate",
        )
    """

    def evaluate(
        self,
        completion_score: float,
        guardian_passed: bool,
        adr_violations: int,
        iterations_used: int,
        tokens_used: int,
        complexity: str = "moderate",
    ) -> QualityScore:
        token_budget = TOKEN_BUDGETS.get(complexity, TOKEN_BUDGETS["moderate"])

        iteration_score = self._iteration_score(iterations_used, complexity)
        token_score = self._token_score(tokens_used, token_budget)
        adr_score = self._adr_score(adr_violations)

        return QualityScore(
            completion_score=max(0.0, min(1.0, completion_score)),
            guardian_score=1.0 if guardian_passed else 0.0,
            adr_compliance_score=adr_score,
            iteration_score=iteration_score,
            token_score=token_score,
            iterations_used=iterations_used,
            tokens_used=tokens_used,
            token_budget=token_budget,
            complexity=complexity,
        )

    @staticmethod
    def _iteration_score(iterations: int, complexity: str) -> float:
        """Penalise for iterations above the expected maximum."""
        max_iterations: dict[str, int] = {
            "trivial": 2, "simple": 3, "moderate": 5,
            "complex": 7, "architectural": 9,
        }
        expected = max_iterations.get(complexity, 5)
        if iterations <= expected:
            return 1.0
        over = iterations - expected
        return max(0.0, 1.0 - (over * 0.15))

    @staticmethod
    def _token_score(used: int, budget: int) -> float:
        """Penalise for token usage over budget."""
        if used <= budget:
            return 1.0
        over_pct = (used - budget) / budget
        return max(0.0, 1.0 - over_pct)

    @staticmethod
    def _adr_score(violations: int) -> float:
        """Score based on ADR violations found by platform-context check."""
        if violations == 0:
            return 1.0
        if violations == 1:
            return 0.7
        if violations <= 3:
            return 0.4
        return 0.0
