#!/usr/bin/env python3
"""Claude Code Stop hook — Artefakt-Budget (Scope-Checkpoint, maschinell).

Macht den meistgezaehlten Retro-Slug ausfuehrbar statt notiert:
`scope-checkpoint-not-durably-recorded` stand am 2026-08-02 bei x9 — der
hoechste Zaehler im ganzen Register (`tools/retro_kpis.py`), ohne dass je ein
Gate daraus wurde. Die Hausregel checkpointet am DRITTEN REPO; real eskalieren
Sessions aber ueber die ARTEFAKT-Zahl: Am 2026-07-31 wurde aus "analysiere
SB-Neu" eine Kette von 12 PRs in 2 Repos — der Repo-Trigger feuerte nie
(Retro 8ed6a2, Massnahme "Artefakt-Budget je Auftrag").

Der Hook zaehlt im Session-Transkript angelegte Artefakte (`gh pr create`,
`gh issue create`) und erinnert ab der Schwelle an den Scope-Checkpoint:
"ist das noch der Auftrag?". Er blockiert NICHTS — der Checkpoint ist eine
Frage an den Menschen, kein Verbot.

Contract (wie evidence_claim_scanner.py): Stop-Event-JSON auf stdin, IMMER
exit 0. Bei Feuern: additionalContext-JSON auf stdout. Feuert je Schwelle
GENAU EINMAL (State-Datei), sonst wird der Reminder zum Rauschen, das er
verhindern soll.

Env:
  ARTEFAKT_BUDGET_PRS  Schwelle (Default 4). 0 deaktiviert den Hook.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

# gh pr create / gh issue create in Bash-tool_use-Kommandos.
# Bewusst NUR create — view/list/merge sind keine neuen Artefakte.
_CREATE = re.compile(r"\bgh\s+(pr|issue)\s+create\b")


def zaehle_artefakte(transcript_path: Path) -> tuple[int, int]:
    """(prs, issues) — gezaehlt ueber tool_use-Bash-Kommandos im Transkript."""
    prs = issues = 0
    try:
        fh = transcript_path.open(encoding="utf-8", errors="replace")
    except OSError:
        return 0, 0
    with fh:
        for raw in fh:
            if '"tool_use"' not in raw or "gh " not in raw:
                continue  # billiger Vorfilter vor dem JSON-Parse
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            msg = obj.get("message", obj)
            content = msg.get("content", [])
            if not isinstance(content, list):
                continue
            for c in content:
                if not (isinstance(c, dict) and c.get("type") == "tool_use"):
                    continue
                cmd = str((c.get("input") or {}).get("command", ""))
                for m in _CREATE.finditer(cmd):
                    if m.group(1) == "pr":
                        prs += 1
                    else:
                        issues += 1
    return prs, issues


def _state_file(session_id: str) -> Path:
    return Path(tempfile.gettempdir()) / f"artefakt_budget_{session_id or 'na'}.txt"


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        return 0

    budget = int(os.environ.get("ARTEFAKT_BUDGET_PRS", "4") or 0)
    if budget <= 0:
        return 0

    tp = event.get("transcript_path")
    if not tp:
        return 0
    prs, issues = zaehle_artefakte(Path(tp))
    if prs < budget:
        return 0

    # Einmal je erreichtem Stand feuern, nicht bei jedem Stop danach.
    sf = _state_file(str(event.get("session_id", "")))
    try:
        last = int(sf.read_text().strip() or 0)
    except (OSError, ValueError):
        last = 0
    if prs <= last:
        return 0
    try:
        sf.write_text(str(prs))
    except OSError:
        pass  # State-Verlust heisst schlimmstenfalls ein Reminder mehr — nie blocken

    hinweis = (
        f"📦 Artefakt-Budget: {prs} PRs"
        + (f" + {issues} Issues" if issues else "")
        + f" in dieser Session (Schwelle {budget}). Scope-Checkpoint: ist das noch "
        "der urspruengliche Auftrag? Wenn ja — kurz dem Menschen spiegeln, woraus "
        "die Kette entstand; wenn unklar — Zwischenstand statt weiterbauen. "
        "(scope-checkpoint x9 im Retro-Register; Schwelle via ARTEFAKT_BUDGET_PRS)"
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "Stop",
                    "additionalContext": hinweis,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
