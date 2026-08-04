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

    def _checkbox(_treffer: re.Match) -> str:
        return f'<input type="checkbox" name="{_naechster_name()}" class="pdf-formularfeld-box">'

    rest = re.sub(re.escape(CHECKBOX), _checkbox, rest)

    def _textfeld(treffer: re.Match) -> str:
        breite = _feldbreite_em(int(treffer.group(1)))
        return (
            f'<input type="text" name="{_naechster_name()}" '
            f'class="pdf-formularfeld-text" style="width:{breite:.1f}em">'
        )

    # Platzhalter aus Schritt 1 …
    rest = _PLATZHALTER_RE.sub(_textfeld, rest)
    # … und rohe Laeufe, falls jemand html_mit_formularfeldern allein benutzt.
    rest = _FILL_RE.sub(lambda t: _textfeld(re.match(r"(\d+)", str(len(t.group(0))))), rest)

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
  padding: 0 2pt;
  vertical-align: baseline;
}
input.pdf-formularfeld-box {
  width: 1.05em;
  height: 1.05em;
  border: 0.7pt solid #52606d;
  background: transparent;
  vertical-align: -0.15em;
  margin-right: 0.25em;
}
/* In Tabellenzellen fuellt das Textfeld die Zelle — dort ist die Zelle der
   Platzhalter, nicht die Unterstrich-Laenge. */
td input.pdf-formularfeld-text { width: 100% !important; }
"""
