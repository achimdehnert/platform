#!/usr/bin/env python3
"""Aus Befunden des Sitzungsstarts werden Fragen an den Owner (#3369,
KONZ-platform-061 MVC-3).

Der Sitzungsstart findet jeden Morgen dieselben Dinge, und sie stehen im
Befund-Journal. Gelesen wird das Journal aber nur, wenn jemand eine Sitzung
startet — im Alltag also selten. Dieses Werkzeug dreht die Richtung um: es
sucht die wenigen Befunde, bei denen der naechste Schritt feststeht, und macht
daraus Fragen, die die Morgen-Meldung mittraegt. Ein 👍 des Owners darauf ist
die Freigabe (`deploy/lotse_auftrag.py pruefe_go_reaktion` in chat-hub).

Drei Grenzen, alle aus KONZ-061:

* **Klassen-Erlaubnisliste** (`ERLAUBT`): nur Befunde, deren naechster Schritt
  ohne Urteil feststeht. Alles andere bleibt stille Meldung. Die Liste steht
  hier als Konstante mit Grund je Zeile — wer sie aendert, sieht daneben,
  warum die Zeile da ist.
* **Sperrliste** (`GESPERRT`): Befunde mit Aussenwirkung werden NIE
  vorgeschlagen, auch wenn sie sonst passen. Ein Daumen ist fuer einen
  unumkehrbaren Schritt zu billig (Charta Art. 2).
* **Hoechstens `MAX_FRAGEN` je Meldung, jeder Befund genau einmal.** Sonst
  wird der Raum zum Melder-Log, und der Owner liest ihn nicht mehr.

Gefragt wird nur, was noch KEIN Artefakt hat (kein Issue, kein Verzicht):
ein getrackter Befund braucht keine Frage, er braucht Arbeit.

    vorschlaege.py                 # Fragen als Text, eine je Zeile
    vorschlaege.py --json          # dasselbe maschinenlesbar
    vorschlaege.py --merken        # gestellte Fragen vormerken (fuer den Lauf)
    vorschlaege.py --status        # was wurde wann gefragt
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

WERKZEUGE = Path(__file__).resolve().parents[1]
JOURNAL_WERKZEUG = WERKZEUGE / "befund_journal.py"
GEFRAGT_DATEI = Path(
    os.environ.get(
        "LOTSE_VORSCHLAEGE_DATEI", str(Path.home() / ".claude" / "lotse-gefragt.json")
    )
)
MAX_FRAGEN = 3

# Phase -> (Frage, was der Lotse dann tut). Nur Befunde, deren naechster
# Schritt ohne Urteil feststeht — der Owner soll zustimmen, nicht entscheiden.
ERLAUBT: dict[str, tuple[str, str]] = {
    # Ein Worktree weit hinter main kostet beim Merge am meisten; nachziehen
    # ist mechanisch und rueckbaubar.
    "0.4.4 basis-abstand": (
        "{n} Arbeitskopien liegen weit hinter dem Hauptstand. Soll ich sie nachziehen?",
        "Worktrees auf origin/main mergen, je Repo ein Lauf",
    ),
    # Eine Prio-Zeile, die auf etwas Geschlossenes zeigt, ist eine Luege im
    # Handover — das Nachziehen aendert nur Text.
    "0.7.4 prio-referenzen": (
        "Im Handover zeigen Prio-Zeilen auf geschlossene Vorgaenge. Soll ich sie nachziehen?",
        "Handover-Referenzen auf offene Vorgaenge korrigieren, PR",
    ),
    # Ein Melder ohne Leser meldet ins Leere; das Eintragen ist eine Zeile.
    "0.7.23 melder-register": (
        "{n} Melder hat keinen Leser im Register. Soll ich ihn eintragen?",
        "Leser im Melder-Register benennen, PR",
    ),
    # Die Schleuse raeumt Uebergabe-Reste; ueberfaellige sind per Definition
    # erledigt oder vergessen.
    "0.5.2 schleuse": (
        "In der Schleuse sind Vorgaenge ueberfaellig. Soll ich aufraeumen?",
        "schleuse.py --aufraeumen, erst Trockenlauf",
    ),
    # Ein Zertifikat mit Restlaufzeit ist ein Datum, kein Urteil.
    "0.7.16 origin-tls": (
        "Ein Origin-Zertifikat laeuft bald ab ({repo}). Soll ich ein Issue im Ziel-Repo anlegen?",
        "Issue im betroffenen Repo mit Ablaufdatum und Erneuerungsweg",
    ),
}

# Diese Phasen werden NIE zur Frage — ihr naechster Schritt hat Aussenwirkung
# (Deploy, Secrets, Sichtbarkeit eines Repos) und braucht das geschriebene
# Wort, nicht einen Daumen. Redundant zur Sperre in `pruefe_go_reaktion`
# (chat-hub): dort am Entwurfstext, hier an der Klasse — zwei Netze, weil ein
# einzelnes Netz hier zu teuer reisst.
GESPERRT = {
    "0.7.12 prod-wirkung",  # Deploy
    "0.7.25 rotation-faelligkeit",  # Secrets
    "0.7.27 sichtbarkeits-drift",  # Repo-Sichtbarkeit
    "0.7.17 backup-deckung",  # Loeschen/Aufbewahren
    "0.7.21 alarmweg",  # Alarmierung
}


class VorschlagFehler(Exception):
    """Etwas laeuft nicht — wird gemeldet, nicht verschluckt."""


def _journal_lesen() -> list[dict]:
    """Ruft `befund_journal.py --bericht --json` auf. Ein Fehler dort ist ein
    Fehler hier — lieber keine Frage als eine aus geratenem Stand."""
    lauf = subprocess.run(
        [sys.executable, str(JOURNAL_WERKZEUG), "--bericht", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if lauf.returncode != 0:
        raise VorschlagFehler(
            f"befund_journal.py fehlgeschlagen: {lauf.stderr.strip()[:200]}"
        )
    try:
        daten = json.loads(lauf.stdout)
    except json.JSONDecodeError as exc:
        raise VorschlagFehler(f"befund_journal.py gab kein JSON: {exc}") from exc
    return daten if isinstance(daten, list) else []


def gefragt_lesen(pfad: Path | None = None) -> dict:
    """Was wurde schon gefragt. Eine kaputte Datei blockiert nie — im
    Zweifel wird eine Frage doppelt gestellt, nie gar keine (dieselbe Regel
    wie in `befund_journal.lade`)."""
    p = pfad or GEFRAGT_DATEI
    try:
        daten = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return daten if isinstance(daten, dict) else {}


def gefragt_merken(ids: list[str], heute: str, pfad: Path | None = None) -> None:
    p = pfad or GEFRAGT_DATEI
    daten = gefragt_lesen(p)
    for fid in ids:
        daten.setdefault(fid, heute)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(daten, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _anzahl(note: str) -> str:
    """Erste Zahl aus dem Melder-Text — fuer `{n}` in der Frage. Ohne Zahl
    bleibt es bei einem unbestimmten „Ein"."""
    for stueck in note.replace("(", " ").split():
        if stueck.isdigit():
            return stueck
    return "Ein"


def waehle(
    befunde: list[dict], gefragt: dict, max_fragen: int = MAX_FRAGEN
) -> list[dict]:
    """Die Fragen dieses Tages. Reine Funktion (Journal und Merkdatei kommen
    von aussen), damit der Test ohne Sitzungsstart auskommt.

    Reihenfolge: aeltester Befund zuerst — wer am laengsten liegt, wird zuerst
    gefragt. Ausgeschlossen: gesperrte Klassen, Befunde mit Artefakt oder
    Verzicht (die sind getrackt), schon Gefragtes, alles ausserhalb der
    Erlaubnisliste."""
    treffer = []
    for e in befunde:
        phase = e.get("phase", "")
        if phase in GESPERRT or phase not in ERLAUBT:
            continue
        if e.get("artefakt") or e.get("verzicht"):
            continue
        if e.get("id") in gefragt:
            continue
        frage, tat = ERLAUBT[phase]
        treffer.append(
            {
                "id": e.get("id"),
                "phase": phase,
                "repo": e.get("repo"),
                "laeufe": e.get("laeufe", 0),
                "frage": frage.format(
                    n=_anzahl(e.get("note") or ""), repo=e.get("repo")
                ),
                "tat": tat,
            }
        )
    treffer.sort(key=lambda t: -t["laeufe"])
    return treffer[:max_fragen]


def als_text(fragen: list[dict]) -> str:
    """Die Zeilen fuer die Morgen-Meldung. Eine Frage je Zeile, am Ende der
    Hinweis auf den Daumen — kurz, weil der Raum kein Bericht ist."""
    if not fragen:
        return ""
    zeilen = [
        "Drei Dinge liegen hier laenger, bei denen der naechste Schritt feststeht:"
    ]
    if len(fragen) == 1:
        zeilen = [
            "Eine Sache liegt hier laenger, bei der der naechste Schritt feststeht:"
        ]
    elif len(fragen) == 2:
        zeilen = [
            "Zwei Dinge liegen hier laenger, bei denen der naechste Schritt feststeht:"
        ]
    for nr, f in enumerate(fragen, start=1):
        zeilen.append(
            f"{nr}. {f['frage']} ({f['laeufe']} Laeufe) — ich wuerde: {f['tat']}"
        )
    zeilen.append(
        "Daumen hoch auf diese Nachricht = einverstanden. Schweigen heisst nein."
    )
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", action="store_true", help="maschinenlesbar")
    p.add_argument("--merken", action="store_true", help="gestellte Fragen vormerken")
    p.add_argument("--status", action="store_true", help="was wurde wann gefragt")
    p.add_argument("--max", type=int, default=MAX_FRAGEN)
    a = p.parse_args(argv)

    if a.status:
        print(json.dumps(gefragt_lesen(), ensure_ascii=False, indent=1, sort_keys=True))
        return 0
    try:
        fragen = waehle(_journal_lesen(), gefragt_lesen(), a.max)
    except VorschlagFehler as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1
    if a.merken and fragen:
        gefragt_merken([f["id"] for f in fragen], date.today().isoformat())
    if a.json:
        print(json.dumps(fragen, ensure_ascii=False, indent=1))
    else:
        text = als_text(fragen)
        if text:
            print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
