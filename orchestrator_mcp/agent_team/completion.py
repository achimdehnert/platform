"""
orchestrator_mcp/agent_team/completion.py

TaskCompletionChecker per ADR-108 §3.1 Phase 1 (Completion Check).

Verifies that all acceptance criteria for a task have been fulfilled.
completion_score = fulfilled_count / total_count

Usage:
    checker = TaskCompletionChecker()
    result = checker.check(
        task_id="t-001",
        criteria=[
            AcceptanceCriterion(id="ac-1", description="Tests pass", fulfilled=True),
            AcceptanceCriterion(id="ac-2", description="Migration exists", fulfilled=False),
        ]
    )
    print(result.completion_score)  # 0.5
    print(result.open_criteria)     # ["ac-2: Migration exists"]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AcceptanceCriterion:
    id: str
    description: str
    fulfilled: bool = False
    evidence: str = ""        # e.g. test name, file path, PR link
    blocking: bool = True     # non-blocking criteria count but don’t reduce score to 0


@dataclass
class CompletionResult:
    task_id: str
    total: int
    fulfilled: int
    open_criteria: list[str] = field(default_factory=list)
    blocking_open: list[str] = field(default_factory=list)

    @property
    def completion_score(self) -> float:
        if self.total == 0:
            return 1.0
        return round(self.fulfilled / self.total, 4)

    @property
    def blocking_complete(self) -> bool:
        return len(self.blocking_open) == 0

    def summary(self) -> str:
        return (
            f"Task {self.task_id}: {self.fulfilled}/{self.total} AC fulfilled "
            f"(score={self.completion_score:.2f}) "
            f"{'COMPLETE' if self.blocking_complete else 'INCOMPLETE'}"
        )


class TaskCompletionChecker:
    """
    Checks task acceptance criteria and returns a CompletionResult.

    Blocking criteria that are open trigger L1-Rollback via QualityEvaluator.
    Non-blocking open criteria generate warnings only.
    """

    def check(
        self,
        task_id: str,
        criteria: list[AcceptanceCriterion],
    ) -> CompletionResult:
        if not criteria:
            logger.warning("Task %s has no acceptance criteria defined.", task_id)
            return CompletionResult(task_id=task_id, total=0, fulfilled=0)

        fulfilled = sum(1 for c in criteria if c.fulfilled)
        open_all = [f"{c.id}: {c.description}" for c in criteria if not c.fulfilled]
        open_blocking = [
            f"{c.id}: {c.description}" for c in criteria if not c.fulfilled and c.blocking
        ]

        result = CompletionResult(
            task_id=task_id,
            total=len(criteria),
            fulfilled=fulfilled,
            open_criteria=open_all,
            blocking_open=open_blocking,
        )

        logger.info("TaskCompletionChecker: %s", result.summary())
        if open_blocking:
            logger.warning(
                "Task %s has %d blocking open criteria: %s",
                task_id,
                len(open_blocking),
                open_blocking,
            )
        return result
