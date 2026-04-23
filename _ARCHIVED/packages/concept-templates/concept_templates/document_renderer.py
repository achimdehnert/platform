"""Document generation from filled concept templates (ADR-147 Phase E).

Renders filled template values into HTML and optionally PDF (via weasyprint).
Designed to be consumer-agnostic — works with any ConceptTemplate + values dict.

Usage:
    from concept_templates.document_renderer import render_html, render_pdf

    html = render_html(template, values, title="Brandschutzkonzept Rathaus")
    pdf_bytes = render_pdf(template, values, title="Brandschutzkonzept Rathaus")
"""

from __future__ import annotations

import logging
from datetime import datetime

from concept_templates.schemas import ConceptTemplate

logger = logging.getLogger(__name__)

DEFAULT_CSS = """
body { font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #1a1a1a; }
h1 { font-size: 24px; border-bottom: 2px solid #6d28d9; padding-bottom: 8px; color: #1e1b4b; }
h2 { font-size: 18px; margin-top: 28px; color: #4c1d95; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }
h3 { font-size: 15px; margin-top: 20px; color: #6d28d9; }
.meta { font-size: 12px; color: #6b7280; margin-bottom: 24px; }
.field { margin-bottom: 12px; }
.field-label { font-weight: 600; font-size: 13px; color: #374151; }
.field-value { font-size: 14px; margin-top: 2px; padding: 4px 0; }
.field-value.empty { color: #9ca3af; font-style: italic; }
.footer { margin-top: 40px; border-top: 1px solid #e5e7eb; padding-top: 8px; font-size: 11px; color: #9ca3af; }
@page { margin: 2cm; }
@page { @bottom-right { content: "Seite " counter(page); font-size: 10px; color: #9ca3af; } }
"""


def render_html(
    template: ConceptTemplate,
    values: dict[str, dict[str, str]],
    title: str = "",
    css: str = "",
    include_empty: bool = True,
) -> str:
    """Render a filled template to HTML.

    Args:
        template: The ConceptTemplate schema.
        values: Nested dict {section_name: {field_name: value}}.
        title: Document title (defaults to template.name).
        css: Custom CSS (defaults to DEFAULT_CSS).
        include_empty: Show fields with no value.

    Returns:
        Complete HTML document as string.
    """
    doc_title = title or template.name
    style = css or DEFAULT_CSS
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    parts: list[str] = [
        "<!DOCTYPE html>",
        "<html lang='de'>",
        "<head>",
        f"<meta charset='utf-8'><title>{_esc(doc_title)}</title>",
        f"<style>{style}</style>",
        "</head>",
        "<body>",
        f"<h1>{_esc(doc_title)}</h1>",
        "<div class='meta'>",
        f"Fachbereich: {_esc(template.scope)} &middot; ",
        f"Framework: {_esc(template.framework or '—')} &middot; ",
        f"Version: {_esc(template.version)} &middot; ",
        f"Erstellt: {now}",
        "</div>",
    ]

    for section in template.sections:
        _render_section(section, values, parts, level=2, include_empty=include_empty)

    parts.append(
        f"<div class='footer'>Generiert aus Template &laquo;{_esc(template.name)}&raquo; "
        f"am {now}</div>"
    )
    parts.extend(["</body>", "</html>"])

    return "\n".join(parts)


def render_pdf(
    template: ConceptTemplate,
    values: dict[str, dict[str, str]],
    title: str = "",
    css: str = "",
    include_empty: bool = False,
) -> bytes:
    """Render a filled template to PDF bytes via weasyprint.

    Requires the [pdf] extra or weasyprint installed separately.

    Args:
        template: The ConceptTemplate schema.
        values: Nested dict {section_name: {field_name: value}}.
        title: Document title.
        css: Custom CSS.
        include_empty: Show fields with no value.

    Returns:
        PDF as bytes.
    """
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise ImportError(
            "weasyprint is required for PDF generation. "
            "Install with: pip install iil-concept-templates[pdf] "
            "or: pip install weasyprint"
        ) from exc

    html_str = render_html(
        template, values, title=title, css=css, include_empty=include_empty,
    )
    return HTML(string=html_str).write_pdf()


def _render_section(
    section,
    values: dict[str, dict[str, str]],
    parts: list[str],
    level: int = 2,
    include_empty: bool = True,
) -> None:
    """Recursively render a section and its subsections."""
    tag = f"h{min(level, 4)}"
    section_values = values.get(section.name, {})

    parts.append(f"<{tag}>{_esc(section.title)}</{tag}>")

    if section.description:
        parts.append(f"<p style='color:#6b7280;font-size:13px;'>{_esc(section.description)}</p>")

    for field in section.fields:
        val = section_values.get(field.name, "")
        if not val and not include_empty:
            continue

        css_class = "field-value" if val else "field-value empty"
        display_val = val or "(nicht ausgefüllt)"

        parts.append("<div class='field'>")
        parts.append(f"<div class='field-label'>{_esc(field.label)}</div>")
        parts.append(f"<div class='{css_class}'>{_esc(display_val)}</div>")
        parts.append("</div>")

    for subsection in section.subsections:
        _render_section(subsection, values, parts, level + 1, include_empty)


def _esc(text: str) -> str:
    """Basic HTML escaping."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
