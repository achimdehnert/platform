#!/usr/bin/env python3
"""Claude Code Stop hook — Deferred-Item-Tracking-Scanner (Welle 1, KONZ-038 D2).

Slug `deferred-item-no-tracking-issue` (×8, retro_kpis): bewusst aufgeschobene
Arbeit ("vertagt", "nicht Teil dieses PRs", "separater PR") bekommt im SELBEN
Turn ein Tracking-Artefakt (GitHub-Issue oder Ledger-/KONZ-Zeile), sonst gilt
sie als nicht existent — "steht im PR-Text" zählt NICHT (CLAUDE.md-Hausregel;
risiko_debt ist mit 2.54 die schwächste Retro-Score-Dimension, ungetrackte
Reste sind der Haupttreiber).

Vier-Wege-Prüfung (KONZ-038 §5.7): Werkzeug statt N-ter Regel-Formulierung —
die Regel existierte, wurde ×8 verletzt; dieser Hook macht sie ausführbar.

GATE-HEADER (KONZ-038 D8, maschinenlesbar):
mode=advisory BEWUSST: neue Muster-Familie ohne False-Positive-Baseline; nach
SUGGEST-first-Disziplin (repo-health) erst ein Kalibrierfenster (bis 16.08.),
blocking erst nach 0-FP-Fenster + eigenem PR.

Contract: identisch zum evidence_claim_scanner — Stop-Event auf stdin, IMMER
Exit 0, advisory via hookSpecificOutput.additionalContext.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_claim_scanner import _last_turn_blocks  # noqa: E402

GATE_HEADER = {
    "slug": "deferred-item-no-tracking-issue",
    "mode": "advisory",
    "owner": "achim",
    "last_drill_pass": "2026-08-02",
    "evidence": "tools/claude-hooks/tests/test_deferred_item_scanner.py",
}

# Explizite Vertagungs-Erklärungen — eng gehalten (Präzision vor Recall):
# "bleibt offen" u. ä. Status-Prosa feuert bewusst NICHT (zu häufig in Boards).
DEFERRAL_PATTERNS = re.compile(
    r"\bbewusst\s+(?:ausgelassen|aufgeschoben|(?:zur(?:ü|ue)ck)gestellt|vertagt|"
    r"(?:ü|ue)bersprungen|weggelassen)\b"
    r"|\b(?:vertagt|aufgeschoben|zur(?:ü|ue)ckgestellt)\b"
    r"|\bnicht\s+Teil\s+dieses\s+(?:PRs?|Turns?|Scopes?|Pakets?)\b"
    r"|\bin\s+einem\s+(?:separaten|eigenen|sp(?:ä|ae)teren)\s+(?:PR|Issue)\b"
    r"|\bals\s+Follow-?up\b|\bFolge-(?:PR|Issue|Refactor)\s+(?:n(?:ö|oe)tig|folgt|sp(?:ä|ae)ter)\b"
    r"|\bsp(?:ä|ae)ter\s+(?:nachziehen|nachholen|nachr(?:ü|ue)sten|erledigen)\b"
    r"|\bziehe\s+ich\s+sp(?:ä|ae)ter\s+nach\b"
    r"|\bout\s+of\s+scope\s+for\s+this\b|\bdeferred\s+(?:to|for)\b"
    r"|\bleft\s+for\s+(?:later|a\s+follow-?up)\b|\bin\s+a\s+(?:separate|follow-?up)\s+PR\b"
    # Retro 287b23 #6: "verschieben" als Vertagungs-Verb fehlte (FN-Klasse). Eng:
    # nur Ich-Form/Arbeits-Kontext, damit "der Termin wurde verschoben" nicht feuert.
    r"|\bverschiebe\s+ich\s+(?:auf|in|nach)\b"
    r"|\bauf\s+(?:sp(?:ä|ae)ter|die\s+n(?:ä|ae)chste\s+Session|morgen)\s+verschoben\b",
    re.I,
)

# Tracking-Artefakt im SELBEN Turn: Issue-Op, Task-Anlage, oder Schreib-Zugriff
# auf eine Tracking-Fläche (KONZ/Ledger/Handover). Ein blosser Issue-LINK im
# Text zählt nicht — der Rule-Wortlaut verlangt das Artefakt, nicht die Erwähnung.
_TRACKING_CMD = re.compile(
    r"gh\s+issue\s+(?:create|comment|edit)|gh\s+pr\s+comment", re.I
)
_TRACKING_FILE = re.compile(
    r"KONZ-[^\s/]*\.md|ledger|AGENT_HANDOVER|docs/konzepte/", re.I
)
_TRACKING_TOOLS = {"TaskCreate"}
# Retro 287b23 #6: Tracking läuft auch über MCP-Tools, nicht nur gh-CLI (FP-Klasse).
_TRACKING_TOOL_PREFIXES = (
    "mcp__github__create_issue",
    "mcp__github__add_issue_comment",
    "mcp__github__update_issue",
)


def _has_tracking_artifact(evidence_text: str, tool_inputs: list) -> bool:
    if _TRACKING_CMD.search(evidence_text):
        return True
    for name, inp in tool_inputs:
        if name in _TRACKING_TOOLS or str(name).startswith(_TRACKING_TOOL_PREFIXES):
            return True
        if name in ("Write", "Edit") and isinstance(inp, dict):
            if _TRACKING_FILE.search(str(inp.get("file_path", ""))):
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
    m = DEFERRAL_PATTERNS.search(assistant_text)
    if not m:
        return 0
    if _has_tracking_artifact(evidence_text, tool_inputs):
        return 0

    msg = (
        "📌 deferred-item check: dieser Turn erklärt Arbeit für vertagt/ausgelassen "
        f"(Marker: '{m.group(0)}'), enthält aber kein Tracking-Artefakt. Hausregel: "
        "Bewusst Ausgelassenes bekommt im SELBEN Turn ein GitHub-Issue oder eine "
        "Ledger-/KONZ-Zeile mit Link — 'steht im PR-Text' zählt nicht. Billigste "
        "Aktion: `gh issue create` oder Kommentar auf dem passenden bestehenden Issue. "
        "(Gate deferred-item-no-tracking-issue, KONZ-038 Welle 1; advisory-Kalibrierung.)"
    )
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": msg}}
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
