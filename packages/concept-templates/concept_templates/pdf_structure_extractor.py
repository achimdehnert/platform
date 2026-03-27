"""PDF structure extraction — convert extracted text to ConceptTemplate.

Analyses extracted PDF text to detect:
- Numbered section headings (with TOC artifact cleanup)
- Content type per section (free text vs. table)
- Table column headers

Usage:
    from concept_templates.pdf_structure_extractor import (
        extract_structure_from_text,
    )

    template = extract_structure_from_text(
        text="1. Einleitung\\n...",
        name="My Template",
        scope="explosionsschutz",
    )
"""

from __future__ import annotations

import logging
import re

from concept_templates.schemas import (
    ConceptTemplate,
    FieldType,
    TemplateField,
    TemplateSection,
)

logger = logging.getLogger(__name__)


def clean_toc_title(title: str) -> str:
    """Remove TOC dots and page numbers from a section title.

    Examples:
        'Anlagenbeschreibung ............. 7' → 'Anlagenbeschreibung'
        'Gefährdungsbeurteilung nach § 6 GefStoffV .... 8' → '...'
    """
    # Remove dot leaders + optional page number
    title = re.sub(r"\s*[.·…]{2,}\s*\d*\s*$", "", title)
    # Remove trailing standalone page number
    title = re.sub(r"\s+\d{1,4}\s*$", "", title)
    return title.strip()


def detect_table_columns(content: str) -> list[str] | None:
    """Detect table structure in section content.

    Looks for tab-separated or multi-space-separated columnar data.
    Returns column headers if a table is detected, else None.
    """
    lines = content.strip().split("\n")
    if len(lines) < 2:
        return None

    # Heuristic 1: Tab-separated or double-space-separated lines
    structured_lines = [
        line for line in lines
        if "\t" in line or line.count("  ") >= 2
    ]
    if len(structured_lines) >= 2:
        header_line = structured_lines[0]
        cols = _split_columns(header_line)
        if 2 <= len(cols) <= 10:
            return cols

    # Heuristic 2: Consistent multi-column pattern
    col_counts = []
    for line in lines[:10]:
        stripped = line.strip()
        if stripped:
            parts = _split_columns(stripped)
            col_counts.append(len(parts))

    if (
        len(col_counts) >= 3
        and all(cc >= 2 for cc in col_counts[:5])
        and len(set(col_counts[:5])) <= 2
    ):
        cols = _split_columns(lines[0].strip())
        if 2 <= len(cols) <= 10:
            return cols

    return None


def _split_columns(line: str) -> list[str]:
    """Split a line into columns by tab or multi-space."""
    if "\t" in line:
        parts = [c.strip() for c in line.split("\t")]
    else:
        parts = [c.strip() for c in re.split(r"\s{2,}", line)]
    return [p for p in parts if p]


def analyze_section_content(content: str) -> list[TemplateField]:
    """Analyze section content and create appropriate fields.

    Detects:
    - Tables → FieldType.TABLE with column headers
    - Free text → FieldType.TEXTAREA
    - Mix → Free text + table as separate fields
    """
    if not content.strip():
        return [
            TemplateField(
                name="inhalt",
                label="Inhalt",
                field_type=FieldType.TEXTAREA,
            ),
        ]

    fields: list[TemplateField] = []
    table_cols = detect_table_columns(content)

    if table_cols:
        lines = content.strip().split("\n")
        pre_table_lines = []
        table_start_idx = 0

        # Find where the table starts
        for idx, line in enumerate(lines):
            stripped = line.strip()
            parts = _split_columns(stripped)
            if len(parts) >= len(table_cols):
                table_start_idx = idx
                break
            pre_table_lines.append(stripped)

        # Add free-text field if there's text before the table
        pre_text = "\n".join(pre_table_lines).strip()
        if pre_text:
            fields.append(
                TemplateField(
                    name="freitext",
                    label="Freitext",
                    field_type=FieldType.TEXTAREA,
                    default=pre_text[:2000],
                ),
            )

        # Extract table rows (skip header)
        table_lines = lines[table_start_idx:]
        table_data: list[list[str]] = []
        for line in table_lines[1:]:
            stripped = line.strip()
            if not stripped:
                continue
            cells = _split_columns(stripped)
            if cells:
                table_data.append(cells)

        fields.append(
            TemplateField(
                name="tabelle",
                label="Tabelle",
                field_type=FieldType.TABLE,
                columns=table_cols,
                default_rows=table_data[:20] or None,
            ),
        )
    else:
        fields.append(
            TemplateField(
                name="inhalt",
                label="Inhalt",
                field_type=FieldType.TEXTAREA,
                default=content[:3000],
            ),
        )

    return fields


def extract_structure_from_text(
    text: str,
    *,
    name: str = "Aus PDF extrahiert",
    scope: str = "explosionsschutz",
    version: str = "1.0",
) -> ConceptTemplate:
    """Convert extracted PDF text into a ConceptTemplate.

    Detects numbered section headings, cleans TOC artifacts,
    and analyzes each section's content to determine field types
    (textarea, table, or mixed).

    Args:
        text: The extracted PDF text.
        name: Template name.
        scope: Concept scope (e.g. 'explosionsschutz').
        version: Template version string.

    Returns:
        A ConceptTemplate with sections and typed fields.
    """
    sections: list[TemplateSection] = []
    heading_pattern = re.compile(
        r"^(\d+(?:\.\d+)*\.?)\s+(.+)$",
        re.MULTILINE,
    )
    matches = list(heading_pattern.finditer(text))

    if matches:
        for i, m in enumerate(matches):
            num = m.group(1).rstrip(".")
            raw_title = m.group(2).strip()
            title = clean_toc_title(raw_title)

            if not title:
                continue

            section_name = f"section_{num.replace('.', '_')}"

            # Extract content between this heading and the next
            start = m.end()
            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )
            content = text[start:end].strip()

            fields = analyze_section_content(content)

            sections.append(
                TemplateSection(
                    name=section_name,
                    title=f"{num}. {title}",
                    order=i + 1,
                    fields=fields,
                ),
            )
    else:
        # Fallback: entire text as one section
        sections.append(
            TemplateSection(
                name="section_1",
                title="1. Dokumentinhalt",
                order=1,
                fields=[
                    TemplateField(
                        name="inhalt",
                        label="Inhalt",
                        field_type=FieldType.TEXTAREA,
                        default=text[:5000],
                    ),
                ],
            ),
        )

    return ConceptTemplate(
        name=name,
        scope=scope,
        version=version,
        sections=sections,
    )
