#!/usr/bin/env python3
"""Messjournal je Lauf fuer Mailcheck und To-do-Liste (K2, #3015).

Jeder Lauf von Mailcheck oder To-do-Liste haengt eine Zeile an ein
maschinenlesbares Journal: Zeitpunkt, Anwendung, Modellkennung und die
Kennzahlen, die `docs/betrieb/mailcheck.md` bzw. `docs/betrieb/todo-liste.md`
im Abschnitt "Kennzahlen je Lauf" nennen. Die Kennzahlen kommen aus den dort
genannten Quellkommandos (je eines ein `subprocess.run` mit Timeout) — schlaegt
eines fehl oder liefert unlesbare Ausgabe, wird der Wert `null` und die
Kennzahl landet im Feld `fehler`. Ein einzelnes scheiterndes Kommando bricht
den Lauf nie ab.

**Nie Personendaten.** Die Journalzeile enthaelt ausschliesslich Zahlen, Daten
und Bezeichner — nie Adressen, Betreffs oder Namen aus dem Vorgangs-Ledger
(`~/.claude/mail-vorgaenge.json`). Wo dieses Werkzeug das Ledger liest (fuer
`ohne_kopf_aktion` und `geschlossen_7_tage`), zaehlt es nur — der Inhalt
einzelner Vorgaenge verlaesst diese Funktion nie.

Kommandos::

    python3 tools/mail_agent/messjournal.py --schreiben --anwendung mailcheck
    python3 tools/mail_agent/messjournal.py --schreiben --anwendung todo
    python3 tools/mail_agent/messjournal.py --schreiben --anwendung auftragsraum
    python3 tools/mail_agent/messjournal.py --schreiben --anwendung alle
    python3 tools/mail_agent/messjournal.py --trend
    python3 tools/mail_agent/messjournal.py --trend --anwendung mailcheck --n 7

`--anwendung auftragsraum` (KONZ-platform-059, #3079) erhebt vier Kennzahlen
aus dem rohen Ereignis-Journal des Auftragsraums
(`~/.claude/auftragsraum-journal.jsonl`, geschrieben von
`tools/chat_agent/auftragsraum.py sortieren`) statt ein eigenes Kommando
aufzurufen: `nachrichten_je_klasse` (Objekt, letzte 7 Tage),
`korrekturen_ohne_artefakt_24h`, `mittlere_stunden_bis_bearbeitung`,
`anteil_angewendete_kurzbefehle`. `tokens` bleibt in Stufe 1 immer `null`
(Feld der Auftragsraum-Journalzeile selbst, nicht dieser Kennzahlen).
`--anwendung alle` schliesst `auftragsraum` mit ein.

`--anwendung sevdesk` (#3102) liest analog NUR die juengste Zeile des rohen
Lauf-Journals von `tools/sevdesk/rechnungslauf.py`
(`~/.claude/sevdesk-rechnungslauf-journal.jsonl`, eine Zeile je Lauf, vom
Werkzeug selbst geschrieben) — fuenf Kennzahlen ohne eigene Erhebung:
`entwuerfe_angelegt`, `uebersprungen`, `gesendet`, `wiederholungen_429`,
`dauer_sekunden`. `--anwendung alle` schliesst `sevdesk` mit ein.

`--anwendung alle` (oder zweimal `--anwendung`) erhebt mailcheck UND todo in
einem Prozess und schreibt zwei Zeilen. Grund (#3067): beide Anwendungen
teilen sich eine teure Quelle — `link_pruefen.py --vorgangsseiten` (184 Links,
ueber zwei Minuten Laufzeit, gemessen). Zwei getrennte Prozesse (wie bis
#3067 in `make boards`) liessen sie zweimal laufen und rissen den
10-Minuten-Timeout von `make boards`. Mit `--anwendung alle` laeuft sie genau
einmal, ihr Ergebnis geht in beide Journalzeilen ein.

`--eingabe JSON` (Inline-JSON oder Pfad zu einer JSON-Datei) ersetzt die
Kommandos durch feste Werte — fuer Tests, ganz ohne Postfach oder Netz. Bei
`--anwendung alle` deckt ein einzelnes `--eingabe`-JSON beide Anwendungen ab:
jede Zeile liest daraus nur die fuer sie benannten Kennzahlen.

`--ablage-ausgabe DATEI` (#3069, Folge von #3076) ersetzt NUR den eigenen Lauf
von `ablage_erledigt.py --pruefe`: die Datei enthaelt dessen bereits erzeugte
Textausgabe (stdout+stderr), z. B. weil `make boards` den Melder ohnehin schon
einmal aufgerufen hat. Gemessen am 2026-09-10 kostet dieser Lauf allein 253s
(75 Abfragen gegen den Mail-Index) — ein zweiter Aufruf allein fuer das
Messjournal verdoppelte die Laufzeit von `make boards`, ohne ein zweites
Ergebnis zu liefern.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TOOL_VERSION = "messjournal.py/1"

REPO = Path(__file__).resolve().parents[2]
MAIL_AGENT_DIR = Path(__file__).resolve().parent
TODO_BOARD_DIR = REPO / "tools" / "todo_board"

JOURNAL_DEFAULT = Path.home() / ".claude" / "mail-messjournal.jsonl"

#: Rohes Ereignis-Journal des Auftragsraums (`auftragsraum.py sortieren`) —
#: eigene Datei, eigenes Format (eine Zeile je Nachricht, nicht je Lauf).
AUFTRAGSRAUM_JOURNAL_DEFAULT = Path.home() / ".claude" / "auftragsraum-journal.jsonl"

#: Rohes Lauf-Journal von `rechnungslauf.py` (#3102) — eine Zeile je Lauf,
#: vom Werkzeug selbst geschrieben; hier wird nur die juengste gelesen.
SEVDESK_JOURNAL_DEFAULT = (
    Path.home() / ".claude" / "sevdesk-rechnungslauf-journal.jsonl"
)

TIMEOUT = 120

#: `link_pruefen.py --vorgangsseiten` allein: 184 Links, gemessen 2m24s
#: (#3067) — der allgemeine TIMEOUT=120s reichte nicht und liess
#: `vorgangsseiten_geprueft`/`_tot`/`mail_links_tot` regelmaessig auf `null`
#: fallen. Eigener, groesserer Timeout mit Marge statt am generischen Wert
#: zu drehen (der fuer die schnellen Quellen passt).
LINK_PRUEFEN_TIMEOUT = 240

#: Reihenfolge und Namen der Kennzahlen je Anwendung — bestimmt sowohl, was
#: `--schreiben` real erhebt, als auch, welche Schluessel `--eingabe` kennt.
KENNZAHLEN_MAILCHECK = (
    "vorgaenge_gesamt",
    "ohne_frist",
    "referenzen_ohne_ordner",
    "unverankert",
    "vorgangsseiten_geprueft",
    "vorgangsseiten_tot",
    "posteingang_geschlossene_vorgaenge",
    "index_alter_tage",
)

KENNZAHLEN_TODO = (
    "vorgangsseiten",
    "mail_links",
    "mail_links_tot",
    "geschlossen_7_tage",
    "ohne_kopf_aktion",
)

KENNZAHLEN_AUFTRAGSRAUM = (
    "nachrichten_je_klasse",
    "korrekturen_ohne_artefakt_24h",
    "mittlere_stunden_bis_bearbeitung",
    "anteil_angewendete_kurzbefehle",
)

KENNZAHLEN_SEVDESK = (
    "entwuerfe_angelegt",
    "uebersprungen",
    "gesendet",
    "wiederholungen_429",
    "dauer_sekunden",
)

_FEHLT = object()


def _run(args: list[str], timeout: int = TIMEOUT) -> tuple[str, str, int | None]:
    """Kommando ausfuehren. Rueckgabe (stdout, stderr, returncode).

    `returncode` ist `None` bei Timeout oder wenn das Kommando gar nicht
    starten konnte (fehlendes Binary, kaputter Pfad) — nie eine Ausnahme.
    """
    try:
        lauf = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout, cwd=REPO
        )
        return lauf.stdout, lauf.stderr, lauf.returncode
    except subprocess.TimeoutExpired:
        return "", f"Timeout nach {timeout}s", None
    except OSError as exc:
        return "", str(exc), None


def _zahl(pattern: str, text: str, gruppe: int = 1) -> int | None:
    treffer = re.search(pattern, text)
    if not treffer:
        return None
    try:
        return int(treffer.group(gruppe))
    except (ValueError, IndexError):
        return None


# --- Mailcheck: echte Erhebung je Kennzahl -------------------------------


def _mailcheck_board() -> dict[str, int | None]:
    out, err, _rc = _run([sys.executable, str(MAIL_AGENT_DIR / "board.py"), "--pruefe"])
    text = out + "\n" + err
    gesamt = _zahl(r"(\d+)\s+Vorgaenge:", text)
    if gesamt is None:
        gesamt = _zahl(r"bei\s+(\d+)\s+Vorgaengen\.", text)
    ohne_frist: int | None = None
    if gesamt is not None:
        ohne_frist = len(re.findall(r"keine Frist und kein frist_grund", text))
    return {"vorgaenge_gesamt": gesamt, "ohne_frist": ohne_frist}


def _mailcheck_referenzen() -> dict[str, int | None]:
    out, _err, _rc = _run(
        [
            sys.executable,
            str(MAIL_AGENT_DIR / "referenzen.py"),
            "--pruefe-ordner",
            "--json",
        ]
    )
    try:
        daten = json.loads(out)
        return {"referenzen_ohne_ordner": len(daten.get("ab_stichtag", []))}
    except (ValueError, TypeError, AttributeError):
        return {"referenzen_ohne_ordner": None}


def _mailcheck_anker() -> dict[str, int | None]:
    out, err, _rc = _run(
        [sys.executable, str(MAIL_AGENT_DIR / "eintrag_anker.py"), "--nur-zaehlen"]
    )
    text = out + err
    return {"unverankert": _zahl(r"(\d+)\s+ohne Anker", text)}


def _link_pruefen_vorgangsseiten() -> dict[str, int | None]:
    """`link_pruefen.py --vorgangsseiten` — Netz, kann fehlen (Dienst lokal).

    Eigener Timeout `LINK_PRUEFEN_TIMEOUT` statt des allgemeinen `TIMEOUT`
    (#3067) — 184 Links brauchen gemessen ueber zwei Minuten."""
    out, err, _rc = _run(
        [sys.executable, str(MAIL_AGENT_DIR / "link_pruefen.py"), "--vorgangsseiten"],
        timeout=LINK_PRUEFEN_TIMEOUT,
    )
    text = out + err
    return {
        "seiten": _zahl(r"(\d+)\s+Vorgangsseiten,", text),
        "links": _zahl(r"Vorgangsseiten,\s*(\d+)\s+Links", text),
        "geprueft": _zahl(r"(\d+)\s+geprueft,", text),
        "tot": _zahl(r"geprueft,\s*(\d+)\s+nicht in Ordnung", text),
    }


def _mailcheck_ablage_aus_text(text: str) -> dict[str, int | None]:
    """Die Kennzahl aus der `--pruefe`-Textausgabe von `ablage_erledigt.py` lesen.

    Eigene Funktion (#3069), damit sowohl der echte Lauf (`_mailcheck_ablage`)
    als auch eine bereits anderswo erzeugte Ausgabe (`--ablage-ausgabe`)
    denselben Text gleich auswerten."""
    treffer = re.findall(
        r":\s*(\d+)\s+Posteingangs-Mails gehoeren zu geschlossenen Vorgaengen", text
    )
    if treffer:
        wert: int | None = sum(int(n) for n in treffer)
    elif "Grundlage:" in text:
        wert = 0  # Lauf durchgelaufen, kein Konto mit Treffern
    else:
        wert = None
    return {"posteingang_geschlossene_vorgaenge": wert}


def _mailcheck_ablage() -> dict[str, int | None]:
    out, err, _rc = _run(
        [sys.executable, str(MAIL_AGENT_DIR / "ablage_erledigt.py"), "--pruefe"]
    )
    return _mailcheck_ablage_aus_text(out + err)


def _mailcheck_index_alter() -> int | None:
    out, err, _rc = _run(
        [sys.executable, str(MAIL_AGENT_DIR / "suche.py"), "--nur-deckung"]
    )
    text = out + err
    daten = re.findall(r"\d{4}-\d{2}-\d{2}", text)
    if not daten:
        return None
    try:
        letztes = date.fromisoformat(daten[-1])
    except ValueError:
        return None
    heute = datetime.now(timezone.utc).date()
    return (heute - letztes).days


def _mailcheck_erheben(
    links: dict[str, int | None] | None = None,
    ablage: dict[str, int | None] | None = None,
) -> dict[str, int | None]:
    """Mailcheck-Rohwerte. `links` optional vorgegeben (#3067), `ablage`
    ebenso (#3069) — sonst werden `link_pruefen.py --vorgangsseiten` bzw.
    `ablage_erledigt.py --pruefe` hier selbst aufgerufen."""
    roh: dict[str, int | None] = {}
    roh.update(_mailcheck_board())
    roh.update(_mailcheck_referenzen())
    roh.update(_mailcheck_anker())
    if links is None:
        links = _link_pruefen_vorgangsseiten()
    roh["vorgangsseiten_geprueft"] = links.get("geprueft")
    roh["vorgangsseiten_tot"] = links.get("tot")
    roh.update(ablage if ablage is not None else _mailcheck_ablage())
    roh["index_alter_tage"] = _mailcheck_index_alter()
    return roh


# --- To-do-Liste: echte Erhebung je Kennzahl -----------------------------


def _todo_direkt() -> dict[str, int | None]:
    """`ohne_kopf_aktion` und `geschlossen_7_tage` — lokale Zaehlung ueber das
    Ledger, kein eigenes Kommando existiert dafuer (Auftrag #3015). Importiert
    `todo_board` statt es aufzurufen — reine Zaehlung, nie Vorgangsinhalt."""
    pfad_alt = list(sys.path)
    try:
        if str(TODO_BOARD_DIR) not in sys.path:
            sys.path.insert(0, str(TODO_BOARD_DIR))
        import todo_board  # type: ignore[import-not-found]
    except Exception:
        return {"geschlossen_7_tage": None, "ohne_kopf_aktion": None}
    finally:
        sys.path[:] = pfad_alt

    try:
        daten = todo_board.lade(todo_board.LEDGER)
    except Exception:
        return {"geschlossen_7_tage": None, "ohne_kopf_aktion": None}

    posten = daten.get("vorgaenge", [])
    heute = date.today()
    geschlossen = 0
    for vorgang in posten:
        if vorgang.get("bucket") != "erledigt":
            continue
        try:
            erledigt_am = date.fromisoformat(str(vorgang.get("erledigt_am")))
        except (ValueError, TypeError):
            continue
        if 0 <= (heute - erledigt_am).days <= 7:
            geschlossen += 1

    try:
        anker = todo_board.aufloesbare_nummern()
    except Exception:
        anker = {}
    ohne_aktion = 0
    for vorgang in posten:
        try:
            ziele = todo_board.aktionen(vorgang, todo_board.MAIL_BASIS, "", anker)
        except Exception:
            continue
        if not ziele:
            ohne_aktion += 1

    return {"geschlossen_7_tage": geschlossen, "ohne_kopf_aktion": ohne_aktion}


def _todo_erheben(
    links: dict[str, int | None] | None = None,
) -> dict[str, int | None]:
    """Todo-Rohwerte. `links` optional vorgegeben (#3067) — sonst wird
    `link_pruefen.py --vorgangsseiten` hier selbst aufgerufen."""
    roh: dict[str, int | None] = {}
    if links is None:
        links = _link_pruefen_vorgangsseiten()
    roh["vorgangsseiten"] = links.get("seiten")
    roh["mail_links"] = links.get("links")
    roh["mail_links_tot"] = links.get("tot")
    roh.update(_todo_direkt())
    return roh


def _erheben_gemeinsam(
    ablage: dict[str, int | None] | None = None,
) -> tuple[dict[str, int | None], dict[str, int | None]]:
    """Mailcheck- und Todo-Rohwerte in EINEM Prozess erheben (#3067).

    `link_pruefen.py --vorgangsseiten` ist die einzige Quelle, die beide
    Anwendungen teilen — sie laeuft hier genau einmal, ihr Ergebnis geht in
    beide Rueckgaben ein. `ablage` (#3069) betrifft nur `mailcheck`; ist sie
    vorgegeben, entfaellt der eigene Lauf von `ablage_erledigt.py --pruefe`."""
    links = _link_pruefen_vorgangsseiten()
    return _mailcheck_erheben(links=links, ablage=ablage), _todo_erheben(links=links)


# --- Auftragsraum: echte Erhebung aus dem rohen Ereignis-Journal ---------


def _auftragsraum_zeit_parsen(text: Any) -> datetime | None:
    if not isinstance(text, str) or not text:
        return None
    try:
        wert = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if wert.tzinfo is None:
        wert = wert.replace(tzinfo=timezone.utc)
    return wert


def _jsonl_lesen(pfad: Path) -> list[dict[str, Any]]:
    """Generischer Zeilen-JSON-Reader — eine Zeile je Eintrag, defekte Zeilen
    werden uebersprungen statt den Lauf abzubrechen. Von `auftragsraum` UND
    `sevdesk` genutzt (#3102), je eigene Journal-Datei."""
    if not pfad.exists():
        return []
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError:
        return []
    eintraege: list[dict[str, Any]] = []
    for zeile in text.splitlines():
        zeile = zeile.strip()
        if not zeile:
            continue
        try:
            eintrag = json.loads(zeile)
        except ValueError:
            continue
        if isinstance(eintrag, dict):
            eintraege.append(eintrag)
    return eintraege


def _auftragsraum_kennzahlen(eintraege: list[dict[str, Any]]) -> dict[str, Any]:
    """Vier Kennzahlen aus den rohen Journalzeilen des Auftragsraums (D5,
    KONZ-platform-059). Nie Nachrichtentext oder Konto — nur Zaehlung und
    Zeitdifferenzen ueber Felder, die das Journal selbst schon fuehrt."""
    jetzt = datetime.now(timezone.utc)
    sieben_tage_alt = jetzt - timedelta(days=7)

    je_klasse: dict[str, int] = {}
    korrekturen_ohne_artefakt_24h = 0
    bearbeitungsdauern_stunden: list[float] = []
    kurzbefehle_gesamt = 0
    kurzbefehle_angewendet = 0

    for eintrag in eintraege:
        klasse = eintrag.get("klasse")
        zeit = _auftragsraum_zeit_parsen(eintrag.get("zeit"))

        if klasse and zeit is not None and zeit >= sieben_tage_alt:
            je_klasse[klasse] = je_klasse.get(klasse, 0) + 1

        if (
            eintrag.get("korrektur")
            and not eintrag.get("artefakt")
            and zeit is not None
            and (jetzt - zeit).total_seconds() / 3600 > 24
        ):
            korrekturen_ohne_artefakt_24h += 1

        bearbeitet = _auftragsraum_zeit_parsen(eintrag.get("bearbeitet_am"))
        if zeit is not None and bearbeitet is not None:
            bearbeitungsdauern_stunden.append(
                (bearbeitet - zeit).total_seconds() / 3600
            )

        if klasse == "kurzbefehl":
            kurzbefehle_gesamt += 1
            if eintrag.get("bearbeitet_am"):
                kurzbefehle_angewendet += 1

    mittlere_stunden = (
        sum(bearbeitungsdauern_stunden) / len(bearbeitungsdauern_stunden)
        if bearbeitungsdauern_stunden
        else None
    )
    anteil = kurzbefehle_angewendet / kurzbefehle_gesamt if kurzbefehle_gesamt else None
    return {
        "nachrichten_je_klasse": je_klasse,
        "korrekturen_ohne_artefakt_24h": korrekturen_ohne_artefakt_24h,
        "mittlere_stunden_bis_bearbeitung": mittlere_stunden,
        "anteil_angewendete_kurzbefehle": anteil,
    }


def _auftragsraum_erheben() -> dict[str, Any]:
    eintraege = _jsonl_lesen(AUFTRAGSRAUM_JOURNAL_DEFAULT)
    return _auftragsraum_kennzahlen(eintraege)


# --- sevdesk: juengste Zeile des rohen Lauf-Journals ---------------------


def _sevdesk_erheben() -> dict[str, Any]:
    """Keine eigene Erhebung — `rechnungslauf.py` schreibt die Kennzahlen
    bereits je Lauf, hier wird nur die juengste Zeile gelesen (#3102)."""
    eintraege = _jsonl_lesen(SEVDESK_JOURNAL_DEFAULT)
    return eintraege[-1] if eintraege else {}


# --- Sammeln, unabhaengig von der Quelle ---------------------------------


def _eingabe_lesen(wert: str) -> dict[str, Any]:
    try:
        geladen = json.loads(wert)
    except ValueError:
        pfad = Path(wert).expanduser()
        geladen = json.loads(pfad.read_text(encoding="utf-8"))
    if not isinstance(geladen, dict):
        raise SystemExit("FEHLER: --eingabe muss ein JSON-Objekt sein.")
    return geladen


def _kennzahlen_namen(anwendung: str) -> tuple[str, ...]:
    if anwendung == "mailcheck":
        return KENNZAHLEN_MAILCHECK
    if anwendung == "auftragsraum":
        return KENNZAHLEN_AUFTRAGSRAUM
    if anwendung == "sevdesk":
        return KENNZAHLEN_SEVDESK
    return KENNZAHLEN_TODO


def sammeln(anwendung: str, roh: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Kennzahlen einer Anwendung aus bereits erhobenen Rohwerten filtern.

    Rueckgabe (Kennzahlen, Fehlerliste). `roh` ist entweder eine `--eingabe`
    (Tests) oder das Ergebnis einer echten Erhebung — welche Quelle das war,
    entscheidet `schreiben()`, nicht diese Funktion (#3067). Werte sind meist
    `int`; `auftragsraum` liefert zusaetzlich `float` (Mittelwerte/Anteile)
    und `dict` (`nachrichten_je_klasse`, auch leer gueltig)."""
    namen = _kennzahlen_namen(anwendung)

    kennzahlen: dict[str, Any] = {}
    fehler: list[str] = []
    for name in namen:
        wert = roh.get(name, _FEHLT)
        if wert is _FEHLT or wert is None or isinstance(wert, bool):
            kennzahlen[name] = None
            fehler.append(name)
        elif isinstance(wert, (int, float, dict)):
            kennzahlen[name] = wert
        else:
            kennzahlen[name] = None
            fehler.append(name)
    return kennzahlen, fehler


def _quelle_version() -> str:
    out, _err, rc = _run(
        ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], timeout=10
    )
    wert = out.strip()
    return wert if wert and rc == 0 else "unbekannt"


def schreiben(
    anwendungen: list[str],
    modell: str,
    journal_pfad: Path,
    eingabe: dict[str, Any] | None,
    ablage_text: str | None = None,
) -> list[dict[str, Any]]:
    """Eine Journalzeile je Anwendung erheben und anhaengen.

    Bei mehreren Anwendungen (typischerweise mailcheck+todo, `--anwendung
    alle`) laufen geteilte Quellen — aktuell `link_pruefen.py
    --vorgangsseiten` — genau einmal (#3067); ihr Ergebnis geht in jede
    betroffene Zeile ein. `--eingabe` (Tests) ueberspringt jede Erhebung und
    deckt alle angefragten Anwendungen aus demselben JSON. `ablage_text`
    (#3069) ist die bereits erzeugte `--pruefe`-Ausgabe von
    `ablage_erledigt.py` — vorgegeben, entfaellt deren eigener, teurer Lauf
    hier (75 Index-Abfragen, gemessen 253s)."""
    ablage = (
        _mailcheck_ablage_aus_text(ablage_text) if ablage_text is not None else None
    )
    if eingabe is not None:
        roh_je_anwendung = {a: eingabe for a in anwendungen}
    elif {"mailcheck", "todo"} <= set(anwendungen):
        # #3067: mailcheck+todo teilen sich link_pruefen.py --vorgangsseiten,
        # egal ob auftragsraum (#3079) zusaetzlich angefragt ist — das laeuft
        # unabhaengig davon separat (eigene Quelle, kein Netz).
        roh_mailcheck, roh_todo = _erheben_gemeinsam(ablage=ablage)
        roh_je_anwendung = {"mailcheck": roh_mailcheck, "todo": roh_todo}
        if "auftragsraum" in anwendungen:
            roh_je_anwendung["auftragsraum"] = _auftragsraum_erheben()
        if "sevdesk" in anwendungen:
            roh_je_anwendung["sevdesk"] = _sevdesk_erheben()
    else:
        roh_je_anwendung = {}
        for a in anwendungen:
            if a == "mailcheck":
                roh_je_anwendung[a] = _mailcheck_erheben(ablage=ablage)
            elif a == "auftragsraum":
                roh_je_anwendung[a] = _auftragsraum_erheben()
            elif a == "sevdesk":
                roh_je_anwendung[a] = _sevdesk_erheben()
            else:
                roh_je_anwendung[a] = _todo_erheben()

    journal_pfad.parent.mkdir(parents=True, exist_ok=True)
    zeilen: list[dict[str, Any]] = []
    for anwendung in anwendungen:
        kennzahlen, fehler = sammeln(anwendung, roh_je_anwendung[anwendung])
        zeile = {
            "zeit": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
            "anwendung": anwendung,
            "modell": modell,
            "kennzahlen": kennzahlen,
            "fehler": fehler,
            "quelle_version": _quelle_version(),
        }
        with journal_pfad.open("a", encoding="utf-8") as datei:
            datei.write(json.dumps(zeile, ensure_ascii=False, sort_keys=True) + "\n")
        zeilen.append(zeile)
    return zeilen


# --- Trend ----------------------------------------------------------------


def _journal_lesen(journal_pfad: Path, anwendung: str | None) -> list[dict[str, Any]]:
    if not journal_pfad.exists():
        return []
    eintraege: list[dict[str, Any]] = []
    for zeile in journal_pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile:
            continue
        try:
            eintrag = json.loads(zeile)
        except ValueError:
            continue
        if anwendung and eintrag.get("anwendung") != anwendung:
            continue
        eintraege.append(eintrag)
    return eintraege


def trend(anwendung: str | None, n: int, journal_pfad: Path) -> str:
    eintraege = _journal_lesen(journal_pfad, anwendung)
    if not eintraege:
        return "Journal leer"
    eintraege = eintraege[-n:]

    alle_kennzahlen: list[str] = []
    for eintrag in eintraege:
        for name in eintrag.get("kennzahlen", {}):
            if name not in alle_kennzahlen:
                alle_kennzahlen.append(name)

    kopf = ["zeit", "anwendung", "modell", *alle_kennzahlen]
    zeilen_text = ["\t".join(kopf)]
    vorher: dict[str, int | None] = {}
    for eintrag in eintraege:
        werte = eintrag.get("kennzahlen", {})
        spalten = [
            str(eintrag.get("zeit", "")),
            str(eintrag.get("anwendung", "")),
            str(eintrag.get("modell", "")),
        ]
        for name in alle_kennzahlen:
            wert = werte.get(name)
            text = "null" if wert is None else str(wert)
            vorheriger = vorher.get(name)
            if (
                isinstance(wert, (int, float))
                and not isinstance(wert, bool)
                and isinstance(vorheriger, (int, float))
                and not isinstance(vorheriger, bool)
            ):
                delta = wert - vorheriger
                text += f" ({'+' if delta >= 0 else ''}{delta})"
            spalten.append(text)
        vorher = {**vorher, **werte}
        zeilen_text.append("\t".join(spalten))
    return "\n".join(zeilen_text)


# --- CLI --------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else "")
    ap.add_argument(
        "--schreiben",
        action="store_true",
        help="eine Journalzeile erheben und anhaengen",
    )
    ap.add_argument(
        "--trend", action="store_true", help="Tabelle der letzten n Laeufe zeigen"
    )
    ap.add_argument(
        "--anwendung",
        action="append",
        choices=["mailcheck", "todo", "auftragsraum", "sevdesk", "alle"],
        help="mailcheck, todo, auftragsraum, sevdesk oder alle (alle vier in "
        "einem Lauf, #3067/#3079/#3102); fuer --schreiben mehrfach angebbar",
    )
    ap.add_argument("--modell", help="Default: $CLAUDE_MODEL oder 'unbekannt'")
    ap.add_argument("--journal", default=str(JOURNAL_DEFAULT))
    ap.add_argument(
        "--eingabe", help="Inline-JSON oder Pfad zu einer JSON-Datei (Tests)"
    )
    ap.add_argument(
        "--ablage-ausgabe",
        help="Pfad zu einer bereits erzeugten `ablage_erledigt.py --pruefe`-"
        "Textausgabe (#3069) — spart deren zweiten, teuren Lauf hier",
    )
    ap.add_argument("--n", type=int, default=7)
    args = ap.parse_args()

    journal_pfad = Path(args.journal).expanduser()

    if args.trend:
        anwendung_filter = args.anwendung[0] if args.anwendung else None
        print(trend(anwendung_filter, args.n, journal_pfad))
        return 0

    if args.schreiben:
        if not args.anwendung:
            print(
                "FEHLER: --schreiben braucht --anwendung "
                "mailcheck|todo|auftragsraum|alle",
                file=sys.stderr,
            )
            return 2
        anwendungen: list[str] = []
        for a in args.anwendung:
            anwendungen.extend(
                ["mailcheck", "todo", "auftragsraum", "sevdesk"] if a == "alle" else [a]
            )
        anwendungen = list(dict.fromkeys(anwendungen))  # Reihenfolge, ohne Duplikate

        eingabe = _eingabe_lesen(args.eingabe) if args.eingabe else None
        ablage_text = None
        if args.ablage_ausgabe:
            try:
                ablage_text = (
                    Path(args.ablage_ausgabe).expanduser().read_text(encoding="utf-8")
                )
            except OSError as fehler:
                # Nicht lesbar heisst nicht abbrechen — dann erhebt
                # `schreiben()` `ablage_erledigt.py --pruefe` einfach selbst
                # (derselbe Weg wie ohne die Option).
                print(
                    f"  ({args.ablage_ausgabe} nicht lesbar ({fehler}) — "
                    "ablage_erledigt.py laeuft selbst)",
                    file=sys.stderr,
                )
        modell = args.modell or os.environ.get("CLAUDE_MODEL") or "unbekannt"
        zeilen = schreiben(anwendungen, modell, journal_pfad, eingabe, ablage_text)
        for zeile in zeilen:
            print(
                f"Journal geschrieben: {journal_pfad} ({zeile['anwendung']}, "
                f"{len(zeile['fehler'])} Fehler von {len(zeile['kennzahlen'])} Kennzahlen)"
            )
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
