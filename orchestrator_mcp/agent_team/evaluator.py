"""
orchestrator_mcp/agent_team/evaluator.py

Quality Evaluator per ADR-108 §3.2.

Evaluates a completed agent task against quality metrics:
  completion_score  : fraction of acceptance criteria fulfilled (weight 40%)
  guardian_passed   : Ruff/Bandit/MyPy all green (weight 20%)
  coverage_delta    : test coverage did not decrease (weight 10%)
  adr_compliance    : no ADR violations detected (weight 20%)
  iteration_count   : number of retries <= 2 (weight 10%)

composite_score < 0.70 triggers L1-Rollback.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RollbackLevel(int, Enum):
    """
    ADR-108 §3.3 Rollback-Eskalation.
    L0 = no rollback needed.
    L1 = Re-Engineer auto (Gate 0).
    L2 = Tech Lead Review (Gate 2).
    L3 = User notification (Gate 3).
    L4 = Task abort (Gate 4).
    """
    NONE = 0
    L1_RE_ENGINEER = 1
    L2_TECH_LEAD = 2
    L3_USER_NOTIFY = 3
    L4_ABORT = 4


@dataclass
class QualityScore:
    """
    Full quality snapshot for a completed agent task.
    All fields public; no private mutation after construction.
    """
    task_id: str
    task_type: str
    agent_role: str
    model_tier: str

    completion_score: float = 0.0      # 0.0 – 1.0 (AC fulfilled / AC total)
    guardian_passed: bool = False
    coverage_delta: float = 0.0        # positive = improved, negative = regressed
    adr_compliance: bool = True
    iteration_count: int = 1

    tokens_used: int = 0
    tokens_budget: int = 0

    details: dict[str, object] = field(default_factory=dict)

    # Computed after construction
    composite_score: float = field(init=False, default=0.0)
    rollback_level: RollbackLevel = field(init=False, default=RollbackLevel.NONE)
    passed: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        self.composite_score = self._compute_composite()
        self.rollback_level = self._determine_rollback()
        self.passed = self.rollback_level == RollbackLevel.NONE

    # Weight constants per ADR-108 Table
    _W_COMPLETION: float = 0.40
    _W_GUARDIAN: float = 0.20
    _W_COVERAGE: float = 0.10
    _W_ADR: float = 0.20
    _W_ITERATIONS: float = 0.10
    _COMPOSITE_THRESHOLD: float = 0.70

    def _compute_composite(self) -> float:
        guardian_val = 1.0 if self.guardian_passed else 0.0
        coverage_val = 1.0 if self.coverage_delta >= 0 else 0.0
        adr_val = 1.0 if self.adr_compliance else 0.0
        iter_val = 1.0 if self.iteration_count <= 2 else max(0.0, 1.0 - (self.iteration_count - 2) * 0.25)
        return round(
            self.completion_score * self._W_COMPLETION
            + guardian_val * self._W_GUARDIAN
            + coverage_val * self._W_COVERAGE
            + adr_val * self._W_ADR
            + iter_val * self._W_ITERATIONS,
            4,
        )

    def _determine_rollback(self) -> RollbackLevel:
        if not self.adr_compliance:
            return RollbackLevel.L2_TECH_LEAD
        if self.iteration_count > 4:
            return RollbackLevel.L2_TECH_LEAD
        budget = self.tokens_budget
        if budget > 0 and self.tokens_used > budget * 1.2:
            return RollbackLevel.L2_TECH_LEAD
        if not self.guardian_passed:
            return RollbackLevel.L1_RE_ENGINEER
        if self.completion_score < 1.0:
            return RollbackLevel.L1_RE_ENGINEER
        if self.composite_score < self._COMPOSITE_THRESHOLD:
            return RollbackLevel.L1_RE_ENGINEER
        return RollbackLevel.NONE

    def summary(self) -> str:
        status = "PASS" if self.passed else f"ROLLBACK-L{self.rollback_level.value}"
        return (
            f"[{status}] {self.task_id} ({self.agent_role}/{self.model_tier}) "
            f"composite={self.composite_score:.2f} "
            f"completion={self.completion_score:.2f} "
            f"guardian={'OK' if self.guardian_passed else 'FAIL'} "
            f"adr={'OK' if self.adr_compliance else 'FAIL'} "
            f"iters={self.iteration_count} "
            f"tokens={self.tokens_used}/{self.tokens_budget or '?'}"
        )


class QualityEvaluator:
    """
    Evaluates agent task output and returns a QualityScore.

    Usage:
        evaluator = QualityEvaluator()
        score = evaluator.evaluate(
            task_id="t-001",
            task_type="feature",
            agent_role="developer",
            model_tier="standard_coding",
            completion_score=0.9,
            guardian_passed=True,
            coverage_delta=0.02,
            adr_compliance=True,
            iteration_count=1,
            tokens_used=45_000,
        )
        if not score.passed:
            trigger_rollback(score.rollback_level)
    """

    # Token budgets per ADR-108 Table 3.4
    TOKEN_BUDGETS: dict[str, int] = {
        "trivial": 5_000,
        "simple": 20_000,
        "moderate": 80_000,
        "complex": 200_000,
        "architectural": 500_000,
    }
    TOKEN_HARD_LIMITS: dict[str, int] = {
        "trivial": 10_000,
        "simple": 40_000,
        "moderate": 150_000,
        "complex": 400_000,
        "architectural": 1_000_000,
    }

    def evaluate(
        self,
        task_id: str,
        task_type: str,
        agent_role: str,
        model_tier: str,
        completion_score: float,
        guardian_passed: bool,
        coverage_delta: float = 0.0,
        adr_compliance: bool = True,
        iteration_count: int = 1,
        tokens_used: int = 0,
        details: dict[str, object] | None = None,
    ) -> QualityScore:
        complexity = task_type  # task_type maps to complexity bucket
        budget = self.TOKEN_BUDGETS.get(complexity, self.TOKEN_BUDGETS["moderate"])
        hard_limit = self.TOKEN_HARD_LIMITS.get(complexity, self.TOKEN_HARD_LIMITS["moderate"])

        if tokens_used > hard_limit:
            logger.error(
                "Task %s exceeded hard token limit: %d > %d",
                task_id, tokens_used, hard_limit,
            )

        score = QualityScore(
            task_id=task_id,
            task_type=task_type,
            agent_role=agent_role,
            model_tier=model_tier,
            completion_score=completion_score,
            guardian_passed=guardian_passed,
            coverage_delta=coverage_delta,
            adr_compliance=adr_compliance,
            iteration_count=iteration_count,
            tokens_used=tokens_used,
            tokens_budget=budget,
            details=details or {},
        )

        logger.info("QualityEvaluator: %s", score.summary())
        return score
