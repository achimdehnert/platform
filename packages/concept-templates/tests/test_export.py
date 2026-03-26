"""Tests for concept_templates.export."""

from __future__ import annotations

import json

from concept_templates.export import to_dict, to_json, to_markdown
from concept_templates.schemas import ConceptScope, ConceptTemplate


class TestToDict:
    def test_should_return_dict(self, sample_template):
        result = to_dict(sample_template)
        assert isinstance(result, dict)
        assert result["name"] == "Test-Brandschutzkonzept"

    def test_should_include_scope(self, sample_template):
        result = to_dict(sample_template)
        assert result["scope"] == "brandschutz"

    def test_should_include_sections(self, sample_template):
        result = to_dict(sample_template)
        assert len(result["sections"]) == 1
        assert result["sections"][0]["name"] == "standort"

    def test_should_include_fields_in_sections(self, sample_template):
        result = to_dict(sample_template)
        fields = result["sections"][0]["fields"]
        assert len(fields) == 2
        assert fields[0]["name"] == "address"


class TestToJson:
    def test_should_return_valid_json(self, sample_template):
        result = to_json(sample_template)
        parsed = json.loads(result)
        assert parsed["name"] == "Test-Brandschutzkonzept"

    def test_should_roundtrip(self, sample_template):
        json_str = to_json(sample_template)
        restored = ConceptTemplate.model_validate_json(json_str)
        assert restored == sample_template

    def test_should_respect_indent(self, sample_template):
        compact = to_json(sample_template, indent=0)
        indented = to_json(sample_template, indent=4)
        assert len(indented) > len(compact)


class TestToMarkdown:
    def test_should_contain_template_name_as_heading(self, sample_template):
        md = to_markdown(sample_template)
        assert md.startswith("# Test-Brandschutzkonzept")

    def test_should_contain_framework_info(self, sample_template):
        md = to_markdown(sample_template)
        assert "brandschutz_mbo" in md

    def test_should_contain_scope(self, sample_template):
        md = to_markdown(sample_template)
        assert "brandschutz" in md

    def test_should_contain_section_title(self, sample_template):
        md = to_markdown(sample_template)
        assert "## 1. Standortbeschreibung" in md

    def test_should_mark_required_sections(self, sample_template):
        md = to_markdown(sample_template)
        assert "*(Pflicht)*" in md

    def test_should_list_fields(self, sample_template):
        md = to_markdown(sample_template)
        assert "**Adresse**" in md
        assert "**[Pflicht]**" in md

    def test_should_list_choices(self, sample_template):
        md = to_markdown(sample_template)
        assert "GK1, GK2, GK3" in md

    def test_should_handle_empty_template(self):
        t = ConceptTemplate(
            name="Empty",
            scope=ConceptScope.BRANDSCHUTZ,
        )
        md = to_markdown(t)
        assert "# Empty" in md
        assert "brandschutz" in md

    def test_should_render_subsections(self):
        from concept_templates.frameworks import BRANDSCHUTZ_MBO

        md = to_markdown(BRANDSCHUTZ_MBO)
        assert "### 4.1 Bauliche Maßnahmen" in md
        assert "### 4.2 Anlagentechnische Maßnahmen" in md
