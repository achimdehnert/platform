"""
orchestrator_mcp/tools.py

MCP Tool implementations for the Orchestrator.

Phase 4 (ADR-107): agent_team_status and agent_plan_task updated
to include Deployment Agent, Review Agent, and role routing.

Tools exposed via orchestrator_mcp MCP server:
  - agent_team_status   : current agent team configuration + active roles
  - agent_plan_task     : decompose task into sub-tasks and assign to roles
  - analyze_task        : classify task and recommend model/gate
  - check_gate          : verify action is allowed at current gate level
  - deploy_check        : deployment health check for known repos
  - get_cost_estimate   : token cost estimate per model
  - log_action          : audit log entry
  - get_audit_log       : retrieve audit log entries
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from orchestrator_mcp.agent_team.planner import (
    TaskPlan,
    build_task_plan,
    classify_task,
)
from orchestrator_mcp.agent_team.roles import (
    ROLE_REGISTRY,
    AgentRole,
    GateLevel,
    get_role,
    route_task,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# agent_team_status
# ---------------------------------------------------------------------------


def agent_team_status() -> dict[str, Any]:
    """
    Returns the current agent team configuration per ADR-107.

    Includes all 7 roles with gate levels, descriptions, and
    which tasks are auto-eligible vs. require human approval.
    """
    roles_info = []
    for role, config in ROLE_REGISTRY.items():
        roles_info.append(
            {
                "role": role.value,
                "gate_level": config.gate_level.value,
                "auto_execute": config.can_auto_execute(),
                "description": config.description,
            }
        )

    deployment_cfg = get_role(AgentRole.DEPLOYMENT)
    review_cfg = get_role(AgentRole.REVIEW)

    return {
        "schema_version": "2.0",
        "adr_reference": "ADR-107",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "roles": roles_info,
        "active_agents": len(roles_info),
        "deployment_agent": {
            "role": AgentRole.DEPLOYMENT.value,
            "gate_level": deployment_cfg.gate_level.value,
            "auto_execute": deployment_cfg.can_auto_execute(),
            "allowed_tools": deployment_cfg.allowed_tools,
            "requires_gate2_for": deployment_cfg.requires_gate2_approval_for,
            "health_check_endpoint": deployment_cfg.health_check_endpoint,
        },
        "review_agent": {
            "role": AgentRole.REVIEW.value,
            "gate_level": review_cfg.gate_level.value,
            "auto_execute": review_cfg.can_auto_execute(),
            "allowed_tools": review_cfg.allowed_tools,
            "check_pipeline": [
                {
                    "name": c["name"],
                    "blocking": c["blocking"],
                    "gate": c["gate"].value,
                }
                for c in review_cfg.check_pipeline
            ],
            "override_label": review_cfg.override_label,
        },
        "gate_levels": {
            "0": "Fully automated — no approval needed",
            "1": "Agent decision — human informed",
            "2": "Human approval required",
            "3": "Tech Lead (Cascade) direct involvement",
        },
        "task_routing": _get_routing_summary(),
    }


def _get_routing_summary() -> list[dict[str, str]]:
    return [
        {"task_type": "adr", "routes_to": AgentRole.TECH_LEAD.value, "gate": "3"},
        {"task_type": "architecture", "routes_to": AgentRole.TECH_LEAD.value, "gate": "3"},
        {"task_type": "concept", "routes_to": AgentRole.TECH_LEAD.value, "gate": "3"},
        {"task_type": "feature", "routes_to": AgentRole.DEVELOPER.value, "gate": "1"},
        {"task_type": "bugfix", "routes_to": AgentRole.DEVELOPER.value, "gate": "1"},
        {"task_type": "test", "routes_to": AgentRole.TESTER.value, "gate": "0"},
        {"task_type": "deployment", "routes_to": AgentRole.DEPLOYMENT.value, "gate": "2"},
        {"task_type": "pr_review", "routes_to": AgentRole.REVIEW.value, "gate": "1"},
        {"task_type": "refactor", "routes_to": AgentRole.RE_ENGINEER.value, "gate": "2"},
        {"task_type": "tech_debt", "routes_to": AgentRole.RE_ENGINEER.value, "gate": "2"},
    ]


# ---------------------------------------------------------------------------
# agent_plan_task
# ---------------------------------------------------------------------------


def agent_plan_task(
    description: str,
    task_type: str = "feature",
    complexity: str = "moderate",
) -> dict[str, Any]:
    """
    Decomposes a task description into a TaskGraph with role assignments.

    Args:
        description: Task description in natural language.
        task_type:   One of feature, bugfix, refactor, test, docs, infra,
                     deployment, pr_review, adr, architecture.
        complexity:  One of trivial, simple, moderate, complex, architectural.

    Returns:
        TaskGraph dict with branches, sub-tasks, assigned roles, and gate levels.
    """
    classification = classify_task(task_type, complexity)
    plan = build_task_plan(description, classification)

    return {
        "task_type": task_type,
        "complexity": complexity,
        "assigned_role": classification["primary_role"],
        "gate_level": classification["gate_level"],
        "needs_tech_lead_plan": classification["needs_tech_lead_plan"],
        "auto_eligible": classification["auto_eligible"],
        "branches": plan.branches,
        "estimated_steps": plan.estimated_steps,
        "adr_reference": "ADR-107",
    }


# ---------------------------------------------------------------------------
# analyze_task
# ---------------------------------------------------------------------------


def analyze_task(description: str) -> dict[str, Any]:
    """
    Classifies a task and recommends model, team composition, and gate.
    Lightweight version of agent_plan_task for quick routing decisions.
    """
    description_lower = description.lower()

    if any(kw in description_lower for kw in ("adr", "architecture", "design", "concept")):
        task_type = "adr"
        complexity = "architectural"
    elif any(kw in description_lower for kw in ("deploy", "deployment", "migrate", "migration")):
        task_type = "deployment"
        complexity = "moderate"
    elif any(kw in description_lower for kw in ("test", "coverage", "pytest", "fixture")):
        task_type = "test"
        complexity = "simple"
    elif any(kw in description_lower for kw in ("refactor", "tech debt", "clean")):
        task_type = "refactor"
        complexity = "moderate"
    elif any(kw in description_lower for kw in ("review", "pr", "pull request")):
        task_type = "pr_review"
        complexity = "simple"
    else:
        task_type = "feature"
        complexity = "moderate"

    classification = classify_task(task_type, complexity)
    role = classification["primary_role"]
    gate = classification["gate_level"]

    model_recommendation = "swe" if gate <= 1 else "opus"

    return {
        "task_type": task_type,
        "complexity": complexity,
        "recommended_role": role,
        "gate_level": gate,
        "model_recommendation": model_recommendation,
        "auto_eligible": classification["auto_eligible"],
        "rationale": classification["rationale"],
    }


# ---------------------------------------------------------------------------
# check_gate
# ---------------------------------------------------------------------------


def check_gate(action: str, component: str) -> dict[str, Any]:
    """
    Checks if an action on a component is allowed at the current gate level.
    Deployment and destructive operations always require Gate-2.
    """
    DESTRUCTIVE_ACTIONS = {"delete", "drop", "truncate", "rollback", "migrate"}
    GATE2_COMPONENTS = {"production", "database", "migrations", "ssh", "docker"}

    action_lower = action.lower()
    component_lower = component.lower()

    requires_gate2 = (
        any(d in action_lower for d in DESTRUCTIVE_ACTIONS)
        or any(c in component_lower for c in GATE2_COMPONENTS)
    )

    if requires_gate2:
        return {
            "allowed": False,
            "required_gate": GateLevel.TWO.value,
            "reason": (
                f"Action '{action}' on '{component}' requires Gate-2 human approval. "
                "Trigger via GitHub Actions environment protection rules."
            ),
            "adr_reference": "ADR-107 \u00a74.3",
        }

    return {
        "allowed": True,
        "required_gate": GateLevel.ONE.value,
        "reason": f"Action '{action}' on '{component}' is auto-eligible at Gate-1.",
        "adr_reference": "ADR-107 \u00a74.1",
    }
