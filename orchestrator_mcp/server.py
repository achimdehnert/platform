"""
orchestrator_mcp/server.py

MCP Server entry point for the Orchestrator.
Exposes all tools defined in tools.py via the MCP protocol.

Usage (in mcp_config or Windsurf MCP settings):
    command: python
    args: ["-m", "orchestrator_mcp.server"]

ADR-107 Phase 4: agent_team_status + agent_plan_task registered.
ADR-108 Phase 5: get_cost_estimate, evaluate_task, verify_task registered.
Infra Context: get_infra_context registered (Hetzner + Cloudflare + Deploy-Targets).
ADR-112 Phase 3: agent_memory + scan_repo registered (Skill Registry v1.0).
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from orchestrator_mcp.skills import discover_skills, invoke_skill
from orchestrator_mcp.tools import (
    agent_plan_task,
    agent_team_status,
    analyze_task,
    check_gate,
    evaluate_task,
    get_cost_estimate,
    get_infra_context,
    get_payment_context,
    verify_task,
)

_SKILLS_LOADED = discover_skills()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------

_TOOLS: dict[str, dict[str, Any]] = {
    "agent_team_status": {
        "description": (
            "Get current AI Engineering Squad status: active agents, "
            "tool count, model scenario, planner version, shell allowlist, "
            "and deploy targets. Per ADR-107."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "handler": lambda _args: agent_team_status(),
    },
    "agent_plan_task": {
        "description": (
            "Decompose a task description using the Planner. "
            "Returns a TaskGraph with branches and sub-tasks. "
            "task_type: feature|bugfix|refactor|test|docs|infra|deployment|pr_review|adr|architecture. "
            "complexity: trivial|simple|moderate|complex|architectural."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Task description to plan",
                },
                "task_type": {
                    "type": "string",
                    "default": "feature",
                    "description": "Task type",
                },
                "complexity": {
                    "type": "string",
                    "default": "moderate",
                    "description": "Task complexity",
                },
            },
            "required": ["description"],
        },
        "handler": lambda args: agent_plan_task(
            description=args["description"],
            task_type=args.get("task_type", "feature"),
            complexity=args.get("complexity", "moderate"),
        ),
    },
    "analyze_task": {
        "description": "Analyze a task and get model/team/gate recommendations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Task description to analyze",
                },
            },
            "required": ["description"],
        },
        "handler": lambda args: analyze_task(args["description"]),
    },
    "check_gate": {
        "description": "Check if an action is allowed at the current gate level.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to check",
                },
                "component": {
                    "type": "string",
                    "description": "Target component",
                },
            },
            "required": ["action", "component"],
        },
        "handler": lambda args: check_gate(args["action"], args["component"]),
    },
    "get_cost_estimate": {
        "description": (
            "Cost estimate + Cascade vs Agent comparison report (reporting only, no enforcement). "
            "model: opus|swe|gpt_low. Returns agent cost, cascade baseline, savings_pct. Per ADR-108."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task identifier"},
                "model": {
                    "type": "string",
                    "enum": ["opus", "swe", "gpt_low"],
                    "description": "Model to use",
                },
                "estimated_tokens": {
                    "type": "integer",
                    "description": "Estimated total tokens",
                },
                "complexity": {
                    "type": "string",
                    "default": "moderate",
                    "description": "trivial|simple|moderate|complex|architectural",
                },
                "cascade_tokens": {
                    "type": "integer",
                    "description": "Actual Cascade session tokens (optional)",
                },
            },
            "required": ["task_id", "model"],
        },
        "handler": lambda args: get_cost_estimate(
            task_id=args["task_id"],
            model=args["model"],
            estimated_tokens=args.get("estimated_tokens"),
            complexity=args.get("complexity", "moderate"),
            cascade_tokens=args.get("cascade_tokens"),
        ),
    },
    "evaluate_task": {
        "description": (
            "Compute QualityScore + rollback decision for a completed task. "
            "Returns composite_score, rollback_level (none/soft/hard/escalate), "
            "sub_scores, and recommendation. Per ADR-108."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task identifier"},
                "completion_score": {
                    "type": "number",
                    "description": "0.0-1.0 — fraction of acceptance criteria met",
                },
                "guardian_passed": {
                    "type": "boolean",
                    "description": "True if Guardian found no blocking issues",
                },
                "adr_violations": {
                    "type": "integer",
                    "description": "Number of ADR violations found",
                },
                "iterations_used": {
                    "type": "integer",
                    "description": "How many agent iterations were needed",
                },
                "tokens_used": {
                    "type": "integer",
                    "description": "Total tokens consumed",
                },
                "complexity": {
                    "type": "string",
                    "default": "moderate",
                    "description": "trivial|simple|moderate|complex|architectural",
                },
            },
            "required": [
                "task_id", "completion_score", "guardian_passed",
                "adr_violations", "iterations_used", "tokens_used",
            ],
        },
        "handler": lambda args: evaluate_task(
            task_id=args["task_id"],
            completion_score=args["completion_score"],
            guardian_passed=args["guardian_passed"],
            adr_violations=args["adr_violations"],
            iterations_used=args["iterations_used"],
            tokens_used=args["tokens_used"],
            complexity=args.get("complexity", "moderate"),
        ),
    },
    "verify_task": {
        "description": (
            "Verify a completed task: checks acceptance criteria + test/lint results. "
            "Tester-Agent entry point after Developer implementation. "
            "Returns is_complete, blocking_open, score, next_action. Per ADR-108."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task identifier"},
                "criteria": {
                    "type": "array",
                    "description": "List of {description, met, blocking, evidence}",
                    "items": {"type": "object"},
                },
                "tests_passed": {
                    "type": "boolean",
                    "description": "True if pytest passed, False if failed",
                },
                "lint_passed": {
                    "type": "boolean",
                    "description": "True if ruff passed, False if failed",
                },
                "adr_violations": {
                    "type": "integer",
                    "default": 0,
                    "description": "Number of ADR violations found",
                },
            },
            "required": ["task_id", "criteria"],
        },
        "handler": lambda args: verify_task(
            task_id=args["task_id"],
            criteria=args.get("criteria", []),
            tests_passed=args.get("tests_passed"),
            lint_passed=args.get("lint_passed"),
            adr_violations=args.get("adr_violations", 0),
        ),
    },
    "get_infra_context": {
        "description": (
            "Get full platform infrastructure context: Hetzner hosts, "
            "Cloudflare domains, deploy targets (9 repos), MCP server registry, "
            "and quick-reference tool calls. Call at session start or before "
            "any deployment/infra operation to eliminate guesswork."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "handler": lambda _args: get_infra_context(),
    },
    "get_payment_context": {
        "description": (
            "Get Stripe + billing-hub context for the Payment Agent. "
            "Returns billing-hub location, Stripe key locations (NOT keys), "
            "Price ID workflow, internal API endpoints, pending setup_plans action. "
            "ADR-062: Central billing for all 9 hubs."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "handler": lambda _args: get_payment_context(),
    },
    "agent_memory": {
        "description": (
            "Read or write the persistent Agent Memory Store (AGENT_MEMORY.md). "
            "Operations: read (all entries), upsert (add/update entry), "
            "gc (remove expired entries), query (filter by type or tag). "
            "ADR-112: git-tracked context store for cross-session agent knowledge."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["read", "upsert", "gc", "query"],
                    "description": "Operation to perform",
                    "default": "read",
                },
                "entry": {
                    "type": "object",
                    "description": "MemoryEntry dict (required for upsert)",
                },
                "agent": {
                    "type": "string",
                    "description": "Name of the writing agent",
                    "default": "unknown-agent",
                },
                "filter_type": {
                    "type": "string",
                    "description": "Filter by entry type (for query)",
                },
                "filter_tag": {
                    "type": "string",
                    "description": "Filter by tag (for query)",
                },
                "commit": {
                    "type": "boolean",
                    "description": "Git-commit after write (default: true)",
                    "default": True,
                },
            },
            "required": [],
        },
        "handler": lambda args: invoke_skill("session_memory", **args).model_dump(),
    },
    "scan_repo": {
        "description": (
            "Scan a GitHub repository and store infra context in AGENT_MEMORY.md. "
            "Detects framework, health URL, migration status, open agent issues, "
            "and AGENT_HANDOVER.md preview. Requires GITHUB_TOKEN or PROJECT_PAT. "
            "ADR-112: automated repo onboarding."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_name": {
                    "type": "string",
                    "description": "Repository name (without org prefix)",
                },
                "org": {
                    "type": "string",
                    "description": "GitHub org (default: achimdehnert)",
                    "default": "achimdehnert",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch to scan (default: main)",
                    "default": "main",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Scan without saving to AGENT_MEMORY.md",
                    "default": False,
                },
                "commit": {
                    "type": "boolean",
                    "description": "Git-commit after scan (default: true)",
                    "default": True,
                },
            },
            "required": ["repo_name"],
        },
        "handler": lambda args: invoke_skill("repo_scan", **args).model_dump(),
    },
}


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 MCP Protocol Handler
# ---------------------------------------------------------------------------


def _handle_request(request: dict[str, Any]) -> dict[str, Any]:
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "orchestrator",
                    "version": "3.2.0",
                },
            },
        }

    if method == "tools/list":
        tools_list = [
            {
                "name": name,
                "description": spec["description"],
                "inputSchema": spec["inputSchema"],
            }
            for name, spec in _TOOLS.items()
        ]
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools_list}}

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name not in _TOOLS:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}",
                },
            }

        try:
            result = _TOOLS[tool_name]["handler"](arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(result, indent=2)}
                    ]
                },
            }
        except Exception as exc:
            logger.exception("Tool %s raised: %s", tool_name, exc)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": str(exc)},
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )
    logger.info("orchestrator_mcp server v3.2 starting (ADR-107+108+112, %d tools, %d skills)", len(_TOOLS), _SKILLS_LOADED)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = _handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError as exc:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    main()
