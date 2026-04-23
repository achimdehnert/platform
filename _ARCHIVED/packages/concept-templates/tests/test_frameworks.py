"""Tests for concept_templates.frameworks."""

from __future__ import annotations

from concept_templates.frameworks import (
    AUSSCHREIBUNG_VOB,
    BRANDSCHUTZ_MBO,
    BUILTIN_FRAMEWORKS,
    EXSCHUTZ_TRGS720,
)
from concept_templates.schemas import ConceptScope


class TestBuiltinFrameworks:
    def test_should_have_three_builtins(self):
        assert len(BUILTIN_FRAMEWORKS) == 3

    def test_should_contain_expected_keys(self):
        expected = {"brandschutz_mbo", "exschutz_trgs720", "ausschreibung_vob"}
        assert set(BUILTIN_FRAMEWORKS.keys()) == expected


class TestBrandschutzMBO:
    def test_should_be_master(self):
        assert BRANDSCHUTZ_MBO.is_master is True

    def test_should_have_brandschutz_scope(self):
        assert BRANDSCHUTZ_MBO.scope == ConceptScope.BRANDSCHUTZ

    def test_should_have_correct_framework_key(self):
        assert BRANDSCHUTZ_MBO.framework == "brandschutz_mbo"

    def test_should_have_six_top_level_sections(self):
        assert len(BRANDSCHUTZ_MBO.sections) == 6

    def test_should_have_standort_as_first_section(self):
        assert BRANDSCHUTZ_MBO.sections[0].name == "standort"
        assert BRANDSCHUTZ_MBO.sections[0].required is True

    def test_should_have_standort_fields(self):
        standort = BRANDSCHUTZ_MBO.sections[0]
        field_names = {f.name for f in standort.fields}
        assert "address" in field_names
        assert "building_class" in field_names

    def test_should_have_massnahmen_subsections(self):
        massnahmen = BRANDSCHUTZ_MBO.sections[3]
        assert massnahmen.name == "massnahmen"
        assert len(massnahmen.subsections) == 3
        sub_names = [s.name for s in massnahmen.subsections]
        assert sub_names == ["baulich", "technisch", "organisatorisch"]

    def test_should_have_optional_sections(self):
        optional = [s for s in BRANDSCHUTZ_MBO.sections if not s.required]
        assert len(optional) == 2
        optional_names = {s.name for s in optional}
        assert optional_names == {"loescheinrichtungen", "prueffristen"}


class TestExschutzTRGS720:
    def test_should_be_master(self):
        assert EXSCHUTZ_TRGS720.is_master is True

    def test_should_have_explosionsschutz_scope(self):
        assert EXSCHUTZ_TRGS720.scope == ConceptScope.EXPLOSIONSSCHUTZ

    def test_should_have_seven_sections(self):
        assert len(EXSCHUTZ_TRGS720.sections) == 7

    def test_should_have_stoffdaten_first(self):
        assert EXSCHUTZ_TRGS720.sections[0].name == "stoffdaten"

    def test_should_have_stoffdaten_fields(self):
        stoffdaten = EXSCHUTZ_TRGS720.sections[0]
        field_names = {f.name for f in stoffdaten.fields}
        assert "substance_name" in field_names
        assert "flash_point_c" in field_names


class TestAusschreibungVOB:
    def test_should_be_master(self):
        assert AUSSCHREIBUNG_VOB.is_master is True

    def test_should_have_ausschreibung_scope(self):
        assert AUSSCHREIBUNG_VOB.scope == ConceptScope.AUSSCHREIBUNG

    def test_should_have_eight_sections(self):
        assert len(AUSSCHREIBUNG_VOB.sections) == 8

    def test_should_have_auftraggeber_first(self):
        assert AUSSCHREIBUNG_VOB.sections[0].name == "auftraggeber"

    def test_should_have_fristen_fields(self):
        fristen = AUSSCHREIBUNG_VOB.sections[6]
        assert fristen.name == "fristen"
        field_names = {f.name for f in fristen.fields}
        assert "submission_deadline" in field_names
