"""Tests for concept_templates.document_renderer."""

from __future__ import annotations

import pytest

from concept_templates.document_renderer import _esc, render_html, render_pdf
from concept_templates.schemas import (
    ConceptScope,
    ConceptTemplate,
    FieldType,
    TemplateField,
    TemplateSection,
)


@pytest.fixture
def sample_template():
    return ConceptTemplate(
        name="Brandschutzkonzept Test",
        scope=ConceptScope.BRANDSCHUTZ,
        version="1.0",
        framework="MBO",
        sections=[
            TemplateSection(
                name="standort",
                title="Standort",
                order=1,
                fields=[
                    TemplateField(
                        name="adresse",
                        label="Adresse",
                        field_type=FieldType.TEXT,
                        required=True,
                    ),
                    TemplateField(
                        name="ort",
                        label="Ort",
                        field_type=FieldType.TEXT,
                    ),
                ],
            ),
            TemplateSection(
                name="gebaeude",
                title="Gebäudedaten",
                order=2,
                fields=[
                    TemplateField(
                        name="flaeche",
                        label="Fläche (m²)",
                        field_type=FieldType.NUMBER,
                    ),
                ],
            ),
        ],
    )


@pytest.fixture
def sample_values():
    return {
        "standort": {"adresse": "Marktplatz 1", "ort": "Musterstadt"},
        "gebaeude": {"flaeche": "500"},
    }


class TestRenderHtml:
    def test_should_contain_title(self, sample_template, sample_values):
        html = render_html(sample_template, sample_values, title="Mein Konzept")
        assert "Mein Konzept" in html

    def test_should_fallback_to_template_name(self, sample_template, sample_values):
        html = render_html(sample_template, sample_values)
        assert "Brandschutzkonzept Test" in html

    def test_should_contain_field_values(self, sample_template, sample_values):
        html = render_html(sample_template, sample_values)
        assert "Marktplatz 1" in html
        assert "Musterstadt" in html
        assert "500" in html

    def test_should_contain_section_titles(self, sample_template, sample_values):
        html = render_html(sample_template, sample_values)
        assert "Standort" in html
        assert "Gebäudedaten" in html

    def test_should_show_empty_fields_by_default(self, sample_template):
        html = render_html(sample_template, {})
        assert "(nicht ausgefüllt)" in html

    def test_should_hide_empty_fields_when_disabled(self, sample_template):
        html = render_html(sample_template, {}, include_empty=False)
        assert "(nicht ausgefüllt)" not in html

    def test_should_contain_framework_info(self, sample_template, sample_values):
        html = render_html(sample_template, sample_values)
        assert "MBO" in html

    def test_should_be_valid_html(self, sample_template, sample_values):
        html = render_html(sample_template, sample_values)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_should_accept_custom_css(self, sample_template, sample_values):
        css = "body { background: red; }"
        html = render_html(sample_template, sample_values, css=css)
        assert "background: red" in html


class TestRenderPdf:
    def test_should_raise_without_weasyprint(self, sample_template, sample_values):
        """PDF generation requires weasyprint — test graceful error."""
        try:
            pdf = render_pdf(sample_template, sample_values, title="Test")
            # If weasyprint IS installed, we should get bytes
            assert isinstance(pdf, bytes)
            assert len(pdf) > 0
            assert pdf[:5] == b"%PDF-"
        except ImportError:
            # Expected on systems without weasyprint
            pass


class TestEsc:
    def test_should_escape_html_entities(self):
        assert _esc("<script>") == "&lt;script&gt;"
        assert _esc('a="b"') == "a=&quot;b&quot;"
        assert _esc("a & b") == "a &amp; b"

    def test_should_handle_empty_string(self):
        assert _esc("") == ""

    def test_should_handle_plain_text(self):
        assert _esc("Hello World") == "Hello World"
