#!/usr/bin/env python3
"""PreToolUse(Bash) gate — blockt `git stash pop|apply|drop` ohne ausdrücklichen Eintrag.

GATE_HEADER (KONZ-038 D8):
  "slug": "parallel-subagents-shared-scratch-state"
  "mode": "blocking"
  "owner": "achim"
  "last_drill_pass": "2026-09-16"
  "evidence": "tools/claude-hooks/tests/test_block_bare_stash_pop.py"

Hintergrund: Retro `session-retro-2026-09-14-apo-hub-40c069.md` Befund #4.
Acht Fix-Subagenten liefen parallel auf demselben Repo. Einer von ihnen führte
beim Rot/Grün-Messen ein blankes `git stash pop` aus und holte damit den Stash
einer FREMDEN Sitzung zurück in den Arbeitsbaum. Keiner der acht Briefs nannte
`git stash`. Der Slug ist seither ×2 aufgetreten und gate-pflichtig
(`tools/gate_deckung.py`).

Warum blank gefährlich ist und mit Eintrag nicht: `refs/stash` liegt in `.git`,
und `.git` ist über alle Worktrees eines Repos GETEILT. „Der oberste Stash" ist
deshalb keine Eigenschaft der eigenen Sitzung — er gehört dem, der zuletzt
gestasht hat. `git stash list` kostet eine Sekunde und macht aus einer Annahme
eine gelesene Angabe; `git stash pop stash@{2}` sagt danach, welcher gemeint war.

Der Hook verlangt genau das: einen expliziten Eintrag. Er verbietet `git stash`
nicht und erzwingt keine Reihenfolge — er nimmt nur die Lesart „der oberste wird
schon meiner sein" aus dem Werkzeugkasten.

FAIL-OPEN (bewusste Grenze): kein JSON, kein `git stash`, `push`/`list`/`show`/
`save`/`clear`, ein `stash@{…}`-Argument, `--` gefolgt von Pfaden (`git stash
drop`-Form ohne Ref gibt es dort nicht), Befehl mit `$`-Variable an der Ref-
Stelle. Der Hook fängt die Familie „blanker Griff in geteilten Zustand", nicht
jede denkbare Stash-Verwechslung. NICHT gefangen — und deshalb hier benannt statt
im Gate behauptet: die zweite Hälfte desselben Slugs (Befund #5, kollidierende
PR-Body-Dateien im geteilten Scratchpad) hat eine andere Wurzel (Dateinamen im
Delegations-Brief) und braucht eine eigene Schranke (platform#3211).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SLUG = "parallel-subagents-shared-scratch-state"

#: `git stash pop`, `git stash apply`, `git stash drop` — auch mit Optionen davor.
_STASH = re.compile(
    r"\bgit\s+(?:-[Cc]\s+\S+\s+|--\S+(?:=\S+)?\s+|-[^\s-]\s+)*"
    r"stash\s+(pop|apply|drop)\b"
)
#: Ein ausdrücklicher Eintrag in irgendeiner Schreibweise.
_REF = re.compile(r"stash@\{\s*\d+\s*\}|\$\S")


def _abschnitt(kommando: str, start: int) -> str:
    """Text ab dem `git stash`-Aufruf bis zum nächsten Shell-Trenner."""
    rest = kommando[start:]
    ende = re.search(r"&&|\|\||;|\n|\|", rest)
    return rest[: ende.start()] if ende else rest


def entscheide(kommando: str) -> str | None:
    """Grund für ein deny oder None (durchlassen)."""
    for treffer in _STASH.finditer(kommando):
        aufruf = _abschnitt(kommando, treffer.start())
        if _REF.search(aufruf):
            continue
        unterbefehl = treffer.group(1)
        return (
            f"`git stash {unterbefehl}` ohne Eintrag greift auf den obersten Stash — "
            "und `refs/stash` ist über alle Worktrees desselben Repos geteilt. Bei "
            "parallelen Sitzungen gehört der oberste womöglich jemand anderem "
            "(Realfall apo-hub 2026-09-14). Erst `git stash list`, dann "
            f"`git stash {unterbefehl} stash@{{n}}`."
        )
    return None


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    kommando = (daten.get("tool_input") or {}).get("command") or ""
    if not _STASH.search(kommando):
        return 0
    grund = entscheide(kommando)
    if grund is None:
        return 0
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG,
            "git stash ohne Eintrag",
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
