"""
orchestrator_mcp/agent_team/planner.py

Task planner per ADR-107 §4.5 Aufgaben-Routing-Entscheidungsbaum.

Classifies incoming tasks and builds structured TaskPlans
with branch/sub-task decomposition and role assignments.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from orchestrator_mcp.agent_team.roles import AgentRole, GateLevel, route_task

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Task Classification
# ---------------------------------------------------------------------------

_COMPLEXITY_GATE: dict[str, int] = {
    "trivial": 0,
    "simple": 0,
    "moderate": 1,
    "complex": 1,
    "architectural": 3,
}

_TECH_LEAD_TYPES = {"adr", "architecture", "concept"}
_DEPLOYMENT_TYPES = {"deployment", "infra"}


def classify_task(
    task_type: str,
    complexity: str = "moderate",
) -> dict[str, object]:
    """
    Returns classification dict used by agent_plan_task and analyze_task.

    Keys:
        primary_role        : AgentRole value string
        gate_level          : int (0-3)
        needs_tech_lead_plan: bool
        auto_eligible       : bool
        rationale           : str
    """
    try:
        role = route_task(task_type, complexity)
    except ValueError:
        role = AgentRole.DEVELOPER

    base_gate = _COMPLEXITY_GATE.get(complexity, 1)

    if role == AgentRole.TECH_LEAD:
        gate = GateLevel.THREE.value
    elif role == AgentRole.DEPLOYMENT:
        gate = GateLevel.TWO.value
    elif role == AgentRole.RE_ENGINEER:
        gate = GateLevel.TWO.value
    elif role == AgentRole.GUARDIAN:
        gate = GateLevel.ZERO.value
    elif role == AgentRole.TESTER:
        gate = GateLevel.ZERO.value
    elif role == AgentRole.REVIEW:
        gate = GateLevel.ONE.value
    else:
        gate = max(base_gate, GateLevel.ONE.value)

    needs_tech_lead_plan = (
        task_type in _TECH_LEAD_TYPES
        or complexity in {"complex", "architectural"}
    )
    auto_eligible = gate <= GateLevel.ONE.value

    rationale = _build_rationale(task_type, complexity, role, gate)

    return {
        "primary_role": role.value,
        "gate_level": gate,
        "needs_tech_lead_plan": needs_tech_lead_plan,
        "auto_eligible": auto_eligible,
        "rationale": rationale,
    }


def _build_rationale(
    task_type: str, complexity: str, role: AgentRole, gate: int
) -> str:
    if role == AgentRole.TECH_LEAD:
        return (
            f"Task type '{task_type}' is an architectural concern — "
            "Cascade (Tech Lead) owns this directly."
        )
    if role == AgentRole.DEPLOYMENT:
        return (
            f"Deployment task at complexity '{complexity}' — "
            "Deployment Agent executes via cd.yml. "
            "Gate-2 required for breaking schema changes."
        )
    if complexity in {"complex", "architectural"} and role == AgentRole.DEVELOPER:
        return (
            f"High-complexity '{task_type}': Cascade plans, Developer Agent executes. "
            "Gate-1 execution after Tech Lead approval."
        )
    return (
        f"Task type '{task_type}' at complexity '{complexity}' — "
        f"{role.value} at Gate-{gate}."
    )


# ---------------------------------------------------------------------------
# Task Plan
# ---------------------------------------------------------------------------


@dataclass
class TaskBranch:
    name: str
    role: str
    gate_level: int
    steps: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)


@dataclass
class TaskPlan:
    description: str
    primary_role: str
    gate_level: int
    branches: list[dict[str, object]] = field(default_factory=list)
    estimated_steps: int = 0


def build_task_plan(
    description: str,
    classification: dict[str, object],
) -> TaskPlan:
    """
    Builds a structured TaskPlan from a description + classification.
    Produces concrete branches for each phase of work.
    """
    role = classification["primary_role"]
    gate = classification["gate_level"]
    needs_plan = classification["needs_tech_lead_plan"]

    branches: list[TaskBranch] = []

    if needs_plan:
        branches.append(
            TaskBranch(
                name="planning",
                role=AgentRole.TECH_LEAD.value,
                gate_level=GateLevel.THREE.value,
                steps=[
                    "Review requirements and constraints",
                    "Write implementation plan / ADR if needed",
                    "Define acceptance criteria",
                    "Assign sub-tasks to Developer/Tester agents",
                ],
            )
        )

    if role == AgentRole.DEPLOYMENT.value:
        branches.append(
            TaskBranch(
                name="breaking_change_check",
                role=AgentRole.DEPLOYMENT.value,
                gate_level=GateLevel.TWO.value,
                steps=[
                    "Run breaking_change_detector.analyse_all_pending_migrations()",
                    "If auto_eligible=False: trigger Gate-2-Approval",
                    "If auto_eligible=True: proceed to deployment",
                ],
                depends_on=[],
            )
        )
        branches.append(
            TaskBranch(
                name="deployment",
                role=AgentRole.DEPLOYMENT.value,
                gate_level=GateLevel.TWO.value,
                steps=[
                    "Step 0: Save current image tag (save_tag)",
                    "Step 1: Pull new image from GHCR",
                    "Step 2: Apply migrations (timeout 300s)",
                    "Step 4: Recreate container (--no-deps --force-recreate)",
                    "Step 5: Health check (3 retries)",
                    "Step 6: Rollback on failure (Tier 1/2/3)",
                    "Step 7: Write DeploymentLog AuditStore entry",
                ],
                depends_on=["breaking_change_check"],
            )
        )
    elif role == AgentRole.REVIEW.value:
        branches.append(
            TaskBranch(
                name="review",
                role=AgentRole.REVIEW.value,
                gate_level=GateLevel.ONE.value,
                steps=[
                    "Run Ruff + Bandit (blocking)",
                    "Run mcp12_check_violations for ADR compliance (blocking)",
                    "Check platform patterns: no inline CSS, no cursor.execute (blocking)",
                    "Check test coverage delta (warning)",
                    "Check RunPython without reverse (warning)",
                    "Post PR comment with structured report",
                    "Write ReviewLog AuditStore entry",
                ],
                depends_on=[],
            )
        )
    else:
        branches.append(
            TaskBranch(
                name="implementation",
                role=str(role),
                gate_level=int(str(gate)),
                steps=[
                    "Implement changes per acceptance criteria",
                    "Write / update tests",
                    "Run CI locally (ruff, pytest)",
                    "Open PR for Review Agent",
                ],
                depends_on=["planning"] if needs_plan else [],
            )
        )

    if role not in (AgentRole.TESTER.value, AgentRole.GUARDIAN.value):
        branches.append(
            TaskBranch(
                name="verification",
                role=AgentRole.TESTER.value,
                gate_level=GateLevel.ZERO.value,
                steps=[
                    "Run full test suite",
                    "Verify coverage delta >= 0",
                    "Report results",
                ],
                depends_on=["implementation"] if "implementation" in [b.name for b in branches] else [],
            )
        )

    all_steps = sum(len(b.steps) for b in branches)

    return TaskPlan(
        description=description,
        primary_role=str(role),
        gate_level=int(str(gate)),
        branches=[
            {
                "name": b.name,
                "role": b.role,
                "gate_level": b.gate_level,
                "steps": b.steps,
                "depends_on": b.depends_on,
            }
            for b in branches
        ],
        estimated_steps=all_steps,
    )
