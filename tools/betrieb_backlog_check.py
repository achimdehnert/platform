#!/usr/bin/env python3
"""K4 aus Auftrag #3015: Backlog-Vorschlag ohne Gegenrede wird abgewiesen.

Jede Betriebsakte fuehrt einen Abschnitt „Verbesserungs-Backlog" mit einer
Tabelle `| # | Vorschlag | Advocatus Diaboli | Out of the Box | Anker |`.
Das Kriterium K4 verlangt, dass **vor dem Bau** zwei Pflichtabschnitte
stehen — das staerkste Gegenargument (Advocatus Diaboli) und eine
Alternative ausserhalb des heutigen Bauplans (Out of the Box) — sonst ist
der Vorschlag nur eine Idee, keine gepruefte Entscheidung.

Warum ein Werkzeug und nicht ein Blick beim Lesen: eine Spalte mit drei
Worten ("Motivationszahl ohne Handlung") liest sich wie eine ausgefuellte
Zelle, traegt aber keine Gegenrede. Ohne Wortgrenze bleibt das unbemerkt,
bis der Vorschlag gebaut ist und die Gegenrede fehlt.

Geprueft wird je Datei NUR der Abschnitt, dessen Ueberschrift mit
„Verbesserungs-Backlog" beginnt (Praefix-Vergleich, damit „... (K4: ...)"
und „... (K4)" beide greifen) — nicht die ganze Datei.
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]

STANDARD_PFADE = ("docs/betrieb/*.md",)

UEBERSCHRIFT_PRAEFIX = "Verbesserungs-Backlog"

PFLICHT_SPALTEN = ("Vorschlag", "Advocatus Diaboli", "Out of the Box", "Anker")

# Anker gilt als gesetzt bei Issue-/PR-Verweis (#N), einem Link, oder dem Wort
# "offen" (Vorschlag bewusst zurueckgestellt, aber benannt — kein leeres Feld).
ANKER_MUSTER = re.compile(r"#\d+|https?://|\boffen\b", re.IGNORECASE)

# "gebaut, PR #N" / "#N" (auch als Markdown-Link) zaehlt zusaetzlich als
# "in Umsetzung/gebaut".
GEBAUT_MUSTER = re.compile(r"\bgebaut\b", re.IGNORECASE)


@dataclass
class Mangel:
    datei: str
    zeile: int
    vorschlag_nr: str
    fehlt: str


@dataclass
class DateiErgebnis:
    datei: str
    vorschlaege: int = 0
    gebaut: int = 0
    maengel: list[Mangel] = field(default_factory=list)
    tabellen_befund: str | None = None


def _woerter(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _zerlege_zeile(zeile: str) -> list[str]:
    """Zerlegt eine Markdown-Tabellenzeile in Zellen (fuehrende/schliessende
    Pipes optional, escaped `\\|` bleibt in der Zelle)."""
    kern = zeile.strip()
    if kern.startswith("|"):
        kern = kern[1:]
    if kern.endswith("|"):
        kern = kern[:-1]
    zellen = re.split(r"(?<!\\)\|", kern)
    return [z.strip().replace(r"\|", "|") for z in zellen]


def _ist_trennzeile(zellen: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", z.strip()) for z in zellen if z.strip())


def _finde_backlog_abschnitt(zeilen: list[str]) -> tuple[int, int] | None:
    """Liefert (start, ende) als Zeilen-Indizes (0-basiert, ende exklusiv)
    des Abschnitts, dessen `## `-Ueberschrift mit UEBERSCHRIFT_PRAEFIX
    beginnt. `ende` ist die naechste `## `-Ueberschrift oder das Dateiende."""
    start = None
    for i, zeile in enumerate(zeilen):
        if zeile.startswith("## ") and zeile[3:].strip().startswith(
            UEBERSCHRIFT_PRAEFIX
        ):
            start = i + 1
            break
    if start is None:
        return None
    ende = len(zeilen)
    for i in range(start, len(zeilen)):
        if zeilen[i].startswith("## "):
            ende = i
            break
    return start, ende


def pruefe_datei(pfad: Path, min_woerter: int) -> DateiErgebnis:
    ergebnis = DateiErgebnis(datei=str(pfad))
    text = pfad.read_text(encoding="utf-8")
    zeilen = text.split("\n")

    spanne = _finde_backlog_abschnitt(zeilen)
    if spanne is None:
        ergebnis.tabellen_befund = (
            f"kein Abschnitt '## {UEBERSCHRIFT_PRAEFIX}...' gefunden"
        )
        return ergebnis
    start, ende = spanne

    kopf_idx = None
    for i in range(start, ende):
        if zeilen[i].strip().startswith("|"):
            kopf_idx = i
            break
    if kopf_idx is None:
        ergebnis.tabellen_befund = "Backlog-Tabelle nicht gefunden"
        return ergebnis

    kopf = [z.lower() for z in _zerlege_zeile(zeilen[kopf_idx])]
    fehlende_spalten = [s for s in PFLICHT_SPALTEN if s.lower() not in kopf]
    if fehlende_spalten:
        ergebnis.tabellen_befund = (
            "Backlog-Tabelle ohne Pflichtspalten: fehlt " + ", ".join(fehlende_spalten)
        )
        return ergebnis

    idx_vorschlag = kopf.index("vorschlag")
    idx_advocatus = kopf.index("advocatus diaboli")
    idx_ootb = kopf.index("out of the box")
    idx_anker = kopf.index("anker")

    zeile_idx = kopf_idx + 1
    if zeile_idx < ende and _ist_trennzeile(_zerlege_zeile(zeilen[zeile_idx])):
        zeile_idx += 1

    while zeile_idx < ende:
        roh = zeilen[zeile_idx]
        if not roh.strip().startswith("|"):
            zeile_idx += 1
            continue
        zellen = _zerlege_zeile(roh)
        if len(zellen) <= max(idx_vorschlag, idx_advocatus, idx_ootb, idx_anker):
            zeile_idx += 1
            continue

        ergebnis.vorschlaege += 1
        nr = zellen[0].strip() or str(ergebnis.vorschlaege)
        advocatus = zellen[idx_advocatus]
        ootb = zellen[idx_ootb]
        anker = zellen[idx_anker]

        if _woerter(advocatus) < min_woerter:
            ergebnis.maengel.append(
                Mangel(str(pfad), zeile_idx + 1, nr, "Advocatus Diaboli")
            )
        if _woerter(ootb) < min_woerter:
            ergebnis.maengel.append(
                Mangel(str(pfad), zeile_idx + 1, nr, "Out of the Box")
            )
        if not ANKER_MUSTER.search(anker):
            ergebnis.maengel.append(Mangel(str(pfad), zeile_idx + 1, nr, "Anker"))

        if GEBAUT_MUSTER.search(anker) or re.search(r"#\d+", anker):
            ergebnis.gebaut += 1

        zeile_idx += 1

    return ergebnis


def _sammle_dateien(pfade: list[str]) -> list[Path]:
    dateien: list[Path] = []
    for muster in pfade:
        basis = muster if Path(muster).is_absolute() else str(WURZEL / muster)
        treffer = sorted(glob.glob(basis))
        for t in treffer:
            p = Path(t)
            if p.is_file() and p not in dateien:
                dateien.append(p)
    return dateien


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "pfade",
        nargs="*",
        default=list(STANDARD_PFADE),
        help="Datei(en) oder Glob-Muster, Default docs/betrieb/*.md",
    )
    p.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    p.add_argument(
        "--block", action="store_true", help="Exit 1 bei mindestens einem Mangel"
    )
    p.add_argument(
        "--min-woerter",
        type=int,
        default=6,
        help="Mindest-Wortzahl je Gegenrede-/Alternative-Spalte (Default 6)",
    )
    args = p.parse_args()

    dateien = _sammle_dateien(args.pfade)
    if not dateien:
        print(f"FEHLER: keine Datei fuer {args.pfade!r} gefunden", file=sys.stderr)
        return 2

    ergebnisse = [pruefe_datei(d, args.min_woerter) for d in dateien]

    gesamt_vorschlaege = sum(e.vorschlaege for e in ergebnisse)
    gesamt_maengel = sum(len(e.maengel) for e in ergebnisse)
    gesamt_maengel += sum(1 for e in ergebnisse if e.tabellen_befund)
    gesamt_gebaut = sum(e.gebaut for e in ergebnisse)

    if args.json:
        daten = {
            "dateien": len(ergebnisse),
            "vorschlaege": gesamt_vorschlaege,
            "maengel": gesamt_maengel,
            "gebaut": gesamt_gebaut,
            "ergebnisse": [
                {
                    "datei": e.datei,
                    "vorschlaege": e.vorschlaege,
                    "gebaut": e.gebaut,
                    "tabellen_befund": e.tabellen_befund,
                    "maengel": [
                        {
                            "zeile": m.zeile,
                            "vorschlag": m.vorschlag_nr,
                            "fehlt": m.fehlt,
                        }
                        for m in e.maengel
                    ],
                }
                for e in ergebnisse
            ],
        }
        print(json.dumps(daten, ensure_ascii=False, indent=2))
    else:
        print(
            f"Backlog-Pruefung: {gesamt_vorschlaege} Vorschlaege in "
            f"{len(ergebnisse)} Akten, {gesamt_maengel} Maengel"
        )
        print(f"  davon in Umsetzung/gebaut: {gesamt_gebaut}")
        for e in ergebnisse:
            print(f"\n  {e.datei}")
            if e.tabellen_befund:
                print(f"    ❌ {e.tabellen_befund}")
                continue
            print(f"    Vorschlaege: {e.vorschlaege}, Maengel: {len(e.maengel)}")
            for m in e.maengel:
                print(
                    f"    ❌ {m.datei}:{m.zeile} Vorschlag {m.vorschlag_nr} — fehlt: {m.fehlt}"
                )
            if not e.maengel:
                print("    ✅ jeder Vorschlag mit Gegenrede, Alternative und Anker")

    if args.block and gesamt_maengel > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
