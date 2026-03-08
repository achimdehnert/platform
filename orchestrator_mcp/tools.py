"""
orchestrator_mcp/tools.py

MCP Tool implementations for the Orchestrator.

Phase 4 (ADR-107): agent_team_status and agent_plan_task updated
to include Deployment Agent, Review Agent, and role routing.

Phase 5 (ADR-108): QA cycle tools added.

Phase 6: get_infra_context + get_payment_context added.

Tools exposed via orchestrator_mcp MCP server:
  - agent_team_status   : current agent team configuration + active roles
  - agent_plan_task     : decompose task into sub-tasks and assign to roles
  - analyze_task        : classify task and recommend model/gate
  - check_gate          : verify action is allowed at current gate level
  - deploy_check        : deployment health check for known repos
  - get_cost_estimate   : token cost estimate per model (ADR-108)
  - evaluate_task       : compute QualityScore + rollback decision (ADR-108)
  - verify_task         : run tests/lint + check acceptance criteria (ADR-108)
  - get_infra_context   : full infra context (Hetzner, Cloudflare, deploy targets)
  - get_payment_context : Stripe + billing-hub context (ADR-062)
  - log_action          : audit log entry
  - get_audit_log       : retrieve audit log entries
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from orchestrator_mcp.agent_team.planner import (
    build_task_plan,
    classify_task,
)
from orchestrator_mcp.agent_team.roles import (
    ROLE_REGISTRY,
    AgentRole,
    GateLevel,
    get_role,
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
        {"task_type": "payment", "routes_to": AgentRole.PAYMENT.value, "gate": "2"},
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
                     deployment, payment, pr_review, adr, architecture.
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
    elif any(kw in description_lower for kw in ("stripe", "payment", "billing", "price", "subscription")):
        task_type = "payment"
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
    GATE2_COMPONENTS = {"production", "database", "migrations", "ssh", "docker", "stripe", "billing"}

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


# ---------------------------------------------------------------------------
# get_cost_estimate  (ADR-108)
# ---------------------------------------------------------------------------

# Cost per 1k tokens (input+output blended estimate)
_COST_PER_1K: dict[str, float] = {
    "opus":    0.015,   # Claude Opus / Cascade Pro
    "swe":     0.003,   # SWE-1 / claude-3-5-sonnet
    "gpt_low": 0.001,   # GPT-4o-mini
    "cascade": 0.015,   # Windsurf Cascade (Opus-tier, for comparison)
}

# Cascade baseline: typical tokens per session type (empirical estimates)
_CASCADE_BASELINE: dict[str, int] = {
    "trivial":       15_000,
    "simple":        40_000,
    "moderate":      80_000,
    "complex":      150_000,
    "architectural": 250_000,
}


def get_cost_estimate(
    task_id: str,
    model: str,
    estimated_tokens: int | None = None,
    complexity: str = "moderate",
    cascade_tokens: int | None = None,
) -> dict[str, Any]:
    """
    Estimates agent cost and compares to Cascade baseline.
    Reporting only — no budget enforcement.
    """
    if model not in _COST_PER_1K:
        valid = list(_COST_PER_1K.keys())
        return {"error": f"Unknown model '{model}'. Valid: {valid}"}

    budget_tokens = _CASCADE_BASELINE.get(complexity, _CASCADE_BASELINE["moderate"])
    tokens = estimated_tokens or budget_tokens

    agent_cost = (tokens / 1000) * _COST_PER_1K[model]

    cascade_tk = cascade_tokens or budget_tokens
    cascade_cost = (cascade_tk / 1000) * _COST_PER_1K["cascade"]

    savings = cascade_cost - agent_cost
    savings_pct = (savings / cascade_cost * 100) if cascade_cost > 0 else 0.0

    if savings_pct > 50:
        verdict = f"Agent {savings_pct:.0f}% cheaper than Cascade"
    elif savings_pct > 0:
        verdict = f"Agent {savings_pct:.0f}% cheaper than Cascade (marginal)"
    else:
        verdict = "Agent not cheaper than Cascade for this task"

    return {
        "task_id": task_id,
        "model": model,
        "complexity": complexity,
        "agent": {
            "tokens": tokens,
            "cost_usd": round(agent_cost, 4),
            "budget_tokens": budget_tokens,
            "within_budget": tokens <= budget_tokens,
        },
        "cascade": {
            "tokens": cascade_tk,
            "cost_usd": round(cascade_cost, 4),
            "baseline_estimate": cascade_tokens is None,
        },
        "comparison": {
            "savings_usd": round(savings, 4),
            "savings_pct": round(savings_pct, 1),
            "verdict": verdict,
        },
        "note": "Reporting only — no enforcement. ADR-108.",
    }


# ---------------------------------------------------------------------------
# evaluate_task  (ADR-108)
# ---------------------------------------------------------------------------


def evaluate_task(
    task_id: str,
    completion_score: float,
    guardian_passed: bool,
    adr_violations: int,
    iterations_used: int,
    tokens_used: int,
    complexity: str = "moderate",
) -> dict[str, Any]:
    """
    Computes QualityScore and rollback recommendation per ADR-108.
    """
    from orchestrator_mcp.agent_team.evaluator import QualityEvaluator, TOKEN_BUDGETS

    budget = TOKEN_BUDGETS.get(complexity, TOKEN_BUDGETS["moderate"])
    efficiency = min(1.0, budget / max(tokens_used, 1))

    evaluator = QualityEvaluator()
    score = evaluator.evaluate(
        completion_score=completion_score,
        guardian_passed=guardian_passed,
        adr_violations=adr_violations,
        iterations_used=iterations_used,
        token_efficiency=efficiency,
    )

    return {
        "task_id": task_id,
        "composite_score": round(score.composite, 3),
        "rollback_level": score.rollback_level.value,
        "recommendation": score.recommendation,
        "sub_scores": {
            "completion": round(score.completion, 3),
            "guardian": round(score.guardian, 3),
            "adr": round(score.adr, 3),
            "efficiency": round(score.efficiency, 3),
        },
        "tokens_used": tokens_used,
        "budget_tokens": budget,
        "adr_reference": "ADR-108",
    }


# ---------------------------------------------------------------------------
# verify_task  (ADR-108)
# ---------------------------------------------------------------------------


def verify_task(
    task_id: str,
    criteria: list[dict[str, Any]],
    tests_passed: bool | None = None,
    lint_passed: bool | None = None,
    adr_violations: int = 0,
) -> dict[str, Any]:
    """
    Verifies task completion against acceptance criteria.
    Tester-Agent entry point after Developer implementation.
    """
    from orchestrator_mcp.agent_team.completion import AcceptanceCriterion, TaskCompletionChecker

    checker = TaskCompletionChecker()

    enriched = list(criteria)

    if tests_passed is False:
        enriched.append({
            "description": "All tests pass (pytest)",
            "met": False,
            "blocking": True,
            "evidence": "tests_passed=False",
        })
    elif tests_passed is True:
        enriched.append({
            "description": "All tests pass (pytest)",
            "met": True,
            "blocking": True,
            "evidence": "tests_passed=True",
        })

    if lint_passed is False:
        enriched.append({
            "description": "Ruff lint clean",
            "met": False,
            "blocking": True,
            "evidence": "lint_passed=False",
        })
    elif lint_passed is True:
        enriched.append({
            "description": "Ruff lint clean",
            "met": True,
            "blocking": True,
            "evidence": "lint_passed=True",
        })

    if adr_violations > 0:
        enriched.append({
            "description": "No ADR violations",
            "met": False,
            "blocking": True,
            "evidence": f"{adr_violations} violation(s) from platform-context check",
        })

    result = checker.from_dict(enriched)

    if result.is_complete:
        next_action = "task_complete — proceed to evaluate_task for QA score"
    elif tests_passed is False:
        next_action = "fix_tests — re-run pytest and address failures"
    elif lint_passed is False:
        next_action = "fix_lint — run ruff check --fix"
    elif adr_violations > 0:
        next_action = "fix_adr — resolve platform-context violations"
    else:
        next_action = f"fix_criteria — {len(result.blocking_open)} blocking criteria open"

    return {
        "task_id": task_id,
        "is_complete": result.is_complete,
        "score": round(result.score, 3),
        "blocking_open": result.blocking_open,
        "criteria_total": len(result.criteria),
        "criteria_met": sum(1 for c in result.criteria if c.met),
        "tests_passed": tests_passed,
        "lint_passed": lint_passed,
        "adr_violations": adr_violations,
        "next_action": next_action,
        "adr_reference": "ADR-108",
    }


# ---------------------------------------------------------------------------
# get_infra_context
# ---------------------------------------------------------------------------


def get_infra_context() -> dict[str, Any]:
    """
    Returns the full platform infrastructure context for the Deployment Agent.

    Eliminates per-session guesswork about hosts, MCP tools, and deploy targets.
    Call this at session start or before any deployment/infra operation.
    """
    from orchestrator_mcp.agent_team.roles import DeploymentAgentConfig

    deployment_cfg = DeploymentAgentConfig()

    mcp_servers = {
        "deployment-mcp": {
            "prefix": "mcp5_",
            "capabilities": ["ssh_manage", "docker_manage", "git_manage",
                              "database_manage", "system_manage"],
            "target": "hetzner-prod (88.198.191.108), user=deploy",
        },
        "orchestrator": {
            "prefix": "mcp11_",
            "capabilities": ["agent_team_status", "agent_plan_task", "analyze_task",
                              "deploy_check", "get_cost_estimate", "evaluate_task",
                              "verify_task", "get_infra_context", "get_payment_context",
                              "log_action"],
            "target": "local (platform/orchestrator_mcp)",
        },
        "platform-context": {
            "prefix": "mcp12_",
            "capabilities": ["get_context_for_task", "check_violations",
                              "get_banned_patterns", "get_project_facts"],
            "target": "local (ADR knowledge graph)",
        },
        "github": {
            "prefix": "mcp8_",
            "capabilities": ["issues", "pull_requests", "repos", "branches",
                              "reviews", "push_files"],
            "target": "github.com/achimdehnert",
        },
        "cloudflare-api": {
            "prefix": "mcp_cloudflare_",
            "capabilities": ["dns_list", "dns_create", "dns_update",
                              "zones", "tunnels"],
            "target": "Cloudflare (API-Keys in Windsurf-Secrets)",
        },
    }

    return {
        "mcp_servers": mcp_servers,
        "infra": deployment_cfg.infra_context,
        "deployment_allowed_tools": deployment_cfg.allowed_tools,
        "session_start_checklist": [
            "Read AGENT_HANDOVER.md in platform root",
            "Call mcp11_agent_team_status() for team state",
            "Call mcp11_deploy_check(action='targets') for deploy config",
            "Call mcp11_get_infra_context() — this tool",
        ],
        "quick_reference": {
            "health_check": "mcp11_deploy_check(action='health', repo='<name>')",
            "container_status": "mcp11_deploy_check(action='status', repo='<name>')",
            "ssh_command": "mcp5_ssh_manage(host='hetzner-prod', action='execute', command='...')",
            "docker_logs": "mcp5_docker_manage(host='hetzner-prod', action='compose_logs', path='/opt/<repo>', service='web', tail=50)",
            "dns_check": "mcp_cloudflare_dns_list(zone='<domain>')",
            "github_comment": "mcp8_add_issue_comment(owner='achimdehnert', repo='<repo>', issue_number=<n>, body='...')",
        },
    }


# ---------------------------------------------------------------------------
# get_payment_context
# ---------------------------------------------------------------------------


def get_payment_context() -> dict[str, Any]:
    """
    Returns the full Stripe + billing-hub context for the Payment Agent.

    Covers: billing-hub location, Stripe key locations (NOT keys),
    Price ID workflow, internal API endpoints, pending setup_plans action.

    IMPORTANT: Never returns actual API keys — only their storage locations.
    Keys are in Windsurf-Secrets and /opt/billing-hub/.env on prod.
    """
    from orchestrator_mcp.agent_team.roles import PaymentAgentConfig

    payment_cfg = PaymentAgentConfig()

    return {
        "payment_context": payment_cfg.payment_context,
        "allowed_tools": payment_cfg.allowed_tools,
        "quick_reference": {
            "billing_health": "mcp11_deploy_check(action='health', repo='billing-hub')",
            "billing_status": "mcp11_deploy_check(action='status', repo='billing-hub')",
            "run_setup_plans": (
                "mcp5_ssh_manage(host='hetzner-prod', action='execute', "
                "command='cd /opt/billing-hub && docker compose -f docker-compose.prod.yml "
                "exec web python manage.py setup_plans "
                "--stripe-monthly=price_xxx --stripe-yearly=price_xxx')"
            ),
            "check_stripe_env": (
                "mcp5_ssh_manage(host='hetzner-prod', action='execute', "
                "command='grep STRIPE /opt/billing-hub/.env | grep -v SECRET')"
            ),
            "billing_logs": (
                "mcp5_docker_manage(host='hetzner-prod', action='compose_logs', "
                "path='/opt/billing-hub', service='web', tail=50)"
            ),
        },
        "stripe_price_id_workflow": [
            "1. Open Stripe Dashboard → Products → Create product per hub/tier",
            "2. Copy Price ID (price_xxx) for monthly + yearly billing",
            "3. SSH to hetzner-prod: run setup_plans management command",
            "4. Verify: mcp11_deploy_check(action='health', repo='billing-hub')",
            "5. Test webhook: Stripe Dashboard → Webhooks → Send test event",
        ],
        "adr_reference": "ADR-062",
    }
