"""Tests fuer tools/claude-hooks/artefakt_budget.py (Stop-Hook, Retro 8ed6a2).

Der Hook macht `scope-checkpoint-not-durably-recorded` (x9, hoechster Zaehler
im Retro-Register) ausfuehrbar: ab N per `gh pr create` angelegten PRs erinnert
er an den Scope-Checkpoint. Beide Richtungen gedeckt — ein Reminder, der immer
oder nie feuert, waere dasselbe Nichts wie die unverdrahtete Notiz.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

HOOK = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "claude-hooks"
    / "artefakt_budget.py"
)


def _transcript(tmp_path: Path, pr_creates: int, issue_creates: int = 0) -> Path:
    """Synthetisches Session-Transkript mit N gh-pr-create-Bash-Aufrufen."""
    p = tmp_path / "session.jsonl"
    zeilen = []
    for i in range(pr_creates):
        zeilen.append(
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Bash",
                                "id": f"t{i}",
                                "input": {"command": f'gh pr create --title "x{i}"'},
                            }
                        ]
                    },
                }
            )
        )
    for i in range(issue_creates):
        zeilen.append(
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Bash",
                                "id": f"i{i}",
                                "input": {"command": "gh issue create --title y"},
                            }
                        ]
                    },
                }
            )
        )
    # Rauschen, das NICHT zaehlen darf: view/merge/list + Text, der create erwaehnt
    zeilen.append(
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "id": "n1",
                            "input": {"command": "gh pr view 7 && gh pr merge 7"},
                        },
                        {"type": "text", "text": "wir koennten gh pr create nutzen"},
                    ]
                },
            }
        )
    )
    p.write_text("\n".join(zeilen) + "\n")
    return p


def _fahre(
    tmp_path: Path,
    transcript: Path,
    *,
    budget: str = "4",
    session: str = "test",
) -> subprocess.CompletedProcess[str]:
    event = {"transcript_path": str(transcript), "session_id": session}
    return subprocess.run(
        ["python3", str(HOOK)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin",
            "ARTEFAKT_BUDGET_PRS": budget,
            "TMPDIR": str(tmp_path),
        },
    )


def test_should_stay_silent_below_budget(tmp_path: Path) -> None:
    e = _fahre(tmp_path, _transcript(tmp_path, pr_creates=3))
    assert e.returncode == 0
    assert e.stdout.strip() == "", e.stdout


def test_should_fire_at_budget(tmp_path: Path) -> None:
    """DER Zielfall — 4 PRs erreichen die Schwelle."""
    e = _fahre(tmp_path, _transcript(tmp_path, pr_creates=4, issue_creates=2))
    assert e.returncode == 0
    out = json.loads(e.stdout)
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "4 PRs" in ctx
    assert "2 Issues" in ctx
    assert "Scope-Checkpoint" in ctx


def test_should_fire_once_per_count_not_every_stop(tmp_path: Path) -> None:
    """Ein Reminder, der bei jedem Stop feuert, ist das Rauschen, das er
    verhindern soll (Realfall Scanner 2026-07-03: 9 Blocks in Folge)."""
    t = _transcript(tmp_path, pr_creates=4)
    first = _fahre(tmp_path, t, session="einmal")
    second = _fahre(tmp_path, t, session="einmal")
    assert first.stdout.strip() != ""
    assert second.stdout.strip() == "", second.stdout


def test_should_fire_again_when_count_grows(tmp_path: Path) -> None:
    t4 = _transcript(tmp_path, pr_creates=4)
    _fahre(tmp_path, t4, session="wachs")
    t5 = _transcript(tmp_path, pr_creates=5)
    e = _fahre(tmp_path, t5, session="wachs")
    assert "5 PRs" in e.stdout


def test_should_not_count_view_merge_or_prose(tmp_path: Path) -> None:
    """Nur echte create-Kommandos zaehlen — nicht view/merge/list und nicht
    Prosa, die das Kommando erwaehnt (die Fixture enthaelt beides)."""
    e = _fahre(tmp_path, _transcript(tmp_path, pr_creates=0, issue_creates=0))
    assert e.stdout.strip() == ""


def test_should_disable_on_zero_budget(tmp_path: Path) -> None:
    e = _fahre(tmp_path, _transcript(tmp_path, pr_creates=9), budget="0")
    assert e.returncode == 0
    assert e.stdout.strip() == ""


def test_should_never_fail_on_garbage_stdin(tmp_path: Path) -> None:
    """Vertrag: ein Hook-Fehler darf Claude NIE blocken — immer exit 0."""
    e = subprocess.run(
        ["python3", str(HOOK)],
        input="kein json {",
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "TMPDIR": str(tmp_path)},
    )
    assert e.returncode == 0
