"""Tests for concept_templates.schemas."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from concept_templates.schemas import (
    AnalysisResult,
    ConceptScope,
    ConceptTemplate,
    ExtractionResult,
    FieldType,
    TemplateField,
    TemplateSection,
)


class TestConceptScope:
    def test_should_have_three_scopes(self):
        assert len(ConceptScope) == 3

    def test_should_have_correct_values(self):
        assert ConceptScope.BRANDSCHUTZ == "brandschutz"
        assert ConceptScope.EXPLOSIONSSCHUTZ == "explosionsschutz"
        assert ConceptScope.AUSSCHREIBUNG == "ausschreibung"


class TestFieldType:
    def test_should_have_seven_types(self):
        assert len(FieldType) == 7

    def test_should_include_all_expected_types(self):
        expected = {"text", "textarea", "number", "date", "choice", "file", "boolean"}
        assert {ft.value for ft in FieldType} == expected


class TestTemplateField:
    def test_should_create_minimal_field(self):
        field = TemplateField(
            name="test",
            label="Test",
            field_type=FieldType.TEXT,
        )
        assert field.name == "test"
        assert field.required is False
        assert field.choices is None

    def test_should_create_choice_field_with_options(self):
        field = TemplateField(
            name="gk",
            label="Gebäudeklasse",
            field_type=FieldType.CHOICE,
            choices=["GK1", "GK2", "GK3"],
            required=True,
        )
        assert field.choices == ["GK1", "GK2", "GK3"]
        assert field.required is True

    def test_should_reject_invalid_field_type(self):
        with pytest.raises(ValidationError):
            TemplateField(
                name="x",
                label="X",
                field_type="invalid_type",
            )


class TestTemplateSection:
    def test_should_create_minimal_section(self):
        section = TemplateSection(name="s1", title="Section 1")
        assert section.fields == []
        assert section.subsections == []
        assert section.required is True

    def test_should_nest_subsections(self):
        parent = TemplateSection(
            name="parent",
            title="Parent",
            subsections=[
                TemplateSection(name="child1", title="Child 1"),
                TemplateSection(name="child2", title="Child 2"),
            ],
        )
        assert len(parent.subsections) == 2
        assert parent.subsections[0].name == "child1"

    def test_should_include_fields(self, sample_section):
        assert len(sample_section.fields) == 2
        assert sample_section.fields[0].name == "address"


class TestConceptTemplate:
    def test_should_create_minimal_template(self):
        t = ConceptTemplate(
            name="Test",
            scope=ConceptScope.BRANDSCHUTZ,
        )
        assert t.version == "1.0"
        assert t.is_master is False
        assert t.sections == []
        assert t.metadata == {}

    def test_should_create_full_template(self, sample_template):
        assert sample_template.scope == ConceptScope.BRANDSCHUTZ
        assert sample_template.framework == "brandschutz_mbo"
        assert len(sample_template.sections) == 1

    def test_should_reject_invalid_scope(self):
        with pytest.raises(ValidationError):
            ConceptTemplate(
                name="Bad",
                scope="nonexistent",
            )

    def test_should_serialize_to_json(self, sample_template):
        json_str = sample_template.model_dump_json()
        assert "brandschutz" in json_str
        assert "brandschutz_mbo" in json_str

    def test_should_roundtrip_json(self, sample_template):
        json_str = sample_template.model_dump_json()
        restored = ConceptTemplate.model_validate_json(json_str)
        assert restored == sample_template

    def test_should_support_valid_dates(self):
        t = ConceptTemplate(
            name="Dated",
            scope=ConceptScope.AUSSCHREIBUNG,
            valid_from=date(2026, 1, 1),
            valid_until=date(2026, 12, 31),
        )
        assert t.valid_from == date(2026, 1, 1)

    def test_should_have_independent_metadata_per_instance(self):
        t1 = ConceptTemplate(name="A", scope=ConceptScope.BRANDSCHUTZ)
        t2 = ConceptTemplate(name="B", scope=ConceptScope.BRANDSCHUTZ)
        t1.metadata["key"] = "value"
        assert "key" not in t2.metadata


class TestExtractionResult:
    def test_should_create_with_defaults(self):
        r = ExtractionResult(text="hello", page_count=1)
        assert r.warnings == []
        assert r.metadata == {}

    def test_should_store_warnings(self):
        r = ExtractionResult(
            text="",
            page_count=0,
            warnings=["Seite 1: kein Text"],
        )
        assert len(r.warnings) == 1


class TestAnalysisResult:
    def test_should_validate_confidence_range(self, sample_template):
        r = AnalysisResult(
            proposed_template=sample_template,
            confidence=0.85,
        )
        assert r.confidence == 0.85

    def test_should_reject_confidence_above_one(self, sample_template):
        with pytest.raises(ValidationError):
            AnalysisResult(
                proposed_template=sample_template,
                confidence=1.5,
            )

    def test_should_reject_negative_confidence(self, sample_template):
        with pytest.raises(ValidationError):
            AnalysisResult(
                proposed_template=sample_template,
                confidence=-0.1,
            )
