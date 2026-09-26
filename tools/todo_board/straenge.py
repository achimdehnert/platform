#!/usr/bin/env python3
"""Strang-Zuordnung fuer Verlaufseintraege eines Vorgangs — LLM statt Regex (platform#3175).

## Warum

`strang_schluessel()` (die alte Fassung von ``todo_board.py``) gruppierte Verlaufs-
eintraege nach dem ERSTEN Zitat in Anfuehrungszeichen. Bei Vorgang #128 (Befund im
Issue) erzeugte das Straenge wie ein woertliches Mail-Zitat ("I will do and share
with you as soon as possible") oder ein Dateiname ("5th Updated Proposal.docx") —
beides keine Mail-Straenge, sondern Textfragmente, die zufaellig in Anfuehrungs-
zeichen standen.

Dieses Modul ersetzt die Regex durch ein Modell: `zuordnen()` schickt alle
Eintraege eines Vorgangs samt seinem `thread_key` in EINEM Aufruf an ein Groq-
Modell und bekommt eine Nummer→Strang-Zuordnung zurueck. Eine deterministische
Nachpruefung (`_validiere`) verwirft jeden Titel, der weder der `thread_key` ist,
noch in einem der beiden festen Puffer-Straenge ("Notizen", "Prüfläufe ohne
Befund") liegt, noch im Text irgendeines Eintrags vorkommt — ein frei erfundener
Titel landet dann in "Notizen".

## Aufrufmuster

Dasselbe Muster wie ``tools/verankerung_pruefer.py`` (Groq, OpenAI-kompatibler
Endpunkt, ``response_format: json_object``, Schluessel NUR aus ``GROQ_API_KEY``
in der Umgebung): ``GROQ_DEFAULT_MODELL`` und der Schluessel-Lader
``_groq_schluessel`` werden von dort importiert statt kopiert.

## Betrieb — Cache und Vorwaermen

Ein Seitenaufruf von ``todo_board.py`` darf NIE 60 Sekunden auf ein Modell
warten. Deshalb:

* Jedes Ergebnis wird unter ``sha256(modell + notiz)`` in
  ``~/.claude/todo-straenge-cache.json`` (Modulkonstante ``CACHE_DATEI``, in
  Tests per ``monkeypatch.setattr`` umlenkbar) zwischengespeichert. Ein
  Cache-Treffer ruft das Modell NICHT erneut auf.
* Ohne Cache-Treffer ruft `zuordnen()` das Modell nur, wenn ein `klassifikator`
  explizit hereingereicht wird ODER die Umgebungsvariable
  ``TODO_STRAENGE_SYNCHRON=1`` gesetzt ist. Sonst liefert es sofort den
  Rueckfall — EIN Strang (Titel = `thread_key` oder "Verlauf") — ohne zu
  cachen und ohne Ausnahme nach aussen.
* ``python3 tools/todo_board/straenge.py --vorwaermen`` fuellt den Cache fuer
  ALLE Vorgaenge des Ledgers, die noch fehlen — das Rendern selbst ruft dieses
  Kommando NICHT auf. Es laeuft am sinnvollsten NACH jeder Ledger-Aenderung
  (z. B. nach ``/mailcheck``); die Einbindung in einen Timer ist Folgeschritt
  der Kapitaens-Sitzung (K5 aus platform#3175).

Jeder Fehler auf dem Modell-Weg — fehlender Schluessel, Netzfehler, Timeout
(<= 60 s), ungueltiges JSON — faellt auf den EIN-Strang-Rueckfall zurueck. Ein
Seitenaufruf scheitert nie am LLM.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verankerung_pruefer import (  # noqa: E402
    GROQ_DEFAULT_MODELL,
    GROQ_ENDPOINT,
    GROQ_KENNUNG,
    _groq_schluessel,
)

#: Zwischenspeicher Nummer→Strang je Vorgang — siehe Modul-Docstring "Betrieb".
CACHE_DATEI = Path.home() / ".claude" / "todo-straenge-cache.json"
#: Nur gelesen (fuer ``--vorwaermen``) — dasselbe Ledger wie ``todo_board.LEDGER``.
LEDGER = Path.home() / ".claude" / "mail-vorgaenge.json"

#: Titel ohne erkennbaren Mail-Bezug.
NOTIZEN_TITEL = "Notizen"
#: Reine Pruefungen ohne neues Ereignis ("kein neuer Eingang", "DB bis ... — leer").
PRUEFLAEUFE_TITEL = "Prüfläufe ohne Befund"
#: Rueckfall-Titel, wenn der Vorgang selbst keinen `thread_key` traegt.
RUECKFALL_TITEL = "Verlauf"

#: Ein Aufruf darf die Seite nicht laenger blockieren als das (K3, platform#3175).
TIMEOUT_SEKUNDEN = 60
MAX_ANTWORT_TOKEN = 4000

_PRAEFIX = re.compile(r"^(?:AW|RE|WG|FWD)\s*:\s*", re.IGNORECASE)


def _normalisiere_titel(text: str) -> str:
    """Antwort-Praefixe weg, Whitespace vereinheitlicht, kleingeschrieben.

    Dieselbe Normalisierung, die vorher `strang_schluessel()` je Eintrag machte
    — hier auf einen kompletten Strang-Titel angewendet, damit "AW: Angebot"
    und "Angebot" als derselbe Strang gelten.
    """
    text = str(text or "").strip()
    while True:
        gekuerzt = _PRAEFIX.sub("", text)
        if gekuerzt == text:
            break
        text = gekuerzt
    return re.sub(r"\s+", " ", text).strip().casefold()


PROMPT = """Du ordnest Verlaufseintraege EINES Vorgangs ihrem Mail-Strang zu.

Ein Strang ist der Betreff der Mail-Kette, um die es in dem Eintrag geht — ohne
die Praefixe AW:/Re:/WG:/Fwd:. Zwei Sonderfaelle:

* Ein Eintrag, der NUR eine Pruefung ohne neues Ereignis protokolliert (z. B.
  "kein neuer Eingang im Strang", "DB bis ... — leer", reine Erhebung ohne
  Sachstand), gehoert in den Strang "Prüfläufe ohne Befund".
* Ein Eintrag ohne erkennbaren Mail-Betreff (interne Notiz, Owner-Aufgabe ohne
  Mailbezug, ein blosses Zitat oder ein Dateiname OHNE zugehoerigen Betreff im
  selben Eintrag) gehoert in den Strang "Notizen".

Ein Vorgang kann MEHRERE Mail-Ketten haben. Nennt ein Eintrag eine Mail mit
anderem Betreff als der Hauptstrang (z. B. eine neue Mail mit eigenem Betreff,
eine Antwort darauf, ihren Anhang), gehoert er in den Strang DIESES Betreffs —
nicht in den Hauptstrang. Verwende den Betreff so, wie er im Eintrag steht.

Bekannter Hauptstrang dieses Vorgangs (thread_key): "%s"

Verlaufseintraege (Nummer: Text):
%s

Antworte NUR mit JSON: {"zuordnung": {"<nummer>": "<strang>"}}"""


def _prompt(vorgang: dict, eintraege: list[tuple[int, str]]) -> str:
    thread_key = str(vorgang.get("thread_key") or "")
    zeilen = "\n".join(f"{nummer}: {text}" for nummer, text in eintraege)
    return PROMPT % (thread_key, zeilen)


def _cache_schluessel(modell: str, notiz: str) -> str:
    return hashlib.sha256(f"{modell}\n{notiz}".encode("utf-8")).hexdigest()


def _cache_laden(pfad: Path) -> dict:
    try:
        with pfad.open(encoding="utf-8") as fh:
            daten = json.load(fh)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return daten if isinstance(daten, dict) else {}


def _cache_schreiben(pfad: Path, daten: dict) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_name(pfad.name + ".tmp")
    tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(pfad)


def _standard_klassifikator(vorgang: dict, eintraege: list[tuple[int, str]]) -> dict:
    """Der eingebaute Groq-Aufruf — dasselbe Muster wie `verankerung_pruefer.groq_klassifikator`.

    `_groq_schluessel()` wirft, wenn `GROQ_API_KEY` fehlt — das ist hier
    ausdruecklich gewollt: der Aufrufer (`zuordnen`) faengt jeden Fehler dieses
    Wegs ab und faellt auf EINEN Strang zurueck.
    """
    schluessel = _groq_schluessel()
    rumpf = json.dumps(
        {
            "model": GROQ_DEFAULT_MODELL,
            "messages": [{"role": "user", "content": _prompt(vorgang, eintraege)}],
            "temperature": 0,
            # gpt-oss denkt vor der Antwort; 800 Token reichten bei Vorgang #128
            # (24 Eintraege) nicht, Groq meldete json_validate_failed mit leerer
            # Generation (2026-09-14). Mehr Budget, wenig Denkaufwand.
            "max_tokens": MAX_ANTWORT_TOKEN,
            "reasoning_effort": "low",
            "response_format": {"type": "json_object"},
        }
    ).encode()
    req = urllib.request.Request(
        GROQ_ENDPOINT,
        data=rumpf,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {schluessel}",
            "User-Agent": GROQ_KENNUNG,
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEKUNDEN) as antwort:
        umschlag = json.load(antwort)
    roh = umschlag["choices"][0]["message"]["content"]
    return json.loads(roh)


def _ein_strang(vorgang: dict, eintraege: list[tuple[int, str]]) -> dict[int, str]:
    """Rueckfall: alle Eintraege in EINEN Strang (K3, platform#3175)."""
    titel = str(vorgang.get("thread_key") or "").strip() or RUECKFALL_TITEL
    return {nummer: titel for nummer, _text in eintraege}


def _validiere(
    vorgang: dict, eintraege: list[tuple[int, str]], roh: dict
) -> dict[int, str]:
    """Rohe Modell-Zuordnung deterministisch nachpruefen (K2, platform#3175).

    Ein Titel gilt nur, wenn er normalisiert gleich dem normalisierten
    `thread_key` ist, ODER einer der beiden festen Puffer-Titel ist, ODER als
    Teilstring im (kleingeschriebenen) Text IRGENDEINES Eintrags des Vorgangs
    vorkommt. Jeder andere Titel — und jede fehlende Nummer — wird zu
    "Notizen". Anzeige-Titel ist die Original-Schreibweise des ERSTEN
    Vorkommens je normalisiertem Schluessel (Ausnahme: der `thread_key` selbst
    und die beiden festen Titel behalten immer ihre kanonische Schreibweise).
    """
    thread_key = str(vorgang.get("thread_key") or "").strip()
    thread_norm = _normalisiere_titel(thread_key)
    feste_norm = {
        _normalisiere_titel(PRUEFLAEUFE_TITEL): PRUEFLAEUFE_TITEL,
        _normalisiere_titel(NOTIZEN_TITEL): NOTIZEN_TITEL,
    }
    texte_norm = [str(text or "").casefold() for _nummer, text in eintraege]
    zuordnung_roh = roh.get("zuordnung") if isinstance(roh, dict) else None
    zuordnung_roh = zuordnung_roh if isinstance(zuordnung_roh, dict) else {}

    anzeige_je_norm: dict[str, str] = dict(feste_norm)
    if thread_key:
        anzeige_je_norm[thread_norm] = thread_key

    ergebnis: dict[int, str] = {}
    for nummer, _text in eintraege:
        titel_roh = str(zuordnung_roh.get(str(nummer), "") or "").strip()
        titel_norm = _normalisiere_titel(titel_roh)
        gueltig = bool(titel_norm) and (
            titel_norm == thread_norm
            or titel_norm in feste_norm
            or any(titel_norm in t for t in texte_norm)
        )
        if not gueltig:
            titel_norm = _normalisiere_titel(NOTIZEN_TITEL)
            titel_roh = NOTIZEN_TITEL
        if titel_norm not in anzeige_je_norm:
            anzeige_je_norm[titel_norm] = titel_roh or NOTIZEN_TITEL
        ergebnis[nummer] = anzeige_je_norm[titel_norm]
    return ergebnis


def _abrufen_und_validieren(
    vorgang: dict,
    eintraege: list[tuple[int, str]],
    klassifikator: Callable[[dict, list], dict] | None,
) -> dict[int, str] | None:
    """Modell aufrufen und validieren — `None` bei JEDEM Fehlschlag.

    Die Fehlerklassen aus K3 (fehlender Schluessel, Netzfehler, Timeout,
    ungueltiges JSON, unerwartete Antwortform) landen bewusst in EINEM breiten
    except: der Aufrufer kennt nur zwei Zustaende — "Ergebnis" oder "Rueckfall"
    — und ein Seitenaufruf darf an keinem dieser Wege scheitern.
    """
    aktiv = klassifikator or _standard_klassifikator
    try:
        roh = aktiv(vorgang, eintraege)
    except (
        RuntimeError,
        OSError,
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
    ):
        return None
    if not isinstance(roh, dict) or not isinstance(roh.get("zuordnung"), dict):
        return None
    return _validiere(vorgang, eintraege, roh)


def zuordnen(
    vorgang: dict,
    eintraege: list[tuple[int, str]],
    klassifikator: Callable[[dict, list], dict] | None = None,
) -> dict[int, str]:
    """Nummer→Strang-Zuordnung fuer die Eintraege EINES Vorgangs (K2, platform#3175).

    `eintraege` sind (nummer, roh_text)-Paare. Ein Cache-Treffer (Schluessel
    `sha256(modell + notiz)`, `notiz` = alle Eintraege mit " | " verbunden)
    ruft das Modell nicht erneut auf. Ohne Treffer wird das Modell NUR
    aufgerufen, wenn `klassifikator` explizit gesetzt ist oder die Umgebung
    `TODO_STRAENGE_SYNCHRON=1` traegt — sonst liefert diese Funktion sofort
    den EIN-Strang-Rueckfall, damit ein Seitenaufruf nie auf ein Modell wartet.
    """
    if not eintraege:
        return {}
    notiz = " | ".join(str(text) for _nummer, text in eintraege)
    schluessel = _cache_schluessel(GROQ_DEFAULT_MODELL, notiz)
    cache = _cache_laden(CACHE_DATEI)
    treffer = cache.get(schluessel)
    if isinstance(treffer, dict):
        rueckfall = str(vorgang.get("thread_key") or "").strip() or NOTIZEN_TITEL
        return {
            nummer: treffer.get(str(nummer), rueckfall) for nummer, _text in eintraege
        }

    synchron = (
        klassifikator is not None or os.environ.get("TODO_STRAENGE_SYNCHRON") == "1"
    )
    if not synchron:
        return _ein_strang(vorgang, eintraege)

    ergebnis = _abrufen_und_validieren(vorgang, eintraege, klassifikator)
    if ergebnis is None:
        return _ein_strang(vorgang, eintraege)

    neu = dict(cache)
    neu[schluessel] = {str(n): t for n, t in ergebnis.items()}
    _cache_schreiben(CACHE_DATEI, neu)
    return ergebnis


def _vorwaermen(ledger_pfad: Path = LEDGER, cache_pfad: Path = CACHE_DATEI) -> int:
    """Cache fuer alle Vorgaenge des Ledgers fuellen, denen ein Treffer fehlt.

    Ruft — anders als `zuordnen()` beim Rendern — IMMER das Modell auf, wenn
    kein Cache-Treffer vorliegt: das ist der ganze Zweck dieses Kommandos.
    """
    try:
        with ledger_pfad.open(encoding="utf-8") as fh:
            daten = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FEHLER: Ledger nicht lesbar: {exc}", file=sys.stderr)
        return 2
    vorgaenge = daten.get("vorgaenge", []) if isinstance(daten, dict) else []
    gefuellt = 0
    fehler = 0
    uebersprungen = 0
    # Spaeter Import: todo_board importiert dieses Modul auf Modulebene.
    import todo_board  # noqa: PLC0415

    erster_fehler = ""
    for vorgang in vorgaenge:
        eintraege = [(n, t) for n, t in todo_board.strang_eingaben(vorgang) if t]
        if not eintraege:
            continue
        notiz = " | ".join(text for _nummer, text in eintraege)
        schluessel = _cache_schluessel(GROQ_DEFAULT_MODELL, notiz)
        if schluessel in _cache_laden(cache_pfad):
            uebersprungen += 1
            continue
        try:
            ergebnis = _validiere(
                vorgang, eintraege, _standard_klassifikator(vorgang, eintraege)
            )
        except Exception as exc:  # noqa: BLE001 — Kommando zaehlt und benennt, statt abzubrechen
            fehler += 1
            erster_fehler = erster_fehler or f"{type(exc).__name__}: {str(exc)[:120]}"
            continue
        cache = _cache_laden(cache_pfad)
        cache[schluessel] = {str(n): t for n, t in ergebnis.items()}
        _cache_schreiben(cache_pfad, cache)
        gefuellt += 1
    print(
        f"OK: {gefuellt} Vorgaenge neu im Cache, {uebersprungen} bereits vorhanden, "
        f"{fehler} Fehler."
        + (f" Erster Fehler: {erster_fehler}" if erster_fehler else "")
    )
    return 1 if fehler else 0


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    ap.add_argument(
        "--vorwaermen",
        action="store_true",
        help="Cache fuer alle Vorgaenge des Ledgers fuellen (fehlende Eintraege)",
    )
    args = ap.parse_args()
    if not args.vorwaermen:
        ap.error("nichts zu tun ohne --vorwaermen")
    sys.exit(_vorwaermen())


if __name__ == "__main__":
    main()
