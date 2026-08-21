#!/usr/bin/env python3
"""Verlaufseinträge auf die Mail auflösen, die sie meinen.

Warum es das gibt (Owner-Wunsch 2026-08-21): Ein Verlaufseintrag sagt „Eigene
Antwort 14.08. 05:23 im Nachbarstrang 'AW: Besprechungszusammenfassung …'". Die
Mail dazu existiert, aber der Weg dorthin ist Handarbeit — Postfach öffnen,
Datum suchen, Betreff vergleichen.

**Aufgelöst wird beim Board-Bau, nicht beim Seitenaufruf.** Der Mail-Index hängt
an SSH; pro Seitenaufruf wären das Sekunden, und eine Ansicht, die drei Sekunden
lädt, macht man nicht mehr auf. Dieses Werkzeug fragt den Index **einmal** und
legt die Zuordnung als Datei ab, die die Seite nur noch liest.

**Ein falscher Link ist schlimmer als keiner.** Deshalb wird nur zugeordnet, was
eindeutig ist: normalisierter Betreff **und** Tag müssen passen, und wenn mehrere
Nachrichten desselben Tages denselben Betreff tragen, entscheidet die Richtung
(„Eigene Antwort" ⇒ Gesendet). Bleibt es mehrdeutig, entsteht kein Link.

Read-only. Die Ausgabedatei liegt unter ~/.claude, nie in einem Repo.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent
LEDGER = Path.home() / ".claude" / "mail-vorgaenge.json"
VERLAUF_ARCHIV = Path.home() / ".claude" / "mail-vorgaenge-archiv.json"
AUSGABE = Path.home() / ".claude" / "mail-eintrag-links.json"

#: Betreff in einfachen oder typografischen Anführungszeichen.
_BETREFF = re.compile(r"['‚'\"„»]([^'''\"«»\n]{6,120})['''\"«»]")

#: Deutsche Kurzform mit optionalem Jahr: 14.08. / 14.08.2026
_TAG_KURZ = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})?")
_ISO = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")

#: Der Eintrag spricht über etwas, das WIR geschickt haben.
_AUSGEHEND = re.compile(r"eigene\s+antwort|gesendet|entwurf|nachfass", re.I)

#: Präfixe, die denselben Strang unterschiedlich benennen.
_PRAEFIX = re.compile(r"^\s*(?:aw|re|wg|fwd|antw)\s*:\s*", re.I)


def normalisiere(betreff: str) -> str:
    text = betreff.strip()
    while True:
        neu = _PRAEFIX.sub("", text)
        if neu == text:
            break
        text = neu
    return re.sub(r"\s+", " ", text).strip().lower()


def index_lesen(seit: str, limit: int, cache: Path | None) -> list[dict]:
    if cache and cache.exists():
        return json.loads(cache.read_text(encoding="utf-8")).get("treffer", [])
    roh = subprocess.run(
        [
            sys.executable,
            str(HIER / "suche.py"),
            "--seit",
            seit,
            "--limit",
            str(limit),
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if roh.returncode != 0:
        raise RuntimeError(f"Mail-Index nicht erreichbar: {roh.stderr[:160]}")
    daten = json.loads(roh.stdout)
    if cache:
        cache.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
    return daten.get("treffer", [])


def eintrags_datum(text: str, bezugsjahr: int) -> date | None:
    """Das Datum, das der Eintrag MEINT — nicht das, an dem er geschrieben wurde.

    Ein Eintrag beginnt mit seinem Bearbeitungsdatum (ISO) und nennt im Text die
    Kurzform des Ereignisses (`14.08. 05:23`). Gemeint ist die Kurzform; die ISO-Form
    ist nur der Zeitpunkt der Notiz.
    """
    kurz = _TAG_KURZ.search(text)
    if kurz:
        tag, monat, jahr = kurz.groups()
        try:
            return date(int(jahr or bezugsjahr), int(monat), int(tag))
        except ValueError:
            return None
    iso = _ISO.search(text)
    if iso:
        try:
            return datetime.strptime(iso.group(1), "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _ausgehend(nachricht: dict) -> bool:
    return any("esendet" in o for o in nachricht.get("ordner", []))


def treffer(text: str, nachrichten: list[dict], bezugsjahr: int) -> dict | None:
    """Die eine Mail, die dieser Eintrag meint — oder nichts."""
    betreff = _BETREFF.search(text)
    tag = eintrags_datum(text, bezugsjahr)
    if not betreff or not tag:
        return None
    ziel = normalisiere(betreff.group(1))
    if len(ziel) < 6:
        return None
    kandidaten = [
        m
        for m in nachrichten
        if normalisiere(m.get("betreff", "")) == ziel
        and m.get("datum") == tag.isoformat()
    ]
    if not kandidaten:
        return None
    if len(kandidaten) > 1:
        richtung = bool(_AUSGEHEND.search(text))
        gefiltert = [m for m in kandidaten if _ausgehend(m) is richtung]
        if len(gefiltert) != 1:
            return None  # mehrdeutig — lieber kein Link
        kandidaten = gefiltert
    return kandidaten[0]


#: Eine adressierbare Mail-Nummer IM TEXT des Eintrags. Der Index liefert sie
#: nicht: seine `id` ist ein Datenbankschluessel, keine IMAP-UID — ein daraus
#: gebauter Link ergab 404 (gemessen 2026-08-21). Adressierbar ist nur, was der
#: Eintrag selbst nennt.
_UID_IM_TEXT = re.compile(r"(?:UID|INBOX\s*#|Objekte'?\s*\(#|#)\s*(\d{4,6})", re.I)
#: Steht die Nummer im Umfeld des Sendeordners, liegt die Mail dort.
_SENDEORDNER_NAH = re.compile(r"gesendet|sendeordner|gesendete", re.I)


def url_aus_text(text: str, konto: str, basis: str) -> str:
    """Link auf die Mail — nur wenn der Eintrag eine adressierbare Nummer nennt.

    Kein Link ist besser als ein falscher: ohne Nummer bleibt es bei Betreff und
    Datum in der Kopfzeile, die den Eintrag identifizieren, ohne etwas zu
    versprechen.
    """
    treffer_ = _UID_IM_TEXT.search(text)
    if not treffer_ or not konto:
        return ""
    nummer = treffer_.group(1)
    umfeld = text[max(0, treffer_.start() - 60) : treffer_.end() + 20]
    ordner = "gesendete/" if _SENDEORDNER_NAH.search(umfeld) else ""
    return f"{basis.rstrip('/')}/m/{konto}/{ordner}{nummer}"


def verlauf_eintraege(v: dict, archiv: dict) -> list[str]:
    aktiv = [t.strip() for t in str(v.get("notiz") or "").split(" | ") if t.strip()]
    return [str(e) for e in archiv.get(str(v.get("nr")), [])] + aktiv


def zuordnen(ledger: dict, archiv: dict, nachrichten: list[dict], basis: str) -> dict:
    """→ {vorgangsnummer: {eintragsnummer: {url, betreff, datum}}}

    Die Eintragsnummer zählt vom ÄLTESTEN Ende — sie muss stabil bleiben, wenn
    oben neue Einträge dazukommen.
    """
    ergebnis: dict[str, dict] = {}
    for v in ledger.get("vorgaenge", []):
        konto = str(v.get("konto") or "")
        eintraege = verlauf_eintraege(v, archiv)
        je_vorgang: dict[str, dict] = {}
        for i, text in enumerate(eintraege, start=1):
            bezug = eintrags_datum(text, date.today().year)
            jahr = bezug.year if bezug else date.today().year
            m = treffer(text, nachrichten, jahr)
            if not m:
                continue
            je_vorgang[str(i)] = {
                "url": url_aus_text(text, konto, basis),
                "betreff": m.get("betreff", ""),
                "datum": m.get("datum", ""),
            }
        if je_vorgang:
            ergebnis[str(v.get("nr"))] = je_vorgang
    return ergebnis


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--verlauf-archiv", default=str(VERLAUF_ARCHIV))
    ap.add_argument("--basis", default="https://mail.iil.pet")
    ap.add_argument("--seit", default="2026-06-01")
    ap.add_argument("--limit", type=int, default=900)
    ap.add_argument("--index-cache", default=None)
    ap.add_argument("--schreibe", nargs="?", const=str(AUSGABE), default=None)
    args = ap.parse_args()

    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    try:
        archiv = json.loads(Path(args.verlauf_archiv).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        archiv = {}
    try:
        nachrichten = index_lesen(
            args.seit, args.limit, Path(args.index_cache) if args.index_cache else None
        )
    except (RuntimeError, json.JSONDecodeError) as fehler:
        print(f"Keine Zuordnung: {fehler}")
        return 1

    ergebnis = zuordnen(ledger, archiv, nachrichten, args.basis)
    gesamt = sum(len(verlauf_eintraege(v, archiv)) for v in ledger.get("vorgaenge", []))
    zugeordnet = sum(len(x) for x in ergebnis.values())
    quote = round(100 * zugeordnet / gesamt) if gesamt else 0
    print(
        f"{zugeordnet} von {gesamt} Verlaufseintraegen aufgeloest ({quote} %) "
        f"ueber {len(nachrichten)} indizierte Nachrichten"
    )
    for nr, eintraege in sorted(ergebnis.items(), key=lambda x: int(x[0])):
        print(
            f"  #{nr}: " + ", ".join(f"{k}→{e['datum']}" for k, e in eintraege.items())
        )
    if args.schreibe:
        Path(args.schreibe).write_text(
            json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Geschrieben: {Path(args.schreibe).name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
