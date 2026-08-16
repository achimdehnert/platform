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
            # PFLICHT, nicht Kosmetik: der Hook laeuft hier als Subprozess mit
            # ersetzter Umgebung — `PYTEST_CURRENT_TEST` kommt dort nie an, die
            # pytest-Sperre in gate_hits greift also NICHT. Ohne diese Zeile
            # schreibt jeder Drill in das echte Protokoll und die FP-Auswertung
            # urteilt wieder ueber sich selbst (Realfall 2026-08-15: 212 von
            # 212 Treffern stammten aus pytest). HOME ist der zweite Riegel.
            "GATE_HITS_DATEI": str(tmp_path / "gate-hits.jsonl"),
            "HOME": str(tmp_path),
        },
    )


def _hits(tmp_path: Path) -> list[dict]:
    p = tmp_path / "gate-hits.jsonl"
    if not p.exists():
        return []
    return [json.loads(z) for z in p.read_text().splitlines() if z.strip()]


def _owner_nachricht(text: str = "mach weiter") -> str:
    return json.dumps({"type": "user", "message": {"content": text}})


def _modul():
    """Hook als Modul laden — fuer die Messfunktionen, die kein Subprozess braucht.

    Import erst hier, damit die Subprozess-Tests oben unabhaengig davon bleiben.
    """
    import sys

    sys.path.insert(0, str(HOOK.parent))
    import artefakt_budget

    return artefakt_budget


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


def test_should_record_hit_when_firing(tmp_path: Path) -> None:
    """Ohne Spur auf Platte laesst sich der Melder nicht kalibrieren.

    Realfall 2026-08-15: er loeste neunmal aus, und die Bilanz musste aus dem
    Sitzungsverlauf rekonstruiert werden, weil er nichts schrieb.
    """
    _fahre(tmp_path, _transcript(tmp_path, pr_creates=4, issue_creates=2))
    treffer = _hits(tmp_path)
    assert len(treffer) == 1, treffer
    assert treffer[0]["slug"] == "artefakt-budget-schwelle-erreicht"
    assert treffer[0]["modus"] == "advisory"
    assert "prs=4" in treffer[0]["marker"]
    assert "prs_seit_owner=" in treffer[0]["marker"]


def test_should_not_record_below_budget(tmp_path: Path) -> None:
    _fahre(tmp_path, _transcript(tmp_path, pr_creates=3))
    assert _hits(tmp_path) == []


def test_should_isolate_drill_from_real_protocol() -> None:
    """Der Drill darf das echte Protokoll nie erreichen — die pytest-Sperre in
    gate_hits greift bei diesem Hook NICHT, weil er als Subprozess mit
    ersetzter Umgebung laeuft. Diese Pruefung haelt die Isolation fest, damit
    sie nicht bei der naechsten Umbau-Runde still verschwindet."""
    import inspect

    quelle = inspect.getsource(_fahre)
    assert '"GATE_HITS_DATEI"' in quelle
    assert '"HOME"' in quelle


def test_should_count_prs_since_last_owner_message(tmp_path: Path) -> None:
    """Der Runaway-Indikator: PRs seit der letzten Nachricht des Menschen.

    Die absolute PR-Zahl unterscheidet Auftrag und Kette nicht — am 2026-08-15
    stand sie an allen neun Ausloesepunkten hoch, waehrend `prs_seit_owner`
    konstant 1 war (jede Eskalation einzeln freigegeben).
    """
    ab = _modul()
    t = tmp_path / "mit_owner.jsonl"
    basis = _transcript(tmp_path, pr_creates=5).read_text().splitlines()
    # Owner meldet sich nach dem dritten PR -> nur die letzten zwei zaehlen.
    t.write_text("\n".join(basis[:3] + [_owner_nachricht()] + basis[3:]) + "\n")
    assert ab.messe_kontext(t)["prs_seit_owner"] == 2


def test_should_ignore_tool_results_as_owner_messages(tmp_path: Path) -> None:
    """`user`-Eintraege tragen auch Tool-Ergebnisse und System-Erinnerungen.
    Zaehlte man die mit, waere der Wert immer 0 und der Melder wieder blind."""
    ab = _modul()
    t = tmp_path / "nur_tool.jsonl"
    basis = _transcript(tmp_path, pr_creates=5).read_text().splitlines()
    rauschen = [
        json.dumps({"type": "user", "message": {"content": [{"type": "tool_result"}]}}),
        json.dumps(
            {"type": "user", "isMeta": True, "message": {"content": "erinnerung"}}
        ),
    ]
    t.write_text("\n".join(basis[:3] + rauschen + basis[3:]) + "\n")
    assert ab.messe_kontext(t)["prs_seit_owner"] == 5


def test_should_measure_repos_and_prod_step(tmp_path: Path) -> None:
    ab = _modul()
    t = tmp_path / "kontext.jsonl"
    t.write_text(
        "\n".join(
            [
                json.dumps(
                    {"type": "pr-link", "prRepository": "achimdehnert/risk-hub"}
                ),
                json.dumps(
                    {
                        "type": "assistant",
                        "cwd": "/home/devuser/github/platform/tools",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "input": {"command": "bash deploy.sh prod"},
                                }
                            ]
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "input": {
                                        "command": "gh pr view 1 -R ttz-lif/ttz-hub"
                                    },
                                }
                            ]
                        },
                    }
                ),
            ]
        )
        + "\n"
    )
    k = ab.messe_kontext(t)
    assert k["repos"] == 3, k
    assert k["prod"] == 1


def test_should_not_flag_merge_as_prod_step(tmp_path: Path) -> None:
    """`gh pr merge` ist KEIN Prod-Marker — ob ein Merge deployt, haengt am
    Repo. Das waere geraten, nicht gemessen."""
    ab = _modul()
    t = _transcript(tmp_path, pr_creates=4)  # enthaelt `gh pr merge 7`
    assert ab.messe_kontext(t)["prod"] == 0


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
