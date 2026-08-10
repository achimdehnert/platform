#!/usr/bin/env python3
"""Gate: aufgeschobene Arbeit im PR-Text braucht einen Anker.

Vier gate-pflichtige Retro-Muster beschreiben denselben Vorgang aus vier
Blickwinkeln — `deferred-item-no-tracking-issue`, `workaround-without-tracking-anchor`,
`planned-phase-no-issue`, `tracking-doc-stale-after-new-occurrence`. Sie sind der
direkte Treiber dafuer, dass `risiko_debt` ueber 60 Retro-Messungen die
schwaechste Dimension ist (Ø 2,55).

Die Hausregel dazu lautet: bewusst Ausgelassenes bekommt im SELBEN Zug ein
Tracking-Artefakt; der PR-Text zaehlt ausdruecklich NICHT als Tracking. Dieser
Check erzwingt genau das — er liest den PR-Text, sucht nach Aufschub-Sprache und
verlangt in ihrer Naehe eine Issue-Referenz.

Bewusst eng gehalten: nur Formulierungen, die eine Auslassung ANKUENDIGEN, nicht
jedes Vorkommen von "offen". Ein Gate mit Fehlalarmen wird umgangen statt befolgt.

Exit: 0 = sauber oder nur Warnung, 1 = Fund im --block-Modus, 2 = Werkzeugfehler.
"""

from __future__ import annotations

import argparse
import re
import sys

# Maschinenlesbarer Kopf (KONZ-038 D8) — von tools/gate_drill_check.py gelesen und
# gegen docs/governance/gate-registry.json abgeglichen. Ohne Kopf verrottet die
# Registry still; ohne Registry-Eintrag drillt das Gate niemand.
#
# `covers` ist der Grund, warum dieses Gate existiert: EIN Mechanismus deckt vier
# gate-pflichtige Retro-Slugs ab, statt vier Einzelgates zu bauen (Empfehlung aus
# platform#1650). `deferred-item-no-tracking-issue` traegt zusaetzlich ein eigenes
# Gate (deferred_item_scanner.py, Session-Kontext) — dieses hier greift im PR-Text.
GATE_HEADER = {
    "slug": "aufschub-anker",
    "mode": "advisory",  # blocking erst nach 0-FP-Kalibrierfenster, s. Registry-frozen_note
    "owner": "achim",
    "last_drill_pass": "2026-08-10",
    "evidence": "tools/tests/test_deferral_anchor_check.py",
    "covers": [
        "workaround-without-tracking-anchor",
        "planned-phase-no-issue",
        "tracking-doc-stale-after-new-occurrence",
        "deferred-item-no-tracking-issue",
    ],
}

# Wendungen, die eine Auslassung ankuendigen. Positivliste — Fliesstext, der
# zufaellig "offen" enthaelt, soll NICHT feuern.
AUFSCHUB = re.compile(
    r"(nicht enthalten|nicht Teil dieses PR|nicht in diesem PR|bewusst ausgelassen"
    r"|bewusst nicht|folgt separat|kommt separat|in einem Folge-PR|Folgearbeit"
    r"|spaeter nachziehen|später nachziehen|bleibt offen|noch offen"
    r"|entscheidet der Owner separat|vertagt|Restschuld|Restarbeit)",
    re.IGNORECASE,
)

# Ein Anker ist eine Issue-Referenz — nicht bloss eine PR-Nummer.
ANKER = re.compile(
    r"(#\d+|(?:Refs|Closes|Fixes|Tracked in|getrackt (?:in|als))\s*[:#]?\s*\S+"
    r"|https://github\.com/[\w.-]+/[\w.-]+/issues/\d+)",
    re.IGNORECASE,
)

# Wie viele Zeilen um die Fundstelle als "Naehe" gelten.
FENSTER = 4


def finde_ankerlose_stellen(text: str, fenster: int = FENSTER) -> list[tuple[int, str]]:
    """(Zeilennummer, Zeile) je Aufschub-Stelle ohne Anker in der Naehe."""
    zeilen = text.splitlines()
    funde: list[tuple[int, str]] = []
    for i, zeile in enumerate(zeilen):
        if not AUFSCHUB.search(zeile):
            continue
        von, bis = max(0, i - fenster), min(len(zeilen), i + fenster + 1)
        if ANKER.search("\n".join(zeilen[von:bis])):
            continue
        funde.append((i + 1, zeile.strip()))
    return funde


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--block", action="store_true", help="Exit 1 bei Fund")
    ap.add_argument("--fenster", type=int, default=FENSTER)
    ap.add_argument("datei", nargs="?", help="PR-Text; ohne Angabe von stdin")
    args = ap.parse_args(argv)

    try:
        if args.datei:
            with open(args.datei, encoding="utf-8") as f:
                text = f.read()
        else:
            text = sys.stdin.read()
    except OSError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2

    funde = finde_ankerlose_stellen(text, args.fenster)
    if not funde:
        print(
            "✅ Aufschub-Anker: jede angekuendigte Auslassung hat eine Issue-Referenz."
        )
        return 0

    kopf = "❌ Aufschub ohne Anker" if args.block else "⚠️  Aufschub ohne Anker"
    print(
        f"{kopf}: {len(funde)} Stelle(n) kuendigen Arbeit an, ohne ein Issue zu nennen:"
    )
    for nr, zeile in funde:
        print(f"  Zeile {nr}: {zeile[:110]}")
    print(
        "\nDer PR-Text zaehlt nicht als Tracking. Lege ein Issue an und nenne es in "
        "der Naehe der Stelle (`Refs #N`), oder streiche die Ankuendigung."
    )
    return 1 if args.block else 0


if __name__ == "__main__":
    sys.exit(main())
