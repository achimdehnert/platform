#!/usr/bin/env python3
"""PreToolUse(Bash) Hinweis — Tag/Release auf ein Reusable-Workflow-Repo ohne gruenen Nicht-PR-Lauf.

GATE_HEADER (KONZ-038 D8):
  "slug": "tag-ohne-nicht-pr-lauf"
  "mode": "advisory"
  "owner": "achim"
  "last_drill_pass": "2026-10-14"
  "evidence": "tools/claude-hooks/tests/test_tag_ohne_nicht_pr_lauf_hinweis.py"

Hintergrund (Retro ec3416 Befunde 1 und 24, Owner-Wort „R6 go" 2026-10-14 21:01Z):
iilgmbh/shared-ci v1.1.27 wurde getaggt, nachdem nur `pull_request`-Laeufe gruen waren.
Jeder Nicht-PR-Lauf (push, workflow_dispatch) seiner Aufrufer scheiterte danach mit
0 Jobs — 13 von 13 (iilgmbh/shared-ci#112). Ein Tag auf ein Repo mit `workflow_call`-
Workflows ist eine Veroeffentlichung an alle Aufrufer; der Beleg, den die PR-CI nicht
liefern kann, ist ein gruener Lauf mit einem anderen Event als `pull_request`.

Der Hook feuert bei `git tag <name>`, `git push … --tags`/`refs/tags/…`/`v<n>` und
`gh release create <tag>`, wenn das Repo unter `.github/workflows/` mindestens einen
Workflow mit `workflow_call` anbietet. Er fragt `gh run list --commit <sha>` nach dem
Zielcommit und schweigt, sobald ein Lauf mit Event ≠ pull_request erfolgreich war. Sonst
nennt er die Laufverteilung und den billigsten Beleg (workflow_dispatch eines Aufrufers
auf den Branch).

FAIL-OPEN: Exit 0 in jedem Fall — kein JSON, anderes Kommando, kein Provider-Repo, kein gh,
Drosselung, Timeout. Ein Fehler erzeugt hoechstens "nicht pruefbar", nie ein deny.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

SLUG = "tag-ohne-nicht-pr-lauf"
GH_TIMEOUT = 10
GIT_TIMEOUT = 3
RUN_LIMIT = 50
WORKFLOW_VERZEICHNIS = Path(".github") / "workflows"
#: Events, deren Erfolg NICHT als Beleg zaehlt: sie laufen im PR-Kontext mit anderen
#: Rechten/Inputs als push oder workflow_dispatch (Retro ec3416 Befund 24).
PR_EVENTS = frozenset({"pull_request", "pull_request_target", "pull_request_review"})

#: `git tag <name>` als Anlegen — nicht `-l/--list`, `-d/--delete`, `-v/--verify`, kein Name.
_GIT_TAG = re.compile(
    r"(?:^|[;&|\n]|&&)\s*git\s+tag\s+(?!(?:-l|--list|-d|--delete|-v|--verify|-n)\b)"
    r"(?:-[afsm]\S*\s+(?:\S+\s+)?)*(?P<name>[A-Za-z0-9][\w./-]*)"
)
_GIT_PUSH_TAGS = re.compile(
    r"(?:^|[;&|\n]|&&)\s*git\s+push\b[^;&|\n]*?(?:--tags\b|refs/tags/(?P<ref>[\w./-]+)|\s(?P<v>v\d[\w.-]*)\s*(?=$|[;&|\n]))"
)
_GH_RELEASE = re.compile(
    r"(?:^|[;&|\n]|&&)\s*gh\s+release\s+create\s+(?P<name>[A-Za-z0-9][\w./-]*)"
)
_WORKFLOW_CALL = re.compile(r"^\s*workflow_call\s*:", re.MULTILINE)


def tag_name(kommando: str) -> str | None:
    """Tag-Name des Veroeffentlichungs-Kommandos oder None, wenn es keines ist."""
    m = _GH_RELEASE.search(kommando)
    if m:
        return m.group("name")
    m = _GIT_TAG.search(kommando)
    if m:
        return m.group("name")
    m = _GIT_PUSH_TAGS.search(kommando)
    if m:
        return m.group("ref") or m.group("v") or "--tags"
    return None


def ist_provider_repo(cwd: str) -> bool:
    """Mindestens ein Workflow unter .github/workflows bietet `workflow_call` an."""
    verzeichnis = Path(cwd) / WORKFLOW_VERZEICHNIS
    if not verzeichnis.is_dir():
        return False
    for datei in list(verzeichnis.glob("*.yml")) + list(verzeichnis.glob("*.yaml")):
        try:
            if _WORKFLOW_CALL.search(
                datei.read_text(encoding="utf-8", errors="replace")
            ):
                return True
        except OSError:
            continue
    return False


def _git(args: list[str], cwd: str) -> str | None:
    try:
        res = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=GIT_TIMEOUT
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return res.stdout.strip() if res.returncode == 0 else None


def ziel_commit(cwd: str, tag: str) -> str | None:
    """Commit, auf den der Tag zeigt (existiert er schon) — sonst HEAD."""
    if tag and tag != "--tags":
        sha = _git(["rev-parse", "--verify", "-q", f"{tag}^{{commit}}"], cwd)
        if sha:
            return sha
    return _git(["rev-parse", "HEAD"], cwd)


def laeufe(sha: str, cwd: str) -> list[dict[str, Any]]:
    res = subprocess.run(
        [
            "gh",
            "run",
            "list",
            "--commit",
            sha,
            "--limit",
            str(RUN_LIMIT),
            "--json",
            "event,conclusion,status,workflowName",
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=GH_TIMEOUT,
        check=True,
    )
    daten = json.loads(res.stdout or "[]")
    return daten if isinstance(daten, list) else []


def bewerte(runs: list[dict[str, Any]]) -> tuple[bool, Counter]:
    """(hat gruenen Nicht-PR-Lauf, Verteilung `event/conclusion`)."""
    verteilung: Counter = Counter()
    beleg = False
    for r in runs:
        event = str(r.get("event") or "?")
        ergebnis = str(r.get("conclusion") or r.get("status") or "?")
        verteilung[f"{event}/{ergebnis}"] += 1
        if event not in PR_EVENTS and ergebnis == "success":
            beleg = True
    return beleg, verteilung


def hinweis(daten: dict[str, Any]) -> str | None:
    kommando = (daten.get("tool_input") or {}).get("command") or ""
    tag = tag_name(kommando)
    if not tag:
        return None
    cwd = daten.get("cwd") or os.getcwd()
    if not ist_provider_repo(cwd):
        return None
    sha = ziel_commit(cwd, tag)
    if not sha:
        return None
    try:
        runs = laeufe(sha, cwd)
    except Exception as exc:  # noqa: BLE001 — gh-Fehler/Drosselung/Timeout: fail-open
        return f"Tag-Hinweis ({SLUG}): nicht pruefbar ({type(exc).__name__})."
    beleg, verteilung = bewerte(runs)
    if beleg:
        return None
    lage = (
        ", ".join(f"{k} ×{n}" for k, n in sorted(verteilung.items())) or "keine Laeufe"
    )
    return (
        f"Tag-Hinweis ({SLUG}, nur Hinweis): {tag} zeigt auf {sha[:7]} in einem Repo mit "
        f"workflow_call-Workflows, aber kein Lauf mit Event ≠ pull_request war gruen "
        f"({lage}). shared-ci v1.1.27 brach so jeden push/dispatch-Lauf seiner Aufrufer "
        f"(13/13, iilgmbh/shared-ci#112). Billigster Beleg vor dem Tag: workflow_dispatch "
        f"eines Aufrufers auf diesen Branch, dann Laufliste erneut lesen."
    )


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(daten, dict):
        return 0
    text = hinweis(daten)
    if not text:
        return 0
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG,
            "tag hinweis",
            beleg=text[:200],
            session=daten.get("session_id", ""),
            modus="advisory",
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stoeren
        pass
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": text,
                }
            },
            ensure_ascii=False,
        )
    )
    return 0


def main_sicher() -> int:
    """Hook-Vertrag: Exit 0 immer."""
    try:
        return main()
    except BaseException as exc:  # noqa: BLE001 — auch Timeout/Interrupt: nie blockieren
        print(
            f"tag_ohne_nicht_pr_lauf_hinweis: {type(exc).__name__}"[:200],
            file=sys.stderr,
        )
        return 0


if __name__ == "__main__":
    sys.exit(main_sicher())
