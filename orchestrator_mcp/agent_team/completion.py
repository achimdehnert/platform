"""
orchestrator_mcp/agent_team/completion.py

TaskCompletionChecker per ADR-108.
Checks whether all acceptance criteria for a task have been fulfilled.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AcceptanceCriterion:
    """A single acceptance criterion for a task."""

    description: str
    met: bool = False
    blocking: bool = True  # If True, task cannot be completed without this
    evidence: str = ""     # Proof that criterion was met


@dataclass
class CompletionResult:
    """Result of a TaskCompletionChecker run."""

    criteria: list[AcceptanceCriterion] = field(default_factory=list)
    score: float = field(init=False, default=0.0)
    is_complete: bool = field(init=False, default=False)
    blocking_open: list[str] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        self._compute()

    def _compute(self) -> None:
        if not self.criteria:
            self.score = 1.0
            self.is_complete = True
            return

        met_count = sum(1 for c in self.criteria if c.met)
        self.score = met_count / len(self.criteria)

        self.blocking_open = [
            c.description
            for c in self.criteria
            if c.blocking and not c.met
        ]
        self.is_complete = len(self.blocking_open) == 0


class TaskCompletionChecker:
    """
    Checks whether a task's acceptance criteria have been met.

    Usage:
        checker = TaskCompletionChecker()
        result = checker.check([
            AcceptanceCriterion("Tests green", met=True),
            AcceptanceCriterion("No ruff errors", met=True),
            AcceptanceCriterion("ADR-compliance", met=False, blocking=True),
        ])
        print(result.is_complete)  # False
        print(result.blocking_open)  # ["ADR-compliance"]
    """

    def check(
        self,
        criteria: list[AcceptanceCriterion],
    ) -> CompletionResult:
        return CompletionResult(criteria=criteria)

    def from_dict(
        self,
        criteria_dicts: list[dict],
    ) -> CompletionResult:
        """
        Convenience: build from list of dicts.
        Each dict: {"description": str, "met": bool, "blocking": bool, "evidence": str}
        """
        criteria = [
            AcceptanceCriterion(
                description=d["description"],
                met=d.get("met", False),
                blocking=d.get("blocking", True),
                evidence=d.get("evidence", ""),
            )
            for d in criteria_dicts
        ]
        return self.check(criteria)
