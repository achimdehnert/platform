#!/usr/bin/env python3
"""PreToolUse(Bash) gate — blockt `gh issue|pr edit` mit leerer oder ungeprüfter Body-Datei.

GATE_HEADER (KONZ-038 D8):
  "slug": "gh-body-file-leer-ueberschrieben"
  "mode": "blocking"
  "owner": "achim"
  "last_drill_pass": "2026-09-14"
  "evidence": "tools/claude-hooks/tests/test_block_empty_body_file.py"

Hintergrund: Retro `session-retro-2026-09-14-apo-hub-kbiAvn-incr.md` Befund #6.
Ein Read-modify-write des Issue-Bodys lief im Scratchpad:
`gh issue view 125 … > i125.md && python3 … ` und in der Folgezeile
`gh issue edit 125 --body-file i125.md`. Das `view` scheiterte (kein Git-Repo,
kein `-R`), die Datei blieb leer, die Folgezeile hing an keinem `&&` und schrieb
den leeren Inhalt ins Issue — zweimal (apo-hub#125, userContentEdits 14:33:20Z
und 14:33:31Z). GitHub prüft `--body-file` nicht auf Leere.

Warum der Hook den Befehlstext liest und nicht nur die Datei: Zum Zeitpunkt von
PreToolUse lag `i125.md` noch mit dem ALTEN, vollen Inhalt auf Platte — erst der
Befehl selbst hat sie geleert. Eine reine Dateiprüfung hätte den Realfall
durchgelassen. Deshalb zwei Regeln:

  1. Taucht die Body-Datei im Befehl VOR dem `edit` auf (sie wird also im selben
     Befehl erzeugt oder verändert), muss das `edit` an ihr letztes Auftauchen
     ausschließlich über `&&` gekoppelt sein — oder, wenn dazwischen `;`, ein
     Zeilenumbruch oder `||` steht (etwa nach einem Heredoc), direkt vor dem `edit`
     ein Leere-Guard `test -s <datei>` / `[ -s <datei> ]` / `[[ -s <datei> ]]`,
     der selbst nur über `&&` am `edit` hängt. Durchgehende `&&`-Ketten passieren:
     scheitert das Erzeugen, läuft das `edit` gar nicht (Fehlalarm-Probe aus dem
     Realfall-Transkript 14:17:07Z).
  2. Sonst: liegt die Datei (ohne Shell-Variablen im Pfad) vor und ist kleiner als
     MIN_BYTES, wird geblockt.

Zusätzlich blockt ein leerer Inline-Body (`--body ""`, `-b ''`).

FAIL-OPEN: kein JSON, kein `gh … edit`, Pfad mit `$`-Variable ohne Erzeugung im
Befehl, Body von stdin (`-`) → exit 0. Die Grenze ist bewusst: der Hook fängt die
Familie „Datei im selben Befehl gebaut, Schreiben nicht an ihren Erfolg gekoppelt",
nicht jede denkbare leere Eingabe.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SLUG = "gh-body-file-leer-ueberschrieben"
MIN_BYTES = 20

_EDIT = re.compile(r"\bgh\s+(?:issue|pr)\s+edit\b")
_BODY_FILE = re.compile(r"(?:--body-file|-F)(?:\s+|=)(\"[^\"]*\"|'[^']*'|\S+)")
_LEERER_BODY = re.compile(r"(?:--body|-b)(?:\s+|=)(?:\"\"|'')(?=\s|$)")


def _ohne_quotes(wert: str) -> str:
    if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "\"'":
        return wert[1:-1]
    return wert


def _edit_abschnitte(kommando: str):
    """(Start des edit-Aufrufs, Text bis zum nächsten Trenner) je `gh … edit`."""
    for treffer in _EDIT.finditer(kommando):
        rest = kommando[treffer.start() :]
        ende = re.search(r"&&|\|\||;|\n|\|", rest)
        yield treffer.start(), rest[: ende.start()] if ende else rest


def _guard_direkt_davor(kommando: str, edit_start: int, datei: str) -> bool:
    davor = kommando[:edit_start]
    guard = re.compile(
        r"(?:test\s+-s\s+|\[\[?\s+-s\s+)(?:\"|')?" + re.escape(datei) + r"(?:\"|')?"
    )
    letzte = None
    for letzte in guard.finditer(davor):
        pass
    if letzte is None:
        return False
    zwischen = davor[letzte.end() :]
    return not re.search(r";|\n|\|\|", zwischen)


def entscheide(kommando: str) -> str | None:
    """Grund für ein deny oder None (durchlassen)."""
    for start, aufruf in _edit_abschnitte(kommando):
        if _LEERER_BODY.search(aufruf):
            return 'leerer Inline-Body (`--body ""`) würde den Text löschen.'
        for roh in _BODY_FILE.findall(aufruf):
            datei = _ohne_quotes(roh)
            if datei == "-":
                continue
            name = os.path.basename(datei)
            zuletzt = kommando.rfind(name, 0, start) if name else -1
            if zuletzt >= 0:
                zwischen = kommando[zuletzt + len(name) : start]
                verkettet = not re.search(r";|\n|\|\|", zwischen)
                if not verkettet and not _guard_direkt_davor(kommando, start, datei):
                    return (
                        f"`{datei}` wird im selben Befehl erzeugt, das `edit` hängt aber nicht "
                        f"an `test -s {datei} &&` — scheitert das Erzeugen, landet eine leere "
                        "Datei im Issue/PR."
                    )
                continue
            if "$" in datei:
                continue
            pfad = Path(os.path.expanduser(datei))
            if pfad.is_file() and pfad.stat().st_size < MIN_BYTES:
                return f"`{datei}` ist leer bzw. kleiner als {MIN_BYTES} Byte."
    return None


def main() -> int:
    try:
        daten = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    kommando = (daten.get("tool_input") or {}).get("command") or ""
    if not _EDIT.search(kommando):
        return 0
    grund = entscheide(kommando)
    if grund is None:
        return 0
    try:
        import gate_hits

        gate_hits.notiere(
            SLUG,
            "gh edit body",
            beleg=kommando[:200],
            session=daten.get("session_id", ""),
            modus="blocking",
        )
    except Exception:  # noqa: BLE001 — Protokoll darf den Hook nie stören
        pass
    antwort = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"Leerer-Body-Guard (Retro kbiAvn #6): {grund} So wurde apo-hub#125 am "
                "2026-09-14 zweimal geleert. Lesen, Ändern und Schreiben in EINE &&-Kette, "
                "`-R owner/repo` außerhalb eines Repos, und direkt vor dem edit "
                "`test -s <datei> &&`."
            ),
        }
    }
    print(json.dumps(antwort, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
