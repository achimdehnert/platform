#!/usr/bin/env python3
"""Ueberfaellige Owner-Vorgaenge ohne Owner-Wort nach `warten` altern (V6, #3015 K4).

Warum es das gibt: Ein Vorgang im Bucket `owner`, dessen Frist verstrichen ist,
bleibt dort stehen — rot, aber unbewegt — solange niemand ihn anfasst. Am
2026-09-13 standen drei Vorgaenge seit dem 11./12.09. so da, ohne dass sich
etwas veraendert hatte. Aufschieben kostet nichts, solange die Frist nur eine
Farbe im Board ist.

Die Regel: `bucket == owner` UND `frist` ist ein ISO-Datum UND der Stichtag
liegt mindestens `--tage` (Default 7) danach UND seit der Frist kam KEIN neuer
Verlaufseintrag in `notiz` — dann wandert der Vorgang nach `warten`. Die Frist
wird aufgehoben (nicht geloescht: der Grund nennt sie), `zustand` traegt das
Ueberfaellig-Etikett, ein Verlaufseintrag protokolliert den Schritt. Sichtbar,
nicht heimlich; umkehrbar per `--zurueck NR`.

Nie Personendaten in Ausgabe oder Code — nur Nummern, Daten, Bucket-Namen
(Charta Art. 2). Der Ledger bleibt unter `~/.claude/`, nie in diesem Repo.

Kommandos::

    python3 tools/mail_agent/alterung.py --pruefe [--stichtag YYYY-MM-DD] [--tage 7]
    python3 tools/mail_agent/alterung.py --schreibe [--stichtag YYYY-MM-DD] [--tage 7]
    python3 tools/mail_agent/alterung.py --zurueck NR
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from board import LEDGER, _verlaufseintrag, lade, vorgaenge_von  # noqa: E402

TOOL_VERSION = "alterung.py/1"

#: Trenner zwischen zwei Verlaufseintraegen — dieselbe Konvention wie
#: `ledger_kappen.py`/`faelligkeit.py`.
TRENNER = " | "

#: Jeder Verlaufseintrag beginnt mit seinem Datum (Aufgabenbeschreibung im
#: Ledger: `YYYY-MM-DD[ HH:MM] [EREIGNIS] (Quelle): …`).
_DATUM = re.compile(r"^(\d{4}-\d{2}-\d{2})")

DEFAULT_TAGE = 7


def letzter_eintrag(notiz: str | None) -> date | None:
    """Juengstes Datum unter allen Verlaufseintraegen von `notiz`; None wenn keiner lesbar ist."""
    juengstes: date | None = None
    for eintrag in str(notiz or "").split(TRENNER):
        treffer = _DATUM.match(eintrag.strip())
        if not treffer:
            continue
        try:
            tag = date.fromisoformat(treffer.group(1))
        except ValueError:
            continue
        if juengstes is None or tag > juengstes:
            juengstes = tag
    return juengstes


def ist_kandidat(vorgang: dict, stichtag: date, tage: int) -> bool:
    """Prueft die Alterungsregel fuer EINEN Vorgang, ohne ihn zu veraendern."""
    if vorgang.get("bucket") != "owner":
        return False
    frist = vorgang.get("frist")
    if not frist:
        return False
    try:
        frist_datum = date.fromisoformat(str(frist)[:10])
    except ValueError:
        return False
    if (stichtag - frist_datum).days < tage:
        return False
    letztes = letzter_eintrag(vorgang.get("notiz"))
    if letztes is not None and letztes > frist_datum:
        return False
    return True


def altern(ledger: dict, stichtag: date, tage: int = DEFAULT_TAGE) -> list[dict]:
    """Kernfunktion: wendet die Alterungsregel auf ALLE Vorgaenge an.

    Mutiert die getroffenen Vorgaenge im `ledger` direkt (wie `board.py`s
    Kernfunktionen) und gibt sie zusaetzlich zurueck, damit CLI und Tests sie
    ohne zweiten Durchlauf melden koennen. Zweiter Lauf mit demselben Stichtag
    aendert nichts mehr (frist ist dann None — kein Kandidat mehr).
    """
    geaendert: list[dict] = []
    for vorgang in vorgaenge_von(ledger):
        if not ist_kandidat(vorgang, stichtag, tage):
            continue
        frist_alt = str(vorgang.get("frist"))
        vorgang["bucket"] = "warten"
        vorgang["frist"] = None
        vorgang["frist_grund"] = (
            f"Owner-Wort ausstehend seit {frist_alt}; automatisch nach warten "
            "(alterung.py)"
        )
        vorgang["zustand"] = f"ueberfaellig-seit-{frist_alt}-owner-wort-offen"
        _verlaufseintrag(
            vorgang,
            f"{stichtag.isoformat()} (alterung.py): {tage} Tage ueberfaellig ohne "
            f"Owner-Wort — nach warten verschoben, Frist {frist_alt} aufgehoben. "
            "Offen: Owner-Wort.",
        )
        geaendert.append(vorgang)
    return geaendert


def zurueck_vorgang(ledger: dict, nr: int, stichtag: date) -> tuple[dict, str]:
    """Rueckweg zu `altern()`: Vorgang #nr wieder nach `owner`, sichtbar vermerkt.

    Die Frist wird NICHT aus dem `frist_grund` rekonstruiert — ein Owner-Wort
    setzt naeher am Fall eine neue, passende Frist (`board.py --frist`); eine
    automatisch zurueckgerechnete waere nur geraten. Rueckgabe `(vorgang,
    status)`: `"zurueck"` beim ersten Lauf, `"bereits"` wenn der Vorgang schon
    bei `owner` war (dann unveraendert — ein zweiter Lauf darf nichts kaputt
    machen). Unbekannte Nummer wirft `ValueError`.
    """
    for vorgang in vorgaenge_von(ledger):
        if vorgang.get("nr") != nr:
            continue
        if vorgang.get("bucket") == "owner":
            return vorgang, "bereits"
        vorgang["bucket"] = "owner"
        vorgang["frist"] = None
        vorgang["frist_grund"] = "Owner hat reaktiviert (alterung.py --zurueck)"
        _verlaufseintrag(
            vorgang,
            f"{stichtag.isoformat()} (alterung.py --zurueck): Owner hat "
            "reaktiviert — zurueck nach owner.",
        )
        return vorgang, "zurueck"
    raise ValueError(f"Vorgang #{nr} gibt es nicht.")


def _kandidaten_zeile(vorgang: dict, stichtag: date) -> str:
    frist = str(vorgang.get("frist"))
    frist_datum = date.fromisoformat(frist[:10])
    ueberfaellig = (stichtag - frist_datum).days
    letztes = letzter_eintrag(vorgang.get("notiz"))
    return (
        f"  #{vorgang.get('nr')} '{vorgang.get('kurz')}': frist={frist}, "
        f"{ueberfaellig} Tage ueberfaellig, letzter Eintrag={letztes.isoformat() if letztes else 'keiner'}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pruefe", action="store_true", help="Trockenlauf: Kandidaten listen"
    )
    parser.add_argument(
        "--schreibe",
        action="store_true",
        help="Alterung ausfuehren und Ledger schreiben",
    )
    parser.add_argument(
        "--zurueck", type=int, metavar="NR", help="Vorgang #NR zurueck nach 'owner'"
    )
    parser.add_argument(
        "--stichtag",
        metavar="YYYY-MM-DD",
        help="Bezugsdatum statt heute (reproduzierbar)",
    )
    parser.add_argument(
        "--tage",
        type=int,
        default=DEFAULT_TAGE,
        help=f"Ueberfaellig-Schwelle (Default {DEFAULT_TAGE})",
    )
    parser.add_argument("--ledger", metavar="DATEI", help="anderer Ledger-Pfad")
    args = parser.parse_args(argv)

    ledger_pfad = Path(args.ledger) if args.ledger else LEDGER
    ledger = lade(ledger_pfad, {"vorgaenge": []})

    if args.zurueck is not None:
        heute = date.today()
        try:
            vorgang, status = zurueck_vorgang(ledger, args.zurueck, heute)
        except ValueError as fehler:
            parser.error(str(fehler))
        if status == "bereits":
            print(
                f"#{args.zurueck} '{vorgang.get('kurz')}': war schon bei 'owner' — keine Aenderung."
            )
            return 0
        ledger_pfad.write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            f"#{args.zurueck} '{vorgang.get('kurz')}': bucket={vorgang.get('bucket')!r}"
        )
        return 0

    stichtag = date.fromisoformat(args.stichtag) if args.stichtag else date.today()

    if args.pruefe:
        kandidaten = [
            v for v in vorgaenge_von(ledger) if ist_kandidat(v, stichtag, args.tage)
        ]
        if not kandidaten:
            print(
                f"Keine Kandidaten (Stichtag {stichtag.isoformat()}, {args.tage} Tage)."
            )
            return 0
        print(
            f"{len(kandidaten)} Kandidat(en) (Stichtag {stichtag.isoformat()}, {args.tage} Tage):"
        )
        for vorgang in kandidaten:
            print(_kandidaten_zeile(vorgang, stichtag))
        return 0

    if args.schreibe:
        geaendert = altern(ledger, stichtag, args.tage)
        if not geaendert:
            print(
                f"Keine Aenderung (Stichtag {stichtag.isoformat()}, {args.tage} Tage)."
            )
            return 0
        ledger_pfad.write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        for vorgang in geaendert:
            print(f"  #{vorgang.get('nr')} '{vorgang.get('kurz')}': owner -> warten")
        print(f"{len(geaendert)} Vorgang/Vorgaenge nach 'warten' verschoben.")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
