#!/usr/bin/env python3
"""Befund → Auto-Issue-Emitter der PyPI-Fleet (#2075 K4, ADR-266).

Schließt die Lücke „Melder ohne Leser": ausgewählte Frühwarn-Befunde
(`pypi_fleet_earlywarn.py --json`) werden zu Issues mit Label `auto`, die der
Queue-Prozessor (/process-agent-queue) abarbeitet — Body im Queue-Format
(Betroffene Komponenten + Akzeptanzkriterien, ADR-081 Scope-Lock).

Sicherheits-Kontrakt (Gate autonomous-no-human-review):
  - ALLOWLIST je Metrik-Klasse — default LEER: keine Klasse ist scharf, bis
    der Owner echte Klassen (M2/M4) bewusst zuschaltet (#2084 / Baseline-Regel).
    Der Lauf ohne Allowlist-Klasse ist ein stiller No-Op (bestehendes
    Verhalten) — kein Fehler, kein Issue.
  - Idempotent: existiert ein offenes Issue mit identischem Titel im Ziel-Repo,
    wird NICHT erneut erstellt.
  - Cap: --max-issues (default 3) je Lauf.
  - --dry-run druckt, schreibt nichts. Der PR-Trigger des Health-Workflows
    erzwingt den Dry-Run in CI (Wiring-Beweis by-construction).
  - GITHUB_TOKEN ist repo-gebunden: Cross-Repo-Emission braucht PAT
    (Owner-Gate, s. #2089).

Die Loop-Canary (`registry/pypi-loop-canary.txt`, #2075 K4) hat den vollen
Zyklus einmal real bewiesen (2026-08-19, PR #2096) und ist mit KONZ-052 V5
entfernt — Melder-Flaeche verkleinern statt einen dauerhaft leerlaufenden
Selbsttest zu pflegen (KONZ-018 §5.4: kein neuer Meter, kein neues Rolling-Issue).

    GH_TOKEN=... python3 tools/pypi_fleet_issue_emitter.py --findings f.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

PLATFORM_DIR = Path(__file__).resolve().parent.parent
PLATFORM_REPO = "achimdehnert/platform"
DEFAULT_ALLOWLIST: tuple[str, ...] = ()
LABELS = ("auto", "pypi-fleet")


# --------------------------------------------------------------------------
# Pure functions (getestet in tools/tests/test_pypi_fleet_issue_emitter.py)
# --------------------------------------------------------------------------


def issue_title(finding: dict) -> str:
    """Deterministischer Titel = Dedup-Schlüssel (idempotenter Emitter)."""
    return f"[pypi-fleet:{finding['metric']}] {finding['text']}"


def issue_body(finding: dict, today: dt.date) -> str:
    komponenten = f"Paket-Repo `{finding['org']}/{finding['repo']}`"
    kriterien = (
        "- [ ] Befund behoben (siehe Titel) und per Frühwarn-Lauf nicht mehr gemeldet\n"
        "- [ ] PR mit grünem CI"
    )
    return (
        f"Automatisch erzeugt vom PyPI-Fleet-Loop (#2075 K4, ADR-266) am {today.isoformat()}.\n\n"
        f"**Befund:** {finding['text']}\n\n"
        f"## Betroffene Komponenten\n\n{komponenten}\n\n"
        f"## Akzeptanzkriterien\n\n{kriterien}\n\n"
        f"_Quelle: `tools/pypi_fleet_earlywarn.py` / `tools/pypi_fleet_issue_emitter.py`;"
        f" Abarbeitung: /process-agent-queue (Label `auto`)._"
    )


def select_findings(
    findings: list[dict], allowlist: tuple[str, ...], cap: int
) -> list[dict]:
    picked = [f for f in findings if f.get("metric") in allowlist]
    return picked[:cap]


# --------------------------------------------------------------------------
# gh-Schreibpfad
# --------------------------------------------------------------------------


def _gh(*args: str) -> str:
    return subprocess.run(
        ["gh", *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def open_issue_exists(repo_slug: str, title: str) -> bool:
    out = _gh(
        "issue",
        "list",
        "-R",
        repo_slug,
        "--state",
        "open",
        "--label",
        "pypi-fleet",
        "--json",
        "title",
    )
    return any(e.get("title") == title for e in json.loads(out or "[]"))


def create_issue(repo_slug: str, title: str, body: str) -> str:
    for label in LABELS:
        subprocess.run(
            [
                "gh",
                "label",
                "create",
                label,
                "-R",
                repo_slug,
                "--force",
                "--description",
                "PyPI-Fleet-Loop (ADR-266 #2075 K4)",
            ],
            capture_output=True,
            text=True,
        )
    return _gh(
        "issue",
        "create",
        "-R",
        repo_slug,
        "--title",
        title,
        "--body",
        body,
        "--label",
        ",".join(LABELS),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--findings", type=Path, help="JSON aus earlywarn --json")
    ap.add_argument("--today", type=dt.date.fromisoformat, default=None)
    ap.add_argument(
        "--allow",
        default=",".join(DEFAULT_ALLOWLIST),
        help="Komma-Liste erlaubter Metrik-Klassen (default: leer — kein Auto-Issue)",
    )
    ap.add_argument("--max-issues", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    today = args.today or dt.date.today()

    findings: list[dict] = []
    if args.findings:
        findings.extend(json.loads(args.findings.read_text()))

    allowlist = tuple(c for c in args.allow.split(",") if c)
    picked = select_findings(findings, allowlist, args.max_issues)
    print(
        f"== Emitter: {len(findings)} Befunde, {len(picked)} nach Allowlist "
        f"({args.allow}) + Cap ({args.max_issues}) =="
    )
    created = 0
    for f in picked:
        repo_slug = (
            PLATFORM_REPO if f["repo"] == "platform" else f"{f['org']}/{f['repo']}"
        )
        title = issue_title(f)
        if args.dry_run:
            print(f"DRY-RUN: würde Issue anlegen in {repo_slug}: {title}")
            continue
        if open_issue_exists(repo_slug, title):
            print(f"SKIP (existiert offen): {repo_slug}: {title}")
            continue
        url = create_issue(repo_slug, title, issue_body(f, today))
        print(f"ERSTELLT: {url}")
        created += 1
    print(f"== {created} Issue(s) erstellt ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
