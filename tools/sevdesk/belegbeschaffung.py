#!/usr/bin/env python3
"""Belegbeschaffung: fehlende Lieferantenbelege aus dem Postfach holen — K9 aus platform#3102.

Warum es das gibt: Der Kostenabgleich (``kostenabgleich.py``, K7) sagt, zu
welchen Bankabgaengen ein Beleg fehlt — aber nicht, wo dieser Beleg herkommt.
Genau das ist die Handarbeit, die jeden Monat wiederkehrt: Postfach
durchsuchen, PDF speichern, Betrag/Datum/Nummer abtippen, Beleg-Entwurf
anlegen. Dieses Werkzeug macht den mechanischen Teil davon und legt alles
andere dem Owner vor, statt zu raten.

Je Abgang ohne Beleg entscheidet ein lokales **Bezugswege-Register**
(``~/.claude/sevdesk-bezugswege.json``, Vorlage
``tools/sevdesk/sevdesk-bezugswege.example.json``) ueber den Weg:

- ``intern``  — es gibt keinen Lieferantenbeleg (Lohn, Steuern, Kontofuehrung,
  Eigenuebertraege). Wird nur aufgelistet, nie beschafft.
- ``mail``    — die Rechnung liegt als PDF im IIL-Postfach. Das Werkzeug sucht
  sie (Microsoft Graph, read-only), legt sie unter ``~/.claude/sevdesk-belege/``
  ab, liest Betrag/Datum/Nummer/Empfaenger aus dem PDF und ordnet sie dem
  Abgang zu.
- ``portal``  — die Rechnung gibt es nur im Kundenportal (Owner-Zug, mit Link).

Zweite Quelle neben dem Postfach ist die **Owner-Ablage**
``~/shared/inbox/invoices/`` (``--ablage-inbox``): Rechnungen, die der Owner
von Hand aus einem Kundenportal laedt und dort einstellt, gehen denselben Weg
wie Postfach-PDFs. Der Lieferant wird ueber Dateiname, sonst ueber den
PDF-Text gegen das Register bestimmt; ohne Treffer ist das ein Owner-Zug.
Die Dateien werden nie verschoben oder geloescht — die Schleuse raeumt der
Owner selbst auf.

    python3 tools/sevdesk/belegbeschaffung.py                      # Vorschau, legt NICHTS an
    python3 tools/sevdesk/belegbeschaffung.py --tage 60            # engeres Fenster
    python3 tools/sevdesk/belegbeschaffung.py --eingabe lauf.json  # Kostenabgleich-JSON statt Live-Lauf
    python3 tools/sevdesk/belegbeschaffung.py --anlegen            # Beleg-ENTWUERFE wirklich anlegen
    python3 tools/sevdesk/belegbeschaffung.py --mandant beide      # je Beleg in den Mandanten, auf den er lautet
    python3 tools/sevdesk/belegbeschaffung.py --json               # maschinenlesbar

Vier Listen im Board:

1. **Entwuerfe angelegt / Vorschau** — PDF und Abgang passen zusammen, der
   Beleg-Entwurf ist angelegt (``--anlegen``) oder vorgemerkt.
2. **Owner-Zug** — Portal-Abruf, Beleg nicht im Postfach, anderer Mandant,
   Empfaenger unklar, kein Bezugsweg im Register, Ordner nicht gefunden.
3. **intern (kein Lieferantenbeleg)** — mit Kontovorschlag aus dem Kostenabgleich.
4. **PDF ohne Abgang** — Rechnung gefunden, aber kein passender Abgang im
   Fenster (anderes Konto, spaetere Abbuchung). Fuer den eigenen Mandanten
   wird trotzdem ein Entwurf angelegt — der Beleg ist echt. Lieferanten, die
   NIE ueber dieses Konto bezahlt werden, tragen im Register
   ``"ohne_abgang": true`` und werden auch ohne Abgang abgesucht.

Gates:

- ``status: 50`` (Entwurf) kommt aus ``beleg_entwurf.py`` und ist dort fest
  verdrahtet — **gebucht wird hier nie**, auch nicht mit ``--anlegen``.
- Ohne ``--anlegen`` laeuft alles im Trockenlauf: sevdesk wird nur gelesen,
  kein PDF hochgeladen (``beleg_entwurf.anlegen(dry_run=True)`` kehrt vor dem
  Upload zurueck).
- Ein Konto wird **nie** gesetzt (``--konto`` bleibt leer) — der Vorschlag
  steht nur im Board, bestaetigen muss ihn der Owner in sevdesk.
- ``--mandant`` entscheidet, WELCHE Belege entstehen: ``iil`` (Standard) nur
  eigene, ``edv`` nur die der zweiten Firma, ``beide`` je Beleg den, auf den
  er laut PDF lautet. ``unklar`` bleibt in jedem Fall Owner-Zug — ein Beleg
  ohne erkennbaren Empfaenger wird nie geraten. Fehlt der Zugang eines
  Mandanten, ist das eine Zeile im Board, kein Abbruch (#3112).
- Dieselbe Rechnung erreicht das Werkzeug mehrfach (Rechnungsmail,
  Zahlungsbeleg, Ablage-Datei): innerhalb eines Laufs gewinnt die erste
  Fundstelle, weitere zaehlen als ``bereits_im_lauf`` (#3118).
- Weist das PDF deutsche Umsatzsteuer aus, gilt Steuerregel 9 — auch wenn im
  Register Reverse Charge steht; die Abweichung nennt das Board (#3118).
- Das Postfach wird nur gelesen; nichts wird verschoben, markiert oder
  geloescht.
- Exit: ``0`` keine Owner-Zug-Zeile, ``2`` Owner-Zug noetig, ``3`` Zugang/API.

Bekannte Fallen:

- **Empfaenger != Postfach**: Eine Rechnung im IIL-Postfach kann an einen
  anderen Mandanten adressiert sein. Der Empfaenger wird deshalb aus dem
  PDF-Text gelesen, nie aus dem Postfach geschlossen.
- **Fremdwaehrung**: Der Abgang steht in EUR, das Receipt in USD. Eine solche
  Zuordnung ist nie "sicher", sondern "Fremdwaehrung — Kurs prueft sevdesk";
  den Stichtagskurs setzt sevdesk selbst.
- **Zahler "—"**: Bei Lastschriften ohne Namen traegt nur der Verwendungszweck
  den Lieferanten. Das Register wird deshalb gegen ``"<zahler> <zweck>"``
  geprueft, nicht nur gegen den Zahler.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bankpositionen import KONTEN_DATEI, konten_laden, kurz  # noqa: E402
from kostenabgleich import positionen_ermitteln  # noqa: E402
from mandant import client, secret_datei  # noqa: E402

VORLAGE = Path(__file__).resolve().parent / "sevdesk-bezugswege.example.json"
STANDARD_REGISTER = Path.home() / ".claude" / "sevdesk-bezugswege.json"
STANDARD_ABLAGE = Path.home() / ".claude" / "sevdesk-belege"
#: Zweite Quelle neben dem Postfach: Rechnungen, die der Owner von Hand aus
#: einem Kundenportal laedt und hier einstellt (Owner-Entscheid B 2026-08-07,
#: Schleuse ``~/shared``). Fehlt der Ordner, ist das kein Fehler — dann gibt
#: es eben nichts abzuholen.
STANDARD_ABLAGE_INBOX = Path.home() / "shared" / "inbox" / "invoices"
INDEX_DATEI = Path.home() / ".claude" / "sevdesk-belegbeschaffung-index.json"
JOURNAL_DATEI = Path.home() / ".claude" / "sevdesk-belegbeschaffung-journal.jsonl"
STANDARD_ZIEL = Path.home() / ".claude" / "boards" / "sevdesk-belegbeschaffung.md"

#: Die Bankabgaenge kommen immer vom Geschaeftskonto der IIL — auch dann,
#: wenn Belege im Mandanten der zweiten Firma angelegt werden.
ABGANG_MANDANT = "iil"

#: Welche Empfaenger je ``--mandant`` angelegt werden. "unklar" ist in keiner
#: Menge: dieser Fall bleibt ausnahmslos Owner-Zug.
MANDANTEN_ZIEL = {
    "iil": ("iil",),
    "edv": ("edv",),
    "beide": ("iil", "edv"),
}

#: Die echten sevdesk-Mandanten (ohne den Sammelwert "beide") — alles andere
#: ist als Empfaenger kein gueltiger Wert.
MANDANTEN_EINZELN = frozenset(MANDANTEN_ZIEL["beide"])

#: Steuerregel fuer ausgewiesene deutsche Umsatzsteuer. Steht im PDF eine
#: Steuer > 0, ist Reverse Charge ausgeschlossen — dann gilt sie und nicht
#: der Register-Wert (#3118).
TAXRULE_MIT_UST = "9"

#: Datumsabstand zwischen Abgang und Rechnung, in Tagen. Grosszuegig, weil
#: Abo-Abbuchungen dem Rechnungsdatum um Wochen nachlaufen koennen.
TAGE_FENSTER = 40

#: Zulaessiger Quotient EUR-Abgang / Fremdwaehrungsbetrag. 0.80-1.00 deckt die
#: ueblichen USD/EUR-Kurse samt Bankaufschlag ab, ohne beliebige Betraege zu
#: verheiraten. Ein Treffer in diesem Band ist NIE "sicher".
KURS_BAND = (0.80, 1.00)

#: Zahlungsbelege nennen teils keinen Rechnungsempfaenger, sondern nur
#: "Account billed <login>". WELCHER Mandant hinter einem Login steht, ist
#: eine Owner-Angabe und steht im Register (``logins``) — nicht im Code.
#: Ohne Zuordnung bleibt der Empfaenger "unklar" und geht an den Owner,
#: statt beim falschen Mandanten zu landen.
EIGENE_LOGINS: dict[str, str] = {}

RE_ISO_DATUM = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
RE_DMY_SLASH = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
RE_DMY_PUNKT = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
#: "May 13, 2026" / "13. Mai 2026" — Rechnungen aus dem englischen Sprachraum
#: schreiben den Monat aus (Echtprobe 2026-09-13: zwei Anbieter, 16 Belege
#: blieben ohne Datum und damit ohne Entwurf).
RE_MONAT_ZUERST = re.compile(
    r"\b([A-Za-zäöüÄÖÜ]{3,10})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b"
)
RE_TAG_ZUERST = re.compile(r"\b(\d{1,2})\.?\s+([A-Za-zäöüÄÖÜ]{3,10})\.?\s+(\d{4})\b")
MONATE = {
    "jan": 1,
    "january": 1,
    "januar": 1,
    "jaen": 1,
    "feb": 2,
    "february": 2,
    "februar": 2,
    "mar": 3,
    "march": 3,
    "mrz": 3,
    "maerz": 3,
    "märz": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "mai": 5,
    "jun": 6,
    "june": 6,
    "juni": 6,
    "jul": 7,
    "july": 7,
    "juli": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "okt": 10,
    "october": 10,
    "oktober": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "dez": 12,
    "december": 12,
    "dezember": 12,
}
RE_ZAHL = re.compile(r"\d[\d.,]*\d|\d")
RE_ACCOUNT_BILLED = re.compile(r"account billed\s+([A-Za-z0-9_.\-]+)", re.IGNORECASE)
RE_NUMMER = re.compile(
    r"(?:abrechnungsnummer|rechnungsnummer|rechnungs-nr\.?|belegnummer|"
    r"invoice number|invoice no\.?|transaction id|receipt id)\s*[:#]?\s*"
    r"([A-Za-z0-9][A-Za-z0-9_\-/]{2,})",
    re.IGNORECASE,
)
RE_VORSCHLAG_KONTO = re.compile(r"^\s*\d+\.\s*Konto\s+(\S+)", re.MULTILINE)

#: Zeilen mit diesen Woertern tragen den Bruttobetrag; der LETZTE Treffer
#: gewinnt (Rechnungen wiederholen die Summe gern im Fuss). "zu zahlender
#: betrag" kam aus der Echtprobe 2026-09-13 dazu — ein Hoster nennt seine
#: Summe so und blieb ohne dieses Wort betragslos.
SUMMEN_WOERTER = (
    "gesamtbetrag",
    "gesamtsumme",
    "rechnungsbetrag",
    "endbetrag",
    "zu zahlender betrag",
    "zahlbetrag",
    "gesamt",
    "total",
)
#: Manche Rechnungen nennen die Endsumme schlicht "Summe" — als eigenes Wort,
#: damit "Zwischensumme" NICHT trifft (Echtprobe 2026-09-13: ein Hoster listet
#: vier Zwischensummen NACH seiner Endsumme; ohne Wortgrenze gewann die
#: letzte Zwischensumme und der Beleg trug 12,49 statt 264,54 EUR).
RE_SUMME_WORT = re.compile(r"\bsumme\b")
#: Hinter der Endsumme steht eine Waehrung und sonst nichts. Ohne diese Probe
#: gewann der Fliesstext "Der Rechnungsbetrag ist ... zahlbar nicht spaeter als
#: 10 Tage nach Rechnungsdatum" und der Beleg trug 10,00 EUR (Echtprobe
#: 2026-09-13, zwei von drei Hoster-Rechnungen).
RE_SUMMEN_SCHWANZ = re.compile(
    r"^[\s.,]*(?:€|\$|eur|usd|chf)?[\s*.,;:)]*$", re.IGNORECASE
)
#: Zeilen mit diesen Woertern tragen die enthaltene Steuer. Summenzeilen sind
#: ausgenommen — "Gesamtbetrag (nach Steuern)" ist keine Steuerzeile.
STEUER_WOERTER = ("steuer", "mwst", "umsatzsteuer")
#: Kurze Steuerwoerter nur als ganzes Wort: "ust" steckt in "Industriestr."
#: und machte aus einer Hausnummer einen Steuerbetrag (Echtprobe 2026-09-13).
RE_STEUER_KURZ = re.compile(r"\b(ust|vat|tax)\b")
#: ... und diese Zeilen tragen eine STEUERNUMMER, keinen Steuerbetrag. Ohne
#: die Ausnahme gewann die Fusszeile "USt-IdNr.: DE..." als letzter Treffer
#: und machte aus einer Identifikationsnummer einen Steuerbetrag in
#: Millionenhoehe (Echtprobe 2026-09-13).
STEUER_AUSNAHMEN = (
    "idnr",
    "id-nr",
    "identifikationsnummer",
    "steuernummer",
    "vat id",
    "tax id",
    "vat number",
)
#: Zeilen mit diesen Woertern tragen das Rechnungsdatum.
DATUM_WOERTER = ("belegdatum", "rechnungsdatum", "invoice date", "datum", "date")


class Bezugsfehler(RuntimeError):
    """Zugang/Register fehlt — Abbruch mit Exit 3, nie stiller Leerlauf."""


# ── Register ───────────────────────────────────────────────────────────────


def register_laden(pfad: Path) -> list[dict]:
    """Bezugswege-Register lesen. Fehlt es, ist das ein Abbruch mit Zeiger auf
    die Vorlage — ein leeres Register saehe sonst aus wie "nichts zu tun"."""
    if not pfad.exists():
        raise Bezugsfehler(
            f"Bezugswege-Register fehlt: {pfad}\n"
            f"  Vorlage kopieren und anpassen: cp {VORLAGE} {pfad}"
        )
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    eintraege = daten.get("eintraege") if isinstance(daten, dict) else daten
    return [e for e in (eintraege or []) if e.get("muster")]


def eintrag_fuer(abgang: dict, register: list[dict]) -> dict | None:
    """Erster Register-Eintrag, dessen Muster auf "<zahler> <zweck>" passt.

    Der Verwendungszweck gehoert zwingend dazu: bei Lastschriften ohne
    geparsten Namen steht im Zahlerfeld nur "—", der Lieferant ausschliesslich
    im Zweck.
    """
    heuhaufen = f"{abgang.get('zahler', '')} {abgang.get('zweck', '')}"
    for eintrag in register:
        try:
            if re.search(eintrag["muster"], heuhaufen, re.IGNORECASE):
                return eintrag
        except re.error:
            continue
    return None


# ── PDF lesen ──────────────────────────────────────────────────────────────


def zahl_lesen(roh: str) -> float | None:
    """ "1.234,56" / "1,234.56" / "742,56" / "46.98" -> float.

    Der LETZTE Trenner ist der Dezimaltrenner, wenn beide vorkommen; ein
    einzelner Punkt vor genau drei Ziffern ist ein Tausenderpunkt.
    """
    roh = (roh or "").strip().replace(" ", "").replace(" ", "")
    if not roh:
        return None
    if "," in roh and "." in roh:
        if roh.rfind(",") > roh.rfind("."):
            roh = roh.replace(".", "").replace(",", ".")
        else:
            roh = roh.replace(",", "")
    elif "," in roh:
        ganz, _, rest = roh.rpartition(",")
        roh = f"{ganz}.{rest}" if len(rest) == 2 else roh.replace(",", "")
    elif "." in roh:
        ganz, _, rest = roh.rpartition(".")
        if len(rest) == 3 and ganz:
            roh = roh.replace(".", "")
    try:
        return round(float(roh), 2)
    except ValueError:
        return None


def _ist_summenzeile(zeile: str) -> bool:
    """Traegt diese Zeile eine Endsumme — oder nur zufaellig eine Zahl?

    Zwei Bedingungen: ein Summenwort UND hinter der letzten Zahl steht nur
    noch eine Waehrung. Die zweite Bedingung trennt die Summe vom Fliesstext,
    in dem dieselben Woerter vorkommen ("Der Rechnungsbetrag ist ... 10 Tage").
    """
    klein = zeile.lower()
    if not (any(w in klein for w in SUMMEN_WOERTER) or RE_SUMME_WORT.search(klein)):
        return False
    treffer = list(RE_ZAHL.finditer(zeile))
    if not treffer:
        return False
    return bool(RE_SUMMEN_SCHWANZ.match(zeile[treffer[-1].end() :]))


def _letzte_zahl(zeile: str) -> float | None:
    werte = [zahl_lesen(t) for t in RE_ZAHL.findall(zeile)]
    werte = [w for w in werte if w is not None]
    return werte[-1] if werte else None


def _monat_nummer(wort: str) -> int | None:
    return MONATE.get((wort or "").strip(".").lower())


def _steuer_aus_summenzeile(zeile: str | None) -> float | None:
    """Steuerbetrag aus einer Summenzeile "… netto steuer brutto".

    Nur wenn die Probe netto+steuer==brutto (1 Cent Toleranz) aufgeht — sonst
    waeren es drei beliebige Zahlen in einer Zeile.
    """
    if not zeile:
        return None
    werte = [
        z for z in (zahl_lesen(t) for t in RE_ZAHL.findall(zeile)) if z is not None
    ]
    if len(werte) < 3:
        return None
    netto, steuer, brutto = werte[-3:]
    if steuer <= 0 or abs((netto + steuer) - brutto) > 0.01:
        return None
    return steuer


def _datum_aus(zeile: str) -> str | None:
    """ISO, DD/MM/YYYY, DD.MM.YYYY, "May 13, 2026", "13. Mai 2026" — alle
    fuenf Schreibweisen real gesehen (2026-09-13)."""
    m = RE_ISO_DATUM.search(zeile)
    if m:
        return _iso_bauen(m.group(1), m.group(2), m.group(3))
    for muster in (RE_DMY_SLASH, RE_DMY_PUNKT):
        m = muster.search(zeile)
        if m:
            return _iso_bauen(m.group(3), m.group(2), m.group(1))
    m = RE_MONAT_ZUERST.search(zeile)
    if m and _monat_nummer(m.group(1)):
        return _iso_bauen(m.group(3), str(_monat_nummer(m.group(1))), m.group(2))
    m = RE_TAG_ZUERST.search(zeile)
    if m and _monat_nummer(m.group(2)):
        return _iso_bauen(m.group(3), str(_monat_nummer(m.group(2))), m.group(1))
    return None


def _iso_bauen(jahr: str, monat: str, tag: str) -> str | None:
    try:
        return dt.date(int(jahr), int(monat), int(tag)).isoformat()
    except ValueError:
        return None


def logins_zuordnung(eintrag: dict) -> dict[str, str]:
    """Login -> Mandant aus einem Register-Eintrag.

    Zwei Schreibweisen, beide gueltig: ``logins`` als Zuordnung
    (``{"<org>": "iil", "<privat>": "edv"}``) und die aeltere Liste
    ``eigene_logins``, bei der alle Logins den eigenen Mandanten meinen. Die
    Zuordnung gibt es, seit der Owner entschieden hat, dass die Belege eines
    persoenlichen Kontos in die zweite Firma gehoeren (Owner-Wort
    2026-09-13) — vorher war das ein Owner-Zug je Beleg.
    """
    roh = eintrag.get("logins")
    if isinstance(roh, dict):
        return {str(k).lower(): str(v).lower() for k, v in roh.items()}
    liste = roh if isinstance(roh, (list, tuple)) else eintrag.get("eigene_logins")
    if isinstance(liste, (list, tuple)):
        return {str(k).lower(): ABGANG_MANDANT for k in liste}
    return dict(EIGENE_LOGINS)


def empfaenger_bestimmen(text: str, logins=EIGENE_LOGINS) -> str:
    """``iil`` | ``edv`` | ``unklar`` — ausschliesslich aus dem PDF-Text.

    Die Reihenfolge ist die Lehre aus der Echtprobe (2026-09-13): eine
    Rechnung im IIL-Postfach war an den zweiten Mandanten adressiert. Wer den
    Empfaenger aus dem Postfach schliesst, legt sie beim falschen an.

    Die Pruefreihenfolge ist bewusst so und nicht anders:

    1. ``EDV Beratung`` schlaegt alles — der zweite Mandant wird nie
       stillschweigend zum eigenen.
    2. ``Account billed <login>`` gewinnt vor dem Domain-Marker. Ein
       Zahlungsbeleg sagt damit ausdruecklich, WELCHES Konto belastet wurde —
       und das Register sagt, zu welchem Mandanten dieses Konto gehoert
       (``logins``). Ein Login ohne Zuordnung bleibt ``unklar``, auch wenn
       als Rechnungsadresse eine eigene Mailadresse daneben steht: diese
       Entscheidung gehoert dem Owner, nicht dem Parser.
    3. Domain-/Namensmarker (``iil.gmbh``, ``iil-institut``, ``IIL`` als
       eigenes Wort) tragen alles uebrige — Rechnungen ohne Kontozeile, die
       nur die Rechnungsadresse nennen.
    """
    flach = " ".join((text or "").split()).lower()
    if re.search(r"edv[\s\-]?beratung", flach):
        return "edv"
    m = RE_ACCOUNT_BILLED.search(flach)
    if m:
        zuordnung = (
            logins
            if isinstance(logins, dict)
            else {str(k).lower(): ABGANG_MANDANT for k in logins}
        )
        mandant = zuordnung.get(m.group(1))
        return mandant if mandant in MANDANTEN_EINZELN else "unklar"
    if "iil.gmbh" in flach or "iil-institut" in flach:
        return "iil"
    if re.search(r"\biil\b", flach):
        return "iil"
    return "unklar"


def pdf_lesen(text: str, dateiname: str = "", logins=EIGENE_LOGINS) -> dict:
    """Rechnungsfelder aus dem PDF-Text — rein, ohne Datei- oder Netzzugriff.

    Rueckgabe: ``datum`` (ISO oder None), ``brutto``, ``steuer`` (0.00 wenn
    keine ausgewiesen), ``waehrung``, ``nummer`` (Fallback: Dateiname ohne
    Endung), ``empfaenger``, ``lieferant_hinweis`` (erste nicht-leere Zeile).
    """
    zeilen = (text or "").splitlines()
    flach = " ".join((text or "").split())

    summen_zeile, steuer_zeile = None, None
    for zeile in zeilen:
        klein = zeile.lower()
        if _ist_summenzeile(zeile) and _letzte_zahl(zeile) is not None:
            summen_zeile = zeile
            continue
        if any(w in klein for w in STEUER_AUSNAHMEN):
            continue
        ist_steuer = any(w in klein for w in STEUER_WOERTER) or RE_STEUER_KURZ.search(
            klein
        )
        if ist_steuer and _letzte_zahl(zeile) is not None:
            steuer_zeile = zeile

    brutto = _letzte_zahl(summen_zeile) if summen_zeile else None
    steuer = _letzte_zahl(steuer_zeile) if steuer_zeile else None
    # Eine Summenzeile der Form "Summe <netto> <steuer> <brutto>" traegt die
    # Steuer selbst — erkennbar an der Probe netto+steuer==brutto. Ohne sie
    # bekaeme eine deutsche Rechnung ohne eigene Steuerzeile 0,00 Steuer und
    # damit die falsche Steuerregel (Echtprobe 2026-09-13).
    aus_summenzeile = _steuer_aus_summenzeile(summen_zeile)
    if aus_summenzeile is not None:
        steuer = aus_summenzeile
    if steuer is not None and brutto is not None and steuer >= brutto:
        steuer = None  # eine Summenzeile in Steuer-Verkleidung, nicht die Steuer

    quelle = summen_zeile or flach
    if "usd" in quelle.lower() or "$" in quelle:
        waehrung = "USD"
    elif "€" in quelle or "eur" in quelle.lower():
        waehrung = "EUR"
    elif "usd" in flach.lower() or "$" in flach:
        waehrung = "USD"
    else:
        waehrung = "EUR"

    datum = None
    for zeile in zeilen:
        if any(w in zeile.lower() for w in DATUM_WOERTER):
            datum = _datum_aus(zeile)
            if datum:
                break
    if not datum:
        for zeile in zeilen:
            datum = _datum_aus(zeile)
            if datum:
                break

    m = RE_NUMMER.search(flach)
    nummer = m.group(1) if m else Path(dateiname).stem

    lieferant_hinweis = next((z.strip() for z in zeilen if z.strip()), "")
    return {
        "datum": datum,
        "brutto": brutto,
        "steuer": 0.00 if steuer is None else steuer,
        "waehrung": waehrung,
        "nummer": nummer,
        "empfaenger": empfaenger_bestimmen(text, logins),
        "lieferant_hinweis": kurz(lieferant_hinweis, 60),
    }


def pdf_text(pfad: Path) -> str:
    """PDF-Text ueber ``pdftotext -layout``; faellt auf ``pypdf`` zurueck.

    ``-layout`` haelt Spalten zusammen — ohne das rutscht der Betrag in eine
    andere Zeile als sein Beschriftungswort, und die Summenzeile ist nicht
    mehr erkennbar.
    """
    try:
        lauf = subprocess.run(  # noqa: S603 — fester Programmname, Pfad als Argument
            ["pdftotext", "-layout", str(pfad), "-"],
            capture_output=True,
            timeout=60,
            check=False,
        )
        if lauf.returncode == 0 and lauf.stdout.strip():
            return lauf.stdout.decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        import pypdf  # noqa: PLC0415 — optionaler Fallback, nicht importieren muessen
    except ImportError:
        return ""
    try:
        leser = pypdf.PdfReader(str(pfad))
        return "\n".join((seite.extract_text() or "") for seite in leser.pages)
    except (OSError, ValueError, pypdf.errors.PdfError) as exc:
        print(f"⚠ {pfad.name}: Text nicht lesbar ({exc})", file=sys.stderr)
        return ""


# ── Zuordnung PDF <-> Abgang ───────────────────────────────────────────────


def _tage_abstand(a: str | None, b: str | None) -> int | None:
    try:
        return abs((dt.date.fromisoformat(a[:10]) - dt.date.fromisoformat(b[:10])).days)
    except (TypeError, ValueError):
        return None


def zuordnen(
    abgaenge: list[dict], belege: list[dict], fenster: int = TAGE_FENSTER
) -> tuple[list[dict], list[dict], list[dict]]:
    """(paare, abgaenge_ohne_pdf, pdf_ohne_abgang) — je PDF hoechstens ein
    Abgang, je Abgang hoechstens ein PDF.

    Greedy nach kleinstem Datumsabstand; EUR-Gleichstand (<= 1 Cent) gilt als
    ``sicher``, eine Fremdwaehrung im Kursband nur als ``fremdwaehrung``.
    """
    kandidaten: list[tuple[int, int, int, int, str]] = []
    for ia, abgang in enumerate(abgaenge):
        for ib, beleg in enumerate(belege):
            abstand = _tage_abstand(abgang.get("datum"), beleg.get("datum"))
            if abstand is None or abstand > fenster:
                continue
            brutto = beleg.get("brutto")
            if brutto is None:
                continue
            art = None
            if (beleg.get("waehrung") or "EUR") == "EUR":
                if abs(brutto - abgang["betrag"]) <= 0.01:
                    art = "sicher"
            elif brutto:
                quotient = abgang["betrag"] / brutto
                if KURS_BAND[0] <= quotient <= KURS_BAND[1]:
                    art = "fremdwaehrung"
            if art:
                kandidaten.append((abstand, 0 if art == "sicher" else 1, ia, ib, art))

    kandidaten.sort()
    belegt_a: set[int] = set()
    belegt_b: set[int] = set()
    paare: list[dict] = []
    for abstand, _rang, ia, ib, art in kandidaten:
        if ia in belegt_a or ib in belegt_b:
            continue
        belegt_a.add(ia)
        belegt_b.add(ib)
        paare.append(
            {
                "abgang": abgaenge[ia],
                "beleg": belege[ib],
                "art": art,
                "abstand": abstand,
            }
        )
    offen_a = [a for i, a in enumerate(abgaenge) if i not in belegt_a]
    offen_b = [b for i, b in enumerate(belege) if i not in belegt_b]
    return paare, offen_a, offen_b


def _nummer_schluessel(nummer) -> str:
    """Vergleichsform einer Rechnungsnummer: ohne Trenner, klein."""
    return re.sub(r"[\s_\-/.]+", "", str(nummer or "")).lower()


def ohne_doppelte_nummern(
    belege: list[dict], gesehen: set[str]
) -> tuple[list[dict], int]:
    """Dieselbe Rechnung nur einmal je Lauf — erste Fundstelle gewinnt.

    Dieselbe Rechnung erreicht uns mehrfach: als Anhang der Rechnungsmail, als
    Zahlungsbeleg derselben Mail und noch einmal als Datei in der Owner-Ablage.
    Der Dedup in ``beleg_entwurf.py`` faengt das erst gegenueber dem BESTAND
    ab — innerhalb eines Laufs entstanden so mehrere Vorschau-Zeilen fuer
    denselben Beleg (#3118).
    """
    frisch: list[dict] = []
    doppelt = 0
    for beleg in belege:
        schluessel = _nummer_schluessel(beleg.get("nummer"))
        if schluessel and schluessel in gesehen:
            doppelt += 1
            continue
        if schluessel:
            gesehen.add(schluessel)
        frisch.append(beleg)
    return frisch, doppelt


# ── Postfach (Microsoft Graph) ─────────────────────────────────────────────


def graph_modul():
    """``graph_mail`` erst beim Zugriff importieren — Tests injizieren Fakes
    und sollen ohne Postfach-Konfiguration laufen."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))
    import graph_mail  # noqa: PLC0415

    return graph_mail


def graph_zugang(konto: str | None = None):
    """(modul, konto, token) — fehlt der Token, ist das ein Abbruch mit dem
    Kommando, das ihn beschafft (nie ein leeres Suchergebnis)."""
    gm = graph_modul()
    cfg = gm.load_cfg()
    acc = konto or cfg["accounts"][0]
    tok = gm.token(cfg, acc)
    if not tok:
        raise Bezugsfehler(
            f"Postfach '{acc}' nicht angemeldet — erst: "
            f"python3 tools/mail_agent/graph_mail.py --login {acc}"
        )
    return gm, acc, tok


def graph_funktionen(konto: str | None = None):
    """(suche_fn, download_fn) gegen das echte Postfach, read-only."""
    gm, _acc, tok = graph_zugang(konto)

    def suche_fn(absender: str, betreff: str, tage: int, ordner: str) -> list[dict]:
        return gm._match_messages(
            tok,
            from_sub=absender,
            subject_sub=betreff,
            days=tage,
            source_path=ordner,
        )

    def download_fn(msg_id: str, ziel: Path) -> list[str]:
        return [
            name for name, _groesse in gm.download_attachments(tok, msg_id, str(ziel))
        ]

    return suche_fn, download_fn


def index_laden(pfad: Path) -> dict:
    if not pfad.exists():
        return {}
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return daten.get("nachrichten") or {}


def index_schreiben(pfad: Path, nachrichten: dict) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(
        json.dumps({"nachrichten": nachrichten}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )


def suchfenster(
    abgaenge: list[dict], heute: dt.date, fenster: int = TAGE_FENSTER
) -> int:
    """Tage zurueck: vom fruehesten zugehoerigen Abgang minus Fenster bis heute."""
    daten = []
    for abgang in abgaenge:
        try:
            daten.append(dt.date.fromisoformat(str(abgang.get("datum"))[:10]))
        except ValueError:
            continue
    if not daten:
        return fenster
    return max(1, (heute - min(daten)).days + fenster)


def belege_beschaffen(
    eintrag: dict,
    abgaenge: list[dict],
    ablage: Path,
    index: dict,
    suche_fn,
    download_fn,
    heute: dt.date,
    lese_fn=None,
    tage: int | None = None,
) -> tuple[list[dict], list[str]]:
    """PDFs eines ``mail``-Lieferanten holen und lesen — einmal je Register-
    Eintrag, nicht je Abgang.

    ``tage`` setzt das Suchfenster von aussen; ohne Angabe rechnet es
    ``suchfenster`` aus den Abgaengen. Fuer Lieferanten ohne Abgang
    (``ohne_abgang``) gibt es keinen Ankerpunkt — dort gilt das Fenster des
    Laufs (``--tage``).

    Idempotenz auf Postfach-Seite: eine Nachricht, die schon im Index steht,
    wird nicht erneut heruntergeladen; ihre bereits abgelegten Dateien werden
    trotzdem gelesen (sonst verschwaende der zweite Lauf den ersten).
    """
    lese_fn = lese_fn or pdf_text
    tage = tage if tage is not None else suchfenster(abgaenge, heute)
    ziel = ablage / re.sub(
        r"[^A-Za-z0-9_.\-]+", "_", eintrag.get("lieferant") or "unbekannt"
    )
    fehler: list[str] = []
    nachrichten: dict[str, dict] = {}
    for ordner in eintrag.get("ordner") or ["inbox"]:
        try:
            treffer = suche_fn(
                eintrag.get("absender", ""), eintrag.get("betreff", ""), tage, ordner
            )
        except (
            SystemExit
        ) as exc:  # _match_messages beendet den Prozess bei fehlendem Ordner
            fehler.append(f"Ordner '{ordner}' nicht lesbar — {exc}")
            continue
        for nachricht in treffer:
            nachrichten.setdefault(nachricht.get("id"), nachricht)

    belege: list[dict] = []
    for msg_id, nachricht in nachrichten.items():
        bekannt = index.get(msg_id)
        if bekannt:
            dateien = [ziel / name for name in bekannt.get("dateien", [])]
        else:
            namen = download_fn(msg_id, ziel)
            dateien = [ziel / name for name in namen]
            index[msg_id] = {
                "lieferant": eintrag.get("lieferant", ""),
                "dateien": [p.name for p in dateien],
                "zeit": heute.isoformat(),
            }
        for pfad in dateien:
            if pfad.suffix.lower() != ".pdf":
                continue
            if not pfad.exists():
                fehler.append(f"PDF fehlt in der Ablage: {pfad}")
                continue
            feld = pdf_lesen(lese_fn(pfad), pfad.name, logins_zuordnung(eintrag))
            feld.update(
                {
                    "pfad": str(pfad),
                    "lieferant": eintrag.get("lieferant", ""),
                    "betreff": kurz(nachricht.get("subject") or "", 60),
                }
            )
            belege.append(feld)
    return belege, fehler


# ── Owner-Ablage (~/shared/inbox/invoices) ─────────────────────────────────


def eintrag_aus_ablage(dateiname: str, text: str, register: list[dict]) -> dict | None:
    """Register-Eintrag zu einer abgelegten Datei — erst Dateiname, dann Text.

    Der Dateiname wird zuerst geprueft, weil der Owner ihn beim Herunterladen
    in der Hand hat; der PDF-Text ist die Rueckfallebene fuer Dateien, die
    nur eine Nummer heissen. ``intern``-Eintraege zaehlen NICHT als Treffer:
    fuer sie gibt es per Definition keinen Lieferantenbeleg, und ein
    Kontoauszug in der Ablage soll keinen Beleg-Entwurf ausloesen.
    """
    for heuhaufen in (dateiname, text):
        for eintrag in register:
            if eintrag.get("weg") == "intern":
                continue
            try:
                if re.search(eintrag["muster"], heuhaufen or "", re.IGNORECASE):
                    return eintrag
            except re.error:
                continue
    return None


def _ablage_schluessel(pfad: Path) -> str:
    """Pfad + Aenderungszeit — eine ersetzte Datei gilt als neue Datei."""
    try:
        stempel = int(pfad.stat().st_mtime)
    except OSError:
        stempel = 0
    return f"ablage:{pfad}:{stempel}"


def ablage_lesen(
    ordner: Path, register: list[dict], index: dict, lese_fn=None
) -> tuple[dict[int, list[dict]], list[dict], int]:
    """PDFs aus der Owner-Ablage lesen und Register-Eintraegen zuordnen.

    Rueckgabe: ``({id(eintrag): [beleg, ...]}, ohne_zuordnung, gelesen)``.
    Dateien werden **nie** verschoben oder geloescht — ``~/shared`` ist die
    Schleuse des Owners, das Aufraeumen bleibt bei ihm. Ein bereits
    angelegter Beleg wird ueber den Index uebersprungen; der harte Schutz
    gegen Doppelbelege bleibt der Dedup ueber die Rechnungsnummer.
    """
    lese_fn = lese_fn or pdf_text
    if not ordner.exists():
        return {}, [], 0
    treffer: dict[int, list[dict]] = {}
    offen: list[dict] = []
    gelesen = 0
    for pfad in sorted(ordner.glob("*.pdf")):
        if _ablage_schluessel(pfad) in index:
            continue
        text = lese_fn(pfad)
        gelesen += 1
        eintrag = eintrag_aus_ablage(pfad.name, text, register)
        if eintrag is None:
            offen.append({"pfad": str(pfad), "dateiname": pfad.name})
            continue
        feld = pdf_lesen(text, pfad.name, logins_zuordnung(eintrag))
        feld.update(
            {
                "pfad": str(pfad),
                "lieferant": eintrag.get("lieferant", ""),
                "betreff": f"Ablage: {pfad.name}",
                "quelle": "ablage",
                "schluessel": _ablage_schluessel(pfad),
            }
        )
        treffer.setdefault(id(eintrag), []).append(feld)
    return treffer, offen, gelesen


# ── Entwurf anlegen (ueber beleg_entwurf.py) ───────────────────────────────


def anlegen_standard(namespace) -> int:
    """Echter Aufruf von ``beleg_entwurf.anlegen`` — lazy, damit Tests ohne
    sevdesk-Zugang laufen."""
    import beleg_entwurf  # noqa: PLC0415

    return beleg_entwurf.anlegen(namespace)


def taxrule_bestimmen(beleg: dict, eintrag: dict) -> tuple[str, str]:
    """(taxrule, hinweis) — das PDF schlaegt das Register.

    Weist eine Rechnung deutsche Umsatzsteuer aus, kann sie keine
    Reverse-Charge-Rechnung sein; ein Register-Eintrag, der noch auf 12 oder
    14 steht, waere dann schlicht falsch (#3118). Die Abweichung wird nicht
    stillschweigend genommen, sondern im Board benannt.
    """
    aus_register = str(eintrag.get("taxrule") or TAXRULE_MIT_UST)
    if (beleg.get("steuer") or 0) <= 0:
        return aus_register, ""
    if aus_register == TAXRULE_MIT_UST:
        return aus_register, ""
    return TAXRULE_MIT_UST, f"Register {aus_register} → {TAXRULE_MIT_UST} (USt im PDF)"


def entwurf_anlegen(beleg: dict, eintrag: dict, anlegen_fn, wirklich: bool) -> dict:
    """Einen Beleg-Entwurf anlegen (oder vormerken) und die Ausgabe auswerten.

    ``beleg_entwurf.anlegen`` schreibt sein Ergebnis als JSON auf stdout —
    das wird hier abgefangen, damit das Board die einzige Ausgabe bleibt.
    Konto wird NIE gesetzt; der Vorschlag landet nur im Board.
    """
    taxrule, taxrule_hinweis = taxrule_bestimmen(beleg, eintrag)
    namespace = argparse.Namespace(
        mandant=beleg.get("empfaenger") or ABGANG_MANDANT,
        pdf=beleg["pfad"],
        lieferant=eintrag.get("lieferant") or beleg.get("lieferant_hinweis") or "",
        datum=beleg["datum"],
        brutto=f"{beleg['brutto']:.2f}",
        steuer=f"{beleg['steuer']:.2f}",
        beschreibung=beleg["nummer"],
        taxrule=taxrule,
        konto=None,
        waehrung=beleg.get("waehrung") or "EUR",
        kurs=None,
        konto_vorschlag=True,
        trotzdem=False,
        strikt=False,
        dry_run=not wirklich,
    )
    puffer = io.StringIO()
    with contextlib.redirect_stdout(puffer):
        code = anlegen_fn(namespace)
    ausgabe = puffer.getvalue()

    beleg_id = None
    for zeile in reversed(ausgabe.splitlines()):
        zeile = zeile.strip()
        if not zeile.startswith("{"):
            continue
        try:
            beleg_id = json.loads(zeile).get("beleg_id")
        except json.JSONDecodeError:
            continue
        break

    if "DUPLIKAT" in ausgabe:
        status = "DUPLIKAT"
    elif beleg_id:
        status = "angelegt"
    elif not wirklich and code == 0:
        status = "VORSCHAU"
    else:
        status = "FEHLER"

    vorschlaege = RE_VORSCHLAG_KONTO.findall(ausgabe)
    return {
        "status": status,
        "beleg_id": beleg_id,
        "code": code,
        "taxrule": taxrule,
        "taxrule_hinweis": taxrule_hinweis,
        "konto_vorschlag": eintrag.get("konto")
        or (vorschlaege[0] if vorschlaege else "—"),
        "ausgabe": ausgabe.strip(),
    }


# ── Abgaenge laden ─────────────────────────────────────────────────────────


def abgaenge_aus_json(daten: dict) -> list[dict]:
    """Die Liste ``beleg_fehlt`` aus ``kostenabgleich.py --json``."""
    return [
        {
            "datum": p.get("datum", ""),
            "zahler": p.get("zahler", ""),
            "zweck": p.get("zweck", ""),
            "betrag": float(p.get("betrag") or 0),
            "konto_vorschlag": p.get("konto_vorschlag", "—"),
            "konto_grund": p.get("konto_grund", ""),
        }
        for p in daten.get("beleg_fehlt") or []
    ]


def abgaenge_laden(args, heute: dt.date) -> list[dict]:
    if args.eingabe:
        return abgaenge_aus_json(
            json.loads(Path(args.eingabe).read_text(encoding="utf-8"))
        )
    regeln = konten_laden(args.konten)
    positionen = positionen_ermitteln(client(ABGANG_MANDANT), heute, args.tage, regeln)
    return [
        {
            "datum": p["datum"],
            "zahler": p["zahler"],
            "zweck": kurz(p.get("zweck", ""), 80),
            "betrag": p["betrag"],
            "konto_vorschlag": p["konto_vorschlag"],
            "konto_grund": p["konto_grund"],
        }
        for p in positionen
        if p["status"] == "fehlend"
    ]


# ── Lauf ───────────────────────────────────────────────────────────────────


def lauf(
    args,
    heute: dt.date,
    suche_fn=None,
    download_fn=None,
    anlegen_fn=None,
    lese_fn=None,
) -> dict:
    """Der ganze Durchgang: Abgaenge -> Register -> Postfach -> Entwuerfe.

    Alle Aussenzugriffe sind injizierbar (Postfach-Suche, Download, PDF-Text,
    Entwurf) — so laeuft der Test ohne Netz und ohne ``pdftotext`` denselben
    Pfad wie der Betrieb.
    """
    start = time.monotonic()
    register = register_laden(Path(args.register))
    abgaenge = abgaenge_laden(args, heute)
    ablage = Path(args.ablage)
    index = index_laden(Path(args.index))

    entwuerfe: list[dict] = []
    owner: list[dict] = []
    intern: list[dict] = []
    pdf_ohne_abgang: list[dict] = []

    gruppen: dict[int, list[dict]] = {}
    for abgang in abgaenge:
        eintrag = eintrag_fuer(abgang, register)
        if eintrag is None:
            owner.append(
                {
                    "art": "kein Bezugsweg",
                    "datum": abgang["datum"],
                    "lieferant": abgang["zahler"],
                    "betrag": abgang["betrag"],
                    "hinweis": f"Register ergaenzen ({kurz(abgang.get('zweck', ''), 40)})",
                }
            )
            continue
        if eintrag.get("weg") == "intern":
            intern.append(
                {
                    "datum": abgang["datum"],
                    "zahler": abgang["zahler"],
                    "betrag": abgang["betrag"],
                    "konto_vorschlag": abgang.get("konto_vorschlag", "—"),
                    "grund": eintrag.get("grund", ""),
                }
            )
            continue
        if eintrag.get("weg") == "portal":
            owner.append(
                {
                    "art": "Portal",
                    "datum": abgang["datum"],
                    "lieferant": eintrag.get("lieferant", abgang["zahler"]),
                    "betrag": abgang["betrag"],
                    "hinweis": eintrag.get("url") or eintrag.get("grund", ""),
                }
            )
            continue
        gruppen.setdefault(id(eintrag), []).append(abgang)

    wirklich = bool(args.anlegen)
    ziel_mandanten = set(MANDANTEN_ZIEL.get(args.mandant, (ABGANG_MANDANT,)))
    # Ein fehlender Zugang ist kein Abbruch: die Belege des Mandanten bleiben
    # dann Owner-Zug, alles andere laeuft weiter (#3112).
    if "edv" in ziel_mandanten and not secret_datei("edv").exists():
        ziel_mandanten.discard("edv")
        owner.append(
            {
                "art": "edv-Zugang fehlt",
                "datum": heute.isoformat(),
                "lieferant": "edv",
                "betrag": 0.0,
                "hinweis": f"erwartete Datei: {secret_datei('edv')}",
            }
        )
    aus_ablage, ablage_offen, ablage_pdf = ablage_lesen(
        Path(args.ablage_inbox), register, index, lese_fn
    )
    for offen in ablage_offen:
        owner.append(
            {
                "art": "Ablage: Lieferant unbekannt",
                "datum": heute.isoformat(),
                "lieferant": kurz(offen["dateiname"], 24),
                "betrag": 0.0,
                "hinweis": offen["pfad"],
            }
        )

    ohne_abgang_eintraege = [
        e
        for e in register
        if e.get("weg") == "mail" and e.get("ohne_abgang") and not gruppen.get(id(e))
    ]
    if suche_fn is None or download_fn is None:
        if gruppen or ohne_abgang_eintraege:
            suche_fn, download_fn = graph_funktionen(args.konto)
        else:
            suche_fn, download_fn = (lambda *a, **k: []), (lambda *a, **k: [])
    if anlegen_fn is None:
        anlegen_fn = anlegen_standard

    pdf_gefunden = 0
    bereits_im_lauf = 0
    gesehene_nummern: set[str] = set()
    for eintrag in register:
        teil = gruppen.get(id(eintrag)) or []
        abgelegte = aus_ablage.get(id(eintrag), [])
        postfach_noetig = eintrag.get("weg") == "mail" and (
            teil or eintrag in ohne_abgang_eintraege
        )
        if not (postfach_noetig or abgelegte):
            continue
        # Ohne Abgang gibt es keinen Ankerpunkt fuer das Fenster — dann gilt
        # das Fenster des Laufs (Lieferanten, die ein anderes Konto bezahlt,
        # deren Rechnung aber hier liegt: Register-Feld "ohne_abgang").
        belege, fehler = (
            belege_beschaffen(
                eintrag,
                teil,
                ablage,
                index,
                suche_fn,
                download_fn,
                heute,
                lese_fn,
                tage=None if teil else int(args.tage),
            )
            if postfach_noetig
            else ([], [])
        )
        belege += abgelegte
        belege, doppelt = ohne_doppelte_nummern(belege, gesehene_nummern)
        bereits_im_lauf += doppelt
        pdf_gefunden += len(belege)
        for text in fehler:
            owner.append(
                {
                    "art": "Postfach",
                    "datum": heute.isoformat(),
                    "lieferant": eintrag.get("lieferant", ""),
                    "betrag": 0.0,
                    "hinweis": text,
                }
            )

        # Der Empfaenger im PDF entscheidet, in welchem Mandanten der Beleg
        # entsteht — und ob ueberhaupt. "unklar" bleibt ausnahmslos Owner-Zug.
        eigene = [
            b for b in belege if b["empfaenger"] == "iil" and "iil" in ziel_mandanten
        ]
        fremde = [
            b for b in belege if b["empfaenger"] == "edv" and "edv" in ziel_mandanten
        ]
        for beleg in belege:
            if beleg in eigene or beleg in fremde:
                continue
            owner.append(
                {
                    "art": "anderer Mandant (edv)"
                    if beleg["empfaenger"] == "edv"
                    else "Empfaenger unklar",
                    "datum": beleg.get("datum") or heute.isoformat(),
                    "lieferant": eintrag.get("lieferant", ""),
                    "betrag": beleg.get("brutto") or 0.0,
                    "hinweis": beleg["pfad"],
                }
            )

        # Die Abgaenge stammen vom IIL-Konto; Belege der zweiten Firma haben
        # dort per Definition keinen Gegenposten und gehen direkt in Liste 4.
        paare, ohne_pdf, ohne_abgang = zuordnen(
            teil if "iil" in ziel_mandanten else [], eigene
        )
        for paar in paare:
            entwuerfe.append(_entwurf_zeile(paar, eintrag, anlegen_fn, wirklich))
        for abgang in ohne_pdf:
            owner.append(
                {
                    "art": "Beleg nicht im Postfach",
                    "datum": abgang["datum"],
                    "lieferant": eintrag.get("lieferant", abgang["zahler"]),
                    "betrag": abgang["betrag"],
                    "hinweis": "Rechnung suchen oder Bezugsweg korrigieren",
                }
            )
        for beleg in ohne_abgang + fremde:
            zeile = _entwurf_zeile(
                {"abgang": None, "beleg": beleg, "art": "ohne Abgang", "abstand": None},
                eintrag,
                anlegen_fn,
                wirklich,
            )
            pdf_ohne_abgang.append(zeile)

    # Eine abgelegte Datei wird erst vermerkt, wenn wirklich ein Beleg daraus
    # entstanden ist — so wird ein misslungener Lauf beim naechsten Mal erneut
    # versucht, statt die Datei stillschweigend zu verlieren.
    schluessel_je_pfad = {
        b["pfad"]: b["schluessel"] for liste in aus_ablage.values() for b in liste
    }
    for zeile in entwuerfe + pdf_ohne_abgang:
        schluessel = schluessel_je_pfad.get(zeile.get("pdf"))
        if schluessel and zeile.get("ergebnis") == "angelegt":
            index[schluessel] = {
                "quelle": "ablage",
                "pfad": zeile["pdf"],
                "beleg_id": zeile.get("beleg_id"),
                "zeit": heute.isoformat(),
            }

    index_schreiben(Path(args.index), index)

    angelegt = sum(
        1 for z in entwuerfe + pdf_ohne_abgang if z.get("ergebnis") == "angelegt"
    )
    duplikate = sum(
        1 for z in entwuerfe + pdf_ohne_abgang if z.get("ergebnis") == "DUPLIKAT"
    )
    vorschau = sum(
        1 for z in entwuerfe + pdf_ohne_abgang if z.get("ergebnis") == "VORSCHAU"
    )
    je_mandant: dict[str, int] = {}
    for zeile in entwuerfe + pdf_ohne_abgang:
        if zeile.get("ergebnis") in ("angelegt", "VORSCHAU"):
            name = zeile.get("mandant") or ABGANG_MANDANT
            je_mandant[name] = je_mandant.get(name, 0) + 1

    kennzahlen = {
        "mandant": args.mandant,
        "entwuerfe_je_mandant": je_mandant,
        "bereits_im_lauf": bereits_im_lauf,
        "lieferanten_abgaenge": sum(len(v) for v in gruppen.values()),
        # pdf_gefunden = PDFs, die einem Register-Eintrag zugeordnet werden
        # konnten; ablage_pdf = aus der Owner-Ablage gelesene Dateien, auch
        # die ohne Zuordnung (die als Owner-Zug erscheinen).
        "pdf_gefunden": pdf_gefunden,
        "ablage_pdf": ablage_pdf,
        "entwuerfe_angelegt": angelegt,
        "duplikate": duplikate,
        "vorschau": vorschau,
        "owner_zug": len(owner),
        "intern": len(intern),
        "pdf_ohne_abgang": len(pdf_ohne_abgang),
        "dauer_s": round(time.monotonic() - start, 2),
        "anlegen": wirklich,
    }
    return {
        "kennzahlen": kennzahlen,
        "entwuerfe": entwuerfe,
        "owner": owner,
        "intern": intern,
        "pdf_ohne_abgang": pdf_ohne_abgang,
    }


def _entwurf_zeile(paar: dict, eintrag: dict, anlegen_fn, wirklich: bool) -> dict:
    beleg = paar["beleg"]
    abgang = paar.get("abgang")
    if beleg.get("datum") is None or beleg.get("brutto") is None:
        taxrule, taxrule_hinweis = taxrule_bestimmen(beleg, eintrag)
        ergebnis = {
            "status": "FEHLER",
            "beleg_id": None,
            "konto_vorschlag": eintrag.get("konto") or "—",
            "ausgabe": "Datum oder Betrag im PDF nicht gefunden — Layout geaendert?",
            "taxrule": taxrule,
            "taxrule_hinweis": taxrule_hinweis,
        }
    else:
        ergebnis = entwurf_anlegen(beleg, eintrag, anlegen_fn, wirklich)
    return {
        "mandant": beleg.get("empfaenger") or ABGANG_MANDANT,
        "taxrule": ergebnis["taxrule"],
        "taxrule_hinweis": ergebnis["taxrule_hinweis"],
        "datum_abgang": abgang["datum"] if abgang else "—",
        "betrag_abgang": abgang["betrag"] if abgang else None,
        "lieferant": eintrag.get("lieferant", ""),
        "pdf_betrag": beleg.get("brutto"),
        "waehrung": beleg.get("waehrung"),
        "steuer": beleg.get("steuer"),
        "datum_beleg": beleg.get("datum"),
        "nummer": beleg.get("nummer"),
        "art": paar["art"],
        "pdf": beleg.get("pfad"),
        "ergebnis": ergebnis["status"],
        "beleg_id": ergebnis["beleg_id"],
        "konto_vorschlag": ergebnis["konto_vorschlag"],
        "meldung": kurz(ergebnis["ausgabe"], 120),
    }


# ── Ausgabe ────────────────────────────────────────────────────────────────


def _betrag(wert) -> str:
    return "—" if wert is None else f"{wert:,.2f}"


def _steuer_hinweise(zeilen_liste: list[dict]) -> list[str]:
    """Abweichungen Register -> PDF ausdruecklich benennen, statt sie still in
    der Spalte verschwinden zu lassen."""
    hinweise = [
        f"- Steuerregel {kurz(str(z.get('nummer')), 24)}: {z['taxrule_hinweis']}"
        for z in zeilen_liste
        if z.get("taxrule_hinweis")
    ]
    return ["\n" + "\n".join(hinweise) + "\n"] if hinweise else []


def render_markdown(ergebnis: dict, args) -> str:
    k = ergebnis["kennzahlen"]
    zeilen = [
        f"# Belegbeschaffung — Fenster {args.tage} Tage (Mandant {args.mandant})\n"
    ]
    zeilen.append(
        f"\n{k['lieferanten_abgaenge']} Abgaenge mit Lieferantenbeleg-Weg — "
        f"**{k['pdf_gefunden']} PDF zugeordnet** · "
        f"{k['ablage_pdf']} aus der Ablage gelesen · "
        f"**{k['entwuerfe_angelegt']} Entwuerfe angelegt** · "
        f"{k['vorschau']} Vorschau · {k['duplikate']} Duplikate · "
        f"**{k['owner_zug']} Owner-Zug** · {k['intern']} intern · "
        f"{k['bereits_im_lauf']} doppelt im Lauf\n"
    )
    je_mandant = k.get("entwuerfe_je_mandant") or {}
    zeilen.append(
        "\nEntwuerfe je Mandant: "
        + (
            " · ".join(
                f"{name} {anzahl}" for name, anzahl in sorted(je_mandant.items())
            )
            or "(keine)"
        )
        + f" (Lauf-Mandant: {k.get('mandant', ABGANG_MANDANT)})\n"
    )
    if not k["anlegen"]:
        zeilen.append(
            "\n> Vorschau — es wurde NICHTS in sevdesk angelegt (`--anlegen` fehlt).\n"
        )

    zeilen.append(
        f"\n## 1. Entwuerfe angelegt / Vorschau ({len(ergebnis['entwuerfe'])})\n"
    )
    if ergebnis["entwuerfe"]:
        zeilen.append(
            "\n| Datum Abgang | Lieferant | Abgang EUR | PDF | Nummer | Beleg | Konto | Steuer | Mandant | Art |"
        )
        zeilen.append("|---|---|---:|---|---|---|---|---|---|---|")
        for z in ergebnis["entwuerfe"]:
            beleg = z["beleg_id"] or z["ergebnis"]
            zeilen.append(
                f"| {z['datum_abgang']} | {kurz(z['lieferant'], 24)} | "
                f"{_betrag(z['betrag_abgang'])} | {_betrag(z['pdf_betrag'])} {z['waehrung']} | "
                f"{kurz(str(z['nummer']), 24)} | {beleg} | {kurz(str(z['konto_vorschlag']), 16)} | "
                f"{z.get('taxrule', '')} | {z.get('mandant', '')} | {z['art']} |"
            )
    else:
        zeilen.append("\n(keine)\n")
    zeilen += _steuer_hinweise(ergebnis["entwuerfe"])

    zeilen.append(f"\n## 2. Owner-Zug ({len(ergebnis['owner'])})\n")
    if ergebnis["owner"]:
        zeilen.append("\n| Datum | Art | Lieferant | Betrag | Hinweis |")
        zeilen.append("|---|---|---|---:|---|")
        for z in ergebnis["owner"]:
            zeilen.append(
                f"| {z['datum']} | {z['art']} | {kurz(z['lieferant'], 24)} | "
                f"{_betrag(z['betrag'])} | {kurz(str(z['hinweis']), 70)} |"
            )
    else:
        zeilen.append("\n(keine)\n")

    zeilen.append(
        f"\n## 3. intern (kein Lieferantenbeleg) ({len(ergebnis['intern'])})\n"
    )
    if ergebnis["intern"]:
        zeilen.append("\n| Datum | Zahler | Betrag EUR | Konto-Vorschlag | Grund |")
        zeilen.append("|---|---|---:|---|---|")
        for z in ergebnis["intern"]:
            zeilen.append(
                f"| {z['datum']} | {kurz(z['zahler'], 24)} | {_betrag(z['betrag'])} | "
                f"{kurz(str(z['konto_vorschlag']), 30)} | {kurz(z['grund'], 50)} |"
            )
    else:
        zeilen.append("\n(keine)\n")

    zeilen.append(f"\n## 4. PDF ohne Abgang ({len(ergebnis['pdf_ohne_abgang'])})\n")
    if ergebnis["pdf_ohne_abgang"]:
        zeilen.append(
            "\n| Datum Beleg | Lieferant | Betrag | Nummer | Beleg | Steuer | Mandant |"
        )
        zeilen.append("|---|---|---:|---|---|---|---|")
        for z in ergebnis["pdf_ohne_abgang"]:
            beleg = z["beleg_id"] or z["ergebnis"]
            zeilen.append(
                f"| {z['datum_beleg']} | {kurz(z['lieferant'], 24)} | "
                f"{_betrag(z['pdf_betrag'])} {z['waehrung']} | {kurz(str(z['nummer']), 24)} | "
                f"{beleg} | {z.get('taxrule', '')} | {z.get('mandant', '')} |"
            )
    else:
        zeilen.append("\n(keine)\n")
    zeilen += _steuer_hinweise(ergebnis["pdf_ohne_abgang"])

    return "\n".join(zeilen) + "\n"


def journal_schreiben(kennzahlen: dict, pfad: Path) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    zeile = dict(kennzahlen)
    zeile["zeit"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    with pfad.open("a", encoding="utf-8") as f:
        f.write(json.dumps(zeile, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # Eigenes Argument statt ``mandant.mandant_argument``: hier gibt es den
    # dritten Wert "beide", den die uebrigen Werkzeuge nicht kennen.
    p.add_argument(
        "--mandant",
        choices=sorted(MANDANTEN_ZIEL),
        default=os.environ.get("SEVDESK_MANDANT", ABGANG_MANDANT),
        help=(
            "welche Belege angelegt werden: iil (Standard), edv (nur Belege der "
            "zweiten Firma) oder beide — je Beleg entscheidet der Empfaenger im PDF"
        ),
    )
    p.add_argument(
        "--tage", type=int, default=120, help="Fenster fuer Bankabgaenge (Standard 120)"
    )
    p.add_argument(
        "--eingabe",
        default=None,
        help="JSON aus 'kostenabgleich.py --json' statt eines Live-Laufs (Reproduzierbarkeit)",
    )
    p.add_argument(
        "--register", type=Path, default=STANDARD_REGISTER, help="Bezugswege-Register"
    )
    p.add_argument(
        "--ablage",
        type=Path,
        default=STANDARD_ABLAGE,
        help="Ablage der PDFs je Lieferant",
    )
    p.add_argument(
        "--ablage-inbox",
        type=Path,
        dest="ablage_inbox",
        default=STANDARD_ABLAGE_INBOX,
        help=(
            "Owner-Ablage fuer von Hand geladene Rechnungen "
            f"(Standard {STANDARD_ABLAGE_INBOX}); fehlender Ordner ist kein Fehler"
        ),
    )
    p.add_argument(
        "--index",
        type=Path,
        default=INDEX_DATEI,
        help="Index bereits geholter Nachrichten",
    )
    p.add_argument("--journal", type=Path, default=JOURNAL_DATEI)
    p.add_argument("--konten", type=Path, default=KONTEN_DATEI)
    p.add_argument(
        "--konto",
        default=None,
        help="Postfach-Konto (Standard: erstes aus calendar.env)",
    )
    p.add_argument(
        "--anlegen",
        action="store_true",
        help="Beleg-ENTWUERFE wirklich anlegen (Status 50) — ohne das nur Vorschau",
    )
    p.add_argument(
        "--json", action="store_true", help="Ausgabe als JSON statt Markdown"
    )
    p.add_argument(
        "--heute", default=None, help="Stichtag YYYY-MM-DD (Reproduzierbarkeit)"
    )
    p.add_argument("--ziel", type=Path, default=STANDARD_ZIEL)
    args = p.parse_args(argv)

    heute = dt.date.fromisoformat(args.heute) if args.heute else dt.date.today()
    try:
        ergebnis = lauf(args, heute)
    except Bezugsfehler as exc:
        print(f"ABBRUCH: {exc}")
        return 3
    except Exception as exc:  # httpx-/Graph-Fehler: benennen statt Traceback
        print(f"ABBRUCH: API-Fehler — {exc}")
        return 3

    journal_schreiben(ergebnis["kennzahlen"], Path(args.journal))

    if args.json:
        print(json.dumps(ergebnis, ensure_ascii=False, indent=1))
    else:
        text = render_markdown(ergebnis, args)
        print(text)
        args.ziel.parent.mkdir(parents=True, exist_ok=True)
        args.ziel.write_text(text, encoding="utf-8")
        print(f"geschrieben: {args.ziel}")

    return 2 if ergebnis["owner"] else 0


if __name__ == "__main__":
    sys.exit(main())
