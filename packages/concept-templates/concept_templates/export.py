"""Export concept templates to various formats."""

from __future__ import annotations

from concept_templates.schemas import ConceptTemplate, TemplateSection


def to_dict(template: ConceptTemplate) -> dict:
    """Export template to a plain dictionary."""
    return template.model_dump(mode="python")


def to_json(template: ConceptTemplate, *, indent: int = 2) -> str:
    """Export template to a JSON string."""
    return template.model_dump_json(indent=indent)


def to_markdown(template: ConceptTemplate) -> str:
    """Export template to a Markdown document outline.

    Produces a hierarchical Markdown document with headings
    for each section and field descriptions as bullet lists.
    """
    lines: list[str] = []
    lines.append(f"# {template.name}")
    lines.append("")

    if template.framework:
        lines.append(
            f"**Framework**: {template.framework} "
            f"v{template.framework_version}"
        )
    lines.append(f"**Fachbereich**: {template.scope}")
    if template.is_master:
        lines.append("**Typ**: Master-Template")
    lines.append(f"**Version**: {template.version}")
    lines.append("")

    for section in template.sections:
        _render_section(section, level=2, lines=lines)

    return "\n".join(lines)


def _render_section(
    section: TemplateSection,
    level: int,
    lines: list[str],
) -> None:
    """Render a single section recursively."""
    prefix = "#" * level
    required = " *(Pflicht)*" if section.required else ""
    lines.append(f"{prefix} {section.title}{required}")

    if section.description:
        lines.append("")
        lines.append(section.description)

    if section.fields:
        lines.append("")
        for field in section.fields:
            req = " **[Pflicht]**" if field.required else ""
            line = f"- **{field.label}**{req}"
            if field.help_text:
                line += f" — {field.help_text}"
            if field.choices:
                line += f" (Auswahl: {', '.join(field.choices)})"
            if field.default:
                line += f" (Standard: {field.default})"
            lines.append(line)

    lines.append("")

    for sub in section.subsections:
        _render_section(sub, level=level + 1, lines=lines)
