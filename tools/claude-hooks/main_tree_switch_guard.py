#!/usr/bin/env python3
"""PreToolUse(Bash) gate — blockt `git switch -c`/`git checkout -b` im Haupt-Tree.

GATE_HEADER (KONZ-038 D8):
  "slug": "main-tree-guard-recurring-incident"
  "mode": "blocking"
  "owner": "achim"
  "last_drill_pass": "2026-09-24"
  "evidence": "tools/claude-hooks/tests/test_main_tree_switch_guard.py"

Hintergrund: Retro 2752dc (2026-08) + Retro f1d54f §5 (2026-09-21, platform#3348
F15). `git switch -c`/`git checkout -b` im Haupt-Tree statt `tools/repo-session.sh
start` ist der wiederkehrende Vorfall hinter ADR-233: der post-checkout-Enforcer
(`tools/main-tree-guard.sh`) ist nur ein Snap-back NACH dem Flip, kein Hard-Block
VOR ihm — `.git/iil-guard-events.log` zählt 120 `unauthorized_head_flip` seit
Einführung des Guards, 6 davon seit 2026-09-16. Positivkontrolle ist der Vorfall
vom 2026-09-21T08:35:36Z (`git switch -c session/...` im Haupt-Tree von platform).

Verhalten: der Hook liest den Befehlstext auf ein branch-erzeugendes
`git switch -c`/`git switch --create`/`git checkout -b`/`git checkout -B`. Trifft
er darauf, bestimmt er das Ziel-Verzeichnis — `-C <pfad>` am selben `git`-Aufruf,
sonst das `cwd` aus dem Hook-Payload — und blockt, wenn dieses Verzeichnis unter
$GITHUB_DIR (Default `~/github`) liegt UND NICHT unter
$REPO_SESSION_DIR/worktrees (Default `~/.repo-session/worktrees`, dieselbe
Env-Variable wie `tools/repo-session.sh`). Das deckt den Haupt-Tree jedes
direkten Klons unter $GITHUB_DIR, egal ob `cwd` die Repo-Wurzel selbst oder ein
Unterverzeichnis ist — ein Session-Worktree bleibt erlaubt.

FAIL-OPEN (bewusste Grenzen, hier benannt statt im Gate behauptet):
  * Kein JSON, kein branch-erzeugender Aufruf, `-C`-Pfad mit `$`/`` ` `` oder ohne
    lesbares `cwd` (Ziel zur Prüfzeit unbekannt) → durchlassen.
  * Erkannt werden nur die vier literalen Formen; ein Alias, eine Funktion oder
    ein Skript, das intern `git switch -c` aufruft, bleibt unsichtbar (gleiche
    Grenze wie bei `block_direct_pr_merge.py`).
  * Kein Netz-, `git`- oder `gh`-Aufruf — reine Textprüfung + Pfadauflösung, damit
    der Hook nie hängt oder scheitert.

Ersatz in der Meldung: `bash tools/repo-session.sh start <repo> --task <slug>`
mit dem tatsächlichen Repo-Namen aus dem erkannten Haupt-Tree-Pfad.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SLUG = "main-tree-guard-recurring-incident"


#: `$REPO_SESSION_DIR/worktrees/` (Default `~/.repo-session/worktrees`, dieselbe
#: Env-Variable wie `tools/repo-session.sh`) ist per Definition NIE der Haupt-Tree.
def _worktrees_root() -> Path:
    basis = os.environ.get("REPO_SESSION_DIR") or str(Path.home() / ".repo-session")
    return Path(os.path.expanduser(basis)) / "worktrees"


#: Branch-erzeugende Formen: `git switch -c|--create`, `git checkout -b|-B`.
#: Optional ein `-C <pfad>` zwischen `git` und dem Unterbefehl (Zielverzeichnis).
_SWITCH_CREATE = re.compile(
    r"\bgit\s+(?:-C\s+(\"[^\"]*\"|'[^']*'|\S+)\s+)?"
    r"(?:switch\s+(?:-c\b|--create\b)|checkout\s+(?:-b\b|-B\b))"
)


def _ohne_quotes(wert: str) -> str:
    if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "\"'":
        return wert[1:-1]
    return wert


def _github_dir() -> Path:
    return Path(os.environ.get("GITHUB_DIR") or str(Path.home() / "github"))


def _ziel_verzeichnis(dash_c: str | None, cwd: str) -> Path | None:
    """Aufgelöstes Zielverzeichnis oder None, wenn zur Prüfzeit unbekannt."""
    roh = dash_c if dash_c is not None else cwd
    if not roh:
        return None
    if "$" in roh or "`" in roh:
        return None  # Variable/Substitution — Ziel unbekannt, fail-open
    pfad = Path(os.path.expanduser(roh))
    if not pfad.is_absolute():
        if not cwd or "$" in cwd or "`" in cwd:
            return None
        pfad = Path(os.path.expanduser(cwd)) / pfad
    try:
        return Path(os.path.normpath(str(pfad)))
    except (OSError, ValueError):
        return None


def _ist_haupt_tree(pfad: Path) -> bool:
    """Unter $GITHUB_DIR, aber nicht unter ~/.repo-session/worktrees/."""
    try:
        pfad.relative_to(_worktrees_root())
        return False  # Worktree — nie der Haupt-Tree
    except ValueError:
        pass
    try:
        pfad.relative_to(_github_dir())
    except ValueError:
        return False
    return True


def entscheide(kommando: str, cwd: str) -> str | None:
    """Grund für ein deny oder None (durchlassen)."""
    for treffer in _SWITCH_CREATE.finditer(kommando):
        dash_c = _ohne_quotes(treffer.group(1)) if treffer.group(1) else None
        ziel = _ziel_verzeichnis(dash_c, cwd)
        if ziel is None or not _ist_haupt_tree(ziel):
            continue
        repo = ziel.name or str(ziel)
        return (
            "`git switch -c`/`git checkout -b` im Haupt-Tree statt "
            "`repo-session.sh start` — der main-tree-guard (ADR-233) fängt den "
            "Flip erst NACH dem Wechsel ab (Snap-back), kein Hard-Block davor; "
            "120 `unauthorized_head_flip` in `.git/iil-guard-events.log`, 6 seit "
            "2026-09-16, zuletzt 2026-09-21T08:35:36Z. Stattdessen: "
            f"`bash tools/repo-session.sh start {repo} --task <slug>`."
        )
    return None


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    kommando = (daten.get("tool_input") or {}).get("command") or ""
    if not kommando or not _SWITCH_CREATE.search(kommando):
        return 0
    grund = entscheide(kommando, str(daten.get("cwd") or ""))
    if grund is None:
        return 0
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG,
            "git switch -c im Haupt-Tree",
            beleg=kommando[:200],
            session=daten.get("session_id", ""),
            modus="blocking",
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stören
        pass
    print(f"⛔ {grund}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
