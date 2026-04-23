"""
Score history tracking (Design #5).

Appends audit results to a JSON file for trend analysis.
Git-friendly: one append per audit run.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from hub_identity.core.scoring import ScoreNode


def record_audit(
    history_path: Path,
    hub: str,
    score: ScoreNode,
) -> None:
    """Append a score snapshot to the history file."""
    history_path.parent.mkdir(parents=True, exist_ok=True)

    data = {"runs": []}
    if history_path.exists():
        try:
            data = json.loads(
                history_path.read_text(encoding="utf-8"),
            )
        except json.JSONDecodeError:
            data = {"runs": []}

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hub": hub,
        "total": round(score.weighted_score, 1),
        "grade": score.grade,
        "passed": score.passed,
        "breakdown": {},
    }

    # Capture category scores
    for child in score.children:
        entry["breakdown"][child.name] = {
            "score": round(child.weighted_score, 1),
            "grade": child.grade,
        }
        for sub in child.children:
            key = f"{child.name}.{sub.name}"
            entry["breakdown"][key] = {
                "score": round(sub.weighted_score, 1),
                "grade": sub.grade,
            }

    data["runs"].append(entry)

    history_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get_trend(
    history_path: Path,
    hub: str,
    last_n: int = 10,
) -> list[dict]:
    """Get score trend for a hub (newest first)."""
    if not history_path.exists():
        return []

    data = json.loads(
        history_path.read_text(encoding="utf-8"),
    )
    runs = [
        r for r in data.get("runs", [])
        if r.get("hub") == hub
    ]
    return list(reversed(runs[-last_n:]))
