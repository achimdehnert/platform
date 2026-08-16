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

**Jedes Feuern wird protokolliert** (`gate_hits.notiere`). Bis 2026-08-16 tat
er das nicht, und genau daran scheiterte seine eigene Kalibrierung: am
2026-08-15 loeste er achtmal aus und bekam achtmal dieselbe Antwort ("im
Auftrag") — nachlesbar aber nur im Sitzungsverlauf, nicht in Daten. Wer ueber
mehrere Sitzungen messen will, misst sonst Erinnerung. Das war am selben Tag
schon der Kernbefund bei den Welle-1-Scannern (Retro d57884).

Protokolliert wird nicht nur die PR-Zahl, sondern die drei Kandidat-Kriterien
aus dem #1640-Register — denn die offene Frage ist nicht "wie viele PRs?",
sondern "Auftrag oder ungefragt gewachsene Kette?":

- ``prs_seit_owner``  PRs seit der letzten Nachricht des Menschen. **Das** ist
  der Runaway-Indikator; die absolute PR-Zahl ist es nicht.
- ``repos``           beruehrte Repos (Hausregel checkpointet am dritten).
- ``prod``            ob ein Prod-/Publish-Schritt vorkam (grobe Marker, s.u.).

Die Schwelle selbst bleibt unveraendert — welches Kriterium sie kuenftig
traegt, ist eine offene Owner-Entscheidung. Dieser Hook liefert ihr Daten,
er nimmt sie nicht vorweg.

Env:
  ARTEFAKT_BUDGET_PRS  Schwelle (Default 4). 0 deaktiviert den Hook.
  GATE_HITS_DATEI      Protokoll-Ziel (siehe gate_hits.py; Tests setzen es).
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate_hits  # noqa: E402  (haengt am sys.path oben)

GATE_HEADER = {
    "slug": "artefakt-budget-schwelle-erreicht",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-08-16",
    "evidence": "tools/tests/test_artefakt_budget.py",
}

# gh pr create / gh issue create in Bash-tool_use-Kommandos.
# Bewusst NUR create — view/list/merge sind keine neuen Artefakte.
_CREATE = re.compile(r"\bgh\s+(pr|issue)\s+create\b")

# Repo-Bezug eines gh-Aufrufs, falls er nicht im Repo-Verzeichnis lief.
_REPO_FLAG = re.compile(r"(?:\B-R|--repo)[= ]\s*([\w.-]+/[\w.-]+)")

# Prod-/Publish-Schritt — bewusst grob und eng zugleich: nur Kommandos, die
# nach draussen wirken. `gh pr merge` steht NICHT drin (zu haeufig, und ob ein
# Merge deployt, haengt am Repo — das waere geraten, nicht gemessen).
_PROD = re.compile(
    r"\bdocker\s+push\b|\btwine\s+upload\b|\bgh\s+release\s+create\b"
    r"|\bdeploy\.sh\b|\bgh\s+workflow\s+run\b[^\n]{0,80}"
    r"(?:deploy|publish|release|ship)"
)


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


def messe_kontext(transcript_path: Path) -> dict:
    """Die drei Kandidat-Kriterien aus dem #1640-Register.

    Zweiter Durchlauf ueber das Transkript, absichtlich **nur beim Feuern**
    aufgerufen: der Zaehl-Durchlauf oben laeuft bei jedem Stop und bleibt
    deshalb mit seinem Vorfilter billig; diese Messung darf teurer sein, weil
    sie selten passiert.

    ``prs_seit_owner`` zaehlt die PR-Anlagen NACH der letzten Nachricht des
    Menschen. Eine Nachricht ist ein `user`-Eintrag, dessen Inhalt Text ist —
    Tool-Ergebnisse und System-Erinnerungen (`isMeta`) sind es nicht, obwohl
    sie denselben Typ tragen. Ohne diese Unterscheidung waere jeder Wert 0.
    """
    kontext = {"repos": 0, "prs_seit_owner": 0, "prod": 0}
    try:
        fh = transcript_path.open(encoding="utf-8", errors="replace")
    except OSError:
        return kontext

    repos: set[str] = set()
    seit_owner = 0
    prod = False
    with fh:
        for raw in fh:
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if obj.get("type") == "user" and not obj.get("isMeta"):
                inhalt = (obj.get("message") or {}).get("content")
                if isinstance(inhalt, str) and inhalt.strip():
                    seit_owner = 0  # der Mensch hat sich gemeldet — Kette neu

            if obj.get("prRepository"):
                repos.add(str(obj["prRepository"]).split("/")[-1])
            cwd = str(obj.get("cwd") or "")
            if "/github/" in cwd:
                repos.add(cwd.split("/github/", 1)[1].split("/")[0])

            msg = obj.get("message", obj)
            content = msg.get("content", []) if isinstance(msg, dict) else []
            if not isinstance(content, list):
                continue
            for c in content:
                if not (isinstance(c, dict) and c.get("type") == "tool_use"):
                    continue
                cmd = str((c.get("input") or {}).get("command", ""))
                if not cmd:
                    continue
                seit_owner += len(_CREATE.findall(cmd))
                repos.update(m.split("/")[-1] for m in _REPO_FLAG.findall(cmd))
                prod = prod or bool(_PROD.search(cmd))

    kontext.update(repos=len(repos), prs_seit_owner=seit_owner, prod=int(prod))
    return kontext


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

    ktx = messe_kontext(Path(tp))

    # Treffer mitschreiben, BEVOR gemeldet wird — ohne Spur laesst sich die
    # Kalibrierung ueber mehrere Sitzungen weder belegen noch bestreiten
    # (#1640; Realfall 2026-08-15: achtmal gefeuert, null Daten).
    gate_hits.notiere(
        GATE_HEADER["slug"],
        f"prs={prs} issues={issues} schwelle={budget} "
        f"repos={ktx['repos']} prs_seit_owner={ktx['prs_seit_owner']} "
        f"prod={ktx['prod']}",
        session=str(event.get("session_id", "")),
        modus=GATE_HEADER["mode"],
    )

    hinweis = (
        f"📦 Artefakt-Budget: {prs} PRs"
        + (f" + {issues} Issues" if issues else "")
        + f" in dieser Session (Schwelle {budget}); davon "
        f"{ktx['prs_seit_owner']} seit der letzten Nachricht des Menschen, "
        f"{ktx['repos']} Repo(s) beruehrt"
        + (", Prod-/Publish-Schritt dabei" if ktx["prod"] else "")
        + ". Scope-Checkpoint: ist das noch "
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
