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

ZWEITE PRUEFBEDINGUNG (Rev 2, 2026-09-07, platform#2374 — Gate war rueckfaellig ×19):
Die erste Bedingung vergleicht die Ueberschrift mit dem letzten Commit, der die DATEI
beruehrt hat. Sie kann damit strukturell nur eine Fehlform sehen: „Datei committet, ohne
den Stand-Abschnitt mitzuziehen". Die Fehlform, die den Slug wiederkehren liess, ist die
andere: die Datei wird GAR NICHT angefasst, waehrend die Sitzung weiterlaeuft. Realfall
Retro 0f59ce (2026-09-03): 13 Merges in 7 Repos, AGENT_HANDOVER.md stand auf 7902c652 vom
Vortag — Ueberschrift 2026-09-02, letzter Datei-Commit 2026-09-02, Abstand 0 Tage, also
PASS. Der Check war gruen, weil er die falsche Groesse mass.

Deshalb zaehlt `--commits-schwelle N` die Commits, die seit der letzten Beruehrung der
Datei auf dem Zweig gelandet sind (dieses Repo squasht beim Merge — ein Commit ist eine
gemergte PR; `--merges` waere hier immer 0, gemessen 2026-09-07). Dependabot-Bumps zaehlen
nicht mit: sie sind keine Sitzungsarbeit und wuerden die Zahl unabhaengig vom Handover
treiben. Die Bedingung ist per Vorgabe AUS (`0`) und wird nur dort eingeschaltet, wo das
Ergebnis advisory ist (`.github/workflows/handover-freshness-advisory.yml`) — die beiden
blockierenden Zweige (handoff-banner-gate, regel-ritual) behalten ihr bisheriges Verhalten
unveraendert.

Stattdessen: ein **Rezenz-Check**, der dialektunabhängig funktioniert — beide Konventionen
tragen bereits ein YYYY-MM-DD-Datum in einer Markdown-Überschrift der ersten HEAD_LINES Zeilen.
Dieses Datum darf gegenüber dem letzten Commit, der die Datei berührt hat, höchstens STALE_DAYS
alt sein; sonst wurde die Datei committet, ohne den Stand-Abschnitt mitzuziehen.

Aufruf:  agent_handover_freshness_check.py [--commits-schwelle N] [--basis <ref>]
                                          <AGENT_HANDOVER.md> [<datei> ...]
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

# KONZ-038 D8 verlangt den Kopf im Modul selbst, nicht nur in der Registry —
# sonst laesst sich von der Datei aus nicht sagen, welches Gate sie ist.
GATE_HEADER = {
    "slug": "handover-stale-vor-merge",
    "mode": "process",
    "owner": "achim",
    "last_drill_pass": "2026-08-06",
    "evidence": "tools/tests/test_agent_handover_freshness_check.py",
}

HEAD_LINES = 40
STALE_DAYS = 30
HEADING_DATE_RE = re.compile(r"^#{1,6}\s.*?(\d{4}-\d{2}-\d{2})")

#: Zweite Bedingung, per Vorgabe AUS. 0 = nur der Rezenz-Check von Rev 1.
#: Der Wert 12 im advisory-Workflow ist an der Realfall-Groesse geeicht (Retro
#: 0f59ce: 13 gemergte PRs ohne Handover-Beruehrung) und an der eigenen Historie
#: gemessen: ueber die letzten 24 Handover-Intervalle dieses Repos liegen 8
#: darueber, 16 darunter — die Bedingung meldet also eine Minderheit, nicht jeden
#: PR. Sie wird bewusst NICHT in den blockierenden Zweigen gesetzt.
DEFAULT_COMMIT_SCHWELLE = 0

#: Abhaengigkeits-Bumps sind keine Sitzungsarbeit. Ohne diesen Filter treibt ein
#: ruhiger Tag mit sechs Dependabot-PRs die Zahl genauso wie ein Arbeitstag —
#: die Zahl wuerde dann etwas anderes messen als das, was im Handover fehlt.
DEPS_SUBJECT_RE = re.compile(
    r"^(?:deps|chore\(deps\)|build\(deps\)|chore\(deps-dev\))[:(]|^Bump\s", re.I
)

FAIL_HINT_NO_DATE = (
    "keine datierte Überschrift in den ersten %d Zeilen — AGENT_HANDOVER.md-Konvention "
    "verlangt z.B. '## Aktueller Stand (2026-07-07)' oder "
    "'## Current state (observed 2026-07-07)' (Gate handover-stale-vor-merge)."
) % HEAD_LINES

FAIL_HINT_COMMITS = (
    "seit der letzten Beruehrung dieser Datei sind %d Commits (ohne Dependabot-Bumps) auf "
    "dem Zweig gelandet — der Stand-Abschnitt bildet die Sitzung nicht mehr ab. Das ist die "
    "Fehlform, gegen die der Rezenz-Check blind ist: die Datei wurde GAR NICHT angefasst "
    "(Gate handover-stale-vor-merge Rev 2, Realfall Retro 0f59ce: 13 Merges in 7 Repos)."
)

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


def last_touch_sha(path: Path) -> str | None:
    """SHA des letzten Commits, der `path` beruehrt hat. None = nicht ermittelbar."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except OSError:
        return None
    out = result.stdout.strip()
    if result.returncode != 0 or not out:
        return None
    return out


def zaehle_sitzungs_commits(betreffs: list[str]) -> int:
    """Commits ohne Dependabot-Bumps. Reine Funktion — der git-Aufruf liegt daneben,
    damit die Zaehlregel ohne Repo drillbar ist."""
    return sum(
        1 for b in betreffs if b.strip() and not DEPS_SUBJECT_RE.match(b.strip())
    )


def commits_seit_beruehrung(path: Path, basis: str = "HEAD") -> int | None:
    """Sitzungs-Commits zwischen der letzten Beruehrung von `path` und `basis`.

    None = nicht ermittelbar (flaches Checkout, unbekannte Ref, neue Datei).
    Wie bei `last_touch_date` degradiert das zu PASS statt zu einem Fehlalarm:
    ein Melder, der bei fehlender Historie rot wird, wird abgeschaltet.
    """
    sha = last_touch_sha(path)
    if sha is None:
        return None
    try:
        result = subprocess.run(
            ["git", "log", "--format=%s", f"{sha}..{basis}"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return zaehle_sitzungs_commits(result.stdout.splitlines())


def check(
    path: Path, commit_schwelle: int = DEFAULT_COMMIT_SCHWELLE, basis: str = "HEAD"
) -> tuple[bool, str]:
    h = heading_date(path)
    if h is None:
        return False, FAIL_HINT_NO_DATE
    touched = last_touch_date(path)
    if touched is not None and (touched - h).days > STALE_DAYS:
        return False, FAIL_HINT_STALE
    # Zweite Bedingung, nur wenn ausdruecklich eingeschaltet. Sie steht NACH der
    # ersten, damit ein Repo mit beiden Fehlformen den aelteren, praeziseren
    # Befund zuerst sieht.
    if commit_schwelle > 0:
        n = commits_seit_beruehrung(path, basis)
        if n is not None and n > commit_schwelle:
            return False, FAIL_HINT_COMMITS % n
    return True, ""


def _argumente(argv: list[str]) -> tuple[int, str, list[str]]:
    """(commit_schwelle, basis, dateien). Handgeschrieben statt argparse, weil das
    Modul in drei Workflows als nacktes Skript aufgerufen wird und seine bisherige
    Aufrufform (`<datei> [...]`) unveraendert weiter gelten muss."""
    schwelle = DEFAULT_COMMIT_SCHWELLE
    basis = "HEAD"
    dateien: list[str] = []
    rest = list(argv)
    while rest:
        arg = rest.pop(0)
        if arg == "--commits-schwelle":
            schwelle = int(rest.pop(0)) if rest else schwelle
        elif arg.startswith("--commits-schwelle="):
            schwelle = int(arg.split("=", 1)[1])
        elif arg == "--basis":
            basis = rest.pop(0) if rest else basis
        elif arg.startswith("--basis="):
            basis = arg.split("=", 1)[1]
        else:
            dateien.append(arg)
    return schwelle, basis, dateien


def main(argv: list[str]) -> int:
    try:
        schwelle, basis, dateien = _argumente(argv)
    except ValueError:
        print("--commits-schwelle erwartet eine Zahl", file=sys.stderr)
        return 2
    if not dateien:
        print(
            "usage: agent_handover_freshness_check.py [--commits-schwelle N] "
            "[--basis <ref>] <AGENT_HANDOVER.md> [...]",
            file=sys.stderr,
        )
        return 2
    failed: list[str] = []
    for name in dateien:
        path = Path(name)
        if not path.is_file():
            print(f"SKIP  {name} (existiert nicht — vermutlich gelöscht)")
            continue
        ok, hint = check(path, schwelle, basis)
        if ok:
            print(f"PASS  {name}")
        else:
            print(f"FAIL  {name} — {hint}")
            failed.append(name)
    if failed:
        print(
            f"\n⛔ Gate handover-stale-vor-merge (AGENT_HANDOVER.md): {len(failed)} Datei(en) nicht frisch."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
