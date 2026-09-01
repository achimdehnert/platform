#!/usr/bin/env python3
"""K6 aus KONZ-platform-051: haelt die Blaupause?

Ein verteilter Skill darf **in seinen Anweisungen** keinen Namen eines
Ziel-Repos tragen — sonst ist er die Anleitung fuer ein Repo und nicht die
Blaupause fuer die Flotte. In seinen **Belegen** darf und soll er das:
ein Realfall ohne Repo-Namen ist kein Realfall.

GATE_HEADER (KONZ-038 D8):
  "slug": "blueprint-names-a-target-repo-in-an-instruction"
  "mode": "gate"
  "owner": "achim"
  "last_drill_pass": "2026-09-01"
  "evidence": "tools/tests/test_blaupause_check.py"

Warum dieses Werkzeug und nicht der grep aus dem Kriterium: der
Original-grep (`grep -icE 'writing-hub|ausschreibungs-hub|meiki|risk-hub'`)
ist **nicht entscheidbar** — er zaehlt Changelog, Dogfood-Tests und
Realfall-Blockquotes mit, die per Konstruktion nie verschwinden, und er
faengt mit `meiki` die Org `meiki-lra` statt eines Repos (platform#2560,
Owner-Entscheid 2026-09-01: Weg (a), Scope eingrenzen).

Drei Praezisierungen gegenueber dem grep:
  1. **Scope:** nur Anweisungs-Abschnitte. Beleg-Abschnitte (Intro,
     Klassen-Katalog, Memory-Pfad, Bezug, Dogfood-Tests, Changelog) sind
     ausgenommen — dort ist der Repo-Name der Zweck.
  2. **Namen aus der Registry**, nicht vier handgetippte. Damit faengt der
     Check auch ein Repo, das erst morgen Pilot wird. Gezaehlt werden nur
     Repos mit Oberflaeche (`django`/`fastapi`/`static`) — nur die koennen
     ueberhaupt Ziel eines Klick-Durchlaufs sein. Eine Bibliothek oder ein
     Framework (`aifw`, `iil-testkit`) in einer Anweisung zu nennen ist so
     wenig eine Zuschneidung wie „Redis" oder „Django".
  3. **Heimat-Repo ausgenommen:** `platform` zu nennen ist keine
     Zuschneidung auf ein Ziel-Repo, sondern der Ort, an dem der Skill lebt.

Geprueft wird der **Block**, nicht die Zeile — ein Listenpunkt oder Absatz
mit seinen Fortsetzungszeilen. Zeilenweise war genau der Defekt, an dem der
Original-grep scheiterte: der Beleg steht regelmaessig eine Zeile unter dem
Repo-Namen, den er belegt (platform#2560, Zeile 18).

Fail-closed: ein neuer `##`-Abschnitt gilt als Anweisung, bis er
ausdruecklich in AUSGENOMMEN steht.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

WURZEL = Path(__file__).resolve().parents[1]

# Abschnitte, die Belege tragen duerfen und sollen (Praefix-Vergleich).
AUSGENOMMEN = (
    "## Klassen-Katalog",
    "## 🌀-Memory-Discovery-Pfad",
    "## Bezug",
    "## Dogfood-Tests",
    "## Changelog",
)

# Ein Beleg weist sich mit Datum oder Issue-/PR-Nummer aus.
BELEG = re.compile(r"\d{4}-\d{2}-\d{2}|#\d+")


# Nur diese Typen haben eine Oberflaeche und koennen Ziel eines Klick-Laufs sein.
ZIEL_TYPEN = {"django", "fastapi", "static"}


def flotten_namen(registry: Path, heimat: str) -> list[str]:
    daten = yaml.safe_load(registry.read_text(encoding="utf-8"))
    namen = []
    for name, eintrag in (daten.get("repos") or {}).items():
        if name == heimat:
            continue
        rich = eintrag.get("rich") or {}
        flat = eintrag.get("flat") or {}
        if (rich.get("type") or flat.get("type")) in ZIEL_TYPEN:
            namen.append(name)
    # laengste zuerst: 'meiki-dms' darf nicht von 'meiki' verdeckt werden
    return sorted(namen, key=len, reverse=True)


BLOCK_START = re.compile(r"^\s*(?:\d+\.|[-*])\s")


def _bloecke(zeilen: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    """Zerlegt Anweisungs-Zeilen in Bloecke: Listenpunkt bzw. Absatz mit
    seinen Fortsetzungszeilen. Leerzeile beendet einen Block."""
    bloecke: list[list[tuple[int, str]]] = []
    aktuell: list[tuple[int, str]] = []
    for nr, zeile in zeilen:
        if not zeile.strip():
            if aktuell:
                bloecke.append(aktuell)
                aktuell = []
            continue
        if BLOCK_START.match(zeile) and aktuell:
            bloecke.append(aktuell)
            aktuell = []
        aktuell.append((nr, zeile))
    if aktuell:
        bloecke.append(aktuell)
    return bloecke


def pruefe(datei: Path, namen: list[str]) -> tuple[list[tuple[int, str, str]], int]:
    """Gibt (Befunde, Zahl der geprueften Anweisungs-Bloecke) zurueck."""
    muster = re.compile(
        r"(?<![\w-])(" + "|".join(re.escape(n) for n in namen) + r")(?![\w-])",
        re.IGNORECASE,
    )
    befunde: list[tuple[int, str, str]] = []
    abschnitt = "(Intro)"
    im_scope = False  # alles vor der ersten '## '-Ueberschrift ist Intro = Beleg
    offen: list[tuple[int, str]] = []
    geprueft = 0
    abschnitt_von: dict[int, str] = {}

    for nr, zeile in enumerate(datei.read_text(encoding="utf-8").split("\n"), 1):
        if zeile.startswith("## "):
            abschnitt = zeile.strip()
            im_scope = not abschnitt.startswith(AUSGENOMMEN)
            offen.append((nr, ""))  # Ueberschrift trennt Bloecke
            continue
        if im_scope:
            offen.append((nr, zeile))
            abschnitt_von[nr] = abschnitt

    for block in _bloecke(offen):
        geprueft += 1
        text = "\n".join(z for _, z in block)
        if not muster.search(text) or BELEG.search(text):
            continue
        nr, zeile = next((n, z) for n, z in block if muster.search(z))
        befunde.append((nr, abschnitt_von.get(nr, "?"), zeile.strip()))
    return befunde, geprueft


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--datei", default=str(WURZEL / ".windsurf/workflows/ux-review.md"))
    p.add_argument("--registry", default=str(WURZEL / "registry/canonical.yaml"))
    p.add_argument("--heimat", default="platform")
    args = p.parse_args()

    datei = Path(args.datei)
    if not datei.is_file():
        print(f"FEHLER: {datei} nicht gefunden", file=sys.stderr)
        return 2

    namen = flotten_namen(Path(args.registry), args.heimat)
    if not namen:
        print("FEHLER: Registry liefert keine Repo-Namen", file=sys.stderr)
        return 2

    befunde, geprueft = pruefe(datei, namen)
    print(f"Blaupausen-Check: {datei.name}")
    print(f"  Ziel-Repos aus Registry: {len(namen)} (Heimat '{args.heimat}' ausgenommen)")
    print(f"  gepruefte Anweisungs-Bloecke: {geprueft}")

    if not befunde:
        print("  ✅ kein Ziel-Repo-Name in einer Anweisung ohne Beleg-Marker")
        return 0

    print(f"  ❌ {len(befunde)} Befund(e) — Repo-Name in einer Anweisung ohne Beleg:")
    for nr, abschnitt, zeile in befunde:
        print(f"     Z{nr} [{abschnitt[:60]}]")
        print(f"        {zeile[:140]}")
    print("\n  Behebung: entweder den Namen aus der Anweisung entfernen (generisch")
    print("  formulieren) oder die Zeile als Beleg ausweisen — Datum oder #Nummer.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
