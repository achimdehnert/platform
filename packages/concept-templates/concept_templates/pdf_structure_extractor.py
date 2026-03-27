"""PDF structure extraction — convert extracted text to ConceptTemplate.

Analyses extracted PDF text to detect:
- Numbered section headings (with TOC artifact cleanup)
- Content type per section (free text vs. table)
- Table column headers

Two-pass approach:
1. Identify candidate headings via regex
2. Validate each candidate (filter table rows, PLZ, measurements)
3. Parse content blocks between validated headings
4. Analyze each block for field types (text, table, mixed)

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

# Max top-level section number for a real document heading
_MAX_SECTION_NUM = 30


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


def _is_valid_heading(
    num: str,
    title: str,
    full_line: str,
) -> bool:
    """Validate whether a regex match is a real section heading.

    Filters out false positives:
    - Table row numbers (e.g. "1  Im Raum  Keine  ...")
    - Measurements (e.g. "1000. m3/h über Öffnungen")
    - Postal codes (e.g. "89077. Ulm")
    - Very short or non-alpha titles
    """
    # Check top-level number is reasonable (≤30)
    top_num_str = num.split(".")[0]
    try:
        top_num = int(top_num_str)
    except ValueError:
        return False
    if top_num > _MAX_SECTION_NUM:
        return False

    # Title must have at least 2 alpha characters
    alpha_chars = sum(1 for c in title if c.isalpha())
    if alpha_chars < 2:
        return False

    # Reject if the full line looks like a table row
    # (3+ columns separated by tabs or double-spaces)
    cols = _split_columns(full_line)
    if len(cols) >= 3:
        return False

    # Reject if title starts with units/measurements
    if re.match(
        r"^(m[²³]?/[hs]|kg|cm|mm|l/|bar|°C|kW)\b",
        title,
        re.IGNORECASE,
    ):
        return False

    # Reject if title looks like a PLZ (5-digit number)
    if re.match(r"^\d{5}\b", num + title):
        return False

    return True


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


def _filter_sequential_headings(
    candidates: list[tuple[re.Match, str, str]],
) -> list[tuple[re.Match, str, str]]:
    """Filter heading candidates by sequential monotonicity.

    Real document headings increase monotonically (1, 2, 3, 4, 5).
    Table row numbers restart from 1 inside a section.
    If we see a top-level number that goes backward (e.g. 4 → 1),
    reject it as a table row — unless it's a subsection (e.g. 4.1).
    """
    result = []
    max_top = 0

    for m, num, title in candidates:
        parts = num.split(".")
        top = int(parts[0])

        # Top-level heading: must not go backward
        if len(parts) == 1 and top < max_top:
            logger.debug(
                "Rejected heading '%s %s' — number %d < max %d",
                num, title, top, max_top,
            )
            continue

        if len(parts) == 1:
            max_top = max(max_top, top)

        result.append((m, num, title))

    return result


def extract_structure_from_text(
    text: str,
    *,
    name: str = "Aus PDF extrahiert",
    scope: str = "explosionsschutz",
    version: str = "1.0",
) -> ConceptTemplate:
    """Convert extracted PDF text into a ConceptTemplate.

    Three-pass approach:
    1. Find all candidate headings via regex (numbered + lettered)
    2. Validate each candidate (filter false positives)
    3. Filter by sequential monotonicity (reject table row resets)
    4. Parse content blocks and analyze field types

    Args:
        text: The extracted PDF text.
        name: Template name.
        scope: Concept scope (e.g. 'explosionsschutz').
        version: Template version string.

    Returns:
        A ConceptTemplate with sections and typed fields.
    """
    sections: list[TemplateSection] = []

    # Pattern 1: Numeric headings (1, 2, 3.1, etc.)
    num_pattern = re.compile(
        r"^(\d+(?:\.\d+)*\.?)\s+(.+)$",
        re.MULTILINE,
    )
    # Pattern 2: Letter headings (A., B., C., etc.)
    letter_pattern = re.compile(
        r"^([A-Z])\.\s+(.+)$",
        re.MULTILINE,
    )

    # Pass 1a: Collect numeric candidates
    num_candidates = []
    for m in num_pattern.finditer(text):
        num = m.group(1).rstrip(".")
        raw_title = m.group(2).strip()
        title = clean_toc_title(raw_title)
        full_line = m.group(0)

        if not title:
            continue
        if not _is_valid_heading(num, title, full_line):
            continue

        num_candidates.append((m, num, title))

    # Pass 2: Sequential monotonicity filter
    num_candidates = _filter_sequential_headings(num_candidates)

    # Pass 1b: Collect letter candidates
    letter_candidates = []
    for m in letter_pattern.finditer(text):
        letter = m.group(1)
        raw_title = m.group(2).strip()
        title = clean_toc_title(raw_title)
        if not title:
            continue
        # Letter headings use letter as section identifier
        letter_candidates.append((m, letter, title))

    # Merge candidates sorted by position in text
    all_valid = sorted(
        num_candidates + letter_candidates,
        key=lambda x: x[0].start(),
    )

    if all_valid:
        for i, (m, num, title) in enumerate(all_valid):
            # Build section name
            if num.isalpha():
                section_name = f"section_{num.lower()}"
                display_title = f"{num}. {title}"
            else:
                section_name = f"section_{num.replace('.', '_')}"
                display_title = f"{num}. {title}"

            # Content between this heading and the next
            start = m.end()
            if i + 1 < len(all_valid):
                end = all_valid[i + 1][0].start()
            else:
                end = len(text)
            content = text[start:end].strip()

            fields = analyze_section_content(content)

            sections.append(
                TemplateSection(
                    name=section_name,
                    title=display_title,
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
