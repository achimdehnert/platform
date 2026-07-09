#!/usr/bin/env python3
"""agent_handover_freshness_check.py — CI-Gate `handover-stale-vor-merge`, AGENT_HANDOVER.md-Zweig.

Hintergrund: dieselbe Drift wie bei HANDOFF-*.md (Retro f5e1d F-S3/F-P3) — ein statisches
Handover-Dokument wird committet, ohne dass sein "Aktueller Stand"-Abschnitt mitgezogen wird,
Folge-Sessions lesen einen falschen Stand. iil-voice-agent Session-Retro 2026-07-06 (9206ac)
fand dasselbe Muster für AGENT_HANDOVER.md und benannte die fleet-weite Erweiterung dieses Gates
als Prio.

Der bestehende HANDOFF-*.md-Check (`handoff_banner_check.py`) verlangt ein wörtliches
"Live-Status: #<nr>"-Banner. Eine Fleet-Erhebung über alle 18 Repos mit einem eigenständigen
AGENT_HANDOVER.md zeigt (platform-pinned ausgenommen — kein eigenständiges Repo, sondern ein
gepinnter Worktree von platform selbst): KEINES trägt dieses Banner, und es gibt ZWEI etablierte,
gegenseitig inkompatible Konventionen ("## ⚡ Aktueller Stand (<datum>)" vs. "## Current state
(observed <datum>)"), aber keine ADR, die eine davon vorschreibt. Den HANDOFF-Banner unverändert
wiederzuverwenden würde alle 18 Dateien sofort brechen.

Stattdessen: ein **Rezenz-Check**, der dialektunabhängig funktioniert — beide Konventionen
tragen bereits ein YYYY-MM-DD-Datum in einer Markdown-Überschrift der ersten HEAD_LINES Zeilen.
Dieses Datum darf gegenüber dem letzten Commit, der die Datei berührt hat, höchstens STALE_DAYS
alt sein; sonst wurde die Datei committet, ohne den Stand-Abschnitt mitzuziehen.

Aufruf:  agent_handover_freshness_check.py <AGENT_HANDOVER.md> [<datei> ...]
Exit 0 = alle frisch (oder kein Git-Verlauf ermittelbar — degradiert zu PASS statt False-Positive)
Exit 1 = mind. eine Datei ohne datierte Überschrift ODER mit zu alter Überschrift
Exit 2 = Usage-Fehler (keine Argumente)
Braucht `git log` im PATH (Checkout mit fetch-depth 0, wie im bestehenden Gate-Workflow).
Verdrahtet in .github/workflows/handoff-banner-gate.yml;
Tests: tools/tests/test_agent_handover_freshness_check.py.

Fleet-Distribution: der Workflow ist als `workflow_call`-reusable-Workflow aufrufbar (platform
ist PUBLIC → auch private Repos in anderen Orgs können ihn referenzieren, ohne Cross-Org-
Freigaben). Jedes aufrufende Repo bekommt eine dünne Caller-Datei; dieses Skript selbst bleibt
unverändert — der Workflow checkt es bei jedem Aufruf aus platform nach (s.
`.github/workflows/handoff-banner-gate.yml`). Rollout-Tracking: platform Issue #982.
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

HEAD_LINES = 40
STALE_DAYS = 30
HEADING_DATE_RE = re.compile(r"^#{1,6}\s.*?(\d{4}-\d{2}-\d{2})")

FAIL_HINT_NO_DATE = (
    "keine datierte Überschrift in den ersten %d Zeilen — AGENT_HANDOVER.md-Konvention "
    "verlangt z.B. '## Aktueller Stand (2026-07-07)' oder "
    "'## Current state (observed 2026-07-07)' (Gate handover-stale-vor-merge)."
) % HEAD_LINES

FAIL_HINT_STALE = (
    "die datierte Überschrift ist mehr als %d Tage älter als der letzte Commit, der diese "
    "Datei berührt hat — der 'Aktueller Stand'-Abschnitt wurde beim Commit vermutlich nicht "
    "mitgezogen (Gate handover-stale-vor-merge, dieselbe Drift wie bei HANDOFF-*.md, Retro f5e1d)."
) % STALE_DAYS


def heading_date(path: Path) -> date | None:
    """Jüngstes YYYY-MM-DD-Datum aus einer Markdown-Überschrift in den ersten HEAD_LINES Zeilen."""
    found: date | None = None
    with path.open(encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            if i >= HEAD_LINES:
                break
            m = HEADING_DATE_RE.match(line)
            if not m:
                continue
            try:
                d = date.fromisoformat(m.group(1))
            except ValueError:
                continue
            if found is None or d > found:
                found = d
    return found


def last_touch_date(path: Path) -> date | None:
    """Datum des letzten Commits, der `path` berührt hat. None = kein Git-Verlauf ermittelbar
    (z.B. flaches Checkout, neue ungetrackte Datei) — degradiert zu PASS, kein False-Positive."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=short", "--", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except OSError:
        return None
    out = result.stdout.strip()
    if result.returncode != 0 or not out:
        return None
    try:
        return date.fromisoformat(out)
    except ValueError:
        return None


def check(path: Path) -> tuple[bool, str]:
    h = heading_date(path)
    if h is None:
        return False, FAIL_HINT_NO_DATE
    touched = last_touch_date(path)
    if touched is None:
        return True, ""
    if (touched - h).days > STALE_DAYS:
        return False, FAIL_HINT_STALE
    return True, ""


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: agent_handover_freshness_check.py <AGENT_HANDOVER.md> [...]", file=sys.stderr)
        return 2
    failed: list[str] = []
    for name in argv:
        path = Path(name)
        if not path.is_file():
            print(f"SKIP  {name} (existiert nicht — vermutlich gelöscht)")
            continue
        ok, hint = check(path)
        if ok:
            print(f"PASS  {name}")
        else:
            print(f"FAIL  {name} — {hint}")
            failed.append(name)
    if failed:
        print(f"\n⛔ Gate handover-stale-vor-merge (AGENT_HANDOVER.md): {len(failed)} Datei(en) nicht frisch.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
