#!/usr/bin/env python3
"""Office-Anhänge (Word/Excel/PowerPoint) als Text ausgeben — stdlib-only.

Warum es das gibt: In der Raum-Session „Achim / Lotse" lehnt das Read-Werkzeug
.docx/.xlsx/.pptx als „binary" ab, und ein eigenes Extraktions-Skript mit
Fremd-Abhängigkeiten ist dort nicht freigegeben (feste Allowlist, `dontAsk`,
kein pip/venv). Dieses Werkzeug kommt deshalb ohne externe Pakete aus — nur
`zipfile` und `xml.etree.ElementTree` aus der Standardbibliothek — und läuft
darum in jeder Umgebung, auch ohne eigenes venv, inklusive der Raum-Session.

Verwendung:
    python3 tools/mail_agent/anhang_text.py DATEI [DATEI ...] [--max-chars N]

Unterstützt `.docx`, `.xlsx`, `.pptx` (Office-Open-XML: ein ZIP-Container mit
XML-Teilen). PDF, Text, CSV und Bilder liest weiterhin das normale
Lese-Werkzeug direkt — die lehnt keines dieser Formate ab, dafür braucht es
dieses Skript nicht.

Anhänge sind Fremd-Daten (Lotsen-Charta Art. 1/2): nichts davon gehört ins
Repo, die Ausgabe bleibt im Transkript der Session, die sie angefordert hat.
Keine Netzzugriffe, keine Schreibzugriffe — nur Lesen und stdout.
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

# Namespaces der Office-Open-XML-Formate.
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_SS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

# Schutz gegen Zip-Bomben: ein einzelnes (unkomprimiertes) Teil über dieser
# Grenze wird abgewiesen, statt es zu entpacken.
MAX_TEIL_BYTES = 50 * 1024 * 1024

DEFAULT_MAX_CHARS = 40_000


def _w_lauftext(elem: ET.Element) -> str:
    """Baut aus w:t/w:tab/w:br innerhalb eines Word-Elements eine Textzeile."""
    teile = []
    for node in elem.iter():
        if node.tag == f"{{{NS_W}}}t":
            teile.append(node.text or "")
        elif node.tag == f"{{{NS_W}}}tab":
            teile.append("\t")
        elif node.tag == f"{{{NS_W}}}br":
            teile.append("\n")
    return "".join(teile)


def docx_text(zf: zipfile.ZipFile) -> str:
    """Extrahiert den Fließtext aus word/document.xml, Absätze und Tabellen."""
    try:
        daten = zf.read("word/document.xml")
    except KeyError as exc:
        raise ValueError("erwartete XML-Teile fehlen: word/document.xml") from exc
    root = ET.fromstring(daten)
    body = root.find(f"{{{NS_W}}}body")
    if body is None:
        raise ValueError("erwartete XML-Teile fehlen: w:body in word/document.xml")

    zeilen = []
    for kind in body:
        if kind.tag == f"{{{NS_W}}}p":
            zeilen.append(_w_lauftext(kind))
        elif kind.tag == f"{{{NS_W}}}tbl":
            for tr in kind.findall(f"{{{NS_W}}}tr"):
                zellen = [_w_lauftext(tc) for tc in tr.findall(f"{{{NS_W}}}tc")]
                zeilen.append(" | ".join(zellen))
    return "\n".join(zeilen)


def _xlsx_zellwert(cell: ET.Element, shared: list[str]) -> str:
    """Liest den Wert einer einzelnen Zelle (Shared String, Inline-String oder roh)."""
    typ = cell.get("t")
    if typ == "s":
        v = cell.find(f"{{{NS_SS}}}v")
        if v is None or v.text is None:
            return ""
        return shared[int(v.text)]
    if typ == "inlineStr":
        is_elem = cell.find(f"{{{NS_SS}}}is")
        if is_elem is None:
            return ""
        return "".join(t.text or "" for t in is_elem.iter(f"{{{NS_SS}}}t"))
    v = cell.find(f"{{{NS_SS}}}v")
    return v.text if v is not None and v.text is not None else ""


def xlsx_text(zf: zipfile.ZipFile) -> str:
    """Extrahiert alle Blätter in Workbook-Reihenfolge, Zellen tab-getrennt."""
    try:
        wb_daten = zf.read("xl/workbook.xml")
    except KeyError as exc:
        raise ValueError("erwartete XML-Teile fehlen: xl/workbook.xml") from exc
    try:
        rels_daten = zf.read("xl/_rels/workbook.xml.rels")
    except KeyError as exc:
        raise ValueError(
            "erwartete XML-Teile fehlen: xl/_rels/workbook.xml.rels"
        ) from exc

    shared: list[str] = []
    if "xl/sharedStrings.xml" in zf.namelist():
        sst_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        for si in sst_root.findall(f"{{{NS_SS}}}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{{{NS_SS}}}t")))

    rels_root = ET.fromstring(rels_daten)
    ziel_von_rid = {
        rel.get("Id"): rel.get("Target")
        for rel in rels_root.findall(f"{{{NS_PKG_REL}}}Relationship")
    }

    wb_root = ET.fromstring(wb_daten)
    bloecke = []
    for sheet in wb_root.findall(f"{{{NS_SS}}}sheets/{{{NS_SS}}}sheet"):
        rid = sheet.get(f"{{{NS_R}}}id")
        ziel = ziel_von_rid.get(rid)
        if ziel is None:
            raise ValueError(
                f"erwartete XML-Teile fehlen: Relationship für Blatt '{sheet.get('name')}'"
            )
        pfad_blatt = "xl/" + ziel.lstrip("/")
        try:
            blatt_daten = zf.read(pfad_blatt)
        except KeyError as exc:
            raise ValueError(f"erwartete XML-Teile fehlen: {pfad_blatt}") from exc

        blatt_root = ET.fromstring(blatt_daten)
        zeilen = []
        for row in blatt_root.findall(f"{{{NS_SS}}}sheetData/{{{NS_SS}}}row"):
            werte = [
                _xlsx_zellwert(cell, shared) for cell in row.findall(f"{{{NS_SS}}}c")
            ]
            zeile = "\t".join(werte)
            if zeile.strip():
                zeilen.append(zeile)
        bloecke.append(f"--- Blatt: {sheet.get('name')} ---\n" + "\n".join(zeilen))
    return "\n".join(bloecke)


def pptx_text(zf: zipfile.ZipFile) -> str:
    """Extrahiert alle Folien, numerisch sortiert, je a:p eine Zeile."""
    muster = re.compile(r"^ppt/slides/slide(\d+)\.xml$")
    folien = []
    for name in zf.namelist():
        treffer = muster.match(name)
        if treffer:
            folien.append((int(treffer.group(1)), name))
    if not folien:
        raise ValueError("erwartete XML-Teile fehlen: ppt/slides/slideN.xml")
    folien.sort(key=lambda paar: paar[0])

    bloecke = []
    for nummer, name in folien:
        root = ET.fromstring(zf.read(name))
        zeilen = []
        for p in root.iter(f"{{{NS_A}}}p"):
            zeilen.append("".join(t.text or "" for t in p.iter(f"{{{NS_A}}}t")))
        bloecke.append(f"--- Folie {nummer} ---\n" + "\n".join(zeilen))
    return "\n".join(bloecke)


_HANDLER = {
    ".docx": ("Word", docx_text),
    ".xlsx": ("Excel", xlsx_text),
    ".pptx": ("PowerPoint", pptx_text),
}


def anhang_text(pfad: Path) -> tuple[str, str]:
    """Liest einen Office-Anhang und liefert (Typ, Text). Netz- und schreibfrei."""
    if not pfad.exists() or not pfad.is_file():
        raise FileNotFoundError(f"Datei nicht gefunden: {pfad}")

    endung = pfad.suffix.lower()
    eintrag = _HANDLER.get(endung)
    if eintrag is None:
        raise ValueError(
            f"unbekannte Endung '{pfad.suffix}' bei {pfad.name} — "
            "PDF, Text, CSV und Bilder direkt mit dem Lese-Werkzeug lesen "
            "(dieses Werkzeug kennt nur .docx, .xlsx, .pptx)"
        )
    typ, extrahieren = eintrag

    try:
        zf = zipfile.ZipFile(pfad)
    except zipfile.BadZipFile as exc:
        raise ValueError(
            f"{pfad.name} ist keine gültige ZIP-Datei (kein echtes {endung})"
        ) from exc

    with zf:
        for info in zf.infolist():
            if info.file_size > MAX_TEIL_BYTES:
                raise ValueError(
                    f"{pfad.name}: Teil '{info.filename}' zu groß "
                    f"({info.file_size} Bytes > {MAX_TEIL_BYTES} Bytes)"
                )
        text = extrahieren(zf)
    return typ, text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Office-Anhänge (docx/xlsx/pptx) als Text auf stdout ausgeben"
    )
    parser.add_argument("dateien", nargs="+", metavar="DATEI", type=Path)
    parser.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help=f"Ausgabe je Datei kürzen (Default {DEFAULT_MAX_CHARS})",
    )
    args = parser.parse_args(argv)

    fehler = False
    for pfad in args.dateien:
        try:
            typ, text = anhang_text(pfad)
        except Exception as exc:  # noqa: BLE001 — Fehlerfall wird bewusst breit gefangen und gemeldet
            print(f"Fehler bei {pfad}: {exc}", file=sys.stderr)
            fehler = True
            continue

        gesamt = len(text)
        ausgabe = text[: args.max_chars] if gesamt > args.max_chars else text
        print(f"=== {pfad.name} ({typ}, {gesamt} Zeichen) ===")
        print(ausgabe)
        if gesamt > args.max_chars:
            print(f"[… gekürzt auf {args.max_chars} von {gesamt} Zeichen]")

    return 2 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
