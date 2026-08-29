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
SUGGEST-first-Disziplin (repo-health) erst ein Kalibrierfenster (2026-08-15 bis
2026-08-29), blocking erst nach 0-FP-Fenster + eigenem PR.

Fenster neu datiert am 2026-08-15 (Owner-Freigabe, #1640): das erste
(02.08.–16.08.) hat nichts gemessen. Alle 212 protokollierten Treffer stammten
aus `pytest` — die Drills schrieben über `gate_hits.notiere()` in das echte
Protokoll, kein einziger Treffer kam aus einer Sitzung. Gesperrt mit #1986; die
Zählung beginnt ab dessen Merge neu.

Ein Fenster OHNE echte Treffer qualifiziert NICHT für blocking — „0 Fehlalarme"
wäre dann vakuum wahr. Vorrangig ist deshalb die Recall-Frage: warum feuerte ein
Gate mit ×8-Regelverletzung in fünf arbeitsreichen Tagen kein einziges Mal?

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
    r"|\bauf\s+(?:sp(?:ä|ae)ter|die\s+n(?:ä|ae)chste\s+Session|morgen)\s+verschoben\b"
    # Retro 9d861a #2 (2026-08-16): ZWEITE Instanz derselben FN-Klasse. Der reale
    # Wortlaut war „ist hier bewusst nicht mitgemacht" — ein Aufschub in
    # VERNEINUNGSFORM, den die Verb-Aufzaehlung oben nicht kannte. Der Befund
    # (Konsolidierung zweier Befund-Gedaechtnisse) blieb dadurch ohne
    # Tracking-Artefakt, obwohl genau dieser Scanner dafuer existiert. Gefunden
    # nur, weil ein Retro den Turn-Text gegen das Muster replayte — nicht vom
    # Scanner selbst.
    #
    # Bewusst eng: nur mit vorangehendem „bewusst|absichtlich|hier", damit ein
    # blosses „das habe ich nicht mitgemacht" (Bericht ueber Fremdes) nicht feuert.
    r"|\b(?:bewusst|absichtlich|hier)\s+nicht\s+"
    r"(?:mitgemacht|mitgezogen|mitgenommen|mitgeliefert|angefasst)\b",
    re.I,
)

# --- Zweite Trefferklasse: die Board-Zeile ---------------------------------
#
# Retro e70d11 (2026-08-28): drei in Prod gemessene Defekte -- Dokument-Dubletten,
# zwei PDFs mit null Zeichen bei fetch_status=ok, ein falsches Quell-Etikett --
# blieben ohne Tracking-Artefakt und existierten nur im Gespraechsverlauf. Der
# Scanner schwieg, und zwar zu Recht nach seinem damaligen Wortlaut: die Zeilen
# lauteten
#
#     | 4 | Dubletten | a-hub | — | 🟢 Befund | fixen (ich) |
#
# also OHNE jedes Vertagungs-Verb. Ein Befund, der offen im Board steht, IST die
# haeufigste Form aufgeschobener Arbeit in diesem Setup -- er sagt nur nicht
# "vertagt", sondern zeigt es. Sechster Rueckfall nach Gate-Bau (gate_wirkung.py).
#
# Bewusst eng, drei Bedingungen gleichzeitig, sonst feuert jedes Statusboard:
#   (a) offener Status-Marker (kein ✅),
#   (b) ein Wort mit Befund-Charakter,
#   (c) KEIN Anker in der Zeile -- weder URL noch #<nummer>.
_BOARD_OFFEN = re.compile(r"[🟢🔵🟡⛔]")
_BOARD_ERLEDIGT = re.compile(r"✅")
_BOARD_BEFUND_WORT = re.compile(
    r"\bBefund\b|\bDefekt\b|\bfehlt\b|\bfalsch\b|\bkaputt\b|\bDublette\b"
    r"|\bLeck\b|\bbricht\b|\bschl(?:ä|ae)gt\s+fehl\b|\bungetrackt\b",
    re.I,
)
_BOARD_ANKER = re.compile(r"https?://|#\d+")


def _board_befund_ohne_anker(text: str) -> str | None:
    """Die erste Board-Zeile, die einen offenen Befund ohne Anker nennt."""
    for zeile in text.splitlines():
        roh = zeile.strip()
        # Tabellenzeile ODER nummerierte Board-Zeile ("- **[12]** …" / "3. 🟢 …").
        ist_zeile = (roh.startswith("|") and roh.count("|") >= 4) or bool(
            re.match(r"^(?:[-*]|\d+\.)\s", roh)
        )
        if not ist_zeile:
            continue
        if _BOARD_ERLEDIGT.search(roh) or not _BOARD_OFFEN.search(roh):
            continue
        if not _BOARD_BEFUND_WORT.search(roh):
            continue
        if _BOARD_ANKER.search(roh):
            continue
        return roh[:120]
    return None


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
    marker = m.group(0) if m else _board_befund_ohne_anker(assistant_text)
    aus_board = m is None and marker is not None
    if not marker:
        return 0
    if _has_tracking_artifact(evidence_text, tool_inputs):
        return 0

    # Treffer mitschreiben, bevor gemeldet wird: ohne Spur laesst sich die
    # FP-Kalibrierung (KONZ-038 D2) spaeter weder belegen noch bestreiten.
    gate_hits.notiere(
        "deferred-item-no-tracking-issue",
        marker,
        turn=assistant_text,
        session=event.get("session_id", ""),
        modus="advisory",
    )

    was = (
        "nennt im Board einen offenen Befund ohne Anker"
        if aus_board
        else "erklärt Arbeit für vertagt/ausgelassen"
    )
    msg = (
        f"📌 deferred-item check: dieser Turn {was} "
        f"(Marker: '{marker}'), enthält aber kein Tracking-Artefakt. Hausregel: "
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
