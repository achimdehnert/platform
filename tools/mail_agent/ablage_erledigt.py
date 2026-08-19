#!/usr/bin/env python3
"""Wohin gehoeren die Mails eines geschlossenen Vorgangs? — Trockenlauf zuerst.

Der Posteingang soll zeigen, was offen ist. Ist ein Vorgang geschlossen, haben
seine Mails dort nichts mehr verloren. Dieses Modul beantwortet die Vorfrage:
**wohin** sie gehoerten. Es bewegt nichts.

Warum ein eigenes Modul und keine Regel in ``regeln.py``
--------------------------------------------------------
``regeln.py`` modelliert *stehende* Regeln: ein Kriterium ueber Nachrichten-
merkmale (Absender, Domain, Betreff) fuehrt auf einen **festen** Zielordner.
Unsere Zuordnung hat weder das eine noch das andere. Das Kriterium lautet
"gehoert zu Vorgang N, und der ist geschlossen", das Ziel ist je Vorgang ein
anderes. Hineingezwungen brauchte es **eine Regel je geschlossenem Vorgang** —
die Regeldatei liefe mit Einwegregeln voll, und ``gegenprobe()``, die auf
Absendermustern beruht, waere fuer jede einzelne bedeutungslos.

Uebernommen wird stattdessen die *Disziplin* von ADR-284 §7a:

* **Trockenlauf ist der Standard.** Dieses Modul kennt gar keinen Schreibpfad.
* **Kein Ordner wird angelegt.** Fehlt das Ziel, ist das ein Befund, keine
  stille Ordnererzeugung — dieselbe Entscheidung wie in
  ``archiv_einsortieren.py``.
* **Nichts wird geraten.** Ein Vorgang ohne aufloesbares Ziel bekommt den Status
  ``keine_zuordnung`` und bleibt liegen.

Die Zuordnungstabelle traegt Namen von Kunden, Studierenden und Privatpersonen.
Sie liegt deshalb **lokal** unter ``~/.claude/mail-ablage-ziele.json`` und nie im
Repo (Charta Art. 2). Dieses Modul liegt versioniert und testbar hier.

Ordnerkonventionen, die schon bestehen und deshalb nicht neu erfunden werden:

* HNU fuehrt ``Betreuungen/<Nachname-Vorname>`` fuer laufende Betreuungen und
  ``Betreuungen/.erledigt/<Nachname-Vorname>`` fuer abgeschlossene. **Ein
  geschlossener Vorgang landet im laufenden Ordner, nicht unter ``.erledigt``** —
  dorthin wandert der ganze Ordner erst, wenn die Betreuung endet. Das bleibt
  eine Handbewegung des Owners.
* Das Geschaeftspostfach fuehrt ``IIL.Kunden/<Kunde>`` und ``Archiv/<Jahr>``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

LEDGER = Path.home() / ".claude" / "mail-vorgaenge.json"
ANKER = Path.home() / ".claude" / "mail-anker.json"
LINKS = Path.home() / ".claude" / "mail-links.json"
ZIELE = Path.home() / ".claude" / "mail-ablage-ziele.json"

#: Fuer diese Vorgangstypen wird in den Betreuungsordnern gesucht.
BETREUUNGS_TYPEN = ("betreuung",)

#: Ordner, aus denen ueberhaupt bewegt wird — je Konto, weil sie anders heissen.
#:
#: Gemessen am 2026-08-18 an einem echten Strang mit neun Nachrichten: drei lagen
#: im Posteingang, drei in "Gesendete Objekte", drei bereits in Fachordnern. Wer den
#: ganzen Strang bewegte, zoege das eigene Gesendete aus seinem Ordner und machte
#: eine bereits getroffene Ablage-Entscheidung rueckgaengig. Aufgeraeumt werden soll
#: der Posteingang — sonst nichts.
#:
#: Der Ordnername ist zugleich der einzige Hinweis auf das Konto, den der Index
#: liefert (siehe ``index_suche``). "Posteingang" gehoert zum Graph-Konto,
#: "INBOX" zu den IMAP-Konten — zwischen den IMAP-Konten trennt er NICHT.
QUELLORDNER_JE_KONTO: dict[str, tuple[str, ...]] = {
    "iil": ("Posteingang",),
    "hnu": ("INBOX",),
    "ad": ("INBOX",),
    "default": ("INBOX",),
}
QUELLORDNER = ("INBOX", "Posteingang")

#: Woran die Zeile haengt, wenn sie nicht ``bereit`` ist. Reihenfolge = Dringlichkeit.
STATUS_REIHENFOLGE = (
    "bereit",
    "ordner_fehlt",
    "kein_anker",
    "keine_zuordnung",
    "kein_datum",
)


@dataclass
class Zeile:
    """Ein geschlossener Vorgang und sein aufgeloestes Ziel."""

    nr: int | None
    konto: str
    gegenueber: str
    kurz: str
    erledigt_am: str | None
    ziel: str | None
    herkunft: str
    status: str

    def als_zeile(self) -> str:
        ziel = self.ziel or "—"
        return (
            f"{str(self.nr or '?'):>4}  {self.konto:<4}  {self.status:<15}  "
            f"{ziel:<34}  {self.kurz[:38]}"
        )


#: Umlaute werden **deutsch** umschrieben, nicht entwertet.
#:
#: Gemessen am 2026-08-18 im Trockenlauf gegen echte Ordner: Der Ordnername traegt
#: den Umlaut ('...oe...' als 'oe'-Ligatur geschrieben), der Vorgangstext dieselbe
#: Firma in ae/oe/ue-Umschrift. Reine Diakritika-Entfernung macht daraus zwei
#: verschiedene Zeichenketten — kein Treffer, und der Vorgang waere still im
#: Jahresarchiv gelandet statt beim Kunden. Beide Schreibweisen kommen real vor;
#: nur die deutsche Umschrift fuehrt sie zusammen.
_UMLAUTE = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "ae", "Ö": "oe", "Ü": "ue", "ß": "ss"}
)


def _slug(text: str) -> str:
    """Kleinbuchstaben ohne Sonderzeichen, Umlaute deutsch umschrieben.

    'Muster-Vorname' und 'Muster, Vorname' sollen sich finden, ebenso ein Name
    mit Umlaut und derselbe Name in ae/oe/ue-Umschrift.
    """
    umgeschrieben = text.translate(_UMLAUTE)
    zerlegt = unicodedata.normalize("NFKD", umgeschrieben)
    ohne = "".join(z for z in zerlegt if not unicodedata.combining(z))
    return re.sub(r"[^a-z0-9]+", " ", ohne.lower()).strip()


def _namensteile(gegenueber: str) -> list[str]:
    """Wortbestandteile eines Gegenuebers, die als Nachname taugen.

    Aus 'HNU / R. Z. Musterfrau (Masterthesis)' wird ['musterfrau', 'masterthesis'];
    kurze Teile und Abkuerzungen fallen weg, weil sie zu unscharf treffen.
    """
    roh = _slug(gegenueber)
    return [t for t in roh.split() if len(t) >= 4]


def ordner_finden(
    gegenueber: str, ordnerbestand: list[str], praefix: str
) -> str | None:
    """Ordner unter ``praefix`` suchen, dessen Name einen Namensteil enthaelt.

    Gesucht wird im **vorhandenen** Bestand statt einen Namen zu bauen: Ein
    konstruierter Pfad koennte auf einen Ordner zeigen, den es nicht gibt, und
    das faellt erst beim Verschieben auf.

    Mehrdeutigkeit ist kein Treffer. Passen zwei Ordner, wird ``None``
    zurueckgegeben — lieber ein Befund als die falsche Schublade.
    """
    teile = _namensteile(gegenueber)
    if not teile:
        return None
    kandidaten = []
    for ordner in ordnerbestand:
        if not ordner.startswith(praefix):
            continue
        # Segmente mit fuehrendem Punkt sind Ablage-Unterbaeume, keine Ziele.
        # Konkret: 'Betreuungen/.erledigt/<Name>' haelt abgeschlossene Betreuungen.
        # Ein geschlossener VORGANG gehoert trotzdem in den laufenden Ordner —
        # der ganze Ordner wandert erst nach '.erledigt', wenn die Betreuung endet,
        # und das ist eine Entscheidung des Owners, nicht dieses Werkzeugs.
        if any(teil.startswith(".") for teil in ordner.split("/")):
            continue
        rest = _slug(ordner[len(praefix) :])
        if not rest:
            continue
        if any(t in rest for t in teile):
            kandidaten.append(ordner)
    # Der kuerzeste Treffer gewinnt, wenn ein Ordner Praefix eines anderen ist
    # ('<Kunden>/<Firma>' vs. '<Kunden>/<Firma>/offen') — sonst ist es echte
    # Mehrdeutigkeit und damit kein Treffer.
    if len(kandidaten) > 1:
        kuerzeste = sorted(kandidaten, key=len)
        if not all(k.startswith(kuerzeste[0]) for k in kuerzeste):
            return None
        return kuerzeste[0]
    return kandidaten[0] if kandidaten else None


def ziel_fuer(
    vorgang: dict,
    ordnerbestand: list[str],
    zuordnung: dict,
) -> tuple[str | None, str]:
    """Zielordner und die Herkunft der Entscheidung.

    Reihenfolge, erste Regel gewinnt — von der ausdruecklichen Ansage zur
    allgemeinsten Konvention:

    1. ``ablage_ziel`` im Vorgang selbst (der Owner hat es hingeschrieben)
    2. Zuordnungstabelle, Muster auf ``gegenueber``
    3. Personen-/Kunden-/Studentenordner des Kontos
    4. Jahresarchiv aus ``erledigt_am``
    """
    if ziel := vorgang.get("ablage_ziel"):
        return ziel, "ansage im vorgang"

    konto = (vorgang.get("konto") or "").lower()
    gegenueber = vorgang.get("gegenueber") or ""

    for muster, ziel in (zuordnung.get(konto) or {}).items():
        if _slug(muster) and _slug(muster) in _slug(gegenueber):
            return ziel, "zuordnungstabelle"

    typ = (vorgang.get("typ") or "").lower()
    praefixe = []
    if typ.startswith(BETREUUNGS_TYPEN):
        praefixe.append("Betreuungen/")
    praefixe += ["IIL.Kunden/", "Betreuungen/"]
    for praefix in praefixe:
        if treffer := ordner_finden(gegenueber, ordnerbestand, praefix):
            return treffer, f"ordnerbestand ({praefix.rstrip('/')})"

    if erledigt := vorgang.get("erledigt_am"):
        jahr = str(erledigt)[:4]
        if jahr.isdigit():
            return f"Archiv/{jahr}", "jahresarchiv"
    return None, "nicht aufloesbar"


def plane(
    ledger: dict,
    anker: dict,
    ordner_je_konto: dict[str, list[str]],
    zuordnung: dict | None = None,
    links: dict | None = None,
) -> list[Zeile]:
    """Fuer jeden geschlossenen Vorgang eine Zeile mit Ziel und Status.

    ``anker`` haelt IMAP-Anker, ``links`` Graph-Kurz-IDs — beide ueber die
    Board-Nummer verschluesselt. Ein Posten gilt als gebunden, wenn EINER von
    beiden ihn kennt; ``board.anker_zustand()`` entscheidet genauso. Nur den
    IMAP-Anker zu pruefen haette jeden Graph-Vorgang faelschlich als ungebunden
    gemeldet.
    """
    links = links or {}
    zuordnung = zuordnung or {}
    zeilen: list[Zeile] = []
    for vorgang in ledger.get("vorgaenge") or []:
        if vorgang.get("bucket") != "erledigt":
            continue
        konto = (vorgang.get("konto") or "").lower()
        bestand = ordner_je_konto.get(konto, [])
        ziel, herkunft = ziel_fuer(vorgang, bestand, zuordnung)

        if not vorgang.get("erledigt_am"):
            status = "kein_datum"
        elif ziel is None:
            status = "keine_zuordnung"
        elif ziel not in bestand:
            # Kein Ordner wird angelegt — das ist eine Owner-Handlung.
            status = "ordner_fehlt"
        elif (
            str(vorgang.get("nr")) not in anker and str(vorgang.get("nr")) not in links
        ):
            # Ohne Anker ist nicht bestimmbar, welche Mails gemeint sind.
            status = "kein_anker"
        else:
            status = "bereit"

        zeilen.append(
            Zeile(
                nr=vorgang.get("nr"),
                konto=konto or "—",
                gegenueber=vorgang.get("gegenueber") or "",
                kurz=vorgang.get("kurz") or vorgang.get("thread_key") or "",
                erledigt_am=vorgang.get("erledigt_am"),
                ziel=ziel,
                herkunft=herkunft,
                status=status,
            )
        )
    return zeilen


def bericht(zeilen: list[Zeile]) -> str:
    """Trockenlauf als Text — Zusammenfassung zuerst, dann die Zeilen."""
    if not zeilen:
        return "Kein geschlossener Vorgang im Ledger — nichts zu planen."
    zaehler = {s: 0 for s in STATUS_REIHENFOLGE}
    for z in zeilen:
        zaehler[z.status] = zaehler.get(z.status, 0) + 1
    kopf = " · ".join(f"{s}: {n}" for s, n in zaehler.items() if n)
    aus = [
        f"Trockenlauf — {len(zeilen)} geschlossene Vorgaenge",
        kopf,
        "",
        f"{'Nr':>4}  {'Kto':<4}  {'Status':<15}  {'Ziel':<34}  Vorgang",
        f"{'-' * 4}  {'-' * 4}  {'-' * 15}  {'-' * 34}  {'-' * 38}",
    ]
    rang = {s: i for i, s in enumerate(STATUS_REIHENFOLGE)}
    for z in sorted(zeilen, key=lambda z: (rang.get(z.status, 99), z.nr or 0)):
        aus.append(z.als_zeile())
    aus += [
        "",
        "Es wurde nichts verschoben. Dieses Werkzeug kennt keinen Schreibpfad.",
    ]
    if zaehler.get("ordner_fehlt"):
        aus.append(
            "Fehlende Ordner werden NICHT angelegt — das ist eine Owner-Handlung."
        )
    return "\n".join(aus)


@dataclass
class Bewegung:
    """Eine geplante Verschiebung — Nachricht, woher, wohin, warum."""

    vorgang_nr: int | None
    konto: str
    betreff: str
    von_ordner: str
    nach_ordner: str
    datum: str

    def als_zeile(self) -> str:
        return (
            f"{str(self.vorgang_nr or '?'):>4}  {self.datum:<10}  "
            f"{self.von_ordner:<12} -> {self.nach_ordner:<30}  {self.betreff[:40]}"
        )


#: Antwort- und Weiterleitungspraefixe, die vor dem Betreffvergleich fallen.
_PRAEFIX = re.compile(r"^\s*(?:(?:aw|re|wg|fw|fwd|antw)\s*:\s*)+", re.IGNORECASE)


def betreff_kern(betreff: str) -> str:
    """Betreff ohne Antwortpraefixe, klein, ohne Mehrfach-Leerzeichen.

    'AW: RE: Postsortierung' und 'Postsortierung' sind derselbe Betreff.
    """
    ohne = _PRAEFIX.sub("", betreff or "")
    return re.sub(r"\s+", " ", ohne).strip().lower()


def strang_fuer(vorgang: dict, suche) -> tuple[str | None, str]:
    """Strang-Kennung des Vorgangs aus dem Index holen.

    ``suche`` wird hereingereicht (Signatur ``suche(**kriterien) -> list[dict]``),
    damit dieser Pfad ohne Datenbank pruefbar bleibt.

    Gesucht wird ueber den Betreff des Vorgangs, weil der Index keine Suche nach
    Message-ID kennt. Trifft mehr als ein Strang, ist das **kein** Ergebnis: Zwei
    Straenge unter demselben Betreff sind zwei Gespraeche, und welches gemeint ist,
    kann dieses Werkzeug nicht entscheiden.

    Ohne Konto-Filter: ``--tenant`` des Index erwartet eine Mandanten-UUID, kein
    Kontokuerzel — gemessen am 2026-08-18. Die Suche laeuft deshalb ueber alle drei
    Konten, und die Trennung passiert erst beim Ordnervergleich unten.
    """
    betreff = (vorgang.get("thread_key") or "").strip()
    if not betreff:
        return None, "kein thread_key im Vorgang"
    treffer = suche(begriff=betreff)
    # Der Index sucht in Betreff, Text UND Anhaengen. Ein `thread_key` wie
    # "Lizenz" trifft damit Dutzende fremder Gespraeche. Gemessen am 2026-08-18:
    # 18 von 23 Vorgaengen kamen so als "mehrdeutig" zurueck. Massgeblich ist
    # deshalb der Betreff selbst, und zwar ohne Antwortpraefixe.
    kern = betreff_kern(betreff)
    genau = [t for t in treffer if betreff_kern(t.get("betreff") or "") == kern]
    straenge = {t.get("strang") for t in genau if t.get("strang")}
    if not straenge:
        if treffer:
            return None, f"{len(treffer)} Volltexttreffer, aber kein gleicher Betreff"
        return None, "im Index nicht gefunden"
    if len(straenge) > 1:
        return None, f"{len(straenge)} Straenge unter diesem Betreff — mehrdeutig"
    return straenge.pop(), "ueber den Betreff"


def bewegungen_fuer(
    vorgang: dict, ziel: str, strang: str, suche
) -> tuple[list[Bewegung], dict[str, int]]:
    """Welche Nachrichten des Strangs bewegt wuerden — und was liegen bleibt.

    Bewegt wird ausschliesslich aus dem Quellordner **des Kontos**. Gesendetes
    bleibt in seinem Ordner, bereits Abgelegtes bleibt abgelegt: Eine getroffene
    Ablage-Entscheidung wird nicht rueckgaengig gemacht, nur eine fehlende
    nachgeholt.

    Bekannte Grenze: Zwischen den beiden IMAP-Konten trennt der Ordnername nicht
    (beide heissen "INBOX"). Traegt derselbe Strang in beiden Konten Nachrichten,
    erscheinen sie hier gemeinsam. Der Schreibpfad muss das aufloesen, bevor er
    bewegt — deshalb gibt es ihn noch nicht.
    """
    konto = (vorgang.get("konto") or "").lower()
    quellen = QUELLORDNER_JE_KONTO.get(konto, QUELLORDNER_JE_KONTO["default"])
    bewegungen: list[Bewegung] = []
    liegen: dict[str, int] = {}
    for nachricht in suche(strang=strang):
        ordner = (nachricht.get("ordner") or [""])[0]
        if ordner not in quellen:
            liegen[ordner or "(ohne Ordner)"] = (
                liegen.get(ordner or "(ohne Ordner)", 0) + 1
            )
            continue
        bewegungen.append(
            Bewegung(
                vorgang_nr=vorgang.get("nr"),
                konto=konto,
                betreff=nachricht.get("betreff") or "",
                von_ordner=ordner,
                nach_ordner=ziel,
                datum=str(nachricht.get("datum") or "")[:10],
            )
        )
    return bewegungen, liegen


def index_suche(**kriterien) -> list[dict]:
    """Echte Index-Abfrage ueber ``suche.py`` — der einzige Ort mit Aussenkontakt.

    Bewusst als eigene Funktion, damit die Logik oben sie als Parameter bekommt
    und ohne Datenbank pruefbar bleibt.
    """
    import subprocess

    hier = Path(__file__).resolve().parent
    befehl = [sys.executable, str(hier / "suche.py"), "--json"]
    for name, wert in kriterien.items():
        if wert:
            befehl += [f"--{name}", str(wert)]
    fertig = subprocess.run(befehl, capture_output=True, text=True)
    if fertig.returncode != 0:
        raise SystemExit(
            f"FEHLER: Index-Abfrage fehlgeschlagen — {fertig.stderr[:300]}"
        )
    try:
        return json.loads(fertig.stdout).get("treffer") or []
    except json.JSONDecodeError:
        raise SystemExit("FEHLER: Index lieferte kein JSON")


def strang_bericht(zeilen: list[Zeile], ledger: dict, suche) -> str:
    """Welche Nachrichten je bereitem Vorgang bewegt wuerden — immer noch trocken."""
    nach_nr = {v.get("nr"): v for v in ledger.get("vorgaenge") or []}
    aus = ["Betroffene Nachrichten (Trockenlauf)", ""]
    gesamt = 0
    for zeile in zeilen:
        if zeile.status != "bereit":
            continue
        vorgang = nach_nr.get(zeile.nr) or {}
        strang, grund = strang_fuer(vorgang, suche)
        if not strang:
            aus.append(f"{str(zeile.nr):>4}  — kein Strang: {grund}")
            continue
        bewegungen, liegen = bewegungen_fuer(vorgang, zeile.ziel or "", strang, suche)
        gesamt += len(bewegungen)
        rest = ", ".join(f"{n}x {o}" for o, n in sorted(liegen.items())) or "nichts"
        aus.append(
            f"{str(zeile.nr):>4}  {len(bewegungen)} aus dem Posteingang · "
            f"bleibt liegen: {rest}"
        )
        for b in bewegungen:
            aus.append("      " + b.als_zeile())
    aus += [
        "",
        f"Summe: {gesamt} Nachrichten wuerden bewegt. Es wurde nichts bewegt.",
        "Der Index ist ein Schnappschuss von 03:30 — was danach umsortiert wurde,",
        "steht hier moeglicherweise mit dem alten Ordner.",
    ]
    return "\n".join(aus)


#: Wohin der Lauf protokolliert wird. Dieselbe Datei wie bei `regeln.py`, damit
#: es EINEN Ort gibt, an dem steht, was dieses System an Mails bewegt hat.
PROTOKOLL = Path.home() / ".claude" / "mail-regeln-protokoll.jsonl"


class AblageFehler(RuntimeError):
    """Abbruch mit Grund — nie stillschweigend weitermachen."""


def _cli(*teile: str) -> str:
    """Ein Werkzeug aus diesem Verzeichnis aufrufen und stdout zurueckgeben."""
    import subprocess

    hier = Path(__file__).resolve().parent
    fertig = subprocess.run(
        [sys.executable, str(hier / teile[0]), *teile[1:]],
        capture_output=True,
        text=True,
    )
    if fertig.returncode != 0:
        raise AblageFehler(f"{teile[0]} fehlgeschlagen: {fertig.stderr[:300]}")
    return fertig.stdout


def graph_zeilen_lesen(ausgabe: str) -> list[dict]:
    """Die zweizeilige Fundausgabe von ``graph_mail --find`` in Datensaetze.

    Format je Treffer::

        · 2026-08-18T07:27  absender@example.com   Betreff
          id: AAMk...=

    Bewusst als eigene Funktion mit eigenem Test: das ist die einzige Stelle,
    an der dieses Modul auf eine Textausgabe angewiesen ist — ``graph_mail``
    kennt kein ``--json``.
    """
    aus: list[dict] = []
    offen: dict | None = None
    for zeile in ausgabe.splitlines():
        roh = zeile.strip()
        if roh.startswith("·"):
            rest = roh.lstrip("· ").strip()
            teile = rest.split(None, 1)
            if not teile:
                continue
            datum = teile[0]
            spur = teile[1] if len(teile) > 1 else ""
            stueck = spur.split(None, 1)
            betreff = stueck[1].strip() if len(stueck) > 1 else spur.strip()
            offen = {"datum": datum[:10], "betreff": betreff, "kennung": None}
        elif roh.startswith("id:") and offen is not None:
            offen["kennung"] = roh[3:].strip()
            aus.append(offen)
            offen = None
    return [e for e in aus if e["kennung"]]


def postfach_auflisten(konto: str, ordner: str) -> list[dict]:
    """Live-Bestand eines Ordners: Kennung, Betreff, Datum.

    Die Kennung ist kontoabhaengig — IMAP-UID oder Graph-messageId. Sie wird
    nur weitergereicht, nie interpretiert.
    """
    if konto == "iil":
        roh = _cli(
            "graph_mail.py", "--find", "--all", "--source", ordner, "--days", "365"
        )
        return graph_zeilen_lesen(roh)
    roh = _cli(
        "read_mail.py",
        "--account",
        konto,
        "--folder",
        ordner,
        "--list",
        "500",
        "--json",
    )
    daten = json.loads(roh)
    return [
        {
            "kennung": str(t.get("nummer")),
            "betreff": t.get("betreff") or "",
            "datum": _datum_kern(t.get("datum") or ""),
        }
        for t in (daten.get("treffer") or [])
    ]


def postfach_verschieben(
    konto: str, ordner: str, kennungen: list[str], ziel: str
) -> None:
    """Genau die benannten Nachrichten bewegen — kein Suchmuster."""
    if not kennungen:
        return
    if konto == "iil":
        args = ["graph_mail.py", "--move", "--to", ziel, "--yes"]
        for k in kennungen:
            args += ["--id", k]
    else:
        args = [
            "organize_mail.py",
            "--account",
            konto,
            "--move",
            "--source",
            ordner,
            "--to",
            ziel,
            "--yes",
        ]
        for k in kennungen:
            args += ["--uid", k]
    _cli(*args)


def _datum_kern(roh: str) -> str:
    """Ein Datum aus verschiedenen Schreibweisen auf ``YYYY-MM-DD`` bringen."""
    roh = (roh or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", roh):
        return roh[:10]
    from email.utils import parsedate_to_datetime

    try:
        return parsedate_to_datetime(roh).date().isoformat()
    except (TypeError, ValueError):
        return roh[:10]


def abgleichen(
    bewegungen: list["Bewegung"], bestand: list[dict]
) -> tuple[list[tuple["Bewegung", str]], list[tuple["Bewegung", str]]]:
    """Erwartete Nachrichten auf echte Kennungen des Postfachs abbilden.

    **Warum dieser Schritt ueberhaupt existiert:** Der Index ist ein
    Schnappschuss von 03:30. Was seither bewegt, geloescht oder umsortiert
    wurde, steht dort noch mit dem alten Ordner. Ohne Abgleich wuerde der
    Schreibpfad auf einen Bestand zielen, den es nicht mehr gibt.

    Abgeglichen wird ueber Betreff-Kern **und** Datum. Der Betreff allein
    genuegt nicht: ein Strang enthaelt oft mehrere Nachrichten mit demselben
    Betreff, und ohne Datum waere nicht entscheidbar, welche gemeint ist.

    Rueckgabe: (zuordenbar, uebersprungen mit Grund).
    """
    frei = list(bestand)
    treffer: list[tuple[Bewegung, str]] = []
    fehlend: list[tuple[Bewegung, str]] = []
    for b in bewegungen:
        kern = betreff_kern(b.betreff)
        passend = [
            e
            for e in frei
            if betreff_kern(e.get("betreff", "")) == kern
            and _datum_kern(e.get("datum", "")) == b.datum
        ]
        if not passend:
            fehlend.append((b, "im Quellordner nicht mehr vorhanden"))
            continue
        gewaehlt = passend[0]
        frei.remove(gewaehlt)
        treffer.append((b, gewaehlt["kennung"]))
    return treffer, fehlend


def ruecknahme_aufloesen(
    eintraege: list[dict], auflisten=None
) -> tuple[list[tuple[dict, str]], list[tuple[dict, str]]]:
    """Protokollierte Rueckbewegungen auf **heute gueltige** Kennungen abbilden.

    **Warum das noetig ist:** Der Umzug entwertet die Kennung, die ihn
    protokolliert hat — die Graph-messageId wird beim Verschieben neu
    vergeben, die IMAP-UID ebenso (gemessen 2026-08-19 an einer echten
    Nachricht). Die Rücknahme muss die Nachricht daher an ihrem *jetzigen*
    Ort neu finden: ueber Betreff-Kern und, wenn protokolliert, das Datum.

    Ohne Datum wird nur der Betreff verglichen; bleiben dann mehrere
    Kandidaten uebrig, wird die Nachricht **nicht** bewegt. Lieber eine
    Fehlanzeige als die falsche Mail zurueckgeholt.
    """
    hole = auflisten or postfach_auflisten
    bestaende: dict[tuple[str, str], list[dict]] = {}
    treffer: list[tuple[dict, str]] = []
    offen: list[tuple[dict, str]] = []
    for e in eintraege:
        konto = e.get("konto")
        if not konto:
            offen.append((e, "kein Konto im Protokoll — Transport unbestimmbar"))
            continue
        e["konto"] = konto
        schluessel = (konto, e["quellordner"])
        if schluessel not in bestaende:
            bestaende[schluessel] = hole(konto, e["quellordner"])
        frei = bestaende[schluessel]
        kern = betreff_kern(e.get("betreff", ""))
        datum = _datum_kern(e.get("datum", "")) if e.get("datum") else ""
        passend = [
            k
            for k in frei
            if betreff_kern(k.get("betreff", "")) == kern
            and (not datum or _datum_kern(k.get("datum", "")) == datum)
        ]
        if not passend:
            offen.append((e, f"in '{e['quellordner']}' nicht gefunden"))
            continue
        if len(passend) > 1:
            offen.append(
                (e, f"{len(passend)} gleiche Betreffe — ohne Datum nicht eindeutig")
            )
            continue
        frei.remove(passend[0])
        treffer.append((e, passend[0]["kennung"]))
    return treffer, offen


def anwenden(
    paare: list[tuple["Bewegung", str]],
    lauf_id: str,
    verschieben=postfach_verschieben,
    protokoll: Path | None = None,
) -> int:
    """Bewegungen ausfuehren und protokollieren. Ohne Protokoll keine Ausfuehrung.

    Das Protokoll wird **vor** dem Verschieben geschrieben. Bricht der Umzug in
    der Mitte ab, ist der begonnene Lauf trotzdem rueckabwickelbar; ein Eintrag
    zu einer nicht bewegten Nachricht kostet bei der Ruecknahme nur eine
    Fehlanzeige. Andersherum waere eine bewegte Nachricht ohne Eintrag
    unauffindbar.
    """
    if not paare:
        return 0
    ziel_protokoll = protokoll or PROTOKOLL
    eintraege = [
        {
            "id": kennung,
            "konto": b.konto,
            "betreff": b.betreff,
            "datum": b.datum,
            "quellordner": b.von_ordner,
            "zielordner": b.nach_ordner,
            "aktion": "verschieben",
            "regel_id": f"vorgang-{b.vorgang_nr}",
            "grund": "Vorgang geschlossen",
        }
        for b, kennung in paare
    ]
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import regeln

    regeln.protokollieren(eintraege, ziel_protokoll, lauf_id)

    gruppen: dict[tuple[str, str, str], list[str]] = {}
    for b, kennung in paare:
        gruppen.setdefault((b.konto, b.von_ordner, b.nach_ordner), []).append(kennung)
    for (konto, quelle, ziel), kennungen in gruppen.items():
        verschieben(konto, quelle, kennungen, ziel)
    return len(paare)


def _lade(pfad: Path, standard):
    if not pfad.exists():
        return standard
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except json.JSONDecodeError as fehler:
        raise SystemExit(f"FEHLER: {pfad} ist kein gueltiges JSON — {fehler}")


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Trockenlauf: wohin die Mails geschlossener Vorgaenge gehoerten. "
            "Verschiebt nichts."
        )
    )
    p.add_argument(
        "--ordner",
        action="append",
        metavar="KONTO=DATEI",
        help="Ordnerliste je Konto (eine Zeile je Ordner); mehrfach moeglich",
    )
    p.add_argument("--ledger", type=Path, default=LEDGER)
    p.add_argument(
        "--straenge",
        action="store_true",
        help="zusaetzlich die betroffenen Nachrichten je Vorgang aufloesen (Index-Abfrage)",
    )
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--apply",
        action="store_true",
        help="tatsaechlich verschieben (Default ist Trockenlauf); setzt --straenge voraus",
    )
    p.add_argument(
        "--ruecknahme",
        metavar="LAUF_ID",
        help="einen protokollierten Lauf rueckgaengig machen",
    )
    args = p.parse_args()

    if args.ruecknahme:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import regeln

        zurueck = regeln.ruecknahme(PROTOKOLL, args.ruecknahme)
        paare, offen = ruecknahme_aufloesen(zurueck)
        for e, grund in offen:
            print(f"  uebersprungen: {e.get('betreff', '')[:50]} — {grund}")
        if not paare:
            raise SystemExit("FEHLER: keine der Nachrichten war am Zielort auffindbar.")
        gruppen: dict[tuple[str, str, str], list[str]] = {}
        for e, kennung in paare:
            schluessel = (e["konto"], e["quellordner"], e["zielordner"])
            gruppen.setdefault(schluessel, []).append(kennung)
        for (konto, quelle, ziel), kennungen in gruppen.items():
            postfach_verschieben(konto, quelle, kennungen, ziel)
        neue_id = f"ruecknahme-{args.ruecknahme}"
        regeln.protokollieren([{**e, "id": k} for e, k in paare], PROTOKOLL, neue_id)
        print(f"OK: {len(paare)} Nachricht(en) zurueckbewegt (Lauf {neue_id}).")
        sys.exit(0)

    ordner_je_konto: dict[str, list[str]] = {}
    for eintrag in args.ordner or []:
        if "=" not in eintrag:
            raise SystemExit(
                f"FEHLER: --ordner erwartet KONTO=DATEI, nicht {eintrag!r}"
            )
        konto, datei = eintrag.split("=", 1)
        pfad = Path(datei).expanduser()
        if not pfad.exists():
            raise SystemExit(f"FEHLER: Ordnerliste {pfad} fehlt")
        ordner_je_konto[konto.lower()] = [
            z.strip()
            for z in pfad.read_text(encoding="utf-8").splitlines()
            if z.strip()
        ]

    zeilen = plane(
        _lade(args.ledger, {}),
        _lade(ANKER, {}),
        ordner_je_konto,
        _lade(ZIELE, {}),
        _lade(LINKS, {}),
    )
    if args.json:
        print(json.dumps([z.__dict__ for z in zeilen], ensure_ascii=False, indent=2))
    else:
        print(bericht(zeilen))

    if args.apply and not args.straenge:
        raise SystemExit(
            "FEHLER: --apply setzt --straenge voraus — ohne aufgeloeste Straenge "
            "gibt es nichts zu verschieben."
        )

    if args.straenge:
        print()
        print(strang_bericht(zeilen, _lade(args.ledger, {}), index_suche))

    if args.apply:
        ledger = _lade(args.ledger, {})
        nach_nr = {v.get("nr"): v for v in ledger.get("vorgaenge") or []}
        lauf_id = f"ablage-{max((z.erledigt_am or '') for z in zeilen) or 'lauf'}-{len(zeilen)}"
        alle: list[tuple[Bewegung, str]] = []
        uebersprungen: list[tuple[Bewegung, str]] = []
        bestaende: dict[tuple[str, str], list[dict]] = {}
        for zeile in zeilen:
            if zeile.status != "bereit":
                continue
            vorgang = nach_nr.get(zeile.nr) or {}
            strang, _ = strang_fuer(vorgang, index_suche)
            if not strang:
                continue
            bewegungen, _ = bewegungen_fuer(
                vorgang, zeile.ziel or "", strang, index_suche
            )
            for b in bewegungen:
                schluessel = (b.konto, b.von_ordner)
                if schluessel not in bestaende:
                    bestaende[schluessel] = postfach_auflisten(*schluessel)
                paare, fehlt = abgleichen([b], bestaende[schluessel])
                alle += paare
                uebersprungen += fehlt
        print()
        print(f"Anwenden — Lauf {lauf_id}")
        for b, grund in uebersprungen:
            print(f"  uebersprungen: {b.betreff[:50]} — {grund}")
        bewegt = anwenden(alle, lauf_id)
        print(f"OK: {bewegt} Nachricht(en) bewegt, {len(uebersprungen)} uebersprungen.")
        print(f"Ruecknahme: --ruecknahme {lauf_id}")
    sys.exit(0)


if __name__ == "__main__":
    main()
