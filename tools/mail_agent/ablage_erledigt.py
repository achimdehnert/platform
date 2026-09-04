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

Was am 2026-09-04 dazukam (platform#2799), weil der Trockenlauf zwar lief, aber
seit dem 2026-08-27 keine einzige Mail ablegte:

* **Der Ordnerbestand wird geholt, nicht erwartet.** ``--ordner`` war ein
  Pflichtargument, das der dokumentierte Aufruf nicht mitgab — Ergebnis: jedes
  Ziel galt als fehlend. Jetzt fragt das Werkzeug Graph bzw. IMAP selbst; ein
  Konto, das nicht antwortet, wird als ``konto_nicht_erreichbar`` gemeldet und
  nicht als fehlender Ordner.
* **Der Strang kommt aus der Konversation**, nicht aus dem Betreff: die
  Message-ID des Ankers, dann ``References``/``In-Reply-To`` (IMAP) bzw.
  ``conversationId`` (Graph). Der Betreff bleibt der zweite Weg.
* **Referenzen ueberleben den Umzug.** ``--apply`` verankert die Verlaufs-
  Referenzen der betroffenen Vorgaenge vorher und zieht die Anker nachher nach.
  Laesst sich eine Referenz nicht verankern, die im Quellordner liegen koennte,
  bricht der Lauf ab.
* **Beide Seiten werden gezaehlt** (Quelle und Ziel, vorher und nachher). Weicht
  der Bestand von der Erfolgsmeldung ab, ist das eine Warnung und Exit 3.
* **``--pruefe`` ist der Melder:** wie viele Posteingangs-Mails gehoeren noch zu
  geschlossenen Vorgaengen. 0 = gruen; laeuft in ``make boards``.

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
import imaplib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

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

#: Ein Konto, dessen Ordnerbestand sich nicht holen liess.
#:
#: Das ist eine Aussage ueber die VERBINDUNG, nicht ueber das Postfach. Bis zum
#: 2026-09-04 gab es diesen Status nicht: ein nicht erreichbares Konto fiel als
#: ``ordner_fehlt`` an — dieselbe Meldung, die auch ein wirklich fehlender Ordner
#: erzeugt. Genau daran haben sich am 2026-08-27 und am 2026-08-31 zwei Laeufe
#: verschluckt (Memory `feedback_folder_list_is_a_required_argument_not_a_comfort`).
KONTO_NICHT_ERREICHBAR = "konto_nicht_erreichbar"

#: Woran die Zeile haengt, wenn sie nicht ``bereit`` ist. Reihenfolge = Dringlichkeit.
STATUS_REIHENFOLGE = (
    "bereit",
    "ordner_fehlt",
    KONTO_NICHT_ERREICHBAR,
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
    nicht_erreichbar: dict[str, str] | None = None,
) -> list[Zeile]:
    """Fuer jeden geschlossenen Vorgang eine Zeile mit Ziel und Status.

    ``anker`` haelt IMAP-Anker, ``links`` Graph-Kurz-IDs — beide ueber die
    Board-Nummer verschluesselt. Ein Posten gilt als gebunden, wenn EINER von
    beiden ihn kennt; ``board.anker_zustand()`` entscheidet genauso. Nur den
    IMAP-Anker zu pruefen haette jeden Graph-Vorgang faelschlich als ungebunden
    gemeldet.

    ``nicht_erreichbar`` ist Konto → Grund. Steht ein Konto darin, ist ueber
    seine Ordner NICHTS bekannt — dann wird das auch so gesagt, statt jede Zeile
    als ``ordner_fehlt`` auszuweisen und damit eine Aussage ueber das Postfach
    vorzutaeuschen, die niemand geprueft hat.
    """
    links = links or {}
    zuordnung = zuordnung or {}
    nicht_erreichbar = nicht_erreichbar or {}
    zeilen: list[Zeile] = []
    for vorgang in ledger.get("vorgaenge") or []:
        if vorgang.get("bucket") != "erledigt":
            continue
        konto = (vorgang.get("konto") or "").lower()
        bestand = ordner_je_konto.get(konto, [])
        ziel, herkunft = ziel_fuer(vorgang, bestand, zuordnung)

        if konto in nicht_erreichbar:
            status = KONTO_NICHT_ERREICHBAR
        elif not vorgang.get("erledigt_am"):
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


def bericht(zeilen: list[Zeile], nicht_erreichbar: dict[str, str] | None = None) -> str:
    """Trockenlauf als Text — Zusammenfassung zuerst, dann die Zeilen."""
    nicht_erreichbar = nicht_erreichbar or {}
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
    for konto, grund in sorted(nicht_erreichbar.items()):
        aus.append(
            f"Konto '{konto}' nicht erreichbar: {grund} — ueber seine Ordner sagt "
            "dieser Lauf nichts."
        )
    return "\n".join(aus)


# --- Ordnerbestand live ------------------------------------------------------
#
# Ohne diesen Abschnitt war die Ordnerliste ein PFLICHTARGUMENT, das der
# dokumentierte Aufruf nicht mitgab: `ordner_je_konto` blieb leer, `ziel not in
# bestand` war fuer alles wahr, und der Lauf meldete jeden Zielordner als
# fehlend. Zweimal (2026-08-27, 2026-08-31) wurde daraus ein Befund ueber das
# Postfach gemacht und dem Owner vorgelegt; beide Ordner existierten. Seit dem
# 2026-09-04 holt sich das Werkzeug den Bestand selbst — `--ordner` bleibt als
# Uebersteuerung erhalten (Testfixtures, Offline-Trockenlauf).


class KontoNichtErreichbar(RuntimeError):
    """Der Ordnerbestand eines Kontos liess sich nicht holen."""


def graph_ordner() -> list[str]:
    """Ordnerpfade des Graph-Kontos ('IIL.Kunden/Talmuehle') — derselbe Weg wie --list-folders."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import graph_mail  # noqa: PLC0415

    cfg = graph_mail.load_cfg()
    konten = cfg.get("accounts") or []
    if not konten:
        raise KontoNichtErreichbar("kein Graph-Konto konfiguriert")
    tok = graph_mail.token(cfg, konten[0])
    if not tok:
        raise KontoNichtErreichbar(f"{konten[0]} nicht fuer Mail angemeldet")
    return [f["path"] for f in graph_mail._folders(tok)]


def imap_ordner(konto: str) -> list[str]:
    """Ordnernamen eines IMAP-Kontos ueber LIST — derselbe Weg wie --list-folders."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import organize_mail  # noqa: PLC0415
    from read_mail import ordner_klartext  # noqa: PLC0415

    pfad = None if konto == "default" else Path.home() / ".claude" / f"mail-{konto}.env"
    imap, _ = organize_mail.connect(pfad)
    try:
        return [ordner_klartext(n) for n in organize_mail.list_folders(imap)]
    finally:
        try:
            imap.logout()
        except (OSError, imaplib.IMAP4.error):
            pass


def ordner_live(konto: str) -> list[str]:
    """Ordnerbestand eines Kontos — Graph fuer iil, IMAP fuer den Rest."""
    return graph_ordner() if konto == "iil" else imap_ordner(konto)


def ordner_je_konto_live(
    konten: list[str], hole=None
) -> tuple[dict[str, list[str]], dict[str, str]]:
    """(Bestand je Konto, Grund je nicht erreichbarem Konto).

    ``hole`` wird hereingereicht, damit dieser Pfad ohne Postfach pruefbar ist.

    ``SystemExit`` wird mitgefangen: ``organize_mail.connect`` und
    ``load_credentials`` beenden bei fehlender Konfiguration den PROZESS statt zu
    werfen (dieselbe Wurzel wie platform#2752). Auf dieser Maschine ist das der
    Normalfall fuer das ad-Konto — es ist nicht freigegeben, und genau das soll
    hier stehen und nicht "Ordner fehlt".
    """
    hole = hole or ordner_live
    bestand: dict[str, list[str]] = {}
    fehlt: dict[str, str] = {}
    for konto in konten:
        try:
            bestand[konto] = hole(konto)
        except (
            KontoNichtErreichbar,
            AblageFehler,
            OSError,
            imaplib.IMAP4.error,
            KeyError,
            ValueError,
            SystemExit,
        ) as fehler:
            fehlt[konto] = str(fehler)[:160] or type(fehler).__name__
    return bestand, fehlt


def konten_der_vorgaenge(ledger: dict) -> list[str]:
    """Konten, in denen ueberhaupt ein geschlossener Vorgang liegt — sortiert."""
    return sorted(
        {
            (v.get("konto") or "").lower()
            for v in ledger.get("vorgaenge") or []
            if v.get("bucket") == "erledigt" and v.get("konto")
        }
    )


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


# --- Strang ueber die Konversation -------------------------------------------
#
# Der Betreff ist die SCHWAECHSTE Art, einen Strang zu bestimmen: er kollidiert
# (zwei Gespraeche, ein Betreff), er wandert (jemand aendert ihn beim Antworten),
# und der Index sucht ihn im Volltext mit. Gemessen am 2026-09-04: von 27 bereiten
# Vorgaengen kamen 7 als "Volltexttreffer, aber kein gleicher Betreff" zurueck und
# 2 als "im Index nicht gefunden".
#
# Der Anker eines Vorgangs traegt dagegen die Message-ID — genau die Kennung, an
# der die Mailprogramme selbst ihre Straenge bilden. Ueber sie fragen wir das
# Postfach direkt: IMAP nach `References`/`In-Reply-To`/`Message-ID`, Graph ueber
# `conversationId`. Erst wenn das nichts liefert, greift der Betreff wie bisher.
#
# **Warum nicht ueber den Index:** Der Index fuehrt (gemessen 2026-09-04 an einer
# echten Antwort) je Treffer `id, datum, von, betreff, strang, ordner, anhaenge` —
# keine `References`, keine `conversationId`, keine Message-ID; `suche.py` reicht
# auch kein Kriterium dafuer durch. Die Konversation ist dort also nicht zu haben,
# und der Live-Weg ist nicht Bequemlichkeit, sondern der einzige.

KONVERSATION = "konversation"
BETREFF = "betreff"

#: Felder, die Graph fuer eine Strang-Nachricht liefern muss.
GRAPH_FELDER = "id,subject,receivedDateTime,parentFolderId,conversationId"


@dataclass
class Strang:
    """Der Strang eines Vorgangs — und woher wir wissen, dass es dieser ist."""

    kennung: str | None
    quelle: str
    grund: str = ""
    #: Bei ``quelle == KONVERSATION`` bereits aufgeloest; der Index kennt diesen
    #: Strang nicht und koennte ihn auch nicht nachschlagen.
    nachrichten: list[dict] | None = None

    def __bool__(self) -> bool:
        return bool(self.kennung)


def anker_message_id(vorgang: dict, anker: dict, links: dict) -> str:
    """Die Message-ID, an der der Vorgang haengt — IMAP-Anker oder Graph-Registry.

    Beide Speicher fuehren denselben RFC-Header unter verschiedenem Namen
    (``message_id`` bzw. ``internet_message_id``); welcher gefuellt ist, haengt am
    Konto. Ohne ihn gibt es keine Konversation, nur den Betreff.
    """
    nr = str(vorgang.get("nr"))
    imap = (anker.get(nr) or {}).get("message_id") or ""
    graph = (links.get(nr) or {}).get("internet_message_id") or ""
    return str(imap or graph).strip()


def strang_aufloesen(
    vorgang: dict,
    suche,
    konversation=None,
    anker: dict | None = None,
    links: dict | None = None,
) -> Strang:
    """Strang zuerst ueber die Konversation, erst dann ueber den Betreff.

    ``konversation`` hat die Signatur ``(konto, message_id) -> list[dict]`` und
    wird hereingereicht, damit dieser Pfad ohne Postfach pruefbar bleibt. Fehlt
    sie oder liefert sie nichts, bleibt es beim bisherigen Betreff-Weg — die
    Reihenfolge ist eine Verbesserung, keine Ersetzung.
    """
    mid = anker_message_id(vorgang, anker or {}, links or {})
    hinweis = ""
    if mid and konversation is not None:
        try:
            nachrichten = konversation((vorgang.get("konto") or "").lower(), mid)
        except (
            KontoNichtErreichbar,
            AblageFehler,
            OSError,
            imaplib.IMAP4.error,
            KeyError,
            ValueError,
            SystemExit,
        ) as fehler:
            nachrichten, hinweis = [], f"Konversation nicht abfragbar: {fehler}"
        if nachrichten:
            return Strang(
                mid,
                KONVERSATION,
                f"{len(nachrichten)} Nachricht(en) ueber die Konversation",
                nachrichten,
            )
        if not hinweis:
            hinweis = "Konversation leer"
    kennung, grund = strang_fuer(vorgang, suche)
    if hinweis:
        grund = f"{hinweis}; {grund}"
    return Strang(kennung, BETREFF if kennung else "", grund)


def nachrichten_des_strangs(strang, suche) -> list[dict]:
    """Die Nachrichten eines Strangs — live aufgeloest oder aus dem Index."""
    if isinstance(strang, Strang):
        if strang.quelle == KONVERSATION:
            return list(strang.nachrichten or [])
        return suche(strang=strang.kennung) if strang.kennung else []
    return suche(strang=strang)


def _uids_der_konversation(imap, message_id: str) -> list[str]:
    """UIDs im GERADE selektierten Ordner, die zu dieser Message-ID gehoeren.

    Drei Kopfzeilen, weil ein Strang drei Rollen kennt: die Nachricht selbst
    (``Message-ID``), ihre direkte Antwort (``In-Reply-To``) und alles, was
    weiter unten im Strang haengt (``References``).
    """
    gefunden: list[str] = []
    for kopf in ("References", "In-Reply-To", "Message-ID"):
        try:
            typ, daten = imap.uid("SEARCH", None, "HEADER", kopf, message_id)
        except (imaplib.IMAP4.error, OSError):
            continue
        if typ == "OK" and daten and daten[0]:
            gefunden += [u.decode() for u in daten[0].split()]
    return sorted(set(gefunden), key=lambda u: int(u) if u.isdigit() else 0)


def _imap_verbinde(konto: str):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from read_mail import _resolve_config, connect  # noqa: PLC0415
    from send_mail import parse_env  # noqa: PLC0415

    return connect(
        parse_env(_resolve_config(None, None if konto == "default" else konto))
    )


def imap_konversation(
    konto: str,
    message_id: str,
    nur_ordner: tuple[str, ...] | None = None,
    imap=None,
    verbinde=None,
) -> list[dict]:
    """Die Konversation im IMAP-Postfach — strikt lesend (``readonly=True``, kein FETCH-Rumpf).

    ``nur_ordner`` verengt die Suche auf die Quellordner. Der Melder (``--pruefe``)
    fragt nur, was im Posteingang liegt, und braucht dafuer nicht alle vierzehn
    Suchordner — das ist der Unterschied zwischen drei und zweiundvierzig
    Rundreisen je Vorgang.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from anker import betreff_von_uid, datum_von_uid  # noqa: PLC0415
    from mail_view import slugify  # noqa: PLC0415
    from read_mail import (  # noqa: PLC0415
        _mailbox_arg,
        alle_ordner,
        ordner_klartext,
    )
    from referenzen import SUCHORDNER  # noqa: PLC0415

    eigene = imap is None
    imap = imap or (verbinde or _imap_verbinde)(konto)
    try:
        namen, _ = alle_ordner(imap)
        if nur_ordner:
            gesucht = {o.lower() for o in nur_ordner}
            kandidaten = [n for n in namen if ordner_klartext(n).lower() in gesucht]
        else:
            nach_slug: dict[str, str] = {}
            for name in namen:
                nach_slug.setdefault(slugify(ordner_klartext(name)), name)
            kandidaten = [nach_slug[s] for s in SUCHORDNER if s in nach_slug]
        aus: list[dict] = []
        for name in kandidaten:
            try:
                typ, _ = imap.select(_mailbox_arg(name), readonly=True)
            except (imaplib.IMAP4.error, OSError):
                continue
            if typ != "OK":
                continue
            for uid in _uids_der_konversation(imap, message_id):
                aus.append(
                    {
                        "kennung": uid,
                        "betreff": betreff_von_uid(imap, uid),
                        "datum": datum_von_uid(imap, uid),
                        "ordner": [ordner_klartext(name)],
                        "strang": message_id,
                    }
                )
        return aus
    finally:
        if eigene:
            try:
                imap.logout()
            except (OSError, imaplib.IMAP4.error):
                pass


def graph_nachrichten_aus_antwort(
    werte: list[dict], ordner_nach_id: dict[str, str]
) -> list[dict]:
    """Graph-Nachrichten in dieselbe Form bringen, die der Index liefert."""
    return [
        {
            "kennung": m.get("id") or "",
            "betreff": m.get("subject") or "",
            "datum": str(m.get("receivedDateTime") or "")[:10],
            "ordner": [ordner_nach_id.get(m.get("parentFolderId") or "", "")],
            "strang": m.get("conversationId") or "",
        }
        for m in werte
    ]


def _graph_token() -> str:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import graph_mail  # noqa: PLC0415

    cfg = graph_mail.load_cfg()
    konten = cfg.get("accounts") or []
    if not konten:
        raise KontoNichtErreichbar("kein Graph-Konto konfiguriert")
    tok = graph_mail.token(cfg, konten[0])
    if not tok:
        raise KontoNichtErreichbar(f"{konten[0]} nicht fuer Mail angemeldet")
    return tok


def graph_ordnerkarte(tok: str) -> dict[str, str]:
    """Graph-Ordner-ID → Pfad; nur so traegt eine Nachricht ihren Ordnernamen."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import graph_mail  # noqa: PLC0415

    return {f["id"]: f["path"] for f in graph_mail._folders(tok)}


def graph_konversation(
    message_id: str,
    tok: str | None = None,
    http=None,
    ordnerkarte: dict[str, str] | None = None,
) -> list[dict]:
    """Die Konversation im Graph-Postfach: internetMessageId → conversationId → Strang."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import graph_anker  # noqa: PLC0415
    import graph_mail  # noqa: PLC0415

    http = http or graph_anker._http_standard
    tok = tok or _graph_token()
    karte = ordnerkarte if ordnerkarte is not None else {}

    def _liste(feld: str, wert: str) -> list[dict]:
        # Das einfache Anfuehrungszeichen wird in OData verdoppelt, nicht escaped —
        # dieselbe Regel, die `graph_anker.finde_per_internet_id` anwendet.
        roh = quote("'" + str(wert).replace("'", "''") + "'", safe="")
        antwort = http(
            "GET",
            f"{graph_mail.GRAPH}/me/messages?$filter={feld} eq {roh}"
            f"&$select={GRAPH_FELDER}&$top=100",
            headers=graph_mail._auth(tok),
        )
        if antwort.status_code != 200:
            raise KontoNichtErreichbar(f"Graph antwortet {antwort.status_code}")
        return antwort.json().get("value") or []

    treffer = _liste("internetMessageId", message_id)
    if not treffer:
        return []
    conv = treffer[0].get("conversationId")
    werte = _liste("conversationId", conv) if conv else treffer
    return graph_nachrichten_aus_antwort(werte, karte)


class Konversationen:
    """Live-Aufloeser ``(konto, message_id) -> Nachrichten`` mit EINER Verbindung je Konto.

    Ohne die Wiederverwendung kostete jeder Vorgang eine eigene IMAP-Anmeldung —
    bei dreissig geschlossenen Vorgaengen dreissig Logins fuer dieselbe Frage.
    """

    def __init__(self, nur_quellordner: bool = False) -> None:
        self.nur_quellordner = nur_quellordner
        self._imap: dict[str, object] = {}
        self._tok: str | None = None
        self._karte: dict[str, str] | None = None

    def __call__(self, konto: str, message_id: str) -> list[dict]:
        if konto == "iil":
            if self._tok is None:
                self._tok = _graph_token()
                self._karte = graph_ordnerkarte(self._tok)
            nachrichten = graph_konversation(
                message_id, self._tok, ordnerkarte=self._karte
            )
        else:
            if konto not in self._imap:
                self._imap[konto] = _imap_verbinde(konto)
            nachrichten = imap_konversation(
                konto,
                message_id,
                nur_ordner=QUELLORDNER_JE_KONTO.get(konto)
                if self.nur_quellordner
                else None,
                imap=self._imap[konto],
            )
        if not self.nur_quellordner:
            return nachrichten
        quellen = QUELLORDNER_JE_KONTO.get(konto, QUELLORDNER_JE_KONTO["default"])
        return [n for n in nachrichten if (n.get("ordner") or [""])[0] in quellen]

    def __enter__(self) -> Konversationen:
        return self

    def __exit__(self, *_) -> None:
        for imap in self._imap.values():
            try:
                imap.logout()
            except (OSError, imaplib.IMAP4.error):
                pass
        self._imap.clear()


def bewegungen_fuer(
    vorgang: dict, ziel: str, strang, suche
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
    for nachricht in nachrichten_des_strangs(strang, suche):
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


def strang_bericht(
    zeilen: list[Zeile],
    ledger: dict,
    suche,
    konversation=None,
    anker: dict | None = None,
    links: dict | None = None,
) -> str:
    """Welche Nachrichten je bereitem Vorgang bewegt wuerden — immer noch trocken."""
    nach_nr = {v.get("nr"): v for v in ledger.get("vorgaenge") or []}
    aus = ["Betroffene Nachrichten (Trockenlauf)", ""]
    gesamt = 0
    quellen: dict[str, int] = {}
    for zeile in zeilen:
        if zeile.status != "bereit":
            continue
        vorgang = nach_nr.get(zeile.nr) or {}
        strang = strang_aufloesen(vorgang, suche, konversation, anker, links)
        if not strang:
            aus.append(f"{str(zeile.nr):>4}  — kein Strang: {strang.grund}")
            continue
        quellen[strang.quelle] = quellen.get(strang.quelle, 0) + 1
        bewegungen, liegen = bewegungen_fuer(vorgang, zeile.ziel or "", strang, suche)
        gesamt += len(bewegungen)
        rest = ", ".join(f"{n}x {o}" for o, n in sorted(liegen.items())) or "nichts"
        aus.append(
            f"{str(zeile.nr):>4}  [{strang.quelle}]  {len(bewegungen)} aus dem "
            f"Posteingang · bleibt liegen: {rest}"
        )
        for b in bewegungen:
            aus.append("      " + b.als_zeile())
    herkunft = ", ".join(f"{n}x {q}" for q, n in sorted(quellen.items())) or "keine"
    aus += [
        "",
        f"Summe: {gesamt} Nachrichten wuerden bewegt. Es wurde nichts bewegt.",
        f"Strang-Quellen: {herkunft}.",
        "Was ueber den Betreff kam, stammt aus dem Index — ein Schnappschuss von",
        "03:30; was danach umsortiert wurde, steht dort mit dem alten Ordner.",
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


# --- Referenzen ueberleben den Umzug (K3) ------------------------------------
#
# Ein Verlaufseintrag verweist auf "INBOX #164024". Diese Nummer gilt NUR in
# INBOX; verschiebt dieser Lauf die Mail, zeigt der Link ins Leere — und zwar
# unwiederbringlich, denn eine tote UID hat keine Message-ID mehr, die man
# nachtraeglich lesen koennte (`eintrag_anker`, Abschnitt "Nachtraeglich
# heilen"). Deshalb verankert der scharfe Lauf VORHER und zieht NACHHER nach.

#: Zustaende, bei denen der scharfe Lauf abbricht statt eine lebende UID zu toeten.
#:
#: ``nicht-gefunden`` gehoert absichtlich nicht dazu (Entscheidung, keine Restarbeit;
#: #2799 K3): die UID lag in keinem Suchordner, also auch nicht im Quellordner —
#: sie ist schon tot, und dieser Lauf ist nicht ihre Ursache. ``mehrdeutig`` (UID in
#: zwei Ordnern) und ``unpruefbar`` (Konto nicht erreichbar) heissen dagegen: wir
#: WISSEN nicht, ob sie im Quellordner liegt. Nichts raten — abbrechen.
BLOCKIERENDE_ZUSTAENDE = ("mehrdeutig", "unpruefbar")


def verankerung_blockiert(ergebnisse) -> list[str]:
    """Meldungen zu Referenzen, die der Lauf entwerten koennte, ohne verankert zu sein."""
    return [
        f"#{e.fund.nr}-{e.fund.eintrag} {e.fund.schluessel}: {e.zustand} — {e.hinweis}"
        for e in ergebnisse
        if e.zustand in BLOCKIERENDE_ZUSTAENDE
    ]


def anker_auswahl(nummern, funde: dict, anker: dict) -> dict:
    """Nur die Anker der genannten Vorgaenge — Vorgangs-Anker UND Verlaufs-Referenzen.

    Der Nachzug nach dem Umzug betrifft genau die bewegten Vorgaenge. Alle Anker
    zu pruefen waere ein zweiter, langsamer `anker.py --pruefe` an der falschen
    Stelle und wuerde fremde Befunde diesem Lauf zuschreiben.
    """
    erlaubt = {str(n) for n in nummern} | {
        k for k, f in funde.items() if f.nr in set(nummern)
    }
    return {k: a for k, a in anker.items() if k in erlaubt}


def nachzug_bilanz(befunde) -> tuple[int, int]:
    """(nachgezogen, tot) aus IMAP- oder Graph-Befunden — beide nennen ihren Zustand."""
    nachgezogen = sum(
        1 for b in befunde if b.zustand in ("verschoben", "nachgezogen", "neu-gesucht")
    )
    tot = sum(1 for b in befunde if b.zustand in ("geloescht", "tot"))
    return nachgezogen, tot


def referenzen_verankern(
    nummern, ledger: dict, ankerdatei: Path | None = None, verbinde=None
) -> tuple[int, list]:
    """Verlaufs-Referenzen der genannten Vorgaenge verankern → (neu, Ergebnisse)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import eintrag_anker  # noqa: PLC0415
    from anker import ANKER_DATEI, lade, speichere  # noqa: PLC0415

    pfad = ankerdatei or ANKER_DATEI
    anker = lade(pfad)
    archiv = _lade(Path.home() / ".claude" / "mail-vorgaenge-archiv.json", {})
    funde = eintrag_anker.referenzen_im_ledger(ledger, archiv)
    meine = {k: f for k, f in funde.items() if f.nr in set(nummern)}
    ergebnisse = eintrag_anker.verankere_alle(meine, anker, verbinde)
    if neu := eintrag_anker.uebernehme(ergebnisse, anker):
        speichere(anker, pfad)
    return neu, ergebnisse


def anker_nachziehen(
    nummern, ledger: dict, konten, ankerdatei: Path | None = None, verbinde=None
) -> tuple[int, int]:
    """Anker der bewegten Vorgaenge nachziehen → (nachgezogen, tot).

    IMAP ueber ``anker.pruefe_anker`` (Message-ID in einem anderen Ordner
    wiederfinden), Graph ueber ``graph_anker.heile`` (internetMessageId). Beide
    Wege gibt es bereits; hier werden sie nur auf die bewegten Vorgaenge verengt.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import anker as anker_modul  # noqa: PLC0415
    import eintrag_anker  # noqa: PLC0415

    pfad = ankerdatei or anker_modul.ANKER_DATEI
    archiv = _lade(Path.home() / ".claude" / "mail-vorgaenge-archiv.json", {})
    alle = anker_modul.lade(pfad)
    auswahl = anker_auswahl(
        nummern, eintrag_anker.referenzen_im_ledger(ledger, archiv), alle
    )
    nach_konto: dict[str, list] = {}
    for a in auswahl.values():
        nach_konto.setdefault(a.konto, []).append(a)

    befunde = []
    for konto, liste in sorted(nach_konto.items()):
        try:
            imap = (verbinde or anker_modul._verbinde)(konto)
        except (
            OSError,
            imaplib.IMAP4.error,
            KeyError,
            ValueError,
            SystemExit,
        ) as fehler:
            print(f"  Nachzug '{konto}' uebersprungen: {fehler}", file=sys.stderr)
            continue
        try:
            befunde += [anker_modul.pruefe_anker(imap, a) for a in liste]
        finally:
            try:
                imap.logout()
            except (OSError, imaplib.IMAP4.error):
                pass
    if befunde:
        anker_modul.speichere(anker_modul.uebernehme(befunde, alle), pfad)

    if "iil" in set(konten):
        befunde += _graph_nachziehen(nummern, ledger)
    return nachzug_bilanz(befunde)


def _graph_nachziehen(nummern, ledger: dict) -> list:
    """Graph-Kurzlinks der bewegten Vorgaenge heilen — die Graph-Haelfte von `anker_nachziehen`."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import graph_anker  # noqa: PLC0415

    registry = _lade(LINKS, {})
    auswahl = {k: v for k, v in registry.items() if k in {str(n) for n in nummern}}
    if not auswahl:
        return []
    try:
        tok = _graph_token()
    except (KontoNichtErreichbar, SystemExit) as fehler:
        print(f"  Graph-Nachzug uebersprungen: {fehler}", file=sys.stderr)
        return []
    befunde = graph_anker.heile(
        auswahl,
        graph_anker.betreffe_aus_ledger(ledger),
        tok,
        fenster=graph_anker.fenster_aus_ledger(ledger),
    )
    registry.update(auswahl)
    LINKS.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return befunde


# --- Beide Seiten zaehlen (K4) -----------------------------------------------
#
# Realfall 2026-08-18: 89 Mails wurden kopiert statt verschoben, das Werkzeug
# meldete `OK`. Die Erfolgszeile eines Werkzeugs ist eine Absichtserklaerung;
# Beweis ist der Bestand vorher und nachher — auf BEIDEN Seiten.


def erwartete_deltas(paare) -> dict[tuple[str, str], int]:
    """(Konto, Ordner) → erwartete Bestandsaenderung; Quelle minus, Ziel plus."""
    deltas: dict[tuple[str, str], int] = {}
    for b, _ in paare:
        deltas[(b.konto, b.von_ordner)] = deltas.get((b.konto, b.von_ordner), 0) - 1
        deltas[(b.konto, b.nach_ordner)] = deltas.get((b.konto, b.nach_ordner), 0) + 1
    return deltas


def zaehle(schluessel, auflisten=None) -> dict[tuple[str, str], int]:
    """Bestand je (Konto, Ordner) — eine Live-Abfrage, kein Index."""
    hole = auflisten or postfach_auflisten
    stand: dict[tuple[str, str], int] = {}
    for konto, ordner in sorted(schluessel):
        try:
            stand[(konto, ordner)] = len(hole(konto, ordner))
        except (AblageFehler, OSError, ValueError, json.JSONDecodeError) as fehler:
            print(
                f"  Zaehlung {konto}/{ordner} fehlgeschlagen: {fehler}", file=sys.stderr
            )
    return stand


def zaehl_bericht(
    vorher: dict, nachher: dict, deltas: dict
) -> tuple[list[str], list[str]]:
    """(Zeilen je Konto, Abweichungen). Eine Abweichung ist ein Befund, kein Rundungsfehler."""
    je_konto: dict[str, list[str]] = {}
    abweichungen: list[str] = []
    for (konto, ordner), delta in sorted(deltas.items()):
        v, n = vorher.get((konto, ordner)), nachher.get((konto, ordner))
        rolle = "Quelle" if delta < 0 else "Ziel"
        if v is None or n is None:
            abweichungen.append(
                f"{konto} {ordner}: nicht zaehlbar (vorher/nachher fehlt)"
            )
            continue
        je_konto.setdefault(konto, []).append(f"{rolle} {ordner}: {v} → {n}")
        if n != v + delta:
            abweichungen.append(
                f"{konto} {ordner}: erwartet {v + delta}, gezaehlt {n} "
                f"(Differenz {n - (v + delta):+d})"
            )
    zeilen = [
        f"{konto}  " + " · ".join(teile) for konto, teile in sorted(je_konto.items())
    ]
    return zeilen, abweichungen


# --- Melder (K5) --------------------------------------------------------------


def pruefe_posteingang(
    ledger: dict,
    suche,
    konversation=None,
    anker: dict | None = None,
    links: dict | None = None,
) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    """Wie viele Posteingangs-Mails gehoeren zu geschlossenen Vorgaengen?

    Rueckgabe: (Anzahl je Konto, Strang-Quellen je Konto). Der Zielordner spielt
    hier keine Rolle — gefragt ist nur, ob im Posteingang noch etwas liegt, das
    laut Ledger abgeschlossen ist.
    """
    zaehler: dict[str, int] = {}
    quellen: dict[str, dict[str, int]] = {}
    for vorgang in ledger.get("vorgaenge") or []:
        if vorgang.get("bucket") != "erledigt":
            continue
        konto = (vorgang.get("konto") or "").lower() or "—"
        zaehler.setdefault(konto, 0)
        quellen.setdefault(konto, {})
        strang = strang_aufloesen(vorgang, suche, konversation, anker, links)
        if not strang:
            quellen[konto]["kein strang"] = quellen[konto].get("kein strang", 0) + 1
            continue
        quellen[konto][strang.quelle] = quellen[konto].get(strang.quelle, 0) + 1
        bewegungen, _ = bewegungen_fuer(vorgang, "", strang, suche)
        zaehler[konto] += len(bewegungen)
    return zaehler, quellen


def pruefe_bericht(zaehler: dict[str, int], quellen: dict[str, dict[str, int]]) -> str:
    zeilen = []
    for konto, n in sorted(zaehler.items()):
        herkunft = ", ".join(
            f"{a}x {q}" for q, a in sorted(quellen.get(konto, {}).items())
        )
        zeilen.append(
            f"{konto}: {n} Posteingangs-Mails gehoeren zu geschlossenen Vorgaengen"
            + (f"  ({herkunft})" if herkunft else "")
        )
    zeilen.append(
        "Grundlage: Strang ueber die Konversation live, der Rest ueber den "
        "Index-Schnappschuss von 03:30."
    )
    return "\n".join(zeilen)


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
        help="Ordnerliste je Konto uebersteuern (eine Zeile je Ordner); ohne diese "
        "Angabe holt das Werkzeug den Bestand selbst aus dem Postfach",
    )
    p.add_argument(
        "--pruefe",
        action="store_true",
        help="Melder: wie viele Posteingangs-Mails gehoeren zu geschlossenen "
        "Vorgaengen (Exit 0 bei 0, sonst 1)",
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

    ledger = _lade(args.ledger, {})
    anker_daten = _lade(ANKER, {})
    links_daten = _lade(LINKS, {})

    if args.pruefe:
        # Der Melder braucht keine Ordnerliste: gefragt ist nur, ob im Posteingang
        # noch etwas liegt, nicht wohin es gehoerte. Deshalb auch nur die
        # Quellordner in der Konversationssuche — drei Rundreisen statt
        # zweiundvierzig je Vorgang, damit `make boards` das taeglich aushaelt.
        with Konversationen(nur_quellordner=True) as konversation:
            zaehler, quellen = pruefe_posteingang(
                ledger, index_suche, konversation, anker_daten, links_daten
            )
        print(pruefe_bericht(zaehler, quellen))
        sys.exit(1 if sum(zaehler.values()) else 0)

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

    # Was nicht uebersteuert wurde, wird geholt — nicht als leere Liste behandelt.
    fehlende_konten = [
        k for k in konten_der_vorgaenge(ledger) if k not in ordner_je_konto
    ]
    live, nicht_erreichbar = ordner_je_konto_live(fehlende_konten)
    ordner_je_konto.update(live)

    zeilen = plane(
        ledger,
        anker_daten,
        ordner_je_konto,
        _lade(ZIELE, {}),
        links_daten,
        nicht_erreichbar,
    )
    if args.json:
        print(json.dumps([z.__dict__ for z in zeilen], ensure_ascii=False, indent=2))
    else:
        print(bericht(zeilen, nicht_erreichbar))

    if args.apply and not args.straenge:
        raise SystemExit(
            "FEHLER: --apply setzt --straenge voraus — ohne aufgeloeste Straenge "
            "gibt es nichts zu verschieben."
        )

    if not (args.straenge or args.apply):
        sys.exit(0)

    with Konversationen() as konversation:
        if args.straenge:
            print()
            print(
                strang_bericht(
                    zeilen, ledger, index_suche, konversation, anker_daten, links_daten
                )
            )

        if not args.apply:
            sys.exit(0)

        nach_nr = {v.get("nr"): v for v in ledger.get("vorgaenge") or []}
        lauf_id = f"ablage-{max((z.erledigt_am or '') for z in zeilen) or 'lauf'}-{len(zeilen)}"
        alle: list[tuple[Bewegung, str]] = []
        uebersprungen: list[tuple[Bewegung, str]] = []
        bestaende: dict[tuple[str, str], list[dict]] = {}
        betroffen: set[int] = set()
        for zeile in zeilen:
            if zeile.status != "bereit":
                continue
            vorgang = nach_nr.get(zeile.nr) or {}
            strang = strang_aufloesen(
                vorgang, index_suche, konversation, anker_daten, links_daten
            )
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
                if paare and zeile.nr is not None:
                    betroffen.add(zeile.nr)

    print()
    print(f"Anwenden — Lauf {lauf_id}")

    # K3, erste Haelfte: verankern, BEVOR der Umzug die UIDs entwertet.
    verankert, ergebnisse = referenzen_verankern(betroffen, ledger)
    if blockiert := verankerung_blockiert(ergebnisse):
        for meldung in blockiert:
            print(f"  BLOCKIERT: {meldung}")
        raise SystemExit(
            f"ABBRUCH: {len(blockiert)} Referenz(en) lassen sich nicht verankern und "
            "koennten im Quellordner liegen. Erst klaeren, dann verschieben — eine "
            "tote UID laesst sich nachtraeglich nicht mehr binden."
        )

    for b, grund in uebersprungen:
        print(f"  uebersprungen: {b.betreff[:50]} — {grund}")

    deltas = erwartete_deltas(alle)
    vorher = zaehle(deltas)
    bewegt = anwenden(alle, lauf_id)
    nachher = zaehle(deltas)

    # K3, zweite Haelfte: Anker der bewegten Vorgaenge auf den neuen Ort ziehen.
    nachgezogen, tot = anker_nachziehen(
        betroffen, ledger, {z.konto for z in zeilen if z.nr in betroffen}
    )
    print(f"OK: {bewegt} Nachricht(en) bewegt, {len(uebersprungen)} uebersprungen.")
    print(
        f"Referenzen: {verankert} verankert vorher · {nachgezogen} nachgezogen "
        f"nachher · {tot} tot"
    )
    zeilen_zaehlung, abweichungen = zaehl_bericht(vorher, nachher, deltas)
    for zeile_text in zeilen_zaehlung:
        print(zeile_text)
    print(f"Ruecknahme: --ruecknahme {lauf_id}")
    if abweichungen:
        for a in abweichungen:
            print(f"WARNUNG: {a}")
        print(
            "Die Erfolgszeile oben ist damit NICHT belegt — der Bestand sagt etwas "
            "anderes (Realfall 2026-08-18: kopiert statt verschoben)."
        )
        sys.exit(3)
    sys.exit(0)


if __name__ == "__main__":
    main()
