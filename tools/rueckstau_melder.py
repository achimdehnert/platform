#!/usr/bin/env python3
"""rueckstau_melder.py — wachsen zwei Stapel im Archiv, ohne dass es jemand sieht?

## Anlass (2026-09-10)

Im Archiv (Paperless auf `hetzner-prod`) sammeln sich Dokumente unter den
Stichwoertern `Posteingang` (331) und `pruefen` (57), die jemand von Hand
durchsehen muss. Niemand sieht, ob diese Stapel wachsen oder schrumpfen.
Owner-Freigabe fuer diesen Melder liegt vor (Wort 2026-09-10).

## Wachstum ist das Signal, nicht die absolute Zahl

Ein Stapel mit 331 Dokumenten, der jede Woche kleiner wird, ist kein Befund —
jemand arbeitet ihn ab. Ein Stapel mit 20 Dokumenten, der jede Woche waechst,
ist einer: die Aufnahme haengt der Bearbeitung ab. Ein Melder, der die absolute
Zahl bewertet, meldete ab Tag eins dauerhaft rot und waere binnen Wochen
ignoriert — genau daran ist der taegliche `backup-deckung`-Kommentar gestorben
(siehe `tools/scan_melder.py`, an dem sich dieser Melder eng orientiert).

## Warum kein Toleranz-Polster ueber 0 (Default `--toleranz 0`)

`scan_melder.py` laeuft stuendlich und braucht ein Alarm-Fenster, weil viele
kurz aufeinanderfolgende Laeufe sonst denselben Fund mehrfach melden wuerden.
Dieser Melder laeuft **woechentlich** (siehe Workflow): zwischen zwei Laeufen
liegen sieben Tage, und die Stichwoerter werden von Menschen gepflegt, nicht
von einem Prozess, der staendig hin- und herschaltet. Ein Delta von +1 nach
einer Woche ist deshalb kein Messrauschen, sondern der Beleg, dass in dieser
Woche mehr hinein- als herausgegangen ist — genau das Signal, das gemeldet
werden soll. `--toleranz N` bleibt als Ventil, falls sich in der Praxis doch
Rauschen zeigt (z.B. wenn ein Stapel routinemaessig kurz vor dem Lauf befuellt
und danach sofort geleert wird).

## Warum eine leere oder unlesbare DB-Antwort NICHT als "0 Dokumente" gilt

`select ... group by t.name` liefert fuer einen Stapel ganz ohne Treffer keine
Zeile — das ist ein legitimes Ergebnis (der Stapel ist leer). Eine KOMPLETT
leere oder unparsebare Antwort ist etwas anderes: Verbindung weg, Passwort
falsch, Container down. Beides sieht auf den ersten Blick gleich aus (keine
Zeilen), und genau diese Verwechslung wuerde eine tote Datenbank als "alles
im Lot" durchgehen lassen. Deshalb gilt: keine einzige Zeile in der Antwort
= blind, nicht gruen (Exit 2) — dieselbe Haltung wie bei `lies_ignoranz()` in
`scan_melder.py`.

## Warum die Normalform verglichen wird, nicht die Schreibweise

`pruefen` und `prüfen` sind derselbe Stapel, nur verschieden geschrieben.
Ein Vergleich ueber die rohe Zeichenkette haette den Stapel bei einer
Schreibweisen-Aenderung im Tag (oder einer gemischten Beschriftung im Archiv)
lautlos in zwei Haelften gerissen und beide als kleiner gemeldet, obwohl nichts
verschwunden ist (Lehre `feedback_version_regex_verliert_die_zweite_stelle`:
Normalform vergleichen, nicht Schreibweise). `_normalform()` loest deshalb
deutsche Umlaute auf, bevor verglichen wird — sowohl beim SQL-Filter
(`_sql_varianten`) als auch beim Einsortieren der DB-Antwort (`parse_zahlen`).

## Zustand zwischen den Laeufen

Wie beim Vorbild eine JSON-Datei (Default `/var/lib/rueckstau-melder/stand.json`).
**Pflicht:** ein nicht beschreibbarer Pfad darf den Lauf NICHT abbrechen — er
meldet auf stderr, dass der naechste Lauf keinen Vergleich ziehen kann, und
gibt den aktuellen Stand trotzdem aus. Genau dieser Fehler (`PermissionError`,
Abbruch VOR der Ausgabe) wurde am 2026-09-10 in `scan_melder.py` behoben; er
wird hier nicht neu eingebaut. `--stand ''` schaltet die Zustandsdatei ab
(Tests, einmalige Laeufe) — dann gilt jeder Lauf als erster Lauf.

## Ein neu hinzugefuegter Stapel bricht den Vergleich nicht global

Kommt spaeter ein drittes Stichwort zu `--stapel` dazu, hat es im alten Stand
noch keinen Eintrag. Das ist kein globaler "erster Lauf" (die anderen Stapel
haben sehr wohl einen Vorwert) — nur fuer den neuen Stapel gibt es diese Woche
noch keinen Vergleich. `gewachsene_stapel()` ueberspringt einzelne Stapel ohne
Vorwert, statt den ganzen Lauf als Erstlauf zu behandeln.

Exit-Codes
----------
    0 = kein Stapel gewachsen (oder: erster Lauf, noch kein Vergleich moeglich)
    1 = mindestens ein Stapel ist gewachsen
    2 = Messung gescheitert (DB nicht erreichbar, Antwort leer/unlesbar)

Usage
-----
    python3 tools/rueckstau_melder.py                     # Vollbericht (auf prod)
    python3 tools/rueckstau_melder.py --kurz               # eine Zeile
    python3 tools/rueckstau_melder.py --ssh hetzner-prod    # von der Dev-Maschine
    python3 tools/rueckstau_melder.py --stand ''            # ohne Zustandsdatei (Tests)
    python3 tools/rueckstau_melder.py --stapel posteingang,pruefen,vertrag
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

CONTAINER_DB = "iil_dochub_db"
DB_USER = "paperless"
DB_NAME = "paperless"
STAPEL_DEFAULT = ("posteingang", "pruefen")
TOLERANZ_DEFAULT = 0
# Liegt auf dem Host, auf dem gemessen wird (prod) — analog INVENTAR in
# scan_melder.py. Ein Stand im Arbeitsverzeichnis waere nach jedem Checkout weg.
STAND = "/var/lib/rueckstau-melder/stand.json"

_UMLAUT_ERSATZ = {"ue": "ü", "ae": "ä", "oe": "ö"}


def _lauf(argv: list[str], ssh: str | None) -> tuple[int, str]:
    """Kommando lokal oder ueber ssh ausfuehren. Gibt (rc, stdout+stderr) zurueck.

    Identischer Aufbau wie `scan_melder._lauf()`: auf prod selbst reicht das
    lokale `subprocess.run`, von der Dev-Maschine aus wird ueber `--ssh`
    getunnelt und jedes Token einzeln quotiert (Leerzeichen/Sonderzeichen im
    SQL-Text duerfen die Remote-Shell nicht aufspalten).
    """
    if ssh:
        argv = [
            "ssh",
            "-o",
            "ConnectTimeout=8",
            ssh,
            " ".join(shlex.quote(a) for a in argv),
        ]
    p = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout + p.stderr


# --- reine Auswertung (testbar ohne Host) ----------------------------------


def _normalform(name: str) -> str:
    """Kleinschreibung + deutsche Umlaute aufgeloest, fuer den reinen Vergleich."""
    n = name.strip().lower()
    for roh, umlaut in _UMLAUT_ERSATZ.items():
        n = n.replace(roh, umlaut)
    return n


def _sql_varianten(stapel: str) -> list[str]:
    """Schreibweisen eines Stichworts, die im SQL-Filter mit abgefragt werden.

    `pruefen` -> ["pruefen", "prüfen"]. So muss das Archiv das Stichwort
    nicht in genau der ASCII-Schreibweise fuehren, die auf der Kommandozeile
    getippt wird.
    """
    s = stapel.strip().lower()
    varianten = {s}
    for roh, umlaut in _UMLAUT_ERSATZ.items():
        if roh in s:
            varianten.add(s.replace(roh, umlaut))
    return sorted(varianten)


def baue_sql(stapel: list[str]) -> str:
    """SQL fuer die Stapelgroessen, gefiltert auf die konfigurierten Stichwoerter."""
    alle = sorted({v for s in stapel for v in _sql_varianten(s)})
    in_liste = ", ".join("'" + v.replace("'", "''") + "'" for v in alle)
    return (
        "select t.name, count(*) from documents_document d "
        "join documents_document_tags dt on dt.document_id=d.id "
        "join documents_tag t on t.id=dt.tag_id "
        f"where lower(t.name) in ({in_liste}) group by t.name;"
    )


def parse_zahlen(psql_output: str, stapel: list[str]) -> dict[str, int] | None:
    """`Name|Anzahl`-Zeilen (psql `-t -A -F'|'`) in {Stapel: Anzahl} einsortieren.

    `None` heisst: die Antwort ist leer oder mindestens eine Zeile passt nicht
    ins erwartete Format — beides zaehlt als nicht gemessen, nicht als "0"
    (siehe Modul-Docstring: eine leere Antwort ist kein Beleg fuer leere
    Stapel). Ein Stapel, der in der Antwort schlicht nicht vorkommt (weil er
    aktuell keine Dokumente traegt), bekommt dagegen ganz regulaer 0.
    """
    text = psql_output.strip()
    if not text:
        return None
    normalform_zu_stapel = {_normalform(s): s for s in stapel}
    zahlen: dict[str, int] = {}
    for zeile in text.splitlines():
        teile = zeile.split("|")
        if len(teile) != 2:
            return None
        name, anzahl_text = (t.strip() for t in teile)
        if not anzahl_text.isdigit():
            return None
        ziel = normalform_zu_stapel.get(_normalform(name))
        if ziel is None:
            # Ein Tag ausserhalb der beobachteten Liste kam theoretisch nicht
            # durch den SQL-Filter — sicherheitshalber trotzdem ignorieren statt
            # den Lauf daran scheitern zu lassen.
            continue
        zahlen[ziel] = zahlen.get(ziel, 0) + int(anzahl_text)
    for s in stapel:
        zahlen.setdefault(s, 0)
    return zahlen


def gewachsene_stapel(
    alt: dict[str, dict] | None,
    neu: dict[str, int],
    *,
    toleranz: int = TOLERANZ_DEFAULT,
) -> list[dict]:
    """Stapel, deren Zahl seit dem letzten Stand um mehr als `toleranz` gestiegen ist.

    `alt is None` (kein Stand, erster Lauf, Zustandsdatei abgeschaltet) liefert
    immer `[]` — ohne Vorwert gibt es nichts zu vergleichen. Ein Stapel, der NUR
    im alten Stand fehlt (neu hinzugekommen), wird einzeln uebersprungen statt
    den ganzen Lauf als Erstlauf zu behandeln (siehe Modul-Docstring).
    """
    if alt is None:
        return []
    treffer = []
    for name, anzahl in neu.items():
        vorwert = alt.get(name)
        if not isinstance(vorwert, dict):
            continue
        alte_anzahl = vorwert.get("anzahl")
        if not isinstance(alte_anzahl, int):
            continue
        delta = anzahl - alte_anzahl
        if delta > toleranz:
            treffer.append(
                {"stapel": name, "alt": alte_anzahl, "neu": anzahl, "delta": delta}
            )
    return sorted(treffer, key=lambda t: -t["delta"])


def kurzzeile(
    zahlen: dict[str, int],
    *,
    gewachsene: list[dict],
    erster_lauf: bool,
    stand_geschrieben: bool,
) -> str:
    """Eine Zeile. Stapelnamen und -zahlen sind unkritisch (keine Dokumenttitel)."""
    nachsatz = "" if stand_geschrieben else " [Zustand nicht gespeichert]"
    stand_text = ", ".join(
        f"{name}={anzahl}" for name, anzahl in sorted(zahlen.items())
    )
    if erster_lauf:
        return (
            f"rueckstau-melder: erster Lauf ({stand_text}) — "
            f"Vergleich erst ab dem naechsten Lauf moeglich{nachsatz}"
        )
    if gewachsene:
        delta_text = ", ".join(
            f"{g['stapel']} {g['alt']}->{g['neu']}" for g in gewachsene
        )
        return (
            f"rueckstau-melder: {len(gewachsene)} Stapel gewachsen: "
            f"{delta_text}{nachsatz}"
        )
    return f"rueckstau-melder: kein Stapel gewachsen ({stand_text}){nachsatz}"


def bericht(
    zahlen: dict[str, int],
    *,
    gewachsene: list[dict],
    erster_lauf: bool,
    stand_geschrieben: bool,
    toleranz: int,
) -> str:
    zeilen = [
        kurzzeile(
            zahlen,
            gewachsene=gewachsene,
            erster_lauf=erster_lauf,
            stand_geschrieben=stand_geschrieben,
        )
    ]
    zeilen.append(f"  Toleranz: Wachstum > {toleranz} gilt als Befund.")
    for name in sorted(zahlen):
        zeilen.append(f"    {name}: {zahlen[name]}")
    return "\n".join(zeilen)


# --- Messung -----------------------------------------------------------------


def messe(stapel: list[str], ssh: str | None) -> tuple[dict[str, int] | None, bool]:
    """Stapelzahlen aus der Paperless-DB lesen. Zweiter Wert: DB erreicht (rc==0)?"""
    sql = baue_sql(stapel)
    argv = [
        "docker",
        "exec",
        CONTAINER_DB,
        "psql",
        "-U",
        DB_USER,
        "-d",
        DB_NAME,
        "-t",
        "-A",
        "-F|",
        "-c",
        sql,
    ]
    rc, out = _lauf(argv, ssh)
    if rc != 0:
        return None, False
    return parse_zahlen(out, stapel), True


def lade_stand(pfad: Path) -> dict[str, dict] | None:
    """Letzten Stand laden. `None` = kein Vergleich moeglich (fehlt oder kaputt)."""
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    stapel = daten.get("stapel")
    return stapel if isinstance(stapel, dict) else None


def schreibe_stand(pfad: Path, zahlen: dict[str, int]) -> bool:
    """Stand fortschreiben. `False`, wenn der Ort nicht beschreibbar ist.

    Analog `scan_melder.schreibe_inventar()`: ein nicht beschreibbarer Pfad ist
    ein Hinweis, kein Grund, den Bericht zu verlieren (siehe Modul-Docstring).
    """
    try:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(
            json.dumps(
                {
                    "gemessen_am": time.time(),
                    "stapel": {
                        name: {"anzahl": anzahl, "gemessen_am": time.time()}
                        for name, anzahl in zahlen.items()
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--ssh", default=None, help="Host-Alias, wenn nicht auf prod gelaufen wird"
    )
    p.add_argument(
        "--stapel",
        default=",".join(STAPEL_DEFAULT),
        help=f"Kommagetrennte Stichwoerter (Default: {','.join(STAPEL_DEFAULT)})",
    )
    p.add_argument(
        "--stand",
        default=STAND,
        help="Pfad des Vergleichsstands; leer ('') schaltet den Vergleich ab",
    )
    p.add_argument(
        "--toleranz",
        type=int,
        default=TOLERANZ_DEFAULT,
        metavar="N",
        help=f"Wachstum > N gilt als Befund (Default {TOLERANZ_DEFAULT}, siehe Modul-Docstring)",
    )
    p.add_argument("--kurz", action="store_true")
    a = p.parse_args(argv)

    stapel = [s.strip().lower() for s in a.stapel.split(",") if s.strip()]
    if not stapel:
        print("rueckstau-melder: --stapel ist leer — nichts zu messen", file=sys.stderr)
        return 2

    zahlen, erreicht = messe(stapel, a.ssh)
    if not erreicht:
        print(
            "rueckstau-melder: Datenbank nicht erreichbar — blind, nicht gruen",
            file=sys.stderr,
        )
        return 2
    if zahlen is None:
        print(
            "rueckstau-melder: Antwort der Datenbank leer oder unlesbar — "
            "blind, nicht gruen",
            file=sys.stderr,
        )
        return 2

    stand_pfad = Path(a.stand) if a.stand else None
    alt = lade_stand(stand_pfad) if stand_pfad is not None else None
    erster_lauf = alt is None
    gewachsene = gewachsene_stapel(alt, zahlen, toleranz=a.toleranz)

    stand_geschrieben = True
    if stand_pfad is not None:
        stand_geschrieben = schreibe_stand(stand_pfad, zahlen)
        if not stand_geschrieben:
            print(
                f"rueckstau-melder: {stand_pfad} nicht beschreibbar — "
                "naechster Lauf kann nicht vergleichen",
                file=sys.stderr,
            )

    if a.kurz:
        print(
            kurzzeile(
                zahlen,
                gewachsene=gewachsene,
                erster_lauf=erster_lauf,
                stand_geschrieben=stand_geschrieben,
            )
        )
    else:
        print(
            bericht(
                zahlen,
                gewachsene=gewachsene,
                erster_lauf=erster_lauf,
                stand_geschrieben=stand_geschrieben,
                toleranz=a.toleranz,
            )
        )

    if erster_lauf:
        return 0
    return 1 if gewachsene else 0


if __name__ == "__main__":
    sys.exit(main())
