"""Deckblatt-Meta: Zeilen wie ``**Auftraggeber:** Firma`` lesen und aus dem Fliesstext nehmen.

Bewusst importfrei (nur ``re``): print_agent zieht litellm/weasyprint, die in der
CI-Test-Umgebung nicht installiert sind. Die Deckblatt-Logik ist reine Textarbeit
und wird deshalb hier getestet, ohne den Renderer zu laden (#2621).

Invariante (Tests in ``tests/test_deckblatt_meta.py``): was ``strip_meta_prefix_lines``
aus dem Text entfernt, muss ``extract_meta`` aufs Deckblatt uebernehmen — sonst ist die
Angabe weg.
"""

from __future__ import annotations

import re

_INLINE_PATTERNS = {
    "stand": r"\*\*Stand:\*\*\s*([^|\n]+)",
    "zielgruppe": r"\*\*Zielgruppe:\*\*\s*([^\n]+)",
    "angebot_nr": r"\*\*Angebot Nr\.:\*\*\s*([^\n]+)",
    "datum": r"\*\*Datum:\*\*\s*([^\n]+)",
    "gueltig_bis": r"\*\*Gültig bis:\*\*\s*([^\n]+)",
    # Beide Schreibweisen: "**Auftraggeber:** Firma" und "**Auftraggeber**\n Firma".
    # Nur die zweite war abgedeckt — die erste wurde vom Deckblatt-Filter aus dem
    # Fliesstext entfernt UND nicht aufs Deckblatt uebernommen, der Mandantenname
    # verschwand also ganz (gefunden 2026-08-26 an einer Reihe Erfassungsboegen).
    "auftraggeber": r"\*\*Auftraggeber:?\*\*:?\s*\n*[ \t]*(.+)",
    # Generic document fields (used by konzept/briefing templates)
    "doc_type": r"\*\*(?:Typ|Doc[- ]?Type|Dokumenttyp):\*\*\s*([^\n]+)",
    "status": r"\*\*Status:\*\*\s*([^\n]+)",
    "adressat": r"\*\*Adressat:\*\*\s*([^\n]+)",
    "zielentscheidung": r"\*\*Zielentscheidung:\*\*\s*([^\n]+)",
    "autor": r"\*\*Autor(?:in)?:\*\*\s*([^\n]+)",
    "anlass": r"\*\*Anlass:\*\*\s*([^\n]+)",
}


def extract_meta(md_text: str, fm: dict | None = None) -> dict:
    """Merge markdown.meta frontmatter (primary) with inline-bold regex (fallback)."""
    meta = {}
    # 1. Frontmatter from markdown.meta extension (key already lowercase)
    if fm:
        for k, v in fm.items():
            meta[k] = " ".join(v) if isinstance(v, list) else v
    # 2. Regex fallback for keys not found in frontmatter
    for key, pattern in _INLINE_PATTERNS.items():
        if key not in meta:
            m = re.search(pattern, md_text)
            if m:
                meta[key] = m.group(1).strip()
    return meta


# Bold-prefix patterns that should NOT appear in the body — they're already in the cover.
_META_PREFIX_RE = re.compile(
    r"^\*\*(?:Stand|Status|Datum|Adressat|Zielentscheidung|Anlass|Autor(?:in)?|"
    r"Typ|Dokumenttyp|Doc[- ]?Type|Zielgruppe|Angebot Nr\.|Gültig bis|Auftraggeber|"
    r"Begleitdokument):\*\*",
    re.IGNORECASE,
)


DEFAULT_VERTRAULICHKEIT = "Vertraulich – nur für Konsortium MEiKI"
DEFAULT_ZIELGRUPPE = "Lenkungskreis, IT-Leitung, Entscheider LRA"


def meta_rows(meta: dict, design: dict, stem: str) -> list:
    """Zeilen der Deckblatt-Meta-Tabelle je ``meta_template`` des Designs."""
    template = design.get("meta_template", "meiki")
    if template == "db":
        felder = ("status", "datum", "adressat", "anlass")
        beschriftung = {
            "status": "Status",
            "datum": "Datum",
            "adressat": "Adressat",
            "anlass": "Anlass",
        }
        return [(beschriftung[f], meta[f]) for f in felder if meta.get(f)]
    if template == "iil":
        rows = []
        if meta.get("angebot_nr"):
            rows.append(("Angebot-Nr.", meta["angebot_nr"]))
        for feld, label in (
            ("status", "Status"),
            ("datum", "Datum"),
            ("gueltig_bis", "Gültig bis"),
            ("adressat", "Adressat"),
            ("anlass", "Anlass"),
            ("zielentscheidung", "Zielentscheidung"),
            ("auftraggeber", "Auftraggeber"),
        ):
            if meta.get(feld):
                rows.append((label, meta[feld]))
        # Die Auftragnehmer-Zeile gehoert zum Angebots-Kontext. Ein IIL-Dokument, in dem
        # IIL selbst der Auftraggeber ist (z.B. ein Pruefbogen an eigene Dienstleister),
        # bekaeme sonst eine sachlich falsche Rollenzuweisung auf dem Deckblatt.
        if meta.get("angebot_nr") or meta.get("gueltig_bis") or meta.get("auftraggeber"):
            rows.append(("Auftragnehmer", "IIL GmbH · Achim Dehnert · info@iil.gmbh"))
        return rows
    # meiki default
    stand = meta.get("stand", "")
    if not stand:
        return []
    rows = [
        ("Dokument-ID", stem.upper().replace("_", "-")),
        ("Konsortium", "LRA Traunstein · LRA Günzburg · TH Rosenheim · HNU Neu-Ulm"),
        ("Stand", stand),
        ("Projektlaufzeit", "März 2026 – März 2027"),
    ]
    # Ein Profil fuer Dokumente an Dritte setzt meta_vertraulichkeit auf "" — sonst
    # liest der Empfaenger auf Seite 1, dass er das Dokument nicht haben duerfte.
    vertraulichkeit = design.get("meta_vertraulichkeit", DEFAULT_VERTRAULICHKEIT)
    if vertraulichkeit:
        rows.append(("Vertraulichkeit", vertraulichkeit))
    return rows


def cover_zielgruppe(meta: dict, design: dict) -> str:
    """Zielgruppen-Zeile des Deckblatts: Dokument schlaegt Profil schlaegt Vorgabe."""
    return meta.get("zielgruppe") or design.get("zielgruppe_default", DEFAULT_ZIELGRUPPE)


def strip_meta_prefix_lines(md_text: str) -> str:
    """Remove lines like '**Status:** Konzept' from MD body — they're already on the cover.

    Keeps everything else intact, including the trailing blank-line separator
    so that downstream markdown parsing doesn't merge paragraphs.
    """
    out_lines = []
    for line in md_text.splitlines():
        if _META_PREFIX_RE.match(line.strip()):
            continue
        out_lines.append(line)
    return "\n".join(out_lines)
