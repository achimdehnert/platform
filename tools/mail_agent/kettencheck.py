#!/usr/bin/env python3
"""Die Kette prüfen: Postfach → Ledger → Vorhersage → Board → Ansicht.

Warum es das gibt (platform#2176 Kriterium 6): Die Mail-/Todo-Arbeit hängt an
einer Kette aus fünf Gliedern, die alle einzeln funktionieren können, während das
Ergebnis trotzdem falsch ist. Der teuerste Fall ist das stille Glied — der Index
hinkt zwei Tage nach, die Vorhersage steht auf altem Stand, das Board zeigt eine
Liste, die stimmt hätte sein können. Nichts davon ist rot; nur niemandem fällt
etwas auf.

**Der Melder sagt den ORT, nicht nur die Störung.** „Etwas ist kaputt" hilft
niemandem; „die Vorhersagedatei ist vier Tage alt, obwohl `make boards` sie
täglich schreibt" ist eine Arbeitsanweisung. Jedes Glied trägt darum seinen
eigenen Prüfsatz und seinen eigenen Reparaturhinweis.

Read-only. Exit 1, sobald ein Glied bricht — damit ein Timer daran scheitern kann.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
LEDGER = Path.home() / ".claude" / "mail-vorgaenge.json"
FAELLIGKEIT = Path.home() / ".claude" / "mail-faelligkeit.json"
ACTION_BOARD = Path.home() / ".claude" / "mail-action-board.md"
TODO_HTML = Path.home() / ".claude" / "boards" / "todo.html"

#: Ab wann ein Artefakt als abgestanden gilt. Zwei Tage lassen ein Wochenende
#: durch, ohne dass ein vergessener Lauf eine Woche unbemerkt bleibt.
MAX_ALTER_TAGE = 2


@dataclass
class Befund:
    glied: str
    ok: bool
    ort: str
    hinweis: str = ""

    def __str__(self) -> str:
        marke = "OK   " if self.ok else "BRUCH"
        zeile = f"  {marke} {self.glied:<12} {self.ort}"
        return zeile if self.ok else f"{zeile}\n        → {self.hinweis}"


def _alter_tage(pfad: Path, heute: date) -> float | None:
    try:
        stand = datetime.fromtimestamp(pfad.stat().st_mtime, tz=timezone.utc).date()
    except OSError:
        return None
    return (heute - stand).days


def pruefe_ledger(heute: date, ledger: Path = LEDGER) -> Befund:
    try:
        daten = json.loads(ledger.read_text(encoding="utf-8"))
    except OSError:
        return Befund("Ledger", False, f"{ledger} fehlt", "Sicherung einspielen")
    except json.JSONDecodeError as fehler:
        return Befund(
            "Ledger",
            False,
            f"{ledger.name} ist kein gueltiges JSON ({fehler.lineno}:{fehler.colno})",
            "letzte Schreiboperation pruefen; Sicherung liegt im Session-Scratchpad",
        )
    anzahl = len(daten.get("vorgaenge", []))
    if anzahl == 0:
        return Befund(
            "Ledger", False, "keine Vorgaenge im Ledger", "Sicherung einspielen"
        )
    return Befund("Ledger", True, f"{anzahl} Vorgaenge")


def pruefe_artefakt(name: str, pfad: Path, heute: date, hinweis: str) -> Befund:
    alter = _alter_tage(pfad, heute)
    if alter is None:
        return Befund(name, False, f"{pfad} fehlt", hinweis)
    if alter < 0:
        # Eine Datei aus der Zukunft ist kein frisches Artefakt, sondern ein
        # Hinweis auf eine falsch gehende Uhr oder eine kopierte Datei. Bis
        # 2026-08-21 meldete der Melder sie als "OK, -5 Tage alt" — ein Alarm,
        # der Unmoegliches durchwinkt, prueft die falsche Richtung.
        return Befund(
            name,
            False,
            f"{pfad.name} traegt ein Datum {abs(alter):.0f} Tage in der Zukunft",
            "Systemuhr pruefen (timedatectl); kopierte Datei mit falscher mtime?",
        )
    if alter > MAX_ALTER_TAGE:
        return Befund(name, False, f"{pfad.name} ist {alter:.0f} Tage alt", hinweis)
    return Befund(name, True, f"{pfad.name}, {alter:.0f} Tage alt")


def pruefe_vorhersage(heute: date, pfad: Path = FAELLIGKEIT) -> Befund:
    befund = pruefe_artefakt(
        "Vorhersage", pfad, heute, "make boards (schreibt sie ueber faelligkeit.py)"
    )
    if not befund.ok:
        return befund
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Befund(
            "Vorhersage", False, f"{pfad.name} ist kein gueltiges JSON", "make boards"
        )
    if not daten:
        return Befund(
            "Vorhersage",
            False,
            "Vorhersage ist leer",
            "faelligkeit.py ohne Treffer — Mail-Index erreichbar?",
        )
    return Befund("Vorhersage", True, f"{len(daten)} Vorgaenge mit Erwartung")


def pruefe_dienst(name: str, url: str, erwartet: str, hinweis: str) -> Befund:
    try:
        with urllib.request.urlopen(url, timeout=5) as antwort:  # noqa: S310
            text = antwort.read(4000).decode("utf-8", errors="replace")
            code = antwort.status
    except (urllib.error.URLError, OSError) as fehler:
        return Befund(name, False, f"{url} nicht erreichbar ({fehler})", hinweis)
    if code != 200:
        return Befund(name, False, f"{url} antwortet mit {code}", hinweis)
    if erwartet not in text:
        return Befund(
            name,
            False,
            f"{url} antwortet, aber ohne '{erwartet}'",
            "Dienst laeuft mit altem Stand? systemctl --user restart",
        )
    return Befund(name, True, f"{url} antwortet")


def pruefe_index(seit: str) -> Befund:
    """Der Index ist die Quelle der Vorhersage — hinkt er, hinkt alles danach."""
    try:
        roh = subprocess.run(
            [
                sys.executable,
                str(HIER / "suche.py"),
                "--seit",
                seit,
                "--limit",
                "5",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return Befund(
            "Mail-Index", False, "Abfrage laeuft in den Timeout", "SSH-Weg pruefen"
        )
    if roh.returncode != 0:
        return Befund(
            "Mail-Index",
            False,
            f"Abfrage scheitert: {roh.stderr.strip()[:80]}",
            "suche.py von Hand aufrufen; Ziel-Host steht in infra/hosts.yaml",
        )
    try:
        treffer = json.loads(roh.stdout).get("treffer", [])
    except json.JSONDecodeError:
        return Befund("Mail-Index", False, "Antwort ist kein JSON", "suche.py pruefen")
    if not treffer:
        return Befund(
            "Mail-Index",
            False,
            f"keine Nachricht seit {seit}",
            "Ingest steht? Der naechtliche Lauf schreibt den Index",
        )
    return Befund("Mail-Index", True, f"{len(treffer)} Nachricht(en) seit {seit}")


def pruefe_timer(einheit: str = "sendeabgleich.timer") -> Befund:
    try:
        roh = subprocess.run(
            ["systemctl", "--user", "is-active", einheit],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return Befund("Timer", False, "systemctl nicht aufrufbar", "Host pruefen")
    zustand = roh.stdout.strip()
    if zustand != "active":
        return Befund(
            "Timer",
            False,
            f"{einheit} ist {zustand or 'unbekannt'}",
            f"systemctl --user enable --now {einheit}",
        )
    return Befund("Timer", True, f"{einheit} aktiv")


def alle(heute: date, mit_index: bool = True) -> list[Befund]:
    seit = (heute - timedelta(days=3)).isoformat()
    befunde = [
        pruefe_index(seit)
        if mit_index
        else Befund("Mail-Index", True, "uebersprungen"),
        # Pfade hier explizit durchreichen statt als Default-Argument: ein Default
        # wird beim Definieren ausgewertet und laesst sich im Test nicht ersetzen —
        # der erste Anlauf meldete deshalb zwei kaputte Glieder als heil.
        pruefe_ledger(heute, LEDGER),
        pruefe_vorhersage(heute, FAELLIGKEIT),
        pruefe_artefakt("Board", ACTION_BOARD, heute, "make boards"),
        pruefe_artefakt("Todo-HTML", TODO_HTML, heute, "make boards"),
        pruefe_dienst(
            "Ansicht",
            "http://127.0.0.1:8789/",
            "Arbeitsliste",
            "systemctl --user restart todo-board.service",
        ),
        pruefe_dienst(
            "Mail-Link",
            "http://127.0.0.1:8787/",
            "mail",
            "systemctl --user restart mail-links.service",
        ),
        pruefe_timer(),
    ]
    return befunde


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--heute", default=None)
    ap.add_argument(
        "--ohne-index",
        action="store_true",
        help="Index-Abfrage ueberspringen (schnell, fuer lokale Laeufe)",
    )
    args = ap.parse_args()
    heute = (
        datetime.strptime(args.heute, "%Y-%m-%d").date() if args.heute else date.today()
    )

    befunde = alle(heute, mit_index=not args.ohne_index)
    print("Kette Postfach → Ledger → Vorhersage → Board → Ansicht\n")
    for b in befunde:
        print(b)
    kaputt = [b for b in befunde if not b.ok]
    if kaputt:
        print(
            f"\n{len(kaputt)} Glied(er) gebrochen: "
            + ", ".join(b.glied for b in kaputt)
        )
        return 1
    print(f"\nAlle {len(befunde)} Glieder tragen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
