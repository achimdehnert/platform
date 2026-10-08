#!/usr/bin/env python3
"""PreToolUse(Bash) gate — blockt Issue-/PR-Texte mit Aufschub ohne Anker beim Schreiben.

GATE_HEADER (KONZ-038 D8):
  "slug": "aufschub-anker"
  "mode": "blocking"
  "owner": "achim"
  "last_drill_pass": "2026-10-08"
  "evidence": "tools/claude-hooks/tests/test_block_aufschub_ohne_anker.py"

Hintergrund: platform#3859 M7 (Retro 767d40-incr Befund #2, Owner-Wort „M7
bauen“). Ein Kommentar in meiki-lra/meiki-hub#582 fuehrte unter „Bewusst
ausgelassen“ sechs Posten, fuenf ohne Issue. Das Gate aufschub-anker sah das
aus zwei Gruenden nicht:

  * Es sitzt als Workflow nur in platform und prueft dort PR-Texte. Kommentare
    und PRs in Ziel-Repos erreicht es nicht; der Close-Hook greift erst beim
    Schliessen eines Issues.
  * Es zaehlte je Abschnitt: ein Anker im ersten Posten deckte alle. Das ist in
    `deferral_anchor_check.finde_ankerlose_stellen` jetzt je Posten.

Dieser Hook sitzt deshalb am Moment des Schreibens, in jedem Repo:
`gh issue create|comment|edit` und `gh pr create|comment|edit` mit `--body`/`-b`
oder `--body-file`/`-F`. Er prueft den Text mit derselben Funktion wie das Werkzeug.

FAIL-OPEN: kein JSON, kein passender Befehl, Werkzeug nicht auffindbar,
Textdatei nicht lesbar, `-F -` (stdin), Parse-Fehler → exit 0.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from block_issue_close_without_anchor import lade_werkzeug  # noqa: E402

SLUG = "aufschub-anker"

_SCHREIBEN = re.compile(r"\bgh\s+(issue|pr)\s+(create|comment|edit)\b")
_TRENNER = {"&&", "||", ";", "|", "&"}
_BODY = ("-b", "--body")
_BODY_DATEI = ("-F", "--body-file")


def texte(kommando: str, cwd: str | None) -> list[tuple[str, str]]:
    """(Herkunft, Text) je `gh issue|pr create|comment|edit` mit Body im Befehl."""
    gefunden: list[tuple[str, str]] = []
    for treffer in _SCHREIBEN.finditer(kommando):
        try:
            woerter = shlex.split(kommando[treffer.end() :])
        except ValueError:
            continue
        herkunft = f"gh {treffer.group(1)} {treffer.group(2)}"
        i = 0
        while i < len(woerter):
            wort = woerter[i]
            if wort in _TRENNER:
                break
            wert = woerter[i + 1] if i + 1 < len(woerter) else ""
            if wort.startswith("--body=") or wort.startswith("--body-file="):
                wort, wert = wort.split("=", 1)
                i -= 1
            if wort in _BODY:
                gefunden.append((herkunft, wert))
                i += 2
                continue
            if wort in _BODY_DATEI:
                if wert and wert != "-":
                    pfad = Path(os.path.expanduser(wert))
                    if not pfad.is_absolute() and cwd:
                        pfad = Path(cwd) / pfad
                    try:
                        gefunden.append((f"{herkunft} -F {wert}", pfad.read_text()))
                    except (OSError, UnicodeDecodeError):
                        pass
                i += 2
                continue
            i += 1
    return gefunden


def entscheide(daten: dict, werkzeug=None) -> str | None:
    """Ablehnungsgrund oder None. `werkzeug` ist fuer Tests injizierbar."""
    kommando = (daten.get("tool_input") or {}).get("command") or ""
    if not _SCHREIBEN.search(kommando):
        return None
    stoff = texte(kommando, daten.get("cwd"))
    if not stoff:
        return None
    werkzeug = werkzeug or lade_werkzeug()
    if werkzeug is None:
        return None
    stellen = [
        f"{herkunft}, Zeile {nr}: {zeile}"
        for herkunft, text in stoff
        for nr, zeile in werkzeug.finde_ankerlose_stellen(text)
    ]
    if not stellen:
        return None
    liste = "\n".join(f"  - {s[:160]}" for s in stellen[:6])
    return (
        f"Aufschub-Anker (platform#3859 M7): {len(stellen)} Stelle(n) kuendigen "
        f"Folgearbeit ohne Issue an:\n{liste}\n"
        "Je Posten ein Issue anlegen und im Posten verlinken, oder ein Sammel-Issue "
        "vor dem ersten Posten nennen. Ein Anker deckt nur den Posten, in dem er steht."
    )


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    grund = entscheide(daten)
    if grund is None:
        return 0
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG,
            "gh issue/pr Text",
            beleg=((daten.get("tool_input") or {}).get("command") or "")[:200],
            session=daten.get("session_id", ""),
            modus="blocking",
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stören
        pass
    antwort = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": grund,
        }
    }
    print(json.dumps(antwort, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 — Hook darf nie die Sitzung blockieren
        sys.exit(0)
