"""Tests für tools/mail_agent/anhang_text.py — Office-Anhänge (docx/xlsx/pptx) als Text.

Alle Fixtures sind minimale, aber gültige ZIP/XML-Konstrukte, in `tmp_path`
selbst gebaut — keine echten Office-Dateien im Repo (Fremd-Daten-Regel gilt
schon für Tests). Kein Netz.
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))

anhang_text_modul = pytest.importorskip("anhang_text")

_SKRIPT = Path(__file__).resolve().parents[1] / "mail_agent" / "anhang_text.py"

NS_W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
NS_SS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
NS_R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
NS_PKG_REL = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
NS_A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
NS_P = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'


def _bauen(pfad: Path, teile: dict[str, str]) -> Path:
    with zipfile.ZipFile(pfad, "w") as zf:
        for name, inhalt in teile.items():
            zf.writestr(name, inhalt)
    return pfad


def _docx(tmp_path: Path) -> Path:
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document {NS_W}>
  <w:body>
    <w:p><w:r><w:t>Erster Absatz</w:t></w:r></w:p>
    <w:p><w:r><w:t>Tab</w:t><w:tab/><w:t>getrennt</w:t></w:r></w:p>
    <w:p><w:r><w:t>Zeile1</w:t><w:br/><w:t>Zeile2</w:t></w:r></w:p>
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>A1</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>B1</w:t></w:r></w:p></w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>A2</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>B2</w:t></w:r></w:p></w:tc>
      </w:tr>
    </w:tbl>
  </w:body>
</w:document>"""
    return _bauen(tmp_path / "test.docx", {"word/document.xml": document_xml})


def _xlsx(tmp_path: Path) -> Path:
    # Rels-Zuordnung ist absichtlich NICHT in Dateinamen-Reihenfolge:
    # Blatt "Erstes" (zuerst im Workbook) zeigt über rId2 auf sheet2.xml,
    # Blatt "Zweites" (zweites im Workbook) über rId1 auf sheet1.xml.
    workbook_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook {NS_SS} {NS_R}>
  <sheets>
    <sheet name="Erstes" sheetId="1" r:id="rId2"/>
    <sheet name="Zweites" sheetId="2" r:id="rId1"/>
  </sheets>
</workbook>"""
    rels_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships {NS_PKG_REL}>
  <Relationship Id="rId1" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Target="worksheets/sheet2.xml"/>
</Relationships>"""
    shared_strings_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sst {NS_SS} count="1" uniqueCount="1"><si><t>Hallo</t></si></sst>"""
    # sheet1.xml wird von "Zweites" benutzt: Shared String + Zahl.
    sheet1_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet {NS_SS}>
  <sheetData>
    <row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1"><v>42</v></c></row>
  </sheetData>
</worksheet>"""
    # sheet2.xml wird von "Erstes" benutzt: Inline-String + eine leere Zeile.
    sheet2_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet {NS_SS}>
  <sheetData>
    <row r="1"><c r="A1" t="inlineStr"><is><t>Inline-Text</t></is></c></row>
    <row r="2"></row>
  </sheetData>
</worksheet>"""
    return _bauen(
        tmp_path / "test.xlsx",
        {
            "xl/workbook.xml": workbook_xml,
            "xl/_rels/workbook.xml.rels": rels_xml,
            "xl/sharedStrings.xml": shared_strings_xml,
            "xl/worksheets/sheet1.xml": sheet1_xml,
            "xl/worksheets/sheet2.xml": sheet2_xml,
        },
    )


def _folie_xml(text: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld {NS_A} {NS_P}>
  <p:cSld><p:spTree><p:sp><p:txBody>
    <a:p><a:r><a:t>{text}</a:t></a:r></a:p>
  </p:txBody></p:sp></p:spTree></p:cSld>
</p:sld>"""


def _pptx(tmp_path: Path) -> Path:
    # Absichtlich unsortiert ins ZIP geschrieben (slide2, slide10, slide1),
    # damit ein Sortieren nach Dateiname (lexikografisch) durchfallen würde.
    return _bauen(
        tmp_path / "test.pptx",
        {
            "ppt/slides/slide2.xml": _folie_xml("Zwei"),
            "ppt/slides/slide10.xml": _folie_xml("Zehn"),
            "ppt/slides/slide1.xml": _folie_xml("Eins"),
        },
    )


class TestDocxText:
    def test_should_render_paragraphs_tab_break_and_table(self, tmp_path):
        pfad = _docx(tmp_path)
        typ, text = anhang_text_modul.anhang_text(pfad)
        assert typ == "Word"
        zeilen = text.split("\n")
        assert "Erster Absatz" in zeilen
        assert "Tab\tgetrennt" in zeilen
        assert "Zeile1" in zeilen and "Zeile2" in zeilen  # w:br -> eigene Zeile
        assert "A1 | B1" in zeilen
        assert "A2 | B2" in zeilen


class TestXlsxText:
    def test_should_map_sheets_via_rels_not_filename_order(self, tmp_path):
        pfad = _xlsx(tmp_path)
        typ, text = anhang_text_modul.anhang_text(pfad)
        assert typ == "Excel"
        # "Erstes" steht im Workbook vor "Zweites" — und muss darum auch
        # vor "Zweites" in der Ausgabe stehen, obwohl es aus sheet2.xml kommt.
        assert text.index("Blatt: Erstes") < text.index("Blatt: Zweites")
        assert "Inline-Text" in text  # aus sheet2.xml, via rId2
        assert "Hallo\t42" in text  # aus sheet1.xml, via rId1 (Shared String + Zahl)

    def test_should_skip_empty_rows(self, tmp_path):
        pfad = _xlsx(tmp_path)
        _, text = anhang_text_modul.anhang_text(pfad)
        zeilen = [z for z in text.split("\n") if z.strip() == ""]
        assert zeilen == []  # keine Leerzeile für die leere row r="2"


class TestPptxText:
    def test_should_sort_slides_numerically_not_lexically(self, tmp_path):
        pfad = _pptx(tmp_path)
        typ, text = anhang_text_modul.anhang_text(pfad)
        assert typ == "PowerPoint"
        assert text.index("Folie 1 ") < text.index("Folie 2 ") < text.index("Folie 10 ")
        assert text.index("Eins") < text.index("Zwei") < text.index("Zehn")


class TestCli:
    def test_should_truncate_with_marker_when_max_chars_exceeded(self, tmp_path):
        pfad = _docx(tmp_path)
        ergebnis = subprocess.run(
            [sys.executable, str(_SKRIPT), str(pfad), "--max-chars", "10"],
            capture_output=True,
            text=True,
        )
        assert ergebnis.returncode == 0
        assert "gekürzt auf 10 von" in ergebnis.stdout
        assert f"=== {pfad.name} (Word, " in ergebnis.stdout

    def test_should_exit_2_and_hint_on_unknown_extension(self, tmp_path):
        pfad = tmp_path / "rechnung.pdf"
        pfad.write_bytes(b"%PDF-1.4 nicht wirklich, nur Endungstest")
        ergebnis = subprocess.run(
            [sys.executable, str(_SKRIPT), str(pfad)],
            capture_output=True,
            text=True,
        )
        assert ergebnis.returncode == 2
        assert "Lese-Werkzeug" in ergebnis.stderr

    def test_should_exit_2_on_non_zip_with_docx_extension(self, tmp_path):
        pfad = tmp_path / "kaputt.docx"
        pfad.write_bytes(b"das ist kein ZIP")
        ergebnis = subprocess.run(
            [sys.executable, str(_SKRIPT), str(pfad)],
            capture_output=True,
            text=True,
        )
        assert ergebnis.returncode == 2
        assert "ZIP" in ergebnis.stderr

    def test_should_process_good_file_and_still_exit_2_when_other_arg_fails(
        self, tmp_path
    ):
        gut = _docx(tmp_path)
        fehlt = tmp_path / "existiert-nicht.docx"
        ergebnis = subprocess.run(
            [sys.executable, str(_SKRIPT), str(gut), str(fehlt)],
            capture_output=True,
            text=True,
        )
        assert ergebnis.returncode == 2
        assert "Erster Absatz" in ergebnis.stdout
        assert "existiert-nicht.docx" in ergebnis.stderr
