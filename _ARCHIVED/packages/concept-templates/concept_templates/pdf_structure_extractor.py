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


# ─── TOC Detection ─────────────────────────────────────────────


_TOC_HEADER_PATTERN = re.compile(
    r"^(Inhaltsverzeichnis|Inhalt|Table of Contents)\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# TOC entry: "A. Title ......... 4" or "3.1 Title ... 12"
_TOC_ENTRY_NUM = re.compile(
    r"^(\d+(?:\.\d+)*\.?)\s+(.+)$",
    re.MULTILINE,
)
_TOC_ENTRY_LETTER = re.compile(
    r"^([A-Z])\.\s+(.+)$",
    re.MULTILINE,
)


def _detect_toc(
    text: str,
) -> list[tuple[str, str]] | None:
    """Detect Table of Contents and return ordered list of (id, title).

    Returns list of (identifier, clean_title) tuples in TOC order,
    or None if no TOC detected.

    Identifier is either a number string ("3.1") or a letter ("A").
    """
    toc_match = _TOC_HEADER_PATTERN.search(text)
    if not toc_match:
        return None

    # TOC usually ends at the first real content heading or blank block
    toc_start = toc_match.end()

    # Find where TOC ends: look for a large gap or a repeated heading
    # Heuristic: TOC entries have dot leaders or page numbers
    # TOC ends when we hit content without dot leaders for 3+ lines
    lines = text[toc_start:].split("\n")
    toc_lines = []
    non_toc_streak = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            non_toc_streak += 1
            if non_toc_streak >= 3:
                break
            continue

        # Is this a TOC-style line? (has dots/numbers or matches heading)
        is_toc_line = bool(
            re.search(r"[.·…]{2,}", stripped)
            or re.match(r"^[A-Z]\.\s+\S", stripped)
            or re.match(r"^\d+(?:\.\d+)*\.?\s+\S", stripped)
        )
        if is_toc_line:
            toc_lines.append(stripped)
            non_toc_streak = 0
        else:
            non_toc_streak += 1
            if non_toc_streak >= 3:
                break

    if len(toc_lines) < 2:
        return None

    toc_text = "\n".join(toc_lines)
    entries: list[tuple[str, str, int]] = []  # (id, title, pos)

    # Parse numeric entries
    for m in _TOC_ENTRY_NUM.finditer(toc_text):
        num = m.group(1).rstrip(".")
        title = clean_toc_title(m.group(2).strip())
        if title:
            entries.append((num, title, m.start()))

    # Parse letter entries
    for m in _TOC_ENTRY_LETTER.finditer(toc_text):
        letter = m.group(1)
        title = clean_toc_title(m.group(2).strip())
        if title:
            entries.append((letter, title, m.start()))

    # Sort by position in TOC text (preserves original order)
    entries.sort(key=lambda x: x[2])

    if len(entries) < 2:
        return None

    logger.debug("Detected TOC with %d entries", len(entries))
    return [(eid, etitle) for eid, etitle, _ in entries]


def _find_body_heading(
    text: str,
    entry_id: str,
    entry_title: str,
    search_start: int = 0,
) -> re.Match | None:
    """Find a TOC entry's heading in the body text.

    Searches for the heading pattern matching the TOC entry after
    the TOC section. Matches by ID + title start (fuzzy: first 20 chars).
    """
    title_prefix = re.escape(entry_title[:20])

    if entry_id.isalpha():
        # Letter heading: "A. Title..."
        pattern = re.compile(
            rf"^{re.escape(entry_id)}\.\s+{title_prefix}",
            re.MULTILINE,
        )
    else:
        # Numeric heading: "3.1 Title..." or "3.1. Title..."
        pattern = re.compile(
            rf"^{re.escape(entry_id)}\.?\s+{title_prefix}",
            re.MULTILINE,
        )

    return pattern.search(text, search_start)


def _extract_with_toc(
    text: str,
    toc_entries: list[tuple[str, str]],
) -> list[TemplateSection]:
    """Extract sections using TOC as the definitive structure.

    For each TOC entry, find the corresponding heading in the body
    text and extract content between it and the next heading.
    """
    sections: list[TemplateSection] = []

    # Find all body heading positions
    body_positions: list[tuple[int, int, str, str]] = []
    # (start, end_of_heading_line, id, title)

    # Start searching after TOC (skip first ~30% of text as TOC area)
    toc_end_estimate = len(text) // 5
    search_from = toc_end_estimate

    for entry_id, entry_title in toc_entries:
        m = _find_body_heading(
            text, entry_id, entry_title, search_from,
        )
        if m:
            # Find end of this heading line
            line_end = text.find("\n", m.start())
            if line_end == -1:
                line_end = len(text)
            body_positions.append(
                (m.start(), line_end, entry_id, entry_title),
            )

    if not body_positions:
        logger.debug("No body headings found for TOC entries")
        return []

    # Sort by position in text
    body_positions.sort(key=lambda x: x[0])

    # Build sections in TOC order (not body order)
    # Map: id -> body position
    pos_map = {}
    for start, end, eid, etitle in body_positions:
        if eid not in pos_map:
            pos_map[eid] = (start, end, etitle)

    for order, (entry_id, entry_title) in enumerate(
        toc_entries, start=1,
    ):
        if entry_id not in pos_map:
            # TOC entry not found in body — create empty section
            if entry_id.isalpha():
                sname = f"section_{entry_id.lower()}"
            else:
                sname = f"section_{entry_id.replace('.', '_')}"

            sections.append(
                TemplateSection(
                    name=sname,
                    title=f"{entry_id}. {entry_title}",
                    order=order,
                    fields=[
                        TemplateField(
                            name="inhalt",
                            label="Inhalt",
                            field_type=FieldType.TEXTAREA,
                        ),
                    ],
                ),
            )
            continue

        hstart, hend, _ = pos_map[entry_id]

        # Find next heading after this one (by body position)
        next_start = len(text)
        for other_start, _, _, _ in body_positions:
            if other_start > hstart:
                next_start = other_start
                break

        content = text[hend:next_start].strip()

        if entry_id.isalpha():
            sname = f"section_{entry_id.lower()}"
        else:
            sname = f"section_{entry_id.replace('.', '_')}"

        fields = analyze_section_content(content)

        sections.append(
            TemplateSection(
                name=sname,
                title=f"{entry_id}. {entry_title}",
                order=order,
                fields=fields,
            ),
        )

    return sections


# ─── Fallback Extraction (no TOC) ──────────────────────────────


def _extract_without_toc(
    text: str,
) -> list[TemplateSection]:
    """Extract sections without TOC — heading detection + filtering."""
    # Pattern 1: Numeric headings
    num_pattern = re.compile(
        r"^(\d+(?:\.\d+)*\.?)\s+(.+)$",
        re.MULTILINE,
    )
    # Pattern 2: Letter headings
    letter_pattern = re.compile(
        r"^([A-Z])\.\s+(.+)$",
        re.MULTILINE,
    )

    # Collect numeric candidates with validation
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

    # Sequential monotonicity filter
    num_candidates = _filter_sequential_headings(num_candidates)

    # Collect letter candidates
    letter_candidates = []
    for m in letter_pattern.finditer(text):
        letter = m.group(1)
        raw_title = m.group(2).strip()
        title = clean_toc_title(raw_title)
        if not title:
            continue
        letter_candidates.append((m, letter, title))

    # Merge sorted by position
    all_valid = sorted(
        num_candidates + letter_candidates,
        key=lambda x: x[0].start(),
    )

    sections: list[TemplateSection] = []
    if all_valid:
        for i, (m, num, title) in enumerate(all_valid):
            if num.isalpha():
                sname = f"section_{num.lower()}"
            else:
                sname = f"section_{num.replace('.', '_')}"

            start = m.end()
            end = (
                all_valid[i + 1][0].start()
                if i + 1 < len(all_valid)
                else len(text)
            )
            content = text[start:end].strip()
            fields = analyze_section_content(content)

            sections.append(
                TemplateSection(
                    name=sname,
                    title=f"{num}. {title}",
                    order=i + 1,
                    fields=fields,
                ),
            )

    return sections


# ─── Main Entry Point ──────────────────────────────────────────


def extract_structure_from_text(
    text: str,
    *,
    name: str = "Aus PDF extrahiert",
    scope: str = "explosionsschutz",
    version: str = "1.0",
) -> ConceptTemplate:
    """Convert extracted PDF text into a ConceptTemplate.

    Strategy:
    1. Detect TOC (Inhaltsverzeichnis) — if present, use it as
       the definitive structure and map body content to TOC entries.
    2. If no TOC, fall back to heading detection with validation
       and sequential monotonicity filter.

    Args:
        text: The extracted PDF text.
        name: Template name.
        scope: Concept scope (e.g. 'explosionsschutz').
        version: Template version string.

    Returns:
        A ConceptTemplate with sections and typed fields.
    """
    # Strategy 1: TOC-first
    toc_entries = _detect_toc(text)
    if toc_entries:
        logger.info(
            "TOC detected with %d entries — using TOC-first",
            len(toc_entries),
        )
        sections = _extract_with_toc(text, toc_entries)
        if sections:
            return ConceptTemplate(
                name=name,
                scope=scope,
                version=version,
                sections=sections,
            )

    # Strategy 2: No TOC — heading detection with filters
    sections = _extract_without_toc(text)
    if sections:
        return ConceptTemplate(
            name=name,
            scope=scope,
            version=version,
            sections=sections,
        )

    # Fallback: entire text as one section
    return ConceptTemplate(
        name=name,
        scope=scope,
        version=version,
        sections=[
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
        ],
    )
