#!/usr/bin/env python3
"""ADR-177 Phase 0a Goldset-Baseline Runner.

Iteriert über `platform/baselines/goldset-2026-04.yaml`, ruft jeden Task
durch die aktuelle FeatureBot/swe-Pipeline (Status quo) und schreibt jeden
LLM-Call in `llm_calls` mit `routing_reason='goldset_baseline_2026-04'`.

Aggregiert am Ende Cost/Tokens/Duration pro task_type.
Output: platform/baselines/goldset-2026-04-results.json

Usage:
    python scripts/run_goldset_baseline.py [--dry-run] [--limit N] [--task-id gs-001]

Voraussetzungen:
    - ORCHESTRATOR_DATABASE_URL env var gesetzt (siehe mcp-hub#13)
    - aifw>=0.5.0 installiert
    - PyYAML installiert

ADR: docs/adr/ADR-177-agent-role-specialization.md (v1.4 Phase 0a)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("goldset_runner")

ROUTING_REASON = "goldset_baseline_2026-04"
GOLDSET_FILE = Path(__file__).parent.parent / "baselines" / "goldset-2026-04.yaml"
RESULTS_FILE = Path(__file__).parent.parent / "baselines" / "goldset-2026-04-results.json"


def _load_goldset(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        logger.error("PyYAML not installed. Run: pip install pyyaml")
        sys.exit(2)
    with path.open() as f:
        return yaml.safe_load(f)


def _get_db_url() -> str:
    url = os.environ.get("ORCHESTRATOR_DATABASE_URL") or os.environ.get(
        "ORCHESTRATOR_MCP_MEMORY_DB_URL"
    )
    if not url:
        logger.error(
            "Neither ORCHESTRATOR_DATABASE_URL nor ORCHESTRATOR_MCP_MEMORY_DB_URL set. "
            "See mcp-hub#13 for setup."
        )
        sys.exit(2)
    return url


def _build_prompt(task: dict[str, Any]) -> str:
    """Build a minimal prompt representing typical Status-quo workload.

    Status quo: alle Tasks gehen durch den gleichen Developer-Agent
    (FeatureBot mit swe-Modell). Der Prompt soll repräsentativ sein für
    durchschnittliche Token-Last (ca. 4K input, 3K output bei feature-Tasks
    laut ADR-177 Cost-Tabelle).
    """
    task_type = task.get("task_type", "feature")
    return (
        f"Task: {task['description']}\n"
        f"Repo: {task.get('repo', 'unknown')}\n"
        f"Type: {task_type}\n"
        f"Complexity: {task.get('complexity', 'moderate')}\n\n"
        "Bitte erläutere kurz (≤ 200 Wörter) wie du diesen Task angehen würdest. "
        "Liste 2-3 betroffene Dateien und 1-2 mögliche Edge-Cases. "
        "Berücksichtige Platform-Konventionen (Service Layer, ADR-009)."
    )


def _run_one_task(task: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    """Run a single task through the current Status-quo pipeline.

    In dry-run mode: simulate (synthetic cost/tokens) for testing without API calls.
    In real mode: ruft `aifw.sync_completion(action_code='goldset_baseline')` auf.
    """
    task_id = task["id"]
    started = time.monotonic()
    prompt = _build_prompt(task)

    if dry_run:
        # Synthetische Antwort — kein echter API-Call
        time.sleep(0.05)
        return {
            "task_id": task_id,
            "task_type": task.get("task_type"),
            "complexity": task.get("complexity"),
            "repo": task.get("repo"),
            "model": "synthetic/dry-run",
            "prompt_tokens": len(prompt.split()) * 2,  # rough estimate
            "completion_tokens": 100,
            "cost_usd": 0.0,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "success": True,
            "dry_run": True,
        }

    # Standalone CI-Script (kein Django) — litellm direkt nutzen,
    # aifw wäre ohne DJANGO_SETTINGS_MODULE nicht funktional (siehe iil-packages rule).
    try:
        import litellm
    except ImportError:
        logger.error("litellm not installed. Run: pip install litellm")
        return {"task_id": task_id, "success": False, "error": "litellm not installed"}

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {
            "task_id": task_id,
            "task_type": task.get("task_type"),
            "success": False,
            "error": "OPENAI_API_KEY not set",
            "duration_ms": int((time.monotonic() - started) * 1000),
        }

    model = "gpt-4o-mini"  # Status quo: FeatureBot/swe tier = gpt_low
    try:
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            api_key=api_key,
        )
        choice = response.choices[0].message
        usage = response.usage
        cost = float(getattr(response, "_hidden_params", {}).get("response_cost", 0.0) or 0.0)
        return {
            "task_id": task_id,
            "task_type": task.get("task_type"),
            "complexity": task.get("complexity"),
            "repo": task.get("repo"),
            "model": model,
            "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
            "cost_usd": cost,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "success": True,
            "content_chars": len(choice.content or ""),
        }
    except Exception as exc:  # noqa: BLE001 — capture all for analysis
        logger.exception("Task %s failed", task_id)
        return {
            "task_id": task_id,
            "task_type": task.get("task_type"),
            "success": False,
            "error": str(exc)[:300],
            "duration_ms": int((time.monotonic() - started) * 1000),
        }


def _insert_llm_calls(db_url: str, results: list[dict]) -> int:
    """INSERT each successful result into llm_calls table directly.

    Standalone-Script umgeht aifw → muss selbst schreiben.
    """
    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        logger.warning("SQLAlchemy not installed — skipping DB insert")
        return 0

    eng = create_engine(db_url)
    inserted = 0
    with eng.begin() as conn:
        for r in results:
            if not r.get("success"):
                continue
            conn.execute(
                text(
                    """
                    INSERT INTO llm_calls
                      (model, prompt_tokens, completion_tokens, total_tokens,
                       cost_usd, duration_ms, routing_reason, task_id, repo,
                       source, call_type, created_at)
                    VALUES
                      (:model, :pt, :ct, :tt, :cost, :dur, :rr, :tid, :repo,
                       :src, :ctype, now())
                    """
                ),
                {
                    "model": r.get("model") or "unknown",
                    "pt": r.get("prompt_tokens", 0),
                    "ct": r.get("completion_tokens", 0),
                    "tt": r.get("total_tokens", r.get("prompt_tokens", 0) + r.get("completion_tokens", 0)),
                    "cost": r.get("cost_usd", 0.0),
                    "dur": r.get("duration_ms", 0),
                    "rr": ROUTING_REASON,
                    "tid": r.get("task_id"),
                    "repo": r.get("repo"),
                    "src": "goldset_runner",
                    "ctype": "completion",
                },
            )
            inserted += 1
    logger.info("Inserted %d rows into llm_calls with routing_reason=%s", inserted, ROUTING_REASON)
    return inserted


def _ensure_routing_tag_in_db(db_url: str, run_id: str, task_results: list[dict]) -> None:
    """Tag the most recent llm_calls entries with our routing_reason.

    aifw.sync_completion writes to llm_calls but doesn't set routing_reason.
    We post-tag the entries by matching on created_at window + task description.

    Pragmatischer Ansatz für Phase 0a: nach Lauf-Ende UPDATE llm_calls
    SET routing_reason='goldset_baseline_2026-04' WHERE created_at > $run_started.
    """
    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        logger.warning("SQLAlchemy not installed — skipping routing_reason tag")
        return

    eng = create_engine(db_url)
    with eng.begin() as conn:
        # Tag all calls during the run window with our routing_reason
        result = conn.execute(
            text(
                "UPDATE llm_calls "
                "SET routing_reason = :rr "
                "WHERE routing_reason IS NULL "
                "  AND created_at > now() - interval '2 hours'"
            ),
            {"rr": ROUTING_REASON},
        )
        logger.info("Tagged %d llm_calls with routing_reason=%s", result.rowcount, ROUTING_REASON)


def _aggregate(results: list[dict]) -> dict[str, Any]:
    """Aggregate per task_type."""
    agg: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "count": 0,
            "success": 0,
            "fail": 0,
            "total_cost_usd": 0.0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_duration_ms": 0,
        }
    )
    for r in results:
        tt = r.get("task_type", "unknown")
        agg[tt]["count"] += 1
        if r.get("success"):
            agg[tt]["success"] += 1
        else:
            agg[tt]["fail"] += 1
        agg[tt]["total_cost_usd"] += float(r.get("cost_usd", 0.0))
        agg[tt]["total_prompt_tokens"] += int(r.get("prompt_tokens", 0))
        agg[tt]["total_completion_tokens"] += int(r.get("completion_tokens", 0))
        agg[tt]["total_duration_ms"] += int(r.get("duration_ms", 0))

    # Add averages
    for tt, d in agg.items():
        if d["count"]:
            d["avg_cost_usd"] = d["total_cost_usd"] / d["count"]
            d["avg_duration_ms"] = d["total_duration_ms"] // d["count"]
    return dict(agg)


def main() -> int:
    parser = argparse.ArgumentParser(description="Goldset Baseline Runner (ADR-177 Phase 0a)")
    parser.add_argument("--dry-run", action="store_true", help="No API calls, synthetic data")
    parser.add_argument("--limit", type=int, default=0, help="Stop after N tasks (0 = all)")
    parser.add_argument("--task-id", default="", help="Run only this task_id (e.g. gs-001)")
    parser.add_argument(
        "--goldset",
        default=str(GOLDSET_FILE),
        help=f"Path to goldset YAML (default: {GOLDSET_FILE})",
    )
    parser.add_argument(
        "--output",
        default=str(RESULTS_FILE),
        help=f"Output JSON path (default: {RESULTS_FILE})",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    goldset = _load_goldset(Path(args.goldset))
    db_url = _get_db_url() if not args.dry_run else ""

    tasks = goldset["tasks"]
    if args.task_id:
        tasks = [t for t in tasks if t["id"] == args.task_id]
    if args.limit:
        tasks = tasks[: args.limit]

    run_id = str(uuid.uuid4())
    run_started = datetime.now(timezone.utc)
    logger.info(
        "Starting goldset run %s (%d tasks, dry_run=%s)",
        run_id,
        len(tasks),
        args.dry_run,
    )

    results = []
    for i, task in enumerate(tasks, 1):
        logger.info("[%d/%d] %s — %s", i, len(tasks), task["id"], task.get("task_type"))
        r = _run_one_task(task, dry_run=args.dry_run)
        results.append(r)
        if args.verbose:
            logger.debug("  → %s", json.dumps(r, default=str))

    if not args.dry_run and db_url:
        _insert_llm_calls(db_url, results)

    aggregated = _aggregate(results)

    output = {
        "run_id": run_id,
        "goldset_version": goldset["goldset_version"],
        "started_at": run_started.isoformat(),
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "task_count": len(tasks),
        "success_count": sum(1 for r in results if r.get("success")),
        "fail_count": sum(1 for r in results if not r.get("success")),
        "total_cost_usd": sum(float(r.get("cost_usd", 0.0)) for r in results),
        "aggregated_by_task_type": aggregated,
        "results": results,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, default=str))
    logger.info("Results written to %s", out_path)
    logger.info("Total cost: $%.6f", output["total_cost_usd"])
    logger.info(
        "Success: %d/%d (%.1f%%)",
        output["success_count"],
        output["task_count"],
        100.0 * output["success_count"] / max(1, output["task_count"]),
    )

    return 0 if output["fail_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
