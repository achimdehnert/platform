#!/usr/bin/env python3
"""Claude Code Stop hook — Scope-Checkpoint-Artefakt-Scanner (Welle 1, KONZ-038 D2).

Slug `scope-checkpoint-not-durably-recorded` (×10, retro_kpis): Der
Scope-Checkpoint (Hausregel: drittes Repo ODER Prod/Publish -> innehalten +
spiegeln) passiert im Chat und hinterlaesst kein durables Artefakt — spaetere
Sessions/Retros koennen nicht pruefen, ob und mit welchem Ergebnis
gecheckpointet wurde. Dies ist Option A aus Issue #1081 (Hook, automatisch);
Option B (reine Board-Konvention) waere dieselbe Merksatz-Gattung, deren
Wirkungslosigkeit die ×10 belegen.

Der Hook feuert, wenn der Turn-Text einen Scope-Checkpoint AUSSPRICHT, der Turn
aber kein durables Artefakt traegt (PR-/Issue-Kommentar oder Doku-Write).

GATE-HEADER (KONZ-038 D8, maschinenlesbar):
mode=advisory BEWUSST: neue Musterfamilie ohne False-Positive-Baseline
(SUGGEST-first-Disziplin); Kalibrierfenster 2026-08-15 bis 2026-08-29, blocking
erst nach 0-FP-Fenster per eigenem PR.

Fenster neu datiert am 2026-08-15 (Owner-Freigabe, #1640): das erste
(02.08.–16.08.) hat nichts gemessen. Alle 212 protokollierten Treffer stammten
aus `pytest` — die Drills schrieben über `gate_hits.notiere()` in das echte
Protokoll, kein einziger Treffer kam aus einer Sitzung. Gesperrt mit #1986; die
Zählung beginnt ab dessen Merge neu.

Ein Fenster OHNE echte Treffer qualifiziert NICHT für blocking — „0 Fehlalarme"
wäre dann vakuum wahr. Vorrangig ist deshalb die Recall-Frage: warum feuerte ein
Gate mit ×10-Regelverletzung in fünf arbeitsreichen Tagen kein einziges Mal?

Contract: identisch zum evidence_claim_scanner — Stop-Event auf stdin, IMMER
Exit 0, advisory via hookSpecificOutput.additionalContext.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate_hits  # noqa: E402  (haengt am sys.path oben)
from evidence_claim_scanner import _last_turn_blocks  # noqa: E402

GATE_HEADER = {
    "slug": "scope-checkpoint-not-durably-recorded",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-08-02",
    "evidence": "tools/claude-hooks/tests/test_scope_checkpoint_scanner.py",
}

# Der Checkpoint-Moment, wie er real formuliert wird (Hausregel-Wortlaut +
# beobachtete Varianten). Eng gehalten: blosse Erwaehnung eines dritten Repos
# in Prosa feuert nicht — es braucht die Spiegel-/Innehalte-Formulierung.
CHECKPOINT_PATTERNS = re.compile(
    r"Scope-Checkpoint"
    r"|\bScope\s+(?:ist\s+|war\s+)?(?:deutlich\s+|stark\s+)?(?:gewachsen|eskaliert|erweitert)\b"
    r"|\bRepos?\b[^.\n]{0,60}\bvon\s+deiner\s+urspr(?:ü|ue)nglichen\s+(?:Frage|Anfrage|Aufgabe)\b"
    r"|\bweiter\s+als\s+(?:die|der)\s+urspr(?:ü|ue)ngliche[nr]?\s+(?:Frage|Auftrag|Scope)\b"
    r"|\bist\s+das\s+noch\s+gewollt\b"
    r"|\bber(?:ü|ue)hren?\s+(?:wir\s+)?(?:jetzt\s+)?(?:ein\s+)?dritte[sn]?\s+Repo\b"
    r"|\berreichen?\s+(?:jetzt\s+)?(?:Prod|Produktion|einen\s+Prod-Schritt)\b",
    re.I,
)

# Durables Artefakt im selben Turn: PR-/Issue-Kommentar/-Anlage oder ein
# Schreibzugriff auf eine git-/board-getrackte Doku-Flaeche.
_DURABLE_CMD = re.compile(r"gh\s+(?:pr|issue)\s+(?:comment|create|edit)", re.I)
_DURABLE_FILE = re.compile(r"docs/|AGENT_HANDOVER|KONZ-|ledger|\.claude/boards/", re.I)
# Retro 287b23 #6 (Schwester-Lücke): auch MCP-Tools erzeugen durable Artefakte.
_DURABLE_TOOL_PREFIXES = (
    "mcp__github__create_issue",
    "mcp__github__add_issue_comment",
    "mcp__github__update_issue",
    "mcp__github__create_pull_request_review",
)


def _has_durable_artifact(evidence_text: str, tool_inputs: list) -> bool:
    if _DURABLE_CMD.search(evidence_text):
        return True
    for name, inp in tool_inputs:
        if str(name).startswith(_DURABLE_TOOL_PREFIXES):
            return True
        if name in ("Write", "Edit") and isinstance(inp, dict):
            if _DURABLE_FILE.search(str(inp.get("file_path", ""))):
                return True
    return False


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        return 0
    if event.get("stop_hook_active"):
        return 0
    transcript_path = event.get("transcript_path") or ""
    if not transcript_path:
        return 0

    assistant_text, evidence_text, tool_inputs = _last_turn_blocks(transcript_path)
    if not assistant_text:
        return 0
    m = CHECKPOINT_PATTERNS.search(assistant_text)
    if not m:
        return 0
    if _has_durable_artifact(evidence_text, tool_inputs):
        return 0

    # Treffer mitschreiben, bevor gemeldet wird: ohne Spur laesst sich die
    # FP-Kalibrierung (KONZ-038 D2) spaeter weder belegen noch bestreiten.
    gate_hits.notiere(
        "scope-checkpoint-not-durably-recorded",
        m.group(0),
        turn=assistant_text,
        session=event.get("session_id", ""),
        modus="advisory",
    )

    msg = (
        "🧭 scope-checkpoint check: dieser Turn spricht einen Scope-Checkpoint aus "
        f"(Marker: '{m.group(0)}'), traegt aber kein durables Artefakt. Hausregel + "
        "Retro-Gate: Checkpoint-Frage UND Owner-Antwort gehoeren als PR-/Issue-Kommentar "
        "oder Doku-Zeile festgehalten, sonst kann keine spaetere Session pruefen, was "
        "freigegeben wurde. Billigste Aktion: `gh pr comment`/`gh issue comment` mit dem "
        "Checkpoint-Wortlaut. (Gate scope-checkpoint-not-durably-recorded, KONZ-038 "
        "Welle 1, Option A aus #1081; advisory-Kalibrierung.)"
    )
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": msg}}
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
