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


# ── Reihenfolge der beiden Schritte ──────────────────────────────────────────


def test_should_protect_underscores_before_markdown_consumes_them():
    """Markdown verbraucht `___` in mehreren Kontexten — deshalb Schritt 1 zuerst.

    Gemessen (2026-08-04), nicht vermutet:

    ======================================  ====================================
    Kontext                                  Markdown macht daraus
    ======================================  ====================================
    ``______`` allein auf einer Zeile        ``<hr />``
    zwei Laeufe in derselben Zeile           ``<strong><em>`` — Lauf zerrissen
    in einer Tabellenzelle                   bleibt erhalten
    ======================================  ====================================

    Die ersten beiden reichen: die erste Fassung suchte erst im fertigen HTML
    und erzeugte in den echten Dokumenten 15 statt 56 Feldern.
    """
    import markdown as _md

    def zu_html(text: str) -> str:
        return _md.Markdown(extensions=["tables"]).convert(text)

    # 1) allein auf einer Zeile -> horizontale Linie, Lauf ist weg
    assert "<hr" in zu_html("______\n")
    # 2) zwei Laeufe in einer Zeile -> Hervorhebung, Lauf ist zerrissen
    assert "<strong>" in zu_html("Datum: ______ Uhrzeit: ______\n")

    # Mit vorgeschaltetem Schutz ueberleben beide und werden zu Feldern.
    for quelle in ("______\n", "Datum: ______ Uhrzeit: ______\n"):
        html = pf.html_mit_formularfeldern(
            zu_html(pf.markdown_mit_platzhaltern(quelle))
        )
        assert "<input" in html, f"kein Feld aus {quelle!r}"
    assert (
        pf.html_mit_formularfeldern(
            zu_html(pf.markdown_mit_platzhaltern("Datum: ______ Uhrzeit: ______\n"))
        ).count("<input")
        == 2
    )


def test_should_carry_the_intended_width_through_the_placeholder():
    """Die Feldbreite muss Schritt 1 ueberleben, sonst sind alle Felder gleich breit."""
    schmal = pf.html_mit_formularfeldern(pf.markdown_mit_platzhaltern("___"))
    breit = pf.html_mit_formularfeldern(pf.markdown_mit_platzhaltern("_" * 40))

    def em(h: str) -> float:
        return float(h.split("width:")[1].split("em")[0])

    assert em(breit) > em(schmal)


def test_should_leave_fenced_code_untouched_in_the_markdown_step():
    quelle = "```\ntabelle_____spalte\n```\n"
    assert pf.markdown_mit_platzhaltern(quelle) == quelle


# ── Anklickbarkeit: das Widget-Rechteck ──────────────────────────────────────
#
# Die Uebersetzung nach oben erzeugt Felder, die ein PDF-Parser findet — das
# belegt aber NICHT, dass ein Mensch sie anklicken kann. WeasyPrint 68.1
# schreibt jedes Rechteck als [x1, y_oben, x2, y_unten] (verdrehte y-Achse) und
# nimmt die Content-Box: bei einem Kaestchen mit Rahmen bleiben davon rund
# 3,6 pt Trefferflaeche. Beides zusammen liess einen realen Erfassungsbogen am
# 2026-08-26 mit 77 gefundenen, aber toten Feldern dastehen.


def test_should_turn_a_flipped_rectangle_the_right_way_round():
    """y1 > y2 ist die Schreibweise, die Viewer als leeres Rechteck lesen."""
    assert pf._rect_nachbessern([10.0, 100.0, 20.0, 90.0], "/Tx")[1] < 100.0
    x1, y1, x2, y2 = pf._rect_nachbessern([10.0, 100.0, 20.0, 90.0], "/Tx")
    assert x1 < x2 and y1 < y2


def test_should_grow_a_tiny_checkbox_to_a_clickable_size():
    x1, y1, x2, y2 = pf._rect_nachbessern([10.0, 103.6, 13.6, 100.0], "/Btn")
    assert x2 - x1 >= pf.MIN_KASTEN_PT
    assert y2 - y1 >= pf.MIN_KASTEN_PT


def test_should_keep_the_checkbox_centred_while_growing_it():
    """Waechst der Kasten einseitig, rutscht er von seinem gezeichneten Rahmen weg."""
    alt = [10.0, 100.0, 13.6, 103.6]
    neu = pf._rect_nachbessern(alt, "/Btn")
    assert (neu[0] + neu[2]) / 2 == pytest.approx((alt[0] + alt[2]) / 2)
    assert (neu[1] + neu[3]) / 2 == pytest.approx((alt[1] + alt[3]) / 2)


def test_should_not_shrink_a_checkbox_that_is_already_big_enough():
    alt = [10.0, 100.0, 30.0, 120.0]
    assert pf._rect_nachbessern(alt, "/Btn") == alt


def test_should_grow_a_text_field_upwards_only():
    """Die Grundlinie ist der gezeichnete Unterstrich — sie darf nicht wandern."""
    neu = pf._rect_nachbessern([10.0, 100.0, 80.0, 102.0], "/Tx")
    assert neu[1] == 100.0
    assert neu[3] - neu[1] >= pf.MIN_TEXT_HOEHE_PT


def test_should_leave_a_wide_text_field_alone():
    alt = [10.0, 100.0, 80.0, 115.0]
    assert pf._rect_nachbessern(alt, "/Tx") == alt


# ── Querformat ───────────────────────────────────────────────────────────────


def test_should_only_switch_to_landscape_when_asked():
    assert pf.querformat_gewuenscht({"querformat": "true"})
    assert pf.querformat_gewuenscht({"querformat": ["ja"]})
    assert pf.querformat_gewuenscht({"landscape": "yes"})
    assert not pf.querformat_gewuenscht({})
    assert not pf.querformat_gewuenscht({"querformat": "nein"})


# ── End-to-End: sind die Felder im fertigen PDF wirklich erreichbar? ─────────


@pytest.mark.slow
def test_should_produce_clickable_rectangles_in_the_finished_pdf(tmp_path):
    """Die eigentliche Zusage des Bogens: man kann hineinklicken.

    Geprueft am fertigen PDF, nicht am HTML — die Ursache lag unterhalb von CSS.
    """
    pdf = _erzeuge(
        tmp_path,
        "forms: true\n\n# Probe\n\n| Nr. | umgesetzt | seit |\n|---|---|---|\n"
        "| 1 | ☐ | ______ |\n",
    )
    reader = _pdf_reader()(str(pdf))
    rechtecke = [
        (a.get_object().get("/FT"), [float(v) for v in a.get_object()["/Rect"]])
        for seite in reader.pages
        for a in seite.get("/Annots") or []
        if a.get_object().get("/Subtype") == "/Widget"
    ]
    assert rechtecke, "keine Widgets im PDF"
    for feldtyp, (x1, y1, x2, y2) in rechtecke:
        assert x2 > x1 and y2 > y1, f"{feldtyp}: verdrehtes Rechteck"
        mindest = pf.MIN_KASTEN_PT if feldtyp == "/Btn" else pf.MIN_TEXT_HOEHE_PT
        assert y2 - y1 >= mindest - 0.01, f"{feldtyp}: nur {y2 - y1:.1f} pt hoch"


@pytest.mark.slow
def test_should_keep_the_page_upright_without_the_landscape_opt_in(tmp_path):
    """Negativprobe — sonst belegt der Querformat-Pfad nur, dass IRGENDWAS kippt."""
    hoch = _pdf_reader()(str(_erzeuge(tmp_path, "# Probe\n\nText.\n"))).pages[0]
    breite = float(hoch.mediabox.width)
    quer_dir = tmp_path / "quer"
    quer_dir.mkdir()
    quer = _pdf_reader()(
        str(_erzeuge(quer_dir, "querformat: true\n\n# Probe\n\nText.\n"))
    ).pages[0]
    assert float(quer.mediabox.width) > breite
