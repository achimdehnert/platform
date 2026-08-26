"""Ausfuellbare PDFs — aus gewoehnlichem Markdown, ohne neue Syntax.

Checklisten, Erfassungsboegen und Aktualisierungslisten werden gedruckt, damit
jemand sie ausfuellt. Bisher entstand daraus ein totes Bild: eine Kaestchen-Zeile
und ein Unterstrich-Lauf sehen im PDF wie ein Formular aus, sind aber keines —
man muss ausdrucken, mit der Hand ausfuellen und wieder einscannen.

WeasyPrint kann seit Version 61 HTML-Formularelemente als echte PDF-Formularfelder
schreiben (`write_pdf(..., pdf_forms=True)`). Dieses Modul schlaegt die Bruecke:
es uebersetzt die **ohnehin uebliche** Markdown-Schreibweise in solche Elemente.

Bewusst KEINE neue Syntax, denn eine neue Syntax muesste gelernt und in jedem
Bestandsdokument nachgezogen werden:

===========================  ==========================================
im Markdown                  im PDF
===========================  ==========================================
``☐`` (U+2610)               ankreuzbare Checkbox
``___`` (3+ Unterstriche)    beschreibbares Textfeld, Breite nach Laenge
===========================  ==========================================

Beides ist genau das, was Autoren heute schon schreiben, um ein Formular
anzudeuten. Aus der Andeutung wird damit die Sache selbst.

**Opt-in je Dokument** ueber das Frontmatter-Feld ``forms: true``. Ohne das Feld
aendert sich nichts — Bestandsdokumente drucken unveraendert, und ein Fliesstext,
in dem zufaellig ein Unterstrich-Lauf steht, wird nicht stillschweigend zum
Eingabefeld.

Nicht angefasst werden Code-Bloecke: dort sind Unterstriche Inhalt (Python-Namen,
ASCII-Zeichnungen) und kein Ausfuellfeld.

**Zwei Schritte, und die Reihenfolge ist wesentlich.** Unterstrich-Laeufe muessen
VOR der Markdown-Konvertierung gesichert werden, weil Markdown sie sonst selbst
verbraucht: ``___`` allein auf einer Zeile ist eine horizontale Linie,
``___text___`` ist Hervorhebung. Wer erst das fertige HTML durchsucht, findet
die Laeufe nicht mehr — genau daran ist die erste Fassung gescheitert
(2026-08-04: 15 statt 56 Feldern, alle Textfelder verschluckt).

    md = markdown_mit_platzhaltern(md_text)   # 1. VOR der Konvertierung
    html = ... markdown ...
    html = html_mit_formularfeldern(html)     # 2. NACH der Konvertierung

Das Kaestchen-Zeichen ist davon nicht betroffen — es ueberlebt die Konvertierung
unveraendert und wird erst in Schritt 2 ersetzt.

**Dritter Schritt, nach dem Schreiben: die Felder anklickbar machen.** WeasyPrint
(gemessen an 68.1) schreibt jedes Widget-Rechteck als ``[x1, y_oben, x2, y_unten]``,
also mit vertauschter y-Reihenfolge, und nimmt dafuer die Content-Box des Inputs —
bei einem Kaestchen mit Rahmen bleiben davon rund 3,6 pt Trefferflaeche, waehrend
der gezeichnete Kasten 10 pt gross ist. Beides zusammen liess die Felder in
gaengigen Viewern tot erscheinen (gemessen 2026-08-26 an einem realen
Erfassungsbogen: 77 Felder, keines anklickbar). ``formularfelder_nachbessern()`` normalisiert die Rechtecke und zieht
jedes Kaestchen auf eine Mindest-Trefferflaeche — am fertigen PDF, weil die Ursache
in WeasyPrint liegt und nicht ueber CSS erreichbar ist.

    pfad = HTML(...).write_pdf(..., pdf_forms=True)
    formularfelder_nachbessern(pfad)           # 3. NACH dem Schreiben

**Querformat je Dokument** ueber ``querformat: true`` im Frontmatter — breite
Erfassungstabellen (Massnahme + drei Kreuze + Datum + Begruendung) brauchen die
Seitenbreite, und eine lose CSS-Datei neben dem Markdown wuerde beim naechsten
Erzeugen vergessen.
"""

from __future__ import annotations

import re

CHECKBOX = "☐"  # ☐ BALLOT BOX

# Unterstrich-Lauf ab 3 Zeichen. Kuerzere Laeufe kommen in Bezeichnern vor
# (``__init__``, ``a__b``) und bleiben deshalb unangetastet.
_FILL_RE = re.compile(r"_{3,}")

# <pre>…</pre> und <code>…</code> am Stueck ausschneiden, damit die Ersetzung
# sie ueberspringt. Nicht-gierig und ueber Zeilengrenzen.
_PROTECTED_RE = re.compile(r"<(pre|code)\b.*?</\1>", re.DOTALL | re.IGNORECASE)

# Breite eines Textfeldes: die Unterstrich-Zahl ist die Absicht des Autors
# ("hier ist viel Platz noetig"), also wird sie uebernommen statt normiert.
_EM_PER_UNDERSCORE = 0.55
_MIN_WIDTH_EM = 4.0
_MAX_WIDTH_EM = 34.0


def formulare_gewuenscht(meta: dict) -> bool:
    """``forms: true`` im Frontmatter? Tolerant gegen Schreibweisen."""
    wert = meta.get("forms")
    if isinstance(wert, list):  # python-markdown `meta` liefert Listen
        wert = wert[0] if wert else ""
    return str(wert).strip().lower() in {"true", "ja", "yes", "1", "on"}


def querformat_gewuenscht(meta: dict) -> bool:
    """``querformat: true`` im Frontmatter? Gleiche Toleranz wie ``forms``."""
    wert = meta.get("querformat", meta.get("landscape"))
    if isinstance(wert, list):
        wert = wert[0] if wert else ""
    return str(wert).strip().lower() in {"true", "ja", "yes", "1", "on"}


def _feldbreite_em(laenge: int) -> float:
    return max(_MIN_WIDTH_EM, min(_MAX_WIDTH_EM, laenge * _EM_PER_UNDERSCORE))


# Platzhalter fuer Textfelder. Bewusst rein alphanumerisch: Markdown laesst so
# etwas unveraendert stehen, waehrend Sonderzeichen-Marker je nach Extension
# escaped oder umgebrochen werden koennten.
_PLATZHALTER = "xFORMFELDx{laenge}x"
_PLATZHALTER_RE = re.compile(r"xFORMFELDx(\d+)x")

# Fenced-Code und Inline-Code im MARKDOWN schuetzen (im HTML greift spaeter
# _PROTECTED_RE, aber da ist es fuer die Unterstriche schon zu spaet).
_MD_PROTECTED_RE = re.compile(r"```.*?```|~~~.*?~~~|`[^`\n]+`", re.DOTALL)


def markdown_mit_platzhaltern(md_text: str) -> str:
    """Schritt 1 — Unterstrich-Laeufe sichern, BEVOR Markdown sie verbraucht.

    Die Laenge des Laufs wird im Platzhalter mitgefuehrt, damit Schritt 2 die
    vom Autor gemeinte Feldbreite noch kennt.
    """
    geschuetzt: list[str] = []

    def _ausschneiden(treffer: re.Match) -> str:
        geschuetzt.append(treffer.group(0))
        return f"\x00MDSCHUTZ{len(geschuetzt) - 1}\x00"

    rest = _MD_PROTECTED_RE.sub(_ausschneiden, md_text)
    rest = _FILL_RE.sub(lambda t: _PLATZHALTER.format(laenge=len(t.group(0))), rest)
    for i, stueck in enumerate(geschuetzt):
        rest = rest.replace(f"\x00MDSCHUTZ{i}\x00", stueck)
    return rest


def html_mit_formularfeldern(html: str) -> str:
    """Ersetzt Checkbox-Zeichen und Unterstrich-Laeufe durch Eingabeelemente.

    Die Feldnamen werden fortlaufend vergeben (``f1``, ``f2``, …) und sind damit
    bei gleichem Eingabe-Markdown stabil — wichtig, weil ein Dokument neu
    erzeugt wird, wenn sich der Text aendert, und ausgefuellte Werte sonst
    unvorhersehbar wandern wuerden.
    """
    geschuetzt: list[str] = []

    def _ausschneiden(treffer: re.Match) -> str:
        geschuetzt.append(treffer.group(0))
        return f"\x00SCHUTZ{len(geschuetzt) - 1}\x00"

    rest = _PROTECTED_RE.sub(_ausschneiden, html)

    zaehler = {"n": 0}

    def _naechster_name() -> str:
        zaehler["n"] += 1
        return f"f{zaehler['n']}"

    def _checkbox(treffer: re.Match) -> str:
        # Kaestchen und seine Beschriftung zusammenhalten. Ohne das bricht eine
        # schmale Tabellenspalte zwischen beiden um, und das Kaestchen steht
        # ueber statt neben seinem Wort — in einer Spalte mit drei Optionen
        # ("ja / nein / entfaellt") wird der Bogen dadurch unlesbar.
        feld = f'<input type="checkbox" name="{_naechster_name()}" class="pdf-formularfeld-box">'
        wort = treffer.group(1) or ""
        if not wort:
            return feld
        return f'<span class="pdf-formularfeld-gruppe">{feld}{wort}</span> '

    # Das Wort direkt nach dem Kaestchen mitnehmen (bis Leerzeichen oder Tag).
    rest = re.sub(re.escape(CHECKBOX) + r"[ \t]*([^\s<]+)?", _checkbox, rest)

    def _textfeld(treffer: re.Match) -> str:
        # Breite UND Mindestbreite: in einer Tabellenzelle wird die Breite auf
        # 100 % der Zelle gesetzt (siehe FORMULAR_CSS) — ohne Mindestbreite
        # schrumpft die Spalte dann auf ihre Ueberschrift, und aus "______"
        # fuer ein Datum wurde ein 10 pt breites Feld.
        breite = _feldbreite_em(int(treffer.group(1)))
        return (
            f'<input type="text" name="{_naechster_name()}" '
            f'class="pdf-formularfeld-text" '
            f'style="width:{breite:.1f}em; min-width:{breite:.1f}em">'
        )

    # Platzhalter aus Schritt 1 …
    rest = _PLATZHALTER_RE.sub(_textfeld, rest)
    # … und rohe Laeufe, falls jemand html_mit_formularfeldern allein benutzt.
    rest = _FILL_RE.sub(
        lambda t: _textfeld(re.match(r"(\d+)", str(len(t.group(0))))), rest
    )

    for i, stueck in enumerate(geschuetzt):
        rest = rest.replace(f"\x00SCHUTZ{i}\x00", stueck)
    return rest


FORMULAR_CSS = """
/* Ausfuellbare Felder — sie sollen im Ausdruck wie ein Formular aussehen und
   am Bildschirm anklickbar sein. Rahmenlos mit Grundlinie statt Kasten: das
   bleibt lesbar, wenn jemand das PDF doch ausdruckt und handschriftlich
   ausfuellt. */
input.pdf-formularfeld-text {
  border: none;
  border-bottom: 0.6pt solid #9aa4b2;
  background: transparent;
  font-family: inherit;
  font-size: inherit;
  line-height: 1.2;
  min-height: 1.35em;
  padding: 0 2pt;
  vertical-align: baseline;
}
/* Kaestchen + Beschriftung sind eine Einheit und duerfen nicht getrennt
   umbrochen werden. */
span.pdf-formularfeld-gruppe {
  white-space: nowrap;
  display: inline-block;
  margin-right: 0.5em;
}
input.pdf-formularfeld-box {
  width: 1.15em;
  height: 1.15em;
  border: 0.7pt solid #52606d;
  background: transparent;
  vertical-align: -0.15em;
  margin-right: 0.25em;
}
/* In Tabellenzellen fuellt das Textfeld die Zelle — dort ist die Zelle der
   Platzhalter, nicht die Unterstrich-Laenge. */
td input.pdf-formularfeld-text { width: 100% !important; }
/* Steht ein Kaestchen allein in seiner Zelle, ist die Spaltenueberschrift seine
   Beschriftung ("umgesetzt" / "offen" / "entfaellt"). Dann gehoert es unter die
   Ueberschrift und nicht an den linken Zellenrand — sonst kreuzt man daneben. */
td > input.pdf-formularfeld-box:only-child { display: block; margin: 0 auto; }
"""

QUERFORMAT_CSS = """
@page { size: A4 landscape; }
"""


# Mindest-Trefferflaeche eines Kaestchens in pt. 10 pt entspricht dem gezeichneten
# Kasten (1.15em bei 9 pt Tabellenschrift); kleiner trifft man mit der Maus nicht.
MIN_KASTEN_PT = 10.0
# Mindesthoehe eines Textfeldes: eine Zeile 9-pt-Schrift mit etwas Luft.
MIN_TEXT_HOEHE_PT = 11.0


def _rect_nachbessern(rect: list[float], feldtyp: str) -> list[float]:
    """Normalisiert ein Widget-Rechteck und sichert die Mindest-Trefferflaeche.

    Reine Funktion ueber ``[x1, y1, x2, y2]`` in PDF-Punkten, damit sie ohne
    PDF-Bibliothek testbar ist. Ein Kaestchen wird um seinen Mittelpunkt auf
    ein Quadrat von mindestens ``MIN_KASTEN_PT`` gezogen; ein Textfeld waechst
    nach oben bis ``MIN_TEXT_HOEHE_PT`` — die Grundlinie, auf der WeasyPrint
    den Unterstrich zeichnet, bleibt, wo sie ist.
    """
    x1, y1, x2, y2 = rect
    x1, x2 = sorted((x1, x2))
    y1, y2 = sorted((y1, y2))
    if feldtyp == "/Btn":
        seite = max(x2 - x1, y2 - y1, MIN_KASTEN_PT)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        x1, x2 = mx - seite / 2, mx + seite / 2
        y1, y2 = my - seite / 2, my + seite / 2
    elif feldtyp == "/Tx" and (y2 - y1) < MIN_TEXT_HOEHE_PT:
        y2 = y1 + MIN_TEXT_HOEHE_PT
    return [round(v, 3) for v in (x1, y1, x2, y2)]


def formularfelder_nachbessern(pdf_pfad) -> int:
    """Schritt 3 — Widget-Rechtecke am fertigen PDF normalisieren.

    Gibt die Zahl der geaenderten Felder zurueck. Ohne PDF-Bibliothek bleibt
    das PDF unveraendert, und das wird gesagt — ein stilles Ueberspringen saehe
    aus wie Erfolg.
    """
    try:
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import ArrayObject, FloatObject, NameObject
    except ImportError:
        try:
            from PyPDF2 import PdfReader, PdfWriter
            from PyPDF2.generic import ArrayObject, FloatObject, NameObject
        except ImportError:
            print(
                "⚠️  pypdf fehlt — Formularfelder bleiben, wie WeasyPrint sie "
                "schreibt (in vielen Viewern nicht anklickbar)"
            )
            return 0

    writer = PdfWriter(clone_from=PdfReader(str(pdf_pfad)))
    geaendert = 0
    for seite in writer.pages:
        for ref in seite.get("/Annots") or []:
            annot = ref.get_object()
            if annot.get("/Subtype") != "/Widget":
                continue
            feldtyp = annot.get("/FT")
            if feldtyp is None and "/Parent" in annot:  # Radio-Kinder erben den Typ
                feldtyp = annot["/Parent"].get_object().get("/FT")
            alt = [float(v) for v in annot["/Rect"]]
            neu = _rect_nachbessern(alt, str(feldtyp or ""))
            if neu != alt:
                annot[NameObject("/Rect")] = ArrayObject(FloatObject(v) for v in neu)
                geaendert += 1
    with open(pdf_pfad, "wb") as ausgabe:
        writer.write(ausgabe)
    return geaendert
