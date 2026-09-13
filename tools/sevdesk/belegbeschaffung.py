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
- ``portal``  — die Rechnung gibt es nur im Kundenkonto (Owner-Zug, mit Link).

    python3 tools/sevdesk/belegbeschaffung.py                      # Vorschau, legt NICHTS an
    python3 tools/sevdesk/belegbeschaffung.py --tage 60            # engeres Fenster
    python3 tools/sevdesk/belegbeschaffung.py --eingabe lauf.json  # Kostenabgleich-JSON statt Live-Lauf
    python3 tools/sevdesk/belegbeschaffung.py --anlegen            # Beleg-ENTWUERFE wirklich anlegen
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
- Belege fuer einen anderen Mandanten (``edv``) werden NICHT angelegt, sondern
  mit lokalem PDF-Pfad als Owner-Zug gelistet (``beleg_entwurf.py`` ist noch
  fest auf IIL, platform#3112).
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
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bankpositionen import KONTEN_DATEI, konten_laden, kurz  # noqa: E402
from kostenabgleich import positionen_ermitteln  # noqa: E402
from mandant import client, mandant_argument  # noqa: E402

VORLAGE = Path(__file__).resolve().parent / "sevdesk-bezugswege.example.json"
STANDARD_REGISTER = Path.home() / ".claude" / "sevdesk-bezugswege.json"
STANDARD_ABLAGE = Path.home() / ".claude" / "sevdesk-belege"
INDEX_DATEI = Path.home() / ".claude" / "sevdesk-belegbeschaffung-index.json"
JOURNAL_DATEI = Path.home() / ".claude" / "sevdesk-belegbeschaffung-journal.jsonl"
STANDARD_ZIEL = Path.home() / ".claude" / "boards" / "sevdesk-belegbeschaffung.md"

#: Nur dieser Mandant darf Entwuerfe anlegen — ``beleg_entwurf.py`` liest seinen
#: Zugang noch fest verdrahtet (platform#3112).
ANLEGE_MANDANT = "iil"

#: Datumsabstand zwischen Abgang und Rechnung, in Tagen. Grosszuegig, weil
#: Abo-Abbuchungen dem Rechnungsdatum um Wochen nachlaufen koennen.
TAGE_FENSTER = 40

#: Zulaessiger Quotient EUR-Abgang / Fremdwaehrungsbetrag. 0.80-1.00 deckt die
#: ueblichen USD/EUR-Kurse samt Bankaufschlag ab, ohne beliebige Betraege zu
#: verheiraten. Ein Treffer in diesem Band ist NIE "sicher".
KURS_BAND = (0.80, 1.00)

#: Zahlungsbelege nennen teils keinen Rechnungsempfaenger, sondern nur
#: "Account billed <login>". Welche Logins den eigenen Mandanten belegen,
#: steht im Register (``eigene_logins``) — nicht im Code, denn es ist eine
#: Owner-Angabe, kein Programmwissen. Ohne Angabe bleibt der Empfaenger
#: "unklar" und geht an den Owner, statt beim falschen Mandanten zu landen.
EIGENE_LOGINS: tuple[str, ...] = ()

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
#: Zeilen mit diesen Woertern tragen die enthaltene Steuer. Summenzeilen sind
#: ausgenommen — "Gesamtbetrag (nach Steuern)" ist keine Steuerzeile.
STEUER_WOERTER = ("steuer", "mwst", "ust", "umsatzsteuer", "vat", "tax")
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


def _letzte_zahl(zeile: str) -> float | None:
    werte = [zahl_lesen(t) for t in RE_ZAHL.findall(zeile)]
    werte = [w for w in werte if w is not None]
    return werte[-1] if werte else None


def _monat_nummer(wort: str) -> int | None:
    return MONATE.get((wort or "").strip(".").lower())


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


def empfaenger_bestimmen(text: str, eigene_logins=EIGENE_LOGINS) -> str:
    """``iil`` | ``edv`` | ``unklar`` — ausschliesslich aus dem PDF-Text.

    Die Reihenfolge ist die Lehre aus der Echtprobe (2026-09-13): eine
    Rechnung im IIL-Postfach war an den zweiten Mandanten adressiert. Wer den
    Empfaenger aus dem Postfach schliesst, legt sie beim falschen an.

    Die Pruefreihenfolge ist bewusst so und nicht anders:

    1. ``EDV Beratung`` schlaegt alles — der zweite Mandant wird nie
       stillschweigend zum eigenen.
    2. ``Account billed <login>`` gewinnt vor dem Domain-Marker. Ein
       Zahlungsbeleg sagt damit ausdruecklich, WELCHES Konto belastet wurde;
       ein fremdes Konto bleibt ``unklar``, auch wenn als Rechnungsadresse
       eine eigene Mailadresse daneben steht (real so gesehen 2026-09-13 —
       vier Belege auf ein privates Konto mit IIL-Rechnungsmail). Diese
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
        return "iil" if m.group(1) in {s.lower() for s in eigene_logins} else "unklar"
    if "iil.gmbh" in flach or "iil-institut" in flach:
        return "iil"
    if re.search(r"\biil\b", flach):
        return "iil"
    return "unklar"


def pdf_lesen(text: str, dateiname: str = "", eigene_logins=EIGENE_LOGINS) -> dict:
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
        if any(w in klein for w in SUMMEN_WOERTER) and _letzte_zahl(zeile) is not None:
            summen_zeile = zeile
            continue
        if any(w in klein for w in STEUER_AUSNAHMEN):
            continue
        if any(w in klein for w in STEUER_WOERTER) and _letzte_zahl(zeile) is not None:
            steuer_zeile = zeile

    brutto = _letzte_zahl(summen_zeile) if summen_zeile else None
    steuer = _letzte_zahl(steuer_zeile) if steuer_zeile else None
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
        "empfaenger": empfaenger_bestimmen(text, eigene_logins),
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
            feld = pdf_lesen(
                lese_fn(pfad),
                pfad.name,
                eintrag.get("eigene_logins") or EIGENE_LOGINS,
            )
            feld.update(
                {
                    "pfad": str(pfad),
                    "lieferant": eintrag.get("lieferant", ""),
                    "betreff": kurz(nachricht.get("subject") or "", 60),
                }
            )
            belege.append(feld)
    return belege, fehler


# ── Entwurf anlegen (ueber beleg_entwurf.py) ───────────────────────────────


def anlegen_standard(namespace) -> int:
    """Echter Aufruf von ``beleg_entwurf.anlegen`` — lazy, damit Tests ohne
    sevdesk-Zugang laufen."""
    import beleg_entwurf  # noqa: PLC0415

    return beleg_entwurf.anlegen(namespace)


def entwurf_anlegen(beleg: dict, eintrag: dict, anlegen_fn, wirklich: bool) -> dict:
    """Einen Beleg-Entwurf anlegen (oder vormerken) und die Ausgabe auswerten.

    ``beleg_entwurf.anlegen`` schreibt sein Ergebnis als JSON auf stdout —
    das wird hier abgefangen, damit das Board die einzige Ausgabe bleibt.
    Konto wird NIE gesetzt; der Vorschlag landet nur im Board.
    """
    namespace = argparse.Namespace(
        pdf=beleg["pfad"],
        lieferant=eintrag.get("lieferant") or beleg.get("lieferant_hinweis") or "",
        datum=beleg["datum"],
        brutto=f"{beleg['brutto']:.2f}",
        steuer=f"{beleg['steuer']:.2f}",
        beschreibung=beleg["nummer"],
        taxrule=str(eintrag.get("taxrule") or "9"),
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
    positionen = positionen_ermitteln(client(args.mandant), heute, args.tage, regeln)
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

    wirklich = bool(args.anlegen) and args.mandant == ANLEGE_MANDANT
    if args.anlegen and not wirklich:
        owner.append(
            {
                "art": "Mandant",
                "datum": heute.isoformat(),
                "lieferant": args.mandant,
                "betrag": 0.0,
                "hinweis": f"--anlegen nur fuer Mandant {ANLEGE_MANDANT} (platform#3112) — Vorschau",
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
    for eintrag in register:
        teil = gruppen.get(id(eintrag)) or []
        if not teil and eintrag not in ohne_abgang_eintraege:
            continue
        # Ohne Abgang gibt es keinen Ankerpunkt fuer das Fenster — dann gilt
        # das Fenster des Laufs (Lieferanten, die ein anderes Konto bezahlt,
        # deren Rechnung aber hier liegt: Register-Feld "ohne_abgang").
        belege, fehler = belege_beschaffen(
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

        eigene = [b for b in belege if b["empfaenger"] == "iil"]
        for beleg in belege:
            if beleg["empfaenger"] == "iil":
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

        paare, ohne_pdf, ohne_abgang = zuordnen(teil, eigene)
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
        for beleg in ohne_abgang:
            zeile = _entwurf_zeile(
                {"abgang": None, "beleg": beleg, "art": "ohne Abgang", "abstand": None},
                eintrag,
                anlegen_fn,
                wirklich,
            )
            pdf_ohne_abgang.append(zeile)

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
    kennzahlen = {
        "lieferanten_abgaenge": sum(len(v) for v in gruppen.values()),
        "pdf_gefunden": pdf_gefunden,
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
        ergebnis = {
            "status": "FEHLER",
            "beleg_id": None,
            "konto_vorschlag": eintrag.get("konto") or "—",
            "ausgabe": "Datum oder Betrag im PDF nicht gefunden — Layout geaendert?",
        }
    else:
        ergebnis = entwurf_anlegen(beleg, eintrag, anlegen_fn, wirklich)
    return {
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


def render_markdown(ergebnis: dict, args) -> str:
    k = ergebnis["kennzahlen"]
    zeilen = [
        f"# Belegbeschaffung — Fenster {args.tage} Tage (Mandant {args.mandant})\n"
    ]
    zeilen.append(
        f"\n{k['lieferanten_abgaenge']} Abgaenge mit Lieferantenbeleg-Weg — "
        f"**{k['pdf_gefunden']} PDF gefunden** · "
        f"**{k['entwuerfe_angelegt']} Entwuerfe angelegt** · "
        f"{k['vorschau']} Vorschau · {k['duplikate']} Duplikate · "
        f"**{k['owner_zug']} Owner-Zug** · {k['intern']} intern\n"
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
            "\n| Datum Abgang | Lieferant | Abgang EUR | PDF | Nummer | Beleg | Konto-Vorschlag | Art |"
        )
        zeilen.append("|---|---|---:|---|---|---|---|---|")
        for z in ergebnis["entwuerfe"]:
            beleg = z["beleg_id"] or z["ergebnis"]
            zeilen.append(
                f"| {z['datum_abgang']} | {kurz(z['lieferant'], 24)} | "
                f"{_betrag(z['betrag_abgang'])} | {_betrag(z['pdf_betrag'])} {z['waehrung']} | "
                f"{kurz(str(z['nummer']), 24)} | {beleg} | {kurz(str(z['konto_vorschlag']), 24)} | "
                f"{z['art']} |"
            )
    else:
        zeilen.append("\n(keine)\n")

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
        zeilen.append("\n| Datum Beleg | Lieferant | Betrag | Nummer | Beleg | PDF |")
        zeilen.append("|---|---|---:|---|---|---|")
        for z in ergebnis["pdf_ohne_abgang"]:
            beleg = z["beleg_id"] or z["ergebnis"]
            zeilen.append(
                f"| {z['datum_beleg']} | {kurz(z['lieferant'], 24)} | "
                f"{_betrag(z['pdf_betrag'])} {z['waehrung']} | {kurz(str(z['nummer']), 24)} | "
                f"{beleg} | {kurz(str(z['pdf']), 50)} |"
            )
    else:
        zeilen.append("\n(keine)\n")

    return "\n".join(zeilen) + "\n"


def journal_schreiben(kennzahlen: dict, pfad: Path) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    zeile = dict(kennzahlen)
    zeile["zeit"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    with pfad.open("a", encoding="utf-8") as f:
        f.write(json.dumps(zeile, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mandant_argument(p)
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
