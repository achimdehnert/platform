#!/usr/bin/env python3
"""Persistente Arbeitsliste — baut aus dem Vorgangs-Ledger eine HTML-Seite und serviert sie.

Warum es das gibt: `/mailcheck` erhebt den Stand offener Vorgaenge und schreibt ihn
nach `~/.claude/mail-vorgaenge.json`. Bisher war das Board fluechtig — es stand in
einer Chat-Antwort und war beim naechsten Fenster weg, waehrend Fristen (AV-Pruefung,
Angebotsfrist, DSGVO-Monatsfrist) genau dort schlummerten, wo niemand hinsieht.
Dieser Dienst macht denselben Zustand dauerhaft sichtbar.

    todo_board.py build            → schreibt ~/.claude/boards/todo.html
    todo_board.py serve            → 127.0.0.1:8789, baut bei jedem Abruf neu

Einstiegskommando fuer den ganzen Stand (platform#2592 K1): `make boards` baut
Action-Board (board.py --render) und diese Seite aus demselben Ledger; `make
boards-check` baut beide zweimal mit festem `--stichtag` und vergleicht byteweise
— die Ausgabe haengt nur vom Ledger, den Ankerdateien und dem Stichtag ab, nie
von Uhrzeit, Laufreihenfolge oder Zufall. Gemessen 2026-09-02: zwei Laeufe
hintereinander identisch, 0 Zeilen Unterschied.

Bewusst getrennt von `mail_agent/mail_link_server.py`: der rendert Mail-Koerper live
aus dem Postfach und darf darum nie oeffentlich stehen. Dieser Dienst kennt nur das
Ledger, spricht kein IMAP und hat genau eine Seite — das ist die Angriffsflaeche, die
hinter Cloudflare Access vertretbar ist.

Das Ledger enthaelt Klarnamen von Mandanten und Betreffs aus laufenden Vorgaengen.
Der Dienst bindet darum auf Loopback und verlangt fuer jede andere Adresse ein
ausdrueckliches `--oeffentlich-hinter-auth`. Wer das setzt, ohne eine
Authentifizierung davorzuhaengen, legt Mandantendaten offen.

Quelle bleibt das Ledger. Dieses Werkzeug schreibt nie hinein.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from datetime import date, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote

# Die Lesart von Mail-Referenzen ist mit dem Mail-Dienst geteilt (platform#2592):
# was hier als Nummer erkannt wird, muss `eintrag_anker.py` unter demselben
# Schluessel verankern koennen. Das Modul ist reine Text-Analyse — kein IMAP.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))
from referenzen import (
    REF_GITHUB as _REF_GITHUB,
)
from referenzen import (
    REF_NUMMER as _REF_NUMMER,
)
from referenzen import (
    Referenz,
    ordner_daneben,
    schluessel_kandidaten,
)

LEDGER = Path.home() / ".claude" / "mail-vorgaenge.json"
#: Vorgaenge, die `vorgaenge_archivieren.py` aus dem Ledger genommen hat. Sie
#: verschwinden aus der LISTE, aber nicht aus dem Netz: ein Link, der gestern
#: funktionierte, zeigt auch morgen die Akte. Ohne diesen Leser waere das
#: Archivieren ein stilles Loeschen aus Sicht jedes Lesezeichens.
ERLEDIGT_ARCHIV = Path.home() / ".claude" / "mail-vorgaenge-erledigt.json"
#: Der gekappte Teil des Verlaufs (tools/mail_agent/ledger_kappen.py). Die
#: Vorgangsansicht setzt beides zusammen — gekappt heisst verschoben, nicht weg.
ARCHIV = Path.home() / ".claude" / "mail-vorgaenge-archiv.json"
#: Erwartete Antwortdaten aus echten Mailzeiten (tools/mail_agent/faelligkeit.py).
#: Die Datei ist optional — fehlt sie, sieht die Liste aus wie vorher.
FAELLIGKEIT = Path.home() / ".claude" / "mail-faelligkeit.json"
#: Zuordnung Verlaufseintrag → Mail (tools/mail_agent/eintrag_mails.py). Optional:
#: fehlt die Datei, bleiben die Eintraege nummeriert, aber ohne Mail-Bezug.
EINTRAG_LINKS = Path.home() / ".claude" / "mail-eintrag-links.json"
AUSGABE = Path.home() / ".claude" / "boards" / "todo.html"
PORT = 8789
# Ab wie vielen Tagen ohne Erhebung die Seite ihren eigenen Stand in Frage stellt.
FRISCH_TAGE = 2

# Reihenfolge der Abschnitte = Reihenfolge der Dringlichkeit. Leere entfallen.
BUCKETS = (
    ("owner", "Dein Zug", "Entscheidung, Berechtigung oder Inhalt, den nur du hast"),
    ("agent", "Ich kann sofort", "Braucht kein Gate — sag zu, dann laeuft es"),
    ("warten", "Wartet auf andere", "Der naechste Zug kommt von aussen"),
    (
        "erledigt",
        "Zuletzt erledigt",
        "Geschlossen — steht hier, bis das Fenster ablaeuft",
    ),
)

#: Deckungsgleich mit `board.py`: geschlossene Vorgaenge bleiben so lange sichtbar.
ERLEDIGT_FENSTER_TAGE = 14
KONTO_LABEL = {"iil": "IIL", "hnu": "HNU", "ad": "Mittwald", "": "—"}

#: Basis fuer Mail-Links. Der Board-Dienst haengt an todo.iil.pet (Port 8789), der
#: Mail-Renderer an mail.iil.pet (Port 8787) — ein relativer Pfad zeigt also ins
#: Leere. Im Ledger steht deshalb nur der PFAD (`/a/118`), der Host kommt von hier
#: und ist fuer lokale Laeufe ueberschreibbar. Host im Datenbestand waere Drift.
MAIL_BASIS = os.environ.get("TODO_BOARD_MAIL_BASIS", "https://mail.iil.pet").rstrip("/")

#: Verankerungs-Index des Mail-Dienstes (IMAP-Konten): Nummer → Ordner/UID.
#: Nur gelesen — geschrieben wird die Datei von `mail_link_server.py`/`anker.py`.
ANKER_DATEI = Path.home() / ".claude" / "mail-anker.json"

#: Kurz-ID-Registry (Graph/IIL): Kurz-ID → Graph-Nachricht. Eine Board-Nummer ist
#: eine gueltige Kurz-ID (`^[A-Za-z0-9_-]{1,24}$`), also dient sie hier als Schluessel.
REGISTRY_DATEI = Path.home() / ".claude" / "mail-links.json"


def _schluessel(pfad: Path) -> frozenset[str]:
    """Die Schluessel einer JSON-Objektdatei — leer, wenn sie fehlt oder bricht."""
    try:
        with pfad.open(encoding="utf-8") as fh:
            daten = json.load(fh)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return frozenset()
    return frozenset(str(k) for k in daten) if isinstance(daten, dict) else frozenset()


def _anker_daten(pfad: Path) -> dict[str, dict]:
    """Die Anker mit ihren Feldern — leer, wenn die Datei fehlt oder bricht.

    `_schluessel` reicht fuer die Frage „verankert?"; fuer die Unterscheidung
    gleichbetreffter Mails braucht der Verlauf auch `betreff` und `datum`.
    """
    try:
        with pfad.open(encoding="utf-8") as fh:
            daten = json.load(fh)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    if not isinstance(daten, dict):
        return {}
    return {str(k): v for k, v in daten.items() if isinstance(v, dict)}


def anker_im_text(text: str, konto: str, verankert) -> list[str]:
    """Die verankerten Schluessel, die dieser (escapte) Text nennt."""
    if not konto:
        return []
    gefunden: list[str] = []
    for m in _REF_NUMMER.finditer(text):
        ref = Referenz(
            uid=m.group("uid"),
            ordner=ordner_daneben(text, m.start()),
            start=m.start(),
            end=m.end(),
        )
        for kandidat in schluessel_kandidaten(konto, ref):
            if kandidat in verankert:
                gefunden.append(kandidat)
                break
    return gefunden


def gleichbetreffte(schluessel_liste, daten: dict[str, dict]) -> dict[str, str]:
    """Schluessel → Datumsmarke, aber nur wo der Betreff nicht unterscheidet.

    Ein weitergeleiteter Strang heisst in jeder Weiterleitung gleich. Standen
    zwei solche Mails im selben Verlauf, sahen ihre Links identisch aus und man
    musste beide oeffnen, um sie zu trennen (Owner-Befund 2026-09-03, Vorgang
    160: zwei Eintraege nannten je eine Weiterleitung desselben Strangs).
    Markiert wird darum nur, was der Betreff offen laesst — und nur, wenn ein
    Datum vorliegt: eine erfundene Marke waere schlimmer als keine.
    """
    je_betreff: dict[str, set[str]] = {}
    for k in schluessel_liste:
        betreff = str(daten.get(k, {}).get("betreff") or "").strip()
        if betreff:
            je_betreff.setdefault(betreff, set()).add(k)
    marken: dict[str, str] = {}
    for treffer in je_betreff.values():
        if len(treffer) < 2:
            continue
        for k in treffer:
            datum = str(daten.get(k, {}).get("datum") or "").strip()
            if len(datum) == 10:
                marken[k] = f"{datum[8:10]}.{datum[5:7]}."
    return marken


def aufloesbare_nummern(
    anker_pfad: Path = ANKER_DATEI, registry_pfad: Path = REGISTRY_DATEI
) -> dict[str, str]:
    """Nummer → Pfad-Praefix, unter dem der Mail-Dienst sie wirklich aufloest.

    Warum das Board diese Dateien liest: die Nummer steht ohnehin im Ledger, ein
    Link liesse sich also blind daraus ableiten. Gemessen am 2026-08-11 waeren das
    aber 14 von 18 Links, die zuverlaessig 404 liefern. Ein Link, der verlaesslich
    ins Leere fuehrt, ist schlechter als der ehrliche Hinweis "keine Mail
    verknuepft" (#1875) — darum die Probe.

    **Zwei Quellen, weil der Dienst zwei Wege hat** (Fehlerbericht 2026-08-11):
    `anker.py --setze` laeuft ueber IMAP und erreicht die HNU-Konten; IIL/Graph
    haengt an der Kurz-ID-Registry. Eine Probe nur gegen die Ankerdatei liess
    darum **jeden IIL-Vorgang unverlinkt**, obwohl der Dienst ihn haette aufloesen
    koennen — genau der gemeldete Fall (Vorgang 107, LS Bau). Diese Funktion
    spiegelt jetzt beide Wege, so wie `mail_link_server._anker()` sie kennt.

    Der Praefix unterscheidet sich bewusst:

    * `/a/` fuer IMAP-Anker — der Dienst rendert die Mail selbst.
    * `/r/` fuer Graph — rendert ebenfalls selbst. **Nicht** `/i/`: das leitet auf
      OWA weiter, und OWA laesst sich weder einbetten noch schnell lesen.

    Faellt eine Datei aus, faellt nur ihr Zweig weg — nicht die ganze Verlinkung.
    """
    ziele = {nr: "/r/" for nr in _schluessel(registry_pfad)}
    # IMAP-Anker gewinnt: er traegt Ordner + UID + Message-ID und zieht bei einem
    # Ordnerwechsel nach, waehrend die Registry nur eine Graph-id festhaelt.
    ziele.update({nr: "/a/" for nr in _schluessel(anker_pfad)})
    return ziele


def mail_ziel(
    v: dict, mail_basis: str = MAIL_BASIS, anker: dict[str, str] | None = None
) -> str | None:
    """Die URL zur Mail dieses Vorgangs — oder None, wenn keine erreichbar ist.

    Zwei Wege, in dieser Reihenfolge:
    1. ausdrueckliches `mail_ref` im Ledger (Bestandsweg, gewinnt immer),
    2. Ableitung aus `nr` — aber nur ueber den Praefix, unter dem der Dienst die
       Nummer wirklich aufloest (`/a/` IMAP-Anker, `/r/` Graph-Registry).

    Weg 2 loest den Handgriff ab, mit dem `/mailcheck` `mail_ref` bisher von Hand
    nachtrug (K1 aus #1869): neue Vorgaenge tragen ihren Link, sobald der
    Mail-Dienst sie kennt — ohne dass jemand daran denken muss.
    """
    ref = str(v.get("mail_ref") or "").strip()
    if ref:
        # Nur serverseitige Pfade akzeptieren. Ein absoluter Wert im Ledger waere
        # ein offener Weiterleitungspunkt — der Ledger speist sich aus fremden Mails.
        # Ist der Wert unbrauchbar, gibt es KEIN Ziel: auf die Nummer auszuweichen
        # wuerde einen vergifteten Eintrag stillschweigend heilen und die Zeile
        # unauffaellig machen, die gerade auffallen soll.
        return f"{mail_basis}{ref}" if ref.startswith("/") and ref[1:2] != "/" else None
    nr = v.get("nr")
    if nr in (None, ""):
        return None
    ziele = aufloesbare_nummern() if anker is None else anker
    praefix = ziele.get(str(nr))
    return f"{mail_basis}{praefix}{quote(str(nr), safe='')}" if praefix else None


def heute() -> date:
    # Kalendertag der Maschine, bewusst ohne Zeitzone: eine Frist laeuft am
    # Datum ab, nicht zu einer Uhrzeit, und das Ledger schreibt reine ISO-Tage.
    return date.today()  # noqa: DTZ011


def lade(pfad: Path) -> dict:
    if not pfad.exists():
        sys.exit(f"FEHLER: Ledger {pfad} fehlt — erst /mailcheck laufen lassen.")
    with pfad.open(encoding="utf-8") as fh:
        return json.load(fh)


def archivierte_vorgaenge(pfad: Path | None = None) -> list[dict]:
    """Die ausgelagerten Vorgaenge — leere Liste, wenn es noch kein Archiv gibt."""
    try:
        roh = (pfad or ERLEDIGT_ARCHIV).read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        return json.loads(roh).get("vorgaenge", [])
    except json.JSONDecodeError:
        return []


def frisch_erledigt(vorgang: dict, stichtag) -> bool:
    """Liegt der Abschluss innerhalb des Anzeigefensters?

    Ohne lesbares `erledigt_am` wird der Posten gezeigt statt versteckt — ein
    fehlendes Datum ist ein Pflegefehler, den man sehen soll.
    """
    roh = vorgang.get("erledigt_am")
    if not roh:
        return True
    try:
        geschlossen = date.fromisoformat(str(roh)[:10])
    except ValueError:
        return True
    return (stichtag - geschlossen).days <= ERLEDIGT_FENSTER_TAGE


def frist_tage(v: dict, stichtag: date) -> int | None:
    """Resttage bis zur Frist; None, wenn der Vorgang keine traegt."""
    roh = v.get("frist")
    if not roh:
        return None
    try:
        # Reiner ISO-Tag aus dem Ledger — ein %z gaebe es dort nicht zu lesen.
        return (datetime.strptime(roh, "%Y-%m-%d").date() - stichtag).days  # noqa: DTZ007
    except ValueError:
        # Ein unlesbares Datum ist ein Befund, kein Grund, die Seite abstuerzen zu
        # lassen — es faellt in der Ausgabe als "?" auf.
        return None


def ampel(tage: int | None) -> tuple[str, str]:
    """(CSS-Klasse, Text) fuer die Fristenspalte."""
    if tage is None:
        return "keine", "—"
    if tage < 0:
        return "rot", f"{abs(tage)} Tage ueberfaellig"
    if tage == 0:
        return "rot", "heute"
    if tage <= 3:
        return "rot", f"in {tage} Tagen"
    if tage <= 10:
        return "gelb", f"in {tage} Tagen"
    return "gruen", f"in {tage} Tagen"


def zustand(v: dict, stichtag: date) -> tuple[str, str]:
    """→ (Klasse, Text) für den Zustand eines wartenden Vorgangs.

    Drei Zustaende, weil "wartet" allein die Frage nicht beantwortet, die man an
    die Liste hat (#2176 Kriterium 4):

    * **wartet**  — die Antwort ist noch im normalen Rahmen (bis zum 90-%-Quantil).
    * **still**   — der Rahmen ist ueberschritten; hier passiert nichts mehr von
      selbst. Das ist der Zustand, der bisher unsichtbar war.
    * **kein Signal** — es gibt keinen datierten Versand, also auch keine
      Erwartung. Ehrlicher als eine erfundene Frist.
    """
    if v.get("bucket") != "warten":
        return "", ""
    erwartung = _erwartung(v.get("nr"))
    if not erwartung.get("spaetestens"):
        return "kein-signal", "kein Signal"
    if erwartung.get("ueberfaellig"):
        try:
            tage = (stichtag - date.fromisoformat(erwartung["spaetestens"])).days
        except ValueError:
            tage = 0
        return "still", f"still seit {tage} Tagen" if tage > 0 else "still"
    return "wartet", f"bis {erwartung['spaetestens']}"


def sortschluessel(v: dict, stichtag: date) -> tuple[int, int, str]:
    """Fristen zuerst, aufsteigend; Fristlose danach, alphabetisch."""
    tage = frist_tage(v, stichtag)
    return (1, 0, v.get("thread_key", "")) if tage is None else (0, tage, "")


#: Ein wartender Entwurf im juengsten Verlaufseintrag. Er ist der haeufigste Grund,
#: warum ein Posten „dein Zug" ist — und stand bisher nur im Verlauf, also einen
#: Klick entfernt (Owner-Befund 2026-08-21: „MUSS bekannt sein").
_ENTWURF_REF = re.compile(r"Entw(?:ue|ü)rfe\s*#(?P<uid>\d{3,7})", re.IGNORECASE)
#: Woerter, mit denen derselbe Eintrag sagt, dass es den Entwurf nicht mehr gibt.
_ENTWURF_ERLEDIGT = re.compile(
    r"gesendet|versendet|verschickt|abgeschickt|verworfen|nicht mehr", re.IGNORECASE
)


def entwurf_link(v: dict, mail_basis: str = MAIL_BASIS) -> str:
    """URL des wartenden Entwurfs — leer, wenn der juengste Eintrag keinen nennt.

    Bewusst nur der JUENGSTE Eintrag: ein Entwurf von vorletzter Woche ist
    entweder gesendet oder verworfen, und ein Link darauf verspricht einen
    Zustand, den es nicht mehr gibt.
    """
    eintraege = [t.strip() for t in str(v.get("notiz") or "").split(" | ") if t.strip()]
    konto = str(v.get("konto") or "")
    if not eintraege or not konto:
        return ""
    juengster = eintraege[-1]
    treffer = _ENTWURF_REF.search(juengster)
    if not treffer:
        return ""
    # Die Nummer allein sagt nur, dass ein Entwurf ERWAEHNT wird. Steht im selben
    # Eintrag, dass er gesendet oder verworfen wurde, zeigt der Link auf etwas,
    # das dort nicht mehr liegt — und ein toter Link ist schlechter als keiner.
    if _ENTWURF_ERLEDIGT.search(juengster):
        return ""
    uid = treffer.group("uid")
    # Verankert gewinnt: `/a/<schluessel>` ueberlebt das Ersetzen des Entwurfs.
    # Ein frischer, noch unverankerter Entwurf bekommt den direkten Ordner-Link —
    # er gilt, bis `eintrag_anker.py` gelaufen ist (Abschluss von /mailcheck).
    ref = Referenz(uid=uid, ordner="Entwuerfe", start=0, end=0)
    verankert = _schluessel(ANKER_DATEI)
    for kandidat in schluessel_kandidaten(konto, ref):
        if kandidat in verankert:
            return f"{mail_basis.rstrip('/')}/a/{quote(kandidat, safe='')}"
    return f"{mail_basis.rstrip('/')}/m/{konto}/entwuerfe/{uid}"


def zeile(
    v: dict,
    stichtag: date,
    basis: str = "",
    mail_basis: str = MAIL_BASIS,
    anker: dict[str, str] | None = None,
) -> str:
    tage = frist_tage(v, stichtag)
    klasse, text = ampel(tage)
    konto = KONTO_LABEL.get(v.get("konto", ""), v.get("konto", "—"))
    frist = v.get("frist") or ""
    # Ohne gesetzte Frist tritt die Erwartung an ihre Stelle: „wartet" allein sagt
    # nicht, ob das normal ist oder ob seit zwei Wochen niemand antwortet.
    if tage is None and v.get("bucket") == "warten":
        zust_klasse, zust_text = zustand(v, stichtag)
        if zust_text:
            # "still" ist der Befund, nicht die Erwartung — deshalb rot und im
            # selben Feld, in dem sonst die Frist steht. Die Erwartung wandert in
            # die kleine Zeile darunter, wo sie erklaert statt zu behaupten.
            klasse = {"still": "rot", "wartet": "gruen", "kein-signal": "keine"}[
                zust_klasse
            ]
            text = zust_text
            erwartung = _erwartung(v.get("nr"))
            frist = (
                f"erwartet war {erwartung.get('erwartet', '')}"
                if zust_klasse == "still"
                else (
                    f"erwartet {erwartung.get('erwartet', '')}"
                    if zust_klasse == "wartet"
                    else "kein datierter Versand"
                )
            )
    # Keine Frist ist eine Aussage, wenn ihr Grund dabeisteht (#2592 K4): „keine —
    # Owner-Aufgabe ohne Termin" liest sich anders als ein leerer Strich.
    if tage is None and not frist and v.get("frist_grund"):
        text = "keine"
        frist = str(v["frist_grund"])
    schluessel = v.get("thread_key", "")
    beschriftung = html.escape(schluessel or "—")
    # Ohne thread_key gibt es kein Ziel — dann bleibt es Text statt totem Link.
    sache = (
        f"<a href='{html.escape(basis)}/t/{quote(schluessel, safe='')}'>{beschriftung}</a>"
        if schluessel
        else beschriftung
    )
    # Die Nummer ist die ID aus dem Ledger, kein Laufindex je Abschnitt: sie bleibt
    # ueber Bucket-Wechsel und ueber Tage hinweg dieselbe und ist genau die Nummer,
    # unter der die Mail als `/a/<nr>` erreichbar ist. Ein Laufindex wuerde springen.
    nr = v.get("nr")
    nr_text = html.escape(str(nr)) if nr not in (None, "") else "—"
    # Das Briefsymbol steht nur noch da, wo es KEINE Vorgangsansicht gibt.
    # Grund (Owner-Befund 2026-08-20): `/a/<nr>` loest ueber die verankerte
    # Message-ID auf, und verankert ist der ANFANG des Strangs. Der Klick landete
    # also verlaesslich auf der aeltesten Mail, waehrend die Frage „was ist der
    # Stand?" lautet. Solange der Dienst keine „letzte Mail des Vorgangs" kennt
    # (platform#2160), ist der Weg ueber den Verlauf der richtige — und der haengt
    # am Sache-Link daneben. Ohne thread_key bleibt das Briefsymbol die einzige
    # Spur zur Mail und darum erhalten.
    ziel = None if schluessel else mail_ziel(v, mail_basis, anker)
    entwurf = entwurf_link(v, mail_basis)
    entwurf_marke = (
        f" <a class='entwurf-marke' href='{html.escape(entwurf)}' target='_blank'"
        f" rel='noreferrer' title='Entwurf oeffnen'>Entwurf</a>"
        if entwurf
        else ""
    )
    mail = (
        f" <a class='maillink' href='{html.escape(ziel)}' target='_blank' "
        f"rel='noreferrer' aria-label='Mail zu #{nr_text} oeffnen' "
        f"title='Mail oeffnen'>&#9993;</a>"
        if ziel
        else ""
    )
    return (
        "<tr>"
        f"<td class='nr'>{nr_text}</td>"
        f"<td class='sache'>{sache}{mail}{entwurf_marke}"
        f"<span class='wer'>{html.escape(v.get('gegenueber', ''))}</span></td>"
        f"<td class='konto'>{html.escape(konto)}</td>"
        f"<td class='frist {klasse}'>{html.escape(text)}"
        f"<span class='datum'>{html.escape(frist)}</span></td>"
        f"<td class='schritt'>{html.escape(v.get('kurz') or v.get('next_trigger', ''))}</td>"
        "</tr>"
    )


def abschnitt(
    titel: str,
    unter: str,
    posten: list[dict],
    stichtag: date,
    basis: str = "",
    mail_basis: str = MAIL_BASIS,
    anker: dict[str, str] | None = None,
) -> str:
    if not posten:
        return ""
    zeilen = "".join(
        zeile(v, stichtag, basis, mail_basis, anker)
        for v in sorted(posten, key=lambda x: sortschluessel(x, stichtag))
    )
    return f"""<section>
<h2>{html.escape(titel)} <span class='zahl'>{len(posten)}</span></h2>
<p class='unter'>{html.escape(unter)}</p>
<table><thead><tr><th>#</th><th>Sache</th><th>Konto</th><th>Frist</th>
<th>Naechster Schritt</th></tr></thead>
<tbody>{zeilen}</tbody></table>
</section>"""


CSS = """
:root{--bg:#fbfbfa;--fg:#1a1a19;--stumm:#6b6b66;--linie:#e3e3df;--karte:#fff;
--rot:#b3261e;--gelb:#8a6100;--gruen:#2c6b3f}
:root:not([data-theme=light]){}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
--bg:#16171a;--fg:#e8e8e6;--stumm:#9a9a95;--linie:#2c2e33;--karte:#1e2024;
--rot:#f2836f;--gelb:#e0b341;--gruen:#7fc79a}}
:root[data-theme=dark]{--bg:#16171a;--fg:#e8e8e6;--stumm:#9a9a95;--linie:#2c2e33;
--karte:#1e2024;--rot:#f2836f;--gelb:#e0b341;--gruen:#7fc79a}
*{box-sizing:border-box}
body{margin:0;padding:2rem 1.25rem 4rem;background:var(--bg);color:var(--fg);
font:16px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:60rem;margin:0 auto}
h1{font-size:1.5rem;margin:0 0 .25rem}
.nr-marke{color:var(--stumm);font-weight:400;font-variant-numeric:tabular-nums}
.stand{color:var(--stumm);font-size:.85rem;margin:0 0 2rem}
section{background:var(--karte);border:1px solid var(--linie);border-radius:10px;
padding:1.1rem 1.25rem;margin-bottom:1.25rem}
h2{font-size:1.05rem;margin:0;display:flex;align-items:center;gap:.5rem}
.zahl{font-size:.75rem;font-weight:600;color:var(--stumm);border:1px solid var(--linie);
border-radius:999px;padding:.05rem .5rem}
.unter{color:var(--stumm);font-size:.82rem;margin:.2rem 0 .9rem}
.tabellenrahmen,section{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th{text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;
color:var(--stumm);font-weight:600;padding:0 .6rem .4rem 0;border-bottom:1px solid var(--linie)}
td{padding:.6rem .6rem .6rem 0;border-bottom:1px solid var(--linie);vertical-align:top}
tr:last-child td{border-bottom:none}
.nr{color:var(--stumm);font-variant-numeric:tabular-nums;white-space:nowrap;
width:2.5rem;font-size:.85rem}
.sache{font-weight:500;min-width:14rem}
a.maillink{text-decoration:none;border-bottom:none;color:var(--stumm);
margin-left:.35rem;font-size:.95rem}
a.maillink:hover{color:var(--fg)}
.wer{display:block;font-weight:400;font-size:.78rem;color:var(--stumm);margin-top:.15rem}
.konto{color:var(--stumm);white-space:nowrap}
.frist{white-space:nowrap;font-variant-numeric:tabular-nums}
.frist .datum{display:block;font-size:.72rem;color:var(--stumm)}
.frist.rot{color:var(--rot);font-weight:600}
.frist.gelb{color:var(--gelb);font-weight:600}
.frist.gruen{color:var(--gruen)}
.frist.keine{color:var(--stumm)}
.schritt{color:var(--fg)}
.alt{background:var(--karte);border:1px solid var(--rot);border-left-width:4px;
border-radius:8px;color:var(--rot);font-size:.88rem;padding:.7rem .9rem;margin:0 0 1.25rem}
footer{color:var(--stumm);font-size:.78rem;margin-top:2rem;text-align:center}
.schritt-text{margin:.4rem 0 .6rem}
.aktionen{display:flex;flex-wrap:wrap;gap:.5rem;margin:.2rem 0 0}
a.aktion{display:inline-block;padding:.35rem .7rem;border:1px solid var(--linie);
border-radius:6px;background:var(--karte);text-decoration:none;font-size:.86rem}
a.aktion:hover{border-color:var(--stumm)}
.kein-ziel{color:var(--stumm);font-size:.84rem;font-style:italic;margin:.2rem 0 0}
.sache a{color:inherit;text-decoration:none;border-bottom:1px solid var(--linie)}
.sache a:hover{border-bottom-color:currentColor}
.kopf-rot{color:var(--rot,#b3261e)}
h2.verlauf-kopf{display:block;margin:1.75rem 0 .6rem}
h2.verlauf-kopf .zusatz{display:block;font-size:.76rem;font-weight:400;color:var(--stumm);
margin-top:.15rem}
table.zusammenfassung{width:100%;border-collapse:collapse;font-size:.9rem;margin:.6rem 0 1rem}
table.zusammenfassung th{text-align:left;font-weight:600;color:var(--stumm);
white-space:nowrap;padding:.25rem .9rem .25rem 0;vertical-align:top;width:1%}
table.zusammenfassung td{padding:.25rem 0;word-break:break-word}
.strang{margin:0 0 1.1rem}
.strang:last-child{margin-bottom:0}
h3.strang-kopf{font-size:.92rem;margin:0 0 .4rem;display:flex;align-items:center;gap:.5rem;
color:var(--fg)}
.eintrag{background:var(--karte);border:1px solid var(--linie);border-radius:8px;
padding:.55rem .8rem;margin:0 0 .4rem;font-size:.88rem;line-height:1.5}
.eintrag-kopf{display:flex;flex-wrap:wrap;align-items:baseline;gap:.5rem;
margin:0 0 .4rem;font-size:.74rem;color:var(--stumm)}
.eintrag-datum{font-variant-numeric:tabular-nums;font-weight:600}
.ereignis{text-transform:uppercase;letter-spacing:.05em;font-weight:600;
border:1px solid var(--linie);border-radius:999px;padding:.02rem .45rem}
.quelle{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.deckung{margin-left:auto}
.deckung summary{cursor:pointer;color:var(--stumm);list-style:none;
border-bottom:1px dotted var(--linie)}
.deckung summary::-webkit-details-marker{display:none}
.deckung p{margin:.4rem 0 0;max-width:42rem;font-size:.74rem;word-break:break-word}
.eintrag p,.eintrag div{margin:0 0 .3rem;word-break:break-word}
.eintrag p:last-child,.eintrag div:last-child{margin-bottom:0}
.eintrag ol{margin:.15rem 0 .3rem;padding-left:1.15rem}
.eintrag ol:last-child{margin-bottom:0}
.eintrag li{margin:0 0 .15rem}
.bahn-marke{display:inline-block;font-size:.68rem;text-transform:uppercase;
letter-spacing:.05em;font-weight:600;color:var(--stumm);margin-right:.4rem}
.bahn-analyse{border-left:2px solid var(--linie);padding-left:.6rem}
.bahn-action{border-left:2px solid var(--gelb);padding-left:.6rem;font-weight:500}
.bahn-action .bahn-marke{color:var(--gelb)}
a.ref{color:inherit;text-decoration:none;border-bottom:1px solid var(--linie);
font-variant-numeric:tabular-nums}
a.ref:hover{border-bottom-color:currentColor}
.ref-datum{font-variant-numeric:tabular-nums;opacity:.7;font-size:.92em;
           margin-left:.15em}
.ref.ohne-anker{border-bottom:1px dotted var(--linie);cursor:help;opacity:.85}
.datei{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.82rem;
background:var(--bg);border:1px solid var(--linie);border-radius:4px;padding:0 .25rem}
"""


def frische_banner(daten: dict, stichtag: date) -> str:
    """Sagt an, wenn die Erhebung veraltet ist — Schweigen waere hier gefaehrlich.

    Die Seite baut bei jedem Abruf neu und sieht darum immer frisch aus, auch
    wenn der naechtliche /mailcheck seit Tagen scheitert. Eine Liste, die
    stillschweigend eine Woche alten Stand zeigt, ist schlimmer als keine:
    sie beruhigt, waehrend eine Frist laeuft.
    """
    roh = daten.get("letzte_pruefung")
    if not roh:
        return "<p class='alt'>Kein Erhebungsdatum im Ledger — Stand unbekannt.</p>"
    try:
        # Reiner ISO-Tag aus dem Ledger, s.o.
        alter = (stichtag - datetime.strptime(str(roh), "%Y-%m-%d").date()).days  # noqa: DTZ007
    except ValueError:
        return f"<p class='alt'>Erhebungsdatum '{html.escape(str(roh))}' unlesbar.</p>"
    if alter <= FRISCH_TAGE:
        return ""
    return (
        f"<p class='alt'>Diese Liste ist {alter} Tage alt. Der naechtliche "
        f"/mailcheck hat sie seit dem {html.escape(str(roh))} nicht "
        "fortgeschrieben — neue Antworten und Fristen fehlen moeglicherweise.</p>"
    )


# Overlay nach dem Muster von tools/mail_agent/mail_link_server.py (dort Z. 126-154).
# Fällt ohne JavaScript auf einen normalen Seitenwechsel zurück: der Link im Markup
# ist ein echter Link, das Skript fängt ihn nur ab.
OVERLAY = """
<div id=ovl style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:9">
 <div id=ovl-box style="position:absolute;inset:4% 6%;background:#fff;border-radius:10px;
  overflow:hidden;display:flex;flex-direction:column;box-shadow:0 12px 40px rgba(0,0,0,.4)">
  <div style="padding:.45rem .9rem;display:flex;justify-content:flex-end;gap:1.2rem;
   border-bottom:1px solid #d0d0d0;font-size:.9rem">
   <a id=ovl-ext href="#" target=_blank rel=noreferrer>in neuem Tab oeffnen &#8599;</a>
   <a href="#" id=ovl-x>&#10005; schliessen (Esc)</a>
  </div>
  <iframe id=ovl-frame title="Vorgang" style="border:0;flex:1;width:100%"></iframe>
 </div>
</div>
<style>@media (prefers-color-scheme:dark){#ovl-box{background:#1e2024}
 #ovl-box>div{border-color:#2c2e33}}</style>
<script>
(function(){
 var ovl=document.getElementById('ovl'),fr=document.getElementById('ovl-frame'),
     ext=document.getElementById('ovl-ext');
 function zu(){ovl.style.display='none';fr.src='about:blank';}
 function auf(src){fr.src=src;ext.href=src;ovl.style.display='block';}
 document.addEventListener('click',function(e){
  var a=e.target.closest('a');if(!a)return;
  var h=a.getAttribute('href')||'';
  if(a.id==='ovl-x'){e.preventDefault();zu();return;}
  if(a===ext)return;
  /* NUR eigene Vorgangsseiten. Mail-Links gehen bewusst NICHT ins Overlay:
     mail.iil.pet steht hinter Cloudflare Access, und Access leitet auf
     iil-team.cloudflareaccess.com um, das `frame-ancestors 'none'` sendet.
     Am 2026-08-11 im Browser gemessen — das Overlay oeffnete sich und zeigte
     "hat die Verbindung abgelehnt". Ein Rahmen, der verlaesslich leer bleibt,
     ist schlechter als ein neuer Tab; die Mail-Links tragen darum target=_blank.
     Wieder moeglich waere das Modal erst, wenn beide Dienste unter DERSELBEN
     Adresse haengen (Pfad-Mount im Tunnel) — siehe #1869. */
  if(h.indexOf('/t/')>=0){e.preventDefault();auf(h);}
 });
 ovl.addEventListener('click',function(e){if(e.target===ovl)zu();});
 document.addEventListener('keydown',function(e){if(e.key==='Escape')zu();});
})();
</script>"""


def aktionen(
    v: dict,
    mail_basis: str = MAIL_BASIS,
    basis: str = "",
    anker: dict[str, str] | None = None,
) -> list[tuple]:
    """Naechste Schritte als Ziele — ausschliesslich anzeigend.

    Bewusste Grenze (#1869): hier entsteht KEIN Knopf, der etwas ausloest. Senden,
    Buchen, Loeschen bleiben aussen vor, und es gibt keinen Rueckkanal, ueber den die
    Seite einen Agenten beauftragen koennte — Kommandokanal ist allein die
    interaktive Sitzung (Lotsen-Charta Art. 1). Wer hier spaeter einen POST ergaenzt,
    hebt genau diese Zusage auf.

    Rueckgabe: Liste aus (Beschriftung, Ziel-URL). Leere Liste heisst: kein Ziel
    ableitbar — der Aufrufer zeigt dann den `next_trigger`-Text, keinen toten Knopf.
    """
    del basis  # noch kein Ziel, das die Board-Basis braucht — siehe unten
    ziele: list[tuple] = []
    ziel = mail_ziel(v, mail_basis, anker)
    if ziel:
        # Beschriftung sagt, was der Link WIRKLICH oeffnet: `/a/<nr>` loest ueber
        # die verankerte Message-ID auf, und verankert ist der Anfang des Strangs.
        # "Mail oeffnen" las sich wie "die aktuelle" (Owner-Befund 2026-08-20);
        # die juengste Mail kann der Dienst noch nicht (platform#2160).
        ziele.append(("Erste Mail des Strangs", ziel))
    # Bewusst KEIN Selbstlink auf `/t/<thread_key>`: die Vorgangsseite ist genau das
    # Ziel, auf dem dieser Abschnitt steht. Er waere ausserdem der einzige Grund,
    # warum Bestandsvorgaenge ohne `mail_ref` ploetzlich einen Knopf trugen.
    # „Antwort entwerfen" fehlt hier absichtlich: der Mail-Dienst hat keinen
    # Entwurfs-Endpunkt, und einen zu bauen waere ein Schreibpfad — in #1869
    # ausdruecklich out of scope.
    return ziele


def naechste_schritte(
    v: dict,
    mail_basis: str = MAIL_BASIS,
    basis: str = "",
    anker: dict[str, str] | None = None,
) -> str:
    """Abschnitt 'Naechste Schritte': der Text aus dem Ledger plus erreichbare Ziele."""
    text = str(v.get("next_trigger") or "").strip()
    ziele = aktionen(v, mail_basis, basis, anker)
    kopf = f"<p class='schritt-text'>{html.escape(text)}</p>" if text else ""
    # Ohne Ziel bleibt der Vorschlag Text. Ein Knopf ohne Ziel waere genau der tote
    # Link, den `zeile()` beim fehlenden thread_key schon vermeidet.
    if ziele:
        rest = (
            "<p class='aktionen'>"
            + " ".join(
                f"<a class='aktion' href='{html.escape(url)}' target='_blank' "
                f"rel='noreferrer'>{html.escape(label)}</a>"
                for label, url in ziele
            )
            + "</p>"
        )
    else:
        # Die Luecke benennen statt sie zu verschweigen: am 2026-08-10 trugen 13 von
        # 17 Vorgaengen keinen Anker, und eine leere Stelle sieht aus wie ein
        # kaputter Link. Der Hinweis trennt "nichts hinterlegt" von "defekt" — und
        # zeigt nebenbei, wo /mailcheck noch nachzutragen hat.
        rest = "<p class='kein-ziel'>keine Mail verknuepft</p>"
    return f"<h2>Naechste Schritte</h2>{kopf}{rest}"


# Was beim Aufschlagen zaehlt, steht jetzt in `zusammenfassung()` (#2856):
# Stand, Naechster Schritt, Frist, Gegenueber, Konto, Typ, Bucket, Nummer.
# Was uebrig bleibt, ist selten gebraucht und steht darum unter „Stammdaten" —
# angelegt/zuletzt geprueft sind Belege, keine Fragen, die man an den Vorgang hat.
DETAIL_FELDER_ZWEITE_REIHE = (
    ("angelegt", "Angelegt"),
    ("letzte_pruefung", "Zuletzt geprueft"),
)


def zusammenfassung(vorgang: dict) -> list[tuple[str, str]]:
    """Feste Kurzfassung eines Vorgangs — nur, was tatsaechlich im Ledger steht.

    Reine Funktion, testbar ohne Server: kein Raten, fehlende Felder werden
    weggelassen statt mit einem Platzhalter aufgefuellt (#2856). Reihenfolge:
    Stand, Naechster Schritt, Frist, Gegenueber, Konto, Typ, Bucket, Nummer —
    das ist die Reihenfolge, in der eine Frage an den Vorgang typischerweise
    beantwortet wird ("wo stehen wir" vor "wer ist das", "wer ist das" vor
    der Buchhaltungs-Klassifikation).
    """
    zeilen: list[tuple[str, str]] = []

    zustand_roh = str(vorgang.get("zustand") or "").strip()
    if zustand_roh:
        # Der Zustands-Slug ist eine Maschinenmarke ("klimm-hat-…-bestaetigt").
        # Bindestriche sind hier Wortgrenzen, keine Trennstriche eines Kompositums.
        text = zustand_roh.replace("-", " ")
        zeilen.append(("Stand", text[:1].upper() + text[1:]))

    schritt = str(vorgang.get("next_trigger") or "").strip()
    if schritt:
        zeilen.append(("Naechster Schritt", schritt))

    frist = str(vorgang.get("frist") or "").strip()
    frist_grund = str(vorgang.get("frist_grund") or "").strip()
    if frist:
        zeilen.append(("Frist", f"{frist} — {frist_grund}" if frist_grund else frist))
    elif frist_grund:
        # Keine Frist ist eine Aussage, wenn ihr Grund dabeisteht (#2592 K4) —
        # dieselbe Regel wie in `zeile()`, hier fuer die Vorgangsseite gespiegelt.
        zeilen.append(("Frist", f"keine — {frist_grund}"))

    gegenueber = str(vorgang.get("gegenueber") or "").strip()
    if gegenueber:
        zeilen.append(("Gegenueber", gegenueber))

    konto = str(vorgang.get("konto") or "").strip()
    if konto:
        zeilen.append(("Konto", KONTO_LABEL.get(konto, konto)))

    typ = str(vorgang.get("typ") or "").strip()
    if typ:
        zeilen.append(("Typ", typ))

    bucket = str(vorgang.get("bucket") or "").strip()
    if bucket:
        zeilen.append(("Bucket", bucket))

    nr = vorgang.get("nr")
    if nr not in (None, ""):
        zeilen.append(("Nummer", f"#{nr}"))

    return zeilen


def _erwartung(nr, pfad: Path | None = None) -> dict:
    """Erwartetes Antwortdatum eines Vorgangs — leer, wenn keine Vorhersage vorliegt.

    Bewusst eine Datei statt eines Aufrufs: die Vorhersage braucht den Mail-Index
    (SSH, Sekunden). Ein Seitenaufruf, der darauf wartet, ist eine Ansicht, die
    man nicht mehr aufmacht.
    """
    try:
        daten = json.loads((pfad or FAELLIGKEIT).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    eintrag = daten.get(str(nr)) if isinstance(daten, dict) else None
    return eintrag if isinstance(eintrag, dict) else {}


def _eintrag_links(nr, pfad: Path | None = None) -> dict:
    """Mail-Bezuege der Verlaufseintraege eines Vorgangs — leer, wenn keine da sind."""
    try:
        daten = json.loads((pfad or EINTRAG_LINKS).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    eintrag = daten.get(str(nr)) if isinstance(daten, dict) else None
    return eintrag if isinstance(eintrag, dict) else {}


def _archiv_eintraege(nr, pfad: Path | None = None) -> list[str]:
    """Der ausgelagerte Teil des Verlaufs — leer, wenn es kein Archiv gibt.

    Faellt die Datei aus oder ist sie kaputt, zeigt die Seite den gekappten
    Verlauf statt gar keinen: eine unvollstaendige Ansicht ist besser als eine
    Fehlerseite, und der Stand steht ohnehin im aktiven Teil.
    """
    ziel = pfad or ARCHIV
    try:
        daten = json.loads(ziel.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    eintraege = daten.get(str(nr), []) if isinstance(daten, dict) else []
    return [str(e).strip() for e in eintraege if str(e).strip()]


# --- Verlauf: aus einem Prosa-Block wird Struktur ---------------------------
#
# Der Verlauf war bis 2026-08-21 ein einziges <pre>: alle Eintraege als
# Fliesstext, durch Leerzeilen getrennt. Bei einem Vorgang mit drei Eintraegen
# geht das noch; das eigentliche Problem ist nicht die Laenge, sondern das
# Mischungsverhaeltnis. In einem typischen /mailcheck-Eintrag sind rund 45 % der
# Zeichen Erhebungsprotokoll ("DB bis …, Restfenster live nachgezogen … — leer"),
# das in JEDEM Eintrag JEDES Vorgangs wortgleich wiederkehrt. Es ist der Beleg
# dafuer, dass sauber gemessen wurde, und es gehoert deshalb auf die Seite —
# aber nicht in die Leselinie.
#
# Drei Eingriffe, alle regelbasiert:
#
# 1. **Kopf abtrennen.** Datum, Uhrzeit, Ereignis und Quelle stehen am Anfang
#    jedes Eintrags in fester Form. Sie werden zur Kopfzeile der Karte, nicht
#    zum ersten Drittel des ersten Satzes.
# 2. **Deckung einklappen.** Saetze, die sich selbst als Erhebungsprotokoll zu
#    erkennen geben, wandern hinter ein <details>. Sichtbar bleibt, DASS gemessen
#    wurde; der Messwert ist einen Klick entfernt.
# 3. **Markierte Saetze in eigene Bahnen.** NUR Saetze, die ihre Funktion selbst
#    benennen ("Offen bleibt …", "HAUPTBEFUND: …", "Fazit: …"), werden
#    herausgezogen. Alles andere bleibt Inhalt.
#
# Punkt 3 ist bewusst eng. Die Versuchung ist gross, aus "… damit abgeschlossen"
# eine Analyse-Bahn zu erraten — dieselbe Versuchung, der `ablage_erledigt.py`
# ausdruecklich widersteht ("Nichts wird geraten"). Ein falsch einsortierter Satz
# ist schlimmer als ein nicht einsortierter: er behauptet eine Gliederung, die der
# Autor nie gemeint hat. Wer die Bahnen will, schreibt sie hin — der Renderer
# belohnt es, er erfindet es nicht.

#: Kopf eines Eintrags. Beide real vorkommenden Formen: "2026-08-21 (/mailcheck):"
#: und "2026-08-20 13:41 GESENDET (Owner):".
_EINTRAG_KOPF = re.compile(
    # Manche Eintraege stellen eine Marke VOR das Datum ("NEU 2026-08-20 (…)").
    # Ohne diesen Zweig faellt der ganze Kopf durch und das Datum steht mitten im
    # Fliesstext — auf der Seite von Vorgang 142 traf das den aeltesten Eintrag.
    r"^(?P<marke>[A-ZÄÖÜ]{2,10}\s+)?"
    r"(?P<datum>\d{4}-\d{2}-\d{2})"
    r"(?:\s+(?P<zeit>\d{1,2}:\d{2}))?"
    r"\s*(?:(?P<ereignis>[A-ZÄÖÜ]{4,14})\s*)?"
    r"(?:\((?P<quelle>[^)]{1,40})\)\s*)?"
    r":\s*"
)

#: Satzgrenze. Gesplittet wird nur vor einem Grossbuchstaben — und NICHT, wenn
#: dem Punkt eine Ziffer vorausgeht. Das schuetzt deutsche Datums- und
#: Ordinalformen: "20.08. Klimm" und "1. Januar" bleiben EIN Satz.
#:
#: Bis 2026-08-21 behauptete der Kommentar an dieser Stelle genau diesen Schutz,
#: waehrend die Regex ihn nicht enthielt — sie hatte nur den Lookbehind auf den
#: Punkt selbst. "Termin am 20.08. Klimm bestaetigt." zerfiel dadurch in zwei
#: Saetze. Der Kommentar ueberlebte eine Vereinfachung des Musters und las sich
#: danach wie ein Beleg. Die zweite Lookbehind-Gruppe unten ist der Schutz, der
#: bis dahin nur behauptet war.
#:
#: Die Sperre greift NUR an den beiden deutschen Formen, nicht an "jeder Ziffer
#: vor dem Punkt". Die erste Fassung dieses Fixes tat genau das — und verschluckte
#: damit echte Satzgrenzen nach Uhrzeiten ("… 16:41. Klimm meldet …"), weil auch
#: dort eine Ziffer vor dem Punkt steht. Gemessen am realen Bestand fiel dadurch
#: der Sachstand ganzer Eintraege in die Deckungs-Bahn. Zwei enge Lookbehinds
#: statt eines breiten:
#:   (?<!\d\.\d\d[.])   — Datum "20.08."  (Uhrzeit "16:41." hat dort ':')
#:   (?!\s+<Monat>)      — Ordinal "1. Januar"
#:
#: Die zweite Bedingung haengt am MONATSNAMEN, nicht an "Ziffer vor dem Punkt".
#: Auch das war eine Zwischenfassung dieses Fixes, und auch sie fiel am realen
#: Bestand: " 2." blockierte die echte Satzgrenze vor einem "OFFEN: …", dessen
#: Vorsatz auf "Anlage 2." endete — der offene Punkt verschwand aus seiner Bahn.
#: Ein Ordinal ist ohne den Monat dahinter nicht von einem Satzende nach einer
#: Zahl zu unterscheiden; also wird nur der Fall gesperrt, der eindeutig ist.
_MONATE = (
    "Januar|Februar|M(?:ä|ae)rz|April|Mai|Juni|Juli|August|"
    "September|Oktober|November|Dezember"
)
#: Die dritte Bedingung ist eine AUSNAHME von der ersten, kein weiterer Filter.
#: Ein deutsches Datum kann einen Satz auch BEENDEN ("Ruecksendefrist 28.08.
#: OFFEN: …"), und von "20.08. Klimm bestaetigt." ist das regelbasiert nicht zu
#: unterscheiden — ausser am Folgewort. Steht dort ein durchgaengig grosses Wort,
#: ist es ein Marker, der nur am Satzanfang vorkommt (OFFEN, FRIST, HAUPTBEFUND).
#: Ohne diese Ausnahme verschwand genau ein realer offener Punkt aus seiner Bahn
#: — gemessen, nicht vermutet: 302 Eintraege, 1 Verlust.
_SATZGRENZE = re.compile(
    r"(?<=[.!?])"
    r"(?:(?<!\d\.\d\d[.])|(?=\s+[A-ZÄÖÜ]{4,}\b))"
    r"(?!\s+(?:" + _MONATE + r")\b)"
    r"\s+(?=[A-ZÄÖÜ„\"'/])"
)

#: Ein Satz ist Erhebungsprotokoll, wenn er sich selbst so ausweist. Absichtlich
#: an den Werkzeug-Vokabeln festgemacht, nicht an "klingt technisch".
_DECKUNG_WORTE = ("nachgezogen", "restfenster", "db bis", "kein neuer eingang")

#: Saetze, die ihre Funktion im ersten Wort nennen. Nur diese werden umgehaengt.
#: Ein Satz meldet einen offenen Punkt, wenn er das in den ersten Worten sagt.
#: Bis zu zwei qualifizierende Woerter davor sind erlaubt — "Unveraendert offen:"
#: und "Weiterhin offen ist …" sind dieselbe Ansage wie "Offen bleibt …", und der
#: reine Wortanfangs-Vergleich hat sie auf der Seite von Vorgang 142 uebersehen.
#: `\b` hinter "offen" haelt "offenbar" und "offensichtlich" heraus.
#: Verneinungen am Satzanfang. "Nichts zu tun." enthaelt den Action-Marker
#: "zu tun" und meint das Gegenteil — ohne diese Sperre wurde der Satz als
#: offener Punkt hervorgehoben. Bewusst nur der Satzanfang: eine Verneinung
#: mitten im Satz ("Der Termin steht, nichts weiter offen") laesst sich nicht
#: mehr regelbasiert zuordnen, und Raten ist hier schlimmer als Nicht-Trennen.
_KEINE_ACTION = re.compile(r"^(?:nichts|kein|keine|keinerlei|nicht)\b", re.IGNORECASE)

_ACTION_MUSTER = re.compile(
    r"^(?:\w+[\s,]+){0,2}(?:offen\b|zu tun\b|to-?do\b|n(?:ae|ä)chste[rn]? schritt|owner:)",
    re.IGNORECASE,
)
_ANALYSE_WORTE = (
    "hauptbefund",
    "befund:",
    "ergebnis:",
    "fazit:",
    "analyse:",
    "bedeutung:",
    "schluss:",
)

#: Ohne Owner ist die Heimat dieser Repos die Standard-Org.
_GITHUB_STANDARD_OWNER = "achimdehnert"

#: Anhaenge bekommen KEINEN Link: der Dienst liefert sie nur unter `<uid>/anhaenge/<name>`
#: aus, und die UID steht im Text nicht verlaesslich daneben.
_DATEI = re.compile(
    r"\b[\w.\-]{3,60}\.(?:pdf|docx?|xlsx?|pptx?|csv|zip|txt|md)\b", re.IGNORECASE
)


def verweise(
    text: str,
    konto: str,
    mail_basis: str = MAIL_BASIS,
    anker: frozenset[str] | None = None,
    marken: dict[str, str] | None = None,
) -> str:
    """Erkannte Referenzen verlinken. `text` ist bereits HTML-escaped.

    Verlinkt wird nur, was VERANKERT ist — also eine Nummer, fuer die
    `eintrag_anker.py` die Message-ID hinterlegt hat. Der Link geht dann auf
    `/a/<schluessel>`, und der Mail-Dienst loest ueber die Message-ID auf: er
    ueberlebt Ablage, Senden und ersetzte Entwuerfe.

    Bis 2026-09-01 zeigte der Link auf `/m/<konto>/<ordner>/<uid>` — die rohe
    IMAP-UID. Gemessen an diesem Tag waren 89 von 203 solcher Links tot
    (platform#2563), weil eine UID nur in ihrem Ordner gilt. Ein toter Link ist
    schlechter als gar keiner: er sieht aus wie ein Beleg und ist keiner. Nicht
    verankerte Nummern werden darum nur ausgezeichnet, nicht verlinkt — und der
    Titel sagt, welches Werkzeug das aendert.

    Ohne `konto` wird gar nichts verlinkt — der Schluessel traegt das Konto, und
    ohne Konto gibt es keinen.

    `marken` traegt fuer die Schluessel, deren Betreff im Vorgang mehrfach
    vorkommt, das Datum der Mail (siehe `gleichbetreffte`). Es wird an den
    Linktext gehaengt, damit zwei Weiterleitungen desselben Strangs
    auseinanderzuhalten sind, ohne beide zu oeffnen.
    """
    if not konto:
        return text
    basis = mail_basis.rstrip("/")
    verankert = _schluessel(ANKER_DATEI) if anker is None else anker
    marken = marken or {}

    def nummer(m: re.Match, segment: str) -> str:
        roh = m.group(0)
        ref = Referenz(
            uid=m.group("uid"),
            ordner=ordner_daneben(segment, m.start()),
            start=m.start(),
            end=m.end(),
        )
        for kandidat in schluessel_kandidaten(konto, ref):
            if kandidat in verankert:
                ziel = f"{basis}/a/{quote(kandidat, safe='')}"
                marke = marken.get(kandidat, "")
                # Die Marke steht IM Link, nicht daneben: sie gehoert zu der
                # Mail, auf die geklickt wird, und ein Zusatz hinter dem Link
                # laese offen, auf welche der beiden Nummern er sich bezieht.
                zusatz = (
                    f" <span class='ref-datum'>{html.escape(marke)}</span>"
                    if marke
                    else ""
                )
                titel = (
                    f"Mail vom {marke.rstrip('.')} oeffnen — gleicher Betreff wie "
                    "eine zweite Mail in diesem Verlauf"
                    if marke
                    else "Mail oeffnen (ueber Message-ID verankert)"
                )
                return (
                    f"<a class='ref' href='{ziel}' target='_blank' rel='noreferrer'"
                    f" title='{html.escape(titel)}'>{roh}{zusatz}</a>"
                )
        return (
            "<span class='ref ohne-anker' title='nicht verankert — "
            "eintrag_anker.py verankert die Nummer, solange sie im Postfach "
            f"noch gilt'>{roh}</span>"
        )

    def schrittweise(roh: str, muster: re.Pattern, ersatz) -> str:
        # Die Ersetzung bekommt das SEGMENT, in dem sie arbeitet: die Ordnersuche
        # rechnet mit Positionen, und die gelten nur innerhalb des Segments —
        # nicht im Gesamttext, in dem vorher schon Links eingesetzt wurden.
        teile = re.split(r"(<a class='ref'.*?</a>)", roh)
        return "".join(
            t
            if t.startswith("<a class='ref'")
            else muster.sub(lambda m, seg=t: ersatz(m, seg), t)
            for t in teile
        )

    def github(m: re.Match, _segment: str) -> str:
        owner = m.group("owner") or _GITHUB_STANDARD_OWNER
        ziel = f"https://github.com/{owner}/{m.group('repo')}/issues/{m.group('nr')}"
        return f"<a class='ref' href='{ziel}' target='_blank' rel='noreferrer'>{m.group(0)}</a>"

    text = schrittweise(text, _REF_GITHUB, github)
    text = schrittweise(text, _REF_NUMMER, nummer)
    return schrittweise(
        text, _DATEI, lambda m, _seg: f"<span class='datei'>{m.group(0)}</span>"
    )


#: Ein Komma ZWISCHEN zwei Ziffern ist ein Dezimaltrennzeichen ("10.160,50 EUR"),
#: kein Listentrenner — es wird beim Split geschuetzt statt zerteilt.
_ZAHL_KOMMA = re.compile(r"(?<=\d),(?=\d)")

#: Nur INNERHALB dieser Bahnen wird ein Komma ueberhaupt als moeglicher Trenner
#: gewertet — ein Fliesstext-Satz mit aufzaehlenden Kommas ("Klimm, Meier und
#: Schulz waren dabei, ...") ist damit ausgenommen; dort ist ein Komma meistens
#: Grammatik, keine Liste.
_LISTEN_PRAEFIX = re.compile(
    r"^(?:Offen|Naechster Schritt|Ergebnis)\s*:\s*", re.IGNORECASE
)


def als_liste(text: str) -> list[str] | None:
    """Zerlegt eine Aufzaehlung im Text in Teile — oder None, wenn keine vorliegt.

    Zwei Erkennungswege, beide konservativ (#2856):

    1. `;` als Trenner, ab zwei Teilen — greift ueberall im Text.
    2. Innerhalb der Bahnen "Offen:"/"Naechster Schritt:"/"Ergebnis:" eine
       Komma-Trennung, aber erst ab drei Teilen — zwei durch Komma getrennte
       Haelften sind meistens ein normaler Satz, keine Liste.

    Datums- und Preisangaben ("04.09.2026 15:05 UTC", "10.160,50 EUR/Jahr")
    werden nicht zerrissen: ein Komma zwischen zwei Ziffern gilt als
    Dezimaltrennzeichen und wird vor dem Split geschuetzt.
    """
    roh = (text or "").strip()
    if not roh:
        return None
    if ";" in roh:
        teile = [t.strip() for t in roh.split(";") if t.strip()]
        if len(teile) >= 2:
            return teile
    treffer = _LISTEN_PRAEFIX.match(roh)
    if treffer:
        rest = roh[treffer.end() :]
        platzhalter = "\x00"
        geschuetzt = _ZAHL_KOMMA.sub(platzhalter, rest)
        teile = [t.replace(platzhalter, ",").strip() for t in geschuetzt.split(",")]
        teile = [t for t in teile if t]
        if len(teile) >= 3:
            return teile
    return None


#: Ein im Eintrag in Anfuehrungszeichen genannter Betreff — beide im Bestand
#: vorkommenden Schreibweisen: gerade Anfuehrungszeichen ("...") und die
#: deutsche Form mit unten oeffnender Anfuehrung (%s...").
_STRANG_ANFUEHRUNG = re.compile(r'["„]([^"„“”]{2,120})["“”]')
#: Antwort-/Weiterleitungspraefixe vor einem zitierten Betreff — mehrfach
#: moeglich ("AW: WG: Angebot"), darum in einer Schleife entfernt.
_STRANG_PRAEFIX = re.compile(r"^(?:AW|RE|WG|FWD)\s*:\s*", re.IGNORECASE)


def strang_schluessel(eintrag: dict) -> str:
    """Gruppierungs-Schluessel eines zerlegten Verlaufseintrags (`zerlege_eintrag`).

    Reihenfolge (#2856): (1) ein im Eintrag in Anfuehrungszeichen genannter
    Betreff — normalisiert (AW:/Re:/WG:/Fwd:-Praefixe entfernt, Kleinschreibung,
    Whitespace vereinheitlicht), damit "AW: Angebot" und "Angebot" denselben
    Strang treffen; (2) sonst das Ereignis bzw. die Quelle aus der Kopfzeile
    (GESENDET, TELEFONAT, Owner, /mailcheck, …); (3) sonst "Sonstiges".
    """
    text = " ".join(eintrag.get("saetze") or [])
    treffer = _STRANG_ANFUEHRUNG.search(text)
    if treffer:
        betreff = treffer.group(1).strip()
        while True:
            gekuerzt = _STRANG_PRAEFIX.sub("", betreff)
            if gekuerzt == betreff:
                break
            betreff = gekuerzt
        norm = re.sub(r"\s+", " ", betreff).strip().lower()
        if norm:
            return norm
    ereignis = str(eintrag.get("ereignis") or "").strip()
    if ereignis:
        return ereignis
    quelle = str(eintrag.get("quelle") or "").strip()
    if quelle:
        return quelle
    return "Sonstiges"


def gruppiere_straenge(eintraege: list[tuple]) -> list[tuple[str, list]]:
    """Verlaufseintraege (bereits zerlegt) nach Strang gruppieren.

    `eintraege` sind (nummer, zerlegt)-Paare in CHRONOLOGISCHER Reihenfolge —
    dieselbe Zaehlung wie im Rest der Vorgangsseite (aelteste Nummer zuerst).
    Straenge werden nach ihrem juengsten enthaltenen Eintrag sortiert (neueste
    zuerst); innerhalb eines Strangs steht die juengste Karte zuerst. Ein
    Strang mit nur einer Karte bleibt ein Strang — kein Sonderfall (#2856).
    """
    gruppen: dict[str, list[tuple]] = {}
    reihenfolge: list[str] = []
    for eintrag in eintraege:
        nummer, t = eintrag
        schluessel = strang_schluessel(t)
        if schluessel not in gruppen:
            gruppen[schluessel] = []
            reihenfolge.append(schluessel)
        gruppen[schluessel].append(eintrag)
    ergebnis = [
        (schluessel, sorted(gruppen[schluessel], key=lambda p: p[0] or 0, reverse=True))
        for schluessel in reihenfolge
    ]
    ergebnis.sort(key=lambda kv: max((p[0] or 0) for p in kv[1]), reverse=True)
    return ergebnis


def _strang_titel(schluessel: str) -> str:
    """Anzeigetitel eines Strangs — Grossschreibung des ersten Buchstabens."""
    text = schluessel.strip()
    return text[:1].upper() + text[1:] if text else "Sonstiges"


def zerlege_eintrag(roh: str) -> dict:
    """Einen Verlaufseintrag in Kopf, Deckung, Inhalt, Analyse und Action zerlegen.

    Rueckgabe immer vollstaendig besetzt (leere Strings statt fehlender Schluessel),
    damit der Aufrufer nicht jedes Feld einzeln absichern muss.
    """
    kopf = _EINTRAG_KOPF.match(roh)
    if kopf:
        rest = roh[kopf.end() :].strip()
        marken = kopf.groupdict()
    else:
        rest, marken = roh.strip(), {}
    saetze = [s.strip() for s in _SATZGRENZE.split(rest) if s.strip()]
    deckung: list[str] = []
    analyse: list[str] = []
    action: list[str] = []
    inhalt: list[str] = []
    for satz in saetze:
        klein = satz.lower()
        if any(w in klein for w in _DECKUNG_WORTE):
            deckung.append(satz)
        elif _ACTION_MUSTER.match(satz) and not _KEINE_ACTION.match(satz):
            action.append(satz)
        elif klein.startswith(_ANALYSE_WORTE):
            analyse.append(satz)
        else:
            inhalt.append(satz)
    return {
        # Die Zerlegung selbst wird mitgegeben, nicht nur ihr Ergebnis. Grund:
        # ein Test, der nur `inhalt` prueft, kann einen Zerlegungsfehler NICHT
        # sehen — die Bahn fuegt ihre Saetze mit " ".join() wieder zusammen, und
        # zwei falsch getrennte Fragmente ergeben denselben String wie ein
        # ungetrennter Satz. Genau daran war die Zusicherung "ein Datum trennt
        # keinen Satz" vakuos: der Test bestand, waehrend die Regex falsch lag.
        "saetze": saetze,
        "datum": marken.get("datum") or "",
        "zeit": marken.get("zeit") or "",
        "ereignis": marken.get("ereignis") or "",
        "quelle": marken.get("quelle") or "",
        "deckung": " ".join(deckung),
        "inhalt": " ".join(inhalt),
        "analyse": " ".join(analyse),
        "action": " ".join(action),
    }


def verlauf(
    eintraege: list,
    konto: str = "",
    mail_basis: str = MAIL_BASIS,
    neueste_zuerst: bool = True,
    nr=None,
    links: dict | None = None,
    anker: frozenset[str] | None = None,
) -> str:
    """Der Verlauf als nach Strang gruppierte Karten — Beiwerk eingeklappt.

    Die Reihenfolge entscheidet der Aufrufer: der Stand steht oben (Default), die
    Entstehung liest sich von unten (`?alt=1`) — beides gilt jetzt fuer Straenge
    UND fuer die Karten innerhalb eines Strangs (#2856).
    """
    if not eintraege:
        return "<p class='kein-ziel'>Kein Verlauf.</p>"
    links = links if links is not None else _eintrag_links(nr)
    # Einmal je Seite gelesen, nicht je Referenz — der Verlauf nennt Dutzende.
    anker = _schluessel(ANKER_DATEI) if anker is None else anker
    # Vorlauf ueber ALLE Eintraege: ob ein Betreff unterscheidet, entscheidet
    # sich am ganzen Verlauf, nicht am einzelnen Eintrag — die beiden Mails, die
    # sich gleichen, stehen typischerweise in verschiedenen Eintraegen.
    genannt: list[str] = []
    for eintrag in eintraege:
        roh_text = eintrag[1] if isinstance(eintrag, tuple) else eintrag
        genannt += anker_im_text(html.escape(str(roh_text)), konto, anker)
    datumsmarken = gleichbetreffte(genannt, _anker_daten(ANKER_DATEI))

    # Nummer und Text kommen als Paar herein: gezaehlt wird vom AELTESTEN Ende,
    # damit `#132-4` derselbe Eintrag bleibt, wenn oben zehn neue dazukommen.
    # Eine Nummer, die sich mit der Anzeige verschiebt, taugt nicht zum Zeigen.
    geparst: list[tuple] = [
        (
            (eintrag[0], zerlege_eintrag(eintrag[1]))
            if isinstance(eintrag, tuple)
            else (None, zerlege_eintrag(eintrag))
        )
        for eintrag in eintraege
    ]

    def karte(nummer, t) -> str | None:
        bezug = links.get(str(nummer), {}) if nummer is not None else {}

        def bahn(schluessel: str, klasse: str, label: str = "", t=t) -> str:
            wert = t[schluessel]
            if not wert:
                return ""
            marke = f"<span class='bahn-marke'>{label}</span>" if label else ""
            # Nummerierte Liste, wenn der Text eine Aufzaehlung ist — sonst
            # bleibt es Fliesstext (#2856 K3).
            teile = als_liste(wert)
            if teile:
                rumpf = (
                    "<ol>"
                    + "".join(
                        f"<li>{verweise(html.escape(teil), konto, mail_basis, anker, datumsmarken)}</li>"
                        for teil in teile
                    )
                    + "</ol>"
                )
            else:
                rumpf = verweise(
                    html.escape(wert), konto, mail_basis, anker, datumsmarken
                )
            return f"<div class='{klasse}'>{marke}{rumpf}</div>"

        marken = []
        if nummer is not None:
            marke_nr = f"#{html.escape(str(nr))}-{nummer}" if nr else f"#{nummer}"
            marken.append(
                f"<a class='eintrag-nr' id='e{nummer}' href='#e{nummer}'>{marke_nr}</a>"
            )
        if t["datum"]:
            zeit = f" {t['zeit']}" if t["zeit"] else ""
            marken.append(
                f"<time class='eintrag-datum'>{html.escape(t['datum'] + zeit)}</time>"
            )
        if t["ereignis"]:
            marken.append(f"<span class='ereignis'>{html.escape(t['ereignis'])}</span>")
        if t["quelle"]:
            marken.append(f"<span class='quelle'>{html.escape(t['quelle'])}</span>")
        # Der Mail-Bezug steht im Kopf, nicht im Text: er sagt, WELCHE Mail dieser
        # Eintrag meint. Ohne adressierbare Nummer bleibt es bei Betreff und Datum
        # — identifizierend, aber ohne Klick, der ins Leere fuehrt.
        if bezug.get("betreff"):
            titel = html.escape(f"{bezug.get('datum', '')} {bezug['betreff']}"[:110])
            marken.append(
                f"<a class='mail-bezug' href='{html.escape(bezug['url'])}'"
                f" target='_blank' rel='noreferrer'>✉ {titel}</a>"
                if bezug.get("url")
                else f"<span class='mail-bezug ohne-link'>✉ {titel}</span>"
            )
        # Die Deckung sitzt IM Kopf, eingeklappt hinter <details>: sie ist eine
        # Eigenschaft der Erhebung, keine Aussage ueber den Vorgang (#2856 K3).
        if t["deckung"]:
            marken.append(
                "<details class='deckung'><summary>Deckung</summary>"
                f"<p>{verweise(html.escape(t['deckung']), konto, mail_basis, anker, datumsmarken)}</p></details>"
            )
        kopfzeile = (
            f"<header class='eintrag-kopf'>{''.join(marken)}</header>" if marken else ""
        )
        rumpf = (
            bahn("inhalt", "bahn-inhalt")
            + bahn("analyse", "bahn-analyse", "Analyse")
            + bahn("action", "bahn-action", "Offen")
        )
        if not rumpf:
            return None
        return f"<article class='eintrag'>{kopfzeile}{rumpf}</article>"

    def strang_karten(alt_zuerst: list) -> list[str]:
        """Karten EINES Strangs, chronologisch hereingereicht — Stille kollabiert."""
        karten: list[str] = []
        stille: list = []
        for nummer, t in alt_zuerst:
            html_karte = karte(nummer, t)
            if html_karte is None:
                # Ein Eintrag, der nur aus Deckung besteht, ist trotzdem ein
                # Eintrag — er belegt, dass an dem Tag geprueft und nichts
                # gefunden wurde. Aber vier solche Karten hintereinander sind
                # vier Karten, die dasselbe sagen: die Erhebung lief, der
                # Vorgang stand still. Sie werden zu EINER Zeile zusammengefasst
                # (Owner-Befund 2026-08-21, „keine wiederkehrenden
                # Redundanzen"); die Nummern bleiben nennbar.
                stille.append((nummer, t["datum"]))
                continue
            karten.extend(_stille_karte(stille))
            stille.clear()
            karten.append(html_karte)
        karten.extend(_stille_karte(stille))
        return karten

    # gruppiere_straenge liefert Straenge neueste-zuerst, Karten je Strang
    # ebenso neueste-zuerst. Fuer `?alt=1` wird beides gedreht.
    straenge = gruppiere_straenge(geparst)
    if not neueste_zuerst:
        straenge = list(reversed(straenge))
    abschnitte: list[str] = []
    for schluessel, karten_dieses_strangs in straenge:
        alt_zuerst = list(reversed(karten_dieses_strangs))
        karten = strang_karten(alt_zuerst)
        # `strang_karten` gibt chronologisch (aelteste zuerst) zurueck — das ist
        # der Fall `?alt=1`. Der Default dreht auf neueste zuerst.
        if neueste_zuerst:
            karten = list(reversed(karten))
        abschnitte.append(
            "<section class='strang'>"
            f"<h3 class='strang-kopf'>{html.escape(_strang_titel(schluessel))} "
            f"<span class='zahl'>{len(karten_dieses_strangs)}</span></h3>"
            f"{''.join(karten)}</section>"
        )
    return "".join(abschnitte)


def _stille_karte(stille: list) -> list[str]:
    """Aus einer Folge ereignisloser Erhebungen wird eine Zeile."""
    if not stille:
        return []
    if len(stille) == 1:
        nummer, datum = stille[0]
        marke = f"<span class='eintrag-nr'>#{nummer}</span> " if nummer else ""
        return [
            (
                f"<article class='eintrag still'>{marke}"
                f"<time class='eintrag-datum'>{html.escape(datum or '')}</time>"
                " <span class='kein-ziel'>Nur Erhebung, kein neuer Sachstand.</span>"
                "</article>"
            )
        ]
    # Chronologisch, nicht in Eingabereihenfolge: die Spanne beschreibt einen
    # Zeitraum, und "12. bis 10." ist keiner.
    datteln = sorted(d for _, d in stille if d)
    spanne = (
        f"{datteln[0]} bis {datteln[-1]}"
        if len(datteln) > 1
        else (datteln[0] if datteln else "")
    )
    nummern = ", ".join(f"#{n}" for n, _ in stille if n)
    return [
        (
            "<article class='eintrag still'>"
            f"<time class='eintrag-datum'>{html.escape(spanne)}</time> "
            f"<span class='kein-ziel'>{len(stille)} Erhebungen ohne neuen Sachstand</span>"
            f"<span class='eintrag-nr'> {html.escape(nummern)}</span></article>"
        )
    ]


def detail(
    v: dict,
    mail_basis: str = MAIL_BASIS,
    basis: str = "",
    anker: dict[str, str] | None = None,
    alt_zuerst: bool = False,
) -> str:
    """Ein einzelner Vorgang als eigenstaendige Seite — auch ohne Overlay lesbar."""

    def _reihe(felder) -> str:
        return "".join(
            f"<tr><th>{html.escape(label)}</th>"
            f"<td>{html.escape(str(v.get(feld) or '—'))}</td></tr>"
            for feld, label in felder
        )

    # Feste Zusammenfassung oben (#2856 Zielbild 1) — Stand, Naechster Schritt,
    # Frist, Gegenueber, Konto, Typ, Bucket, Nummer. Fehlende Felder fehlen
    # einfach in der Liste, kein Rate-Ersatzwert.
    zus_zeilen = zusammenfassung(v)
    # Erwartung statt leerer Frist: bei einem wartenden Vorgang ohne Frist ist
    # „bis wann ist das normal" die Frage, die man an die Seite hat. Das ist
    # IO-abhaengig (liest `mail-faelligkeit.json`) und bleibt darum ausserhalb
    # der reinen Funktion `zusammenfassung()`.
    if not v.get("frist") and not v.get("frist_grund"):
        erwartung = _erwartung(v.get("nr"))
        if erwartung.get("spaetestens"):
            wort = (
                "ueberfaellig seit" if erwartung.get("ueberfaellig") else "erwartet bis"
            )
            zus_zeilen = [*zus_zeilen, ("Frist", f"{wort} {erwartung['spaetestens']}")]
    zusammenfassung_html = (
        "<table class='zusammenfassung'><tbody>"
        + "".join(
            f"<tr><th>{html.escape(label)}</th><td>{html.escape(wert)}</td></tr>"
            for label, wert in zus_zeilen
        )
        + "</tbody></table>"
        if zus_zeilen
        else ""
    )
    zweite = _reihe(DETAIL_FELDER_ZWEITE_REIHE)
    schritte = naechste_schritte(v, mail_basis, basis, anker)
    nr = v.get("nr")
    # Dieselbe Nummer wie in der Uebersicht — sie ist der Wiedererkennungsanker
    # zwischen Liste, Chat-Board und Mail-Adresse `/a/<nr>`.
    nr_marke = (
        f"<span class='nr-marke'>#{html.escape(str(nr))}</span> "
        if nr not in (None, "")
        else ""
    )
    # Neuester Eintrag zuerst. Die Notiz waechst durch Anhaengen, chronologisch
    # gelesen steht der aktuelle Stand also ganz unten — bei Vorgaengen mit
    # 15.000 Zeichen Verlauf muss man dafuer erst ans Ende scrollen. Umgedreht
    # steht der Stand da, wo man hinsieht (Owner-Weisung 2026-08-20).
    eintraege = [t.strip() for t in str(v.get("notiz") or "").split(" | ") if t.strip()]
    # Archivierte Eintraege davorsetzen: sie sind aelter, und die Anzeige dreht
    # gleich um. So bleibt der Verlauf vollstaendig, obwohl der Ledger gekappt ist.
    eintraege = _archiv_eintraege(v.get("nr")) + eintraege
    # Erst nummerieren, dann drehen: die Nummer gehoert zum Eintrag, nicht zur
    # Anzeige. Sonst waere `#132-1` je nach Sortierung ein anderer Eintrag.
    nummeriert = list(enumerate(eintraege, start=1))
    verlaufskarten = verlauf(
        nummeriert,
        str(v.get("konto") or ""),
        mail_basis,
        neueste_zuerst=not alt_zuerst,
        nr=v.get("nr"),
    )
    schalter = (
        "<a class='reihenfolge' href='?'>neueste zuerst</a>"
        if alt_zuerst
        else "<a class='reihenfolge' href='?alt=1'>aelteste zuerst</a>"
    )
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{html.escape(v.get("thread_key", "Vorgang"))}</title><style>{CSS}</style></head>
<body><main>
<h1>{nr_marke}{html.escape(v.get("thread_key", "Vorgang"))}</h1>
<p class="stand">{html.escape(v.get("kurz") or "")}</p>
{zusammenfassung_html}
<details class="stammdaten"><summary>Stammdaten</summary>
<table><tbody>{zweite}</tbody></table></details>
{schritte}
<h2 class="verlauf-kopf">Verlauf
<span class='zusatz'>{schalter} · Erhebungsdetails unter „Deckung"</span></h2>
{verlaufskarten}
<footer>Quelle: mail-vorgaenge.json</footer>
</main></body></html>"""


def baue(
    daten: dict,
    stichtag: date,
    basis: str = "",
    mail_basis: str = MAIL_BASIS,
    anker: dict[str, str] | None = None,
) -> str:
    posten = daten.get("vorgaenge", [])
    # Einmal je Seitenaufbau lesen statt einmal je Zeile: die Datei aendert sich
    # waehrend eines Aufbaus nicht, und 18 Dateizugriffe fuer 18 Zeilen waeren
    # Verschwendung. `None` heisst hier "noch nicht geladen", nicht "leer".
    if anker is None:
        anker = aufloesbare_nummern()
    nach_bucket: dict[str, list[dict]] = {k: [] for k, _, _ in BUCKETS}
    # Ein Vorgang ohne bekannten Bucket verschwindet nicht — er landet sichtbar
    # bei "Dein Zug", damit eine fehlende Klassifikation auffaellt statt zu schweigen.
    for v in posten:
        schluessel = v.get("bucket")
        if schluessel == "erledigt" and not frisch_erledigt(v, stichtag):
            continue  # laengst geschlossen — bleibt im Ledger, nicht auf der Seite
        nach_bucket[schluessel if schluessel in nach_bucket else "owner"].append(v)
    abschnitte = "".join(
        abschnitt(t, u, nach_bucket.get(k, []), stichtag, basis, mail_basis, anker)
        for k, t, u in BUCKETS
    )
    geprueft = html.escape(str(daten.get("letzte_pruefung", "unbekannt")))
    offen = sum(1 for v in posten if v.get("bucket") != "erledigt")
    faellig = sum(
        1 for v in posten if (d := frist_tage(v, stichtag)) is not None and d <= 3
    )
    # Der Drei-Sekunden-Blick (#2176 Kriterium 4): die Seite beantwortet die drei
    # Fragen schon in der Kopfzeile, bevor jemand eine Tabelle liest.
    still = sum(1 for v in posten if zustand(v, stichtag)[0] == "still")
    dein_zug = sum(1 for v in posten if v.get("bucket") == "owner")
    teile = [f"<strong>{dein_zug} dein Zug</strong>"]
    if faellig:
        teile.append(f"<strong class='kopf-rot'>{faellig} faellig in 3 Tagen</strong>")
    if still:
        teile.append(f"<strong class='kopf-rot'>{still} still</strong>")
    warnung = " · " + " · ".join(teile)
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Arbeitsliste</title><style>{CSS}</style></head>
<body><main>
<h1>Arbeitsliste</h1>
<p class="stand">{offen} offene Vorgaenge · Erhebung vom {geprueft}{warnung}</p>
{frische_banner(daten, stichtag)}
{abschnitte}
<footer>Quelle: mail-vorgaenge.json · gebaut {html.escape(stichtag.isoformat())} ·
fortgeschrieben durch /mailcheck</footer>
</main>{OVERLAY}</body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "todo-board"

    def _sende(self, status: HTTPStatus, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        # Pfade und Query-Strings koennten Vorgangsnamen tragen — nicht ins Log.
        sys.stderr.write(
            f"{self.address_string()} {self.command} {args[1] if len(args) > 1 else ''}\n"
        )

    def do_HEAD(self) -> None:
        self.do_GET()

    def _vorgang(self, schluessel: str, alt_zuerst: bool = False) -> None:
        """Einen Vorgang ausliefern. Der Schluessel wird gegen das Ledger geprueft,
        nicht gegen das Dateisystem — es gibt hier keinen Pfad, der entgleiten kann."""
        try:
            daten = lade(LEDGER)
        except (OSError, json.JSONDecodeError) as exc:
            body = (
                f"<h1>Ledger nicht lesbar</h1><p>{html.escape(str(exc))}</p>".encode()
            )
            self._sende(
                HTTPStatus.INTERNAL_SERVER_ERROR, body, "text/html; charset=utf-8"
            )
            return
        for v in list(daten.get("vorgaenge", [])) + archivierte_vorgaenge():
            if v.get("thread_key") == schluessel and schluessel:
                self._sende(
                    HTTPStatus.OK,
                    detail(v, alt_zuerst=alt_zuerst).encode("utf-8"),
                    "text/html; charset=utf-8",
                )
                return
        self._sende(
            HTTPStatus.NOT_FOUND,
            b"Diesen Vorgang gibt es nicht.\n",
            "text/plain; charset=utf-8",
        )

    def do_GET(self) -> None:
        pfad = self.path.split("?", 1)[0].rstrip("/") or "/"
        if pfad == "/healthz":
            self._sende(HTTPStatus.OK, b"ok\n", "text/plain; charset=utf-8")
            return
        if pfad.startswith("/t/"):
            # `?alt=1` dreht den Verlauf auf aelteste-zuerst. Beide Richtungen haben
            # ihren Fall: der Stand steht oben (Default), die Entstehung liest sich
            # von unten. Ein Schalter kostet weniger als eine Entscheidung, die fuer
            # jeden Vorgang falsch waere.
            alt_zuerst = "alt=1" in (self.path.split("?", 1)[1:] or [""])[0]
            self._vorgang(unquote(pfad[3:]), alt_zuerst)
            return
        if pfad != "/":
            self._sende(
                HTTPStatus.NOT_FOUND, b"nicht gefunden\n", "text/plain; charset=utf-8"
            )
            return
        try:
            seite = baue(lade(LEDGER), heute())
        except (OSError, json.JSONDecodeError) as exc:
            # Ein kaputtes Ledger darf nicht als leere, beruhigende Liste erscheinen.
            body = (
                f"<h1>Ledger nicht lesbar</h1><p>{html.escape(str(exc))}</p>".encode()
            )
            self._sende(
                HTTPStatus.INTERNAL_SERVER_ERROR, body, "text/html; charset=utf-8"
            )
            return
        self._sende(HTTPStatus.OK, seite.encode("utf-8"), "text/html; charset=utf-8")


def cmd_build(args: argparse.Namespace) -> None:
    ziel = Path(args.ausgabe).expanduser()
    ziel.parent.mkdir(parents=True, exist_ok=True)
    # Die gebaute Datei wird als Datei geoeffnet — relative Links zeigten dann ins
    # Dateisystem. Darum absolute Loopback-Adresse, nie file:// (Owner-Entscheid).
    ziel.write_text(
        baue(
            lade(LEDGER),
            date.fromisoformat(args.stichtag) if args.stichtag else heute(),
            basis=f"http://127.0.0.1:{args.basis_port}",
        ),
        encoding="utf-8",
    )
    print(f"OK: {ziel}")


def cmd_serve(args: argparse.Namespace) -> None:
    if args.bind != "127.0.0.1" and not args.oeffentlich_hinter_auth:
        sys.exit(
            f"FEHLER: --bind {args.bind} verweigert. Das Ledger traegt Mandanten- und\n"
            "Pruefungsdaten. Nur mit vorgelagerter Authentifizierung (Cloudflare Access,\n"
            "Tunnel-only) und dann mit --oeffentlich-hinter-auth."
        )
    srv = ThreadingHTTPServer((args.bind, args.port), Handler)
    print(f"Arbeitsliste auf http://{args.bind}:{args.port}/ — Strg-C beendet.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="HTML-Datei schreiben")
    b.add_argument("--ausgabe", default=str(AUSGABE))
    b.add_argument("--basis-port", type=int, default=PORT, dest="basis_port")
    b.add_argument(
        "--stichtag",
        metavar="YYYY-MM-DD",
        help="Bezugsdatum statt heute — macht den Bau tagesunabhaengig reproduzierbar (#2592 K1)",
    )
    b.set_defaults(fn=cmd_build)
    s = sub.add_parser("serve", help="lokal ausliefern, bei jedem Abruf frisch gebaut")
    s.add_argument("--port", type=int, default=PORT)
    s.add_argument("--bind", default="127.0.0.1")
    s.add_argument("--oeffentlich-hinter-auth", action="store_true")
    s.set_defaults(fn=cmd_serve)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
