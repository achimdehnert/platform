"""Dynamic Django form generation from ConceptTemplate schemas (ADR-147 Phase E).

Converts template sections + fields into Django Form classes at runtime.
Supports LLM-prefill hints for AI-assisted form filling.

Usage:
    from concept_templates.contrib.django.form_generator import build_template_form

    FormClass = build_template_form(concept_template)
    form = FormClass(initial=existing_values)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django import forms

if TYPE_CHECKING:
    from concept_templates.schemas import ConceptTemplate, TemplateField, TemplateSection

logger = logging.getLogger(__name__)

FIELD_TYPE_MAP = {
    "text": forms.CharField,
    "textarea": forms.CharField,
    "number": forms.DecimalField,
    "date": forms.DateField,
    "choice": forms.ChoiceField,
    "boolean": forms.BooleanField,
    "file": forms.FileField,
}

WIDGET_MAP = {
    "textarea": forms.Textarea,
    "date": forms.DateInput,
}


def _make_form_field(field: TemplateField) -> forms.Field:
    """Convert a TemplateField to a Django form field."""
    field_class = FIELD_TYPE_MAP.get(field.field_type, forms.CharField)
    kwargs: dict = {
        "required": field.required,
        "label": field.label,
        "help_text": field.help_text,
    }

    if field.default is not None:
        kwargs["initial"] = field.default

    # Widget overrides
    widget_class = WIDGET_MAP.get(field.field_type)
    if widget_class:
        if field.field_type == "textarea":
            kwargs["widget"] = widget_class(attrs={"rows": 4})
        elif field.field_type == "date":
            kwargs["widget"] = widget_class(attrs={"type": "date"})

    # Choice field options
    if field.field_type == "choice" and field.choices:
        kwargs["choices"] = [("", "---")] + [
            (c, c) for c in field.choices
        ]

    # Boolean: never required (unchecked = False is valid)
    if field.field_type == "boolean":
        kwargs["required"] = False

    return field_class(**kwargs)


def _section_field_key(section: TemplateSection, field: TemplateField) -> str:
    """Generate a unique form field key: section_name__field_name."""
    return f"{section.name}__{field.name}"


def build_template_form(
    template: ConceptTemplate,
    base_class: type[forms.Form] = forms.Form,
) -> type[forms.Form]:
    """Build a Django Form class from a ConceptTemplate.

    Each template field becomes a form field with key: section_name__field_name.

    Args:
        template: The ConceptTemplate schema to generate from.
        base_class: Optional base form class for customization.

    Returns:
        A Form class (not instance) with all template fields.
    """
    form_fields: dict[str, forms.Field] = {}
    field_meta: dict[str, dict] = {}

    for section in template.sections:
        _add_section_fields(section, form_fields, field_meta)

    # Attach metadata as class attribute for template rendering
    attrs = {**form_fields, "_field_meta": field_meta}
    return type(f"{template.name}Form", (base_class,), attrs)


def _add_section_fields(
    section: TemplateSection,
    form_fields: dict,
    field_meta: dict,
    parent_prefix: str = "",
) -> None:
    """Recursively add fields from a section and its subsections."""
    for field in section.fields:
        key = _section_field_key(section, field)
        form_fields[key] = _make_form_field(field)
        field_meta[key] = {
            "section_name": section.name,
            "section_title": section.title,
            "section_order": section.order,
            "field_name": field.name,
            "field_type": field.field_type,
            "llm_hint": field.llm_hint,
            "llm_prefill": field.llm_prefill,
        }

    for subsection in section.subsections:
        _add_section_fields(subsection, form_fields, field_meta)


def get_sections_with_fields(form: forms.Form) -> list[dict]:
    """Group form fields by section for template rendering.

    Returns a list of dicts:
    [
        {
            "name": "standort",
            "title": "Standort",
            "order": 1,
            "fields": [
                {
                    "key": "standort__adresse",
                    "bound_field": <BoundField>,
                    "llm_hint": "...",
                    "llm_prefill": True,
                },
            ],
        },
    ]
    """
    meta = getattr(form.__class__, "_field_meta", {})
    sections: dict[str, dict] = {}

    for key, _bound_field in form.fields.items():
        info = meta.get(key, {})
        section_name = info.get("section_name", "unknown")

        if section_name not in sections:
            sections[section_name] = {
                "name": section_name,
                "title": info.get("section_title", section_name),
                "order": info.get("section_order", 99),
                "fields": [],
            }

        sections[section_name]["fields"].append({
            "key": key,
            "bound_field": form[key],
            "field_type": info.get("field_type", "text"),
            "llm_hint": info.get("llm_hint", ""),
            "llm_prefill": info.get("llm_prefill", False),
        })

    return sorted(sections.values(), key=lambda s: s["order"])


def extract_values(form: forms.Form) -> dict[str, dict[str, str]]:
    """Extract filled values from a submitted form into nested dict.

    Returns: {section_name: {field_name: value}}
    """
    if not form.is_valid():
        raise ValueError("Form has validation errors.")

    meta = getattr(form.__class__, "_field_meta", {})
    result: dict[str, dict] = {}

    for key, value in form.cleaned_data.items():
        info = meta.get(key, {})
        section = info.get("section_name", "unknown")
        field = info.get("field_name", key)

        if section not in result:
            result[section] = {}

        # Serialize dates and other non-string types
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        elif value is None:
            value = ""
        else:
            value = str(value)

        result[section][field] = value

    return result
