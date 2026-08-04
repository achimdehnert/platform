"""Tests fuer die Uebersetzung Markdown → PDF-Formularfelder (pdf_forms.py).

Der Kern ist eine Ersetzung im fertigen HTML. Zwei Dinge muessen dabei
zuverlaessig sein, sonst richtet die Erweiterung mehr Schaden an als Nutzen:

1. Sie greift **nur** bei ``forms: true`` — sonst wuerde jeder Fliesstext mit
   einem Unterstrich-Lauf oder einem Kaestchen-Zeichen unbemerkt zum Formular.
2. Sie fasst **keinen Code** an — dort sind Unterstriche Inhalt.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

_MODUL = Path(__file__).resolve().parents[1] / "pdf_forms.py"
_spec = importlib.util.spec_from_file_location("pdf_forms", _MODUL)
pf = importlib.util.module_from_spec(_spec)
sys.modules["pdf_forms"] = pf
_spec.loader.exec_module(pf)


# ── Opt-in ───────────────────────────────────────────────────────────────────


def test_should_only_build_forms_when_the_document_asks_for_it():
    assert pf.formulare_gewuenscht({"forms": "true"})
    assert pf.formulare_gewuenscht(
        {"forms": ["true"]}
    )  # python-markdown liefert Listen
    assert pf.formulare_gewuenscht({"forms": "ja"})
    assert not pf.formulare_gewuenscht({})
    assert not pf.formulare_gewuenscht({"forms": "false"})
    assert not pf.formulare_gewuenscht({"forms": ""})


# ── Ersetzung ────────────────────────────────────────────────────────────────


def test_should_turn_the_ballot_box_into_a_checkbox():
    html = pf.html_mit_formularfeldern("<p>☐ erledigt</p>")
    assert 'type="checkbox"' in html
    assert pf.CHECKBOX not in html


def test_should_turn_an_underscore_run_into_a_text_field():
    html = pf.html_mit_formularfeldern("<p>Name: ______</p>")
    assert 'type="text"' in html
    assert "___" not in html


def test_should_not_touch_short_underscore_sequences():
    """`__init__` ist ein Bezeichner, kein Ausfuellfeld."""
    html = pf.html_mit_formularfeldern("<p>siehe __init__ der Klasse</p>")
    assert "<input" not in html
    assert "__init__" in html


def test_should_scale_the_field_width_with_the_authors_intent():
    """Ein laengerer Lauf heisst 'hier ist mehr Platz noetig'."""
    schmal = pf.html_mit_formularfeldern("<p>___</p>")
    breit = pf.html_mit_formularfeldern("<p>" + "_" * 40 + "</p>")

    def em(h: str) -> float:
        return float(h.split("width:")[1].split("em")[0])

    assert em(breit) > em(schmal)


def test_should_cap_the_field_width():
    """Ein sehr langer Lauf darf die Seite nicht sprengen."""
    html = pf.html_mit_formularfeldern("<p>" + "_" * 500 + "</p>")
    assert float(html.split("width:")[1].split("em")[0]) <= pf._MAX_WIDTH_EM


# ── Schutzzonen ──────────────────────────────────────────────────────────────


def test_should_leave_code_blocks_alone():
    """In `<pre>` stehen ASCII-Zeichnungen und Bezeichner — kein Formular."""
    quelle = "<pre><code>tabelle_____spalte\n☐ nicht anklickbar</code></pre>"
    assert pf.html_mit_formularfeldern(quelle) == quelle


def test_should_leave_inline_code_alone():
    quelle = "<p>Feld <code>wert_____</code> im Schema</p>"
    assert "<input" not in pf.html_mit_formularfeldern(quelle)


def test_should_still_convert_outside_a_protected_block():
    """Beisskraft: der Schutz darf nicht das ganze Dokument stilllegen."""
    html = pf.html_mit_formularfeldern(
        "<pre><code>a_____b</code></pre><p>Name: _____</p>"
    )
    assert html.count("<input") == 1
    assert "a_____b" in html


# ── Feldnamen ────────────────────────────────────────────────────────────────


def test_should_name_fields_deterministically():
    """Gleiche Eingabe → gleiche Namen; sonst wandern ausgefuellte Werte."""
    quelle = "<p>☐ eins ___ zwei ☐ drei</p>"
    assert pf.html_mit_formularfeldern(quelle) == pf.html_mit_formularfeldern(quelle)


def test_should_give_every_field_its_own_name():
    """Doppelte Namen wuerden im PDF denselben Wert teilen."""
    html = pf.html_mit_formularfeldern("<p>☐ a ☐ b ___ c</p>")
    namen = [t.split('"')[0] for t in html.split('name="')[1:]]
    assert len(namen) == 3
    assert len(set(namen)) == 3


# ── End-to-End: erzeugt der Agent ein WIRKLICH ausfuellbares PDF? ────────────
#
# Diese Pruefung muss ueber einen PDF-Parser laufen, NICHT ueber eine Bytesuche
# im PDF. WeasyPrint komprimiert die Objekt-Streams, deshalb steht `/AcroForm`
# dort nicht im Klartext — ein `grep` liefert zuverlaessig 0 Treffer, auch wenn
# die Felder vorhanden sind. Genau diese Fehlmessung hat bei der Entwicklung
# dieser Erweiterung zu der falschen Schlussfolgerung gefuehrt, `pdf_forms`
# wirke nicht (2026-08-04).

_AGENT = Path(__file__).resolve().parents[1] / "print_agent.py"


def _pdf_reader():
    """PdfReader aus pypdf ODER PyPDF2 — beide sind im Bestand anzutreffen.

    Ein Skip waere hier gefaehrlich: er sieht gruen aus und belegt nichts. Nur
    wenn wirklich KEIN Parser da ist, wird uebersprungen — und dann sichtbar.
    """
    for modul in ("pypdf", "PyPDF2"):
        try:
            return __import__(modul, fromlist=["PdfReader"]).PdfReader
        except ImportError:
            continue
    pytest.skip("weder pypdf noch PyPDF2 vorhanden — Pruefung nicht belegbar")


def _felder(pdf_pfad: Path) -> dict:
    return _pdf_reader()(str(pdf_pfad)).get_fields() or {}


def _erzeuge(tmp_path: Path, markdown_text: str) -> Path:
    quelle = tmp_path / "probe.md"
    quelle.write_text(markdown_text, encoding="utf-8")
    subprocess.run(
        [
            "python3",
            str(_AGENT),
            str(quelle),
            str(tmp_path),
            "--design",
            "iil",
            "--no-enrich",
        ],
        check=True,
        capture_output=True,
    )
    return tmp_path / "probe.pdf"


@pytest.mark.slow
def test_should_produce_a_pdf_with_real_form_fields(tmp_path):
    pdf = _erzeuge(
        tmp_path,
        "forms: true\n\n# Probe\n\n| Feld | Eintrag |\n|---|---|\n"
        "| Name | ______ |\n| Erledigt | ☐ ja ☐ nein |\n",
    )
    felder = _felder(pdf)

    assert len(felder) == 3, f"erwartet 3 Felder, gefunden {sorted(felder)}"
    typen = sorted(v.get("/FT") for v in felder.values())
    assert typen == ["/Btn", "/Btn", "/Tx"]


@pytest.mark.slow
def test_should_produce_a_plain_pdf_without_the_opt_in(tmp_path):
    """Negativprobe — ohne `forms: true` bleibt es ein totes Bild.

    Ohne sie belegt der Test oben nur, dass IRGENDWAS Felder erzeugt, nicht
    dass die Opt-in-Schranke wirkt.
    """
    pdf = _erzeuge(
        tmp_path, "# Probe\n\n| Feld | Eintrag |\n|---|---|\n| Name | ______ |\n"
    )

    assert _felder(pdf) == {}
