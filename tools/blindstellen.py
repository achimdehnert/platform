#!/usr/bin/env python3
"""Blindstellen-Melder — Phasen, die GRÜN melden können, ohne geprüft zu haben.

Warum das existiert (gemessen am 2026-08-23, nicht vermutet):
`0.7.4 prio-referenzen` meldete PASS mit der Notiz „keine Prio-Liste im Handover —
nichts zu pruefen", während dieselbe Datei sieben Prio-Zeilen trug. Der Parser des
Checks kennt nur nummerierte Listen (`^\\d+\\.\\s`), die Liste stand als Tabelle da.
Folge: die Prio „kd.iil.pet-Nachverify" stand **19 Tage** als offen in der Liste,
obwohl sie seit dem Ingest vom 2026-08-04 erledigt war — gefunden hat das ein Mensch,
nicht der Melder, der genau dafür gebaut wurde.

Der strukturelle Fehler ist nicht der Parser, sondern die Übersetzung:
**SKIP wird als PASS verbucht.** „Konnte nicht prüfen" und „geprüft, alles gut" landen
in derselben grünen Zelle der Summary-Tabelle. Ein Melder, der nicht laufen konnte,
ist von einem, der sauber durchlief, nicht mehr zu unterscheiden.

Was dieses Werkzeug tut: es liest `tools/session_start_checks.sh` und listet jeden
`record`-Aufruf, der PASS meldet, obwohl seine eigene Notiz eine Nicht-Prüfung
beschreibt. Es urteilt nicht über die Phase — es zeigt, wo Grün keine Aussage ist.

Advocatus Diabolus gegen dieses Werkzeug selbst: ein Melder über Melder ist genau
die Meta-Ebene, an der die Flotte ohnehin leidet, und er könnte selbst blind sein.
Deshalb ist er **laut**, wenn er nichts findet: parst er null `record`-Aufrufe, ist das
ein Fehler (Exit 2), keine Erfolgsmeldung. Ein Werkzeug, das bei kaputtem Parser „0
Blindstellen" meldet, wäre die Krankheit, die es behandeln soll.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# record "<phase>" "<status>" "<note>"
RECORD_RE = re.compile(r'record\s+"([^"]+)"\s+"([A-Z]+)"\s+"(.*)"\s*(?:;;)?\s*$')

# Formulierungen, die eine NICHT durchgeführte Prüfung beschreiben.
# Bewusst eng gehalten: jede Erweiterung ist eine Behauptung darüber, was „nicht
# geprüft" heißt, und gehört belegt — nicht geraten.
BLIND_RE = re.compile(
    r"nichts zu pruefen|nichts zu prüfen|nicht pruefbar|nicht prüfbar"
    r"|uebersprungen|übersprungen|by design"
    r"|kein[e]? .{0,40}(vorhanden|gefunden|konfiguriert)"
    r"|ohne .{0,30}\.(yaml|yml|json|md)",
    re.I,
)


def scan(pfad: Path) -> tuple[list[dict], int]:
    treffer: list[dict] = []
    gesamt = 0
    for nr, zeile in enumerate(pfad.read_text(encoding="utf-8").splitlines(), 1):
        m = RECORD_RE.search(zeile.strip())
        if not m:
            continue
        gesamt += 1
        phase, status, notiz = m.group(1), m.group(2), m.group(3)
        if status != "PASS":
            continue
        if BLIND_RE.search(notiz):
            treffer.append({"zeile": nr, "phase": phase, "notiz": notiz})
    return treffer, gesamt


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--datei",
        default=str(Path(__file__).with_name("session_start_checks.sh")),
        help="zu prüfende Runner-Datei",
    )
    args = ap.parse_args(argv)

    pfad = Path(args.datei)
    if not pfad.is_file():
        print(f"FEHLER: {pfad} nicht gefunden", file=sys.stderr)
        return 2

    treffer, gesamt = scan(pfad)

    # Selbstvalidierung: nichts geparst = kaputter Parser, nicht „alles sauber".
    if gesamt == 0:
        print(
            f"FEHLER: 0 record-Aufrufe in {pfad.name} geparst — der Melder ist blind, "
            "nicht die Datei sauber.",
            file=sys.stderr,
        )
        return 2

    print(f"Blindstellen-Melder · {pfad.name} · {gesamt} record-Aufrufe geparst")
    if not treffer:
        print("RESULT: OK — kein PASS beschreibt eine Nicht-Pruefung.")
        return 0

    breite = max(len(t["phase"]) for t in treffer)
    print()
    for t in treffer:
        notiz = t["notiz"] if len(t["notiz"]) <= 64 else t["notiz"][:61] + "..."
        print(f"  Z.{t['zeile']:<5} {t['phase']:<{breite}}  {notiz}")
    print()
    print(
        f"RESULT: BLINDSTELLEN — {len(treffer)} von {gesamt} record-Aufrufen melden PASS "
        "fuer eine Pruefung, die nicht stattfand."
    )
    print(
        "Diese Zellen sind in der Summary-Tabelle nicht von echtem Gruen zu "
        "unterscheiden. Fix-Richtung: eigener Status SKIP statt PASS."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
