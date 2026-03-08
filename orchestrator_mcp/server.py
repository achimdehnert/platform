"""
orchestrator_mcp/server.py

MCP Server entry point for the Orchestrator.
Exposes all tools defined in tools.py via the MCP protocol.

Usage (in mcp_config or Windsurf MCP settings):
    command: python
    args: ["-m", "orchestrator_mcp.server"]

ADR-107 Phase 4: agent_team_status + agent_plan_task registered.
ADR-108 Phase 5: get_cost_estimate, evaluate_task, verify_task registered.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from orchestrator_mcp.tools import (
    agent_plan_task,
    agent_team_status,
    analyze_task,
    check_gate,
    evaluate_task,
    get_cost_estimate,
    verify_task,
)

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
            "Get cost estimate for a task. "
            "model: opus|swe|gpt_low. "
            "Returns cost_usd, token_budget, budget_status. Per ADR-108."
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
            },
            "required": ["task_id", "model"],
        },
        "handler": lambda args: get_cost_estimate(
            task_id=args["task_id"],
            model=args["model"],
            estimated_tokens=args.get("estimated_tokens"),
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
                    "description": "True if pytest passed, False if failed, omit if not run",
                },
                "lint_passed": {
                    "type": "boolean",
                    "description": "True if ruff passed, False if failed, omit if not run",
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
                    "version": "3.0.0",
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
    logger.info("orchestrator_mcp server v3.0 starting (ADR-107+108 Phase 5, %d tools)", len(_TOOLS))

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
