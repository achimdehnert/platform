"""Tests for pdf_structure_extractor module."""

from concept_templates.pdf_structure_extractor import (
    analyze_section_content,
    clean_toc_title,
    detect_table_columns,
    extract_structure_from_text,
)
from concept_templates.schemas import FieldType


class TestCleanTocTitle:
    """Tests for TOC title cleanup."""

    def test_should_remove_dots_and_page_number(self):
        result = clean_toc_title(
            "Anlagenbeschreibung ............. 7"
        )
        assert result == "Anlagenbeschreibung"

    def test_should_remove_unicode_dots(self):
        result = clean_toc_title(
            "Gefährdungsbeurteilung ··········· 8"
        )
        assert result == "Gefährdungsbeurteilung"

    def test_should_remove_ellipsis_dots(self):
        result = clean_toc_title(
            "Zoneneinteilung …………………… 12"
        )
        assert result == "Zoneneinteilung"

    def test_should_remove_trailing_page_number(self):
        result = clean_toc_title(
            "Schutzmaßnahmen 15"
        )
        assert result == "Schutzmaßnahmen"

    def test_should_keep_title_without_toc_artifacts(self):
        result = clean_toc_title(
            "Gefährdungsbeurteilung nach § 6 GefStoffV"
        )
        assert result == (
            "Gefährdungsbeurteilung nach § 6 GefStoffV"
        )

    def test_should_handle_empty_string(self):
        assert clean_toc_title("") == ""

    def test_should_handle_only_dots(self):
        assert clean_toc_title("......... 3") == ""


class TestDetectTableColumns:
    """Tests for table detection."""

    def test_should_detect_tab_separated_table(self):
        content = (
            "Anforderung\tEinschätzung\tBemerkung\n"
            "Gefahrstoffe?\tNein\tKeine vorhanden\n"
            "Substitution?\tNein\tNicht möglich\n"
        )
        cols = detect_table_columns(content)
        assert cols is not None
        assert cols == [
            "Anforderung", "Einschätzung", "Bemerkung",
        ]

    def test_should_detect_space_separated_table(self):
        content = (
            "Anforderung       Einschätzung      Bemerkung\n"
            "Gefahrstoffe      Nein              Keine\n"
            "Substitution      Nein              Unmöglich\n"
        )
        cols = detect_table_columns(content)
        assert cols is not None
        assert len(cols) == 3

    def test_should_return_none_for_plain_text(self):
        content = (
            "Ein Ersatz von Wasserstoff ist nicht möglich.\n"
            "Ein Austreten ist verfahrensbedingt möglich.\n"
        )
        assert detect_table_columns(content) is None

    def test_should_return_none_for_single_line(self):
        assert detect_table_columns("Just one line") is None

    def test_should_return_none_for_empty(self):
        assert detect_table_columns("") is None


class TestAnalyzeSectionContent:
    """Tests for content analysis."""

    def test_should_create_textarea_for_plain_text(self):
        content = (
            "Ein Ersatz von Wasserstoff ist nicht möglich.\n"
            "Ein Austreten von Wasserstoff ist "
            "verfahrensbedingt möglich."
        )
        fields = analyze_section_content(content)
        assert len(fields) == 1
        assert fields[0].field_type == FieldType.TEXTAREA
        assert fields[0].name == "inhalt"

    def test_should_create_table_for_tabular_content(self):
        content = (
            "Anforderung\tEinschätzung\tBemerkung\n"
            "Gefahrstoffe?\tNein\tKeine\n"
            "Substitution?\tNein\tUnmöglich\n"
        )
        fields = analyze_section_content(content)
        assert any(
            f.field_type == FieldType.TABLE for f in fields
        )
        table_field = [
            f for f in fields
            if f.field_type == FieldType.TABLE
        ][0]
        assert table_field.columns is not None
        assert len(table_field.columns) == 3

    def test_should_create_mixed_fields_for_text_plus_table(self):
        content = (
            "Entsprechend § 6 GefStoffV ist eine "
            "Gefährdungsbeurteilung durchzuführen:\n"
            "Anforderung\tEinschätzung\tBemerkung\n"
            "Gefahrstoffe?\tNein\tKeine\n"
            "Substitution?\tNein\tUnmöglich\n"
        )
        fields = analyze_section_content(content)
        assert len(fields) == 2
        assert fields[0].field_type == FieldType.TEXTAREA
        assert fields[0].name == "freitext"
        assert fields[1].field_type == FieldType.TABLE
        assert fields[1].name == "tabelle"

    def test_should_create_textarea_for_empty_content(self):
        fields = analyze_section_content("")
        assert len(fields) == 1
        assert fields[0].field_type == FieldType.TEXTAREA


class TestExtractStructureFromText:
    """Tests for full structure extraction."""

    def test_should_extract_numbered_sections(self):
        text = (
            "1. Anlagenbeschreibung\n"
            "Die Anlage befindet sich...\n"
            "2. Gefährdungsbeurteilung\n"
            "Entsprechend § 6 GefStoffV...\n"
            "3. Zoneneinteilung\n"
            "Zone 1 gemäß TRGS 720...\n"
        )
        template = extract_structure_from_text(text)
        assert len(template.sections) == 3
        assert template.sections[0].title == (
            "1. Anlagenbeschreibung"
        )
        assert template.sections[1].title == (
            "2. Gefährdungsbeurteilung"
        )
        assert template.sections[2].title == (
            "3. Zoneneinteilung"
        )

    def test_should_clean_toc_from_section_titles(self):
        text = (
            "1. Anlagenbeschreibung ............. 7\n"
            "Inhalt des ersten Kapitels.\n"
            "2. Gefährdungsbeurteilung .......... 8\n"
            "Inhalt des zweiten Kapitels.\n"
        )
        template = extract_structure_from_text(text)
        assert template.sections[0].title == (
            "1. Anlagenbeschreibung"
        )
        assert template.sections[1].title == (
            "2. Gefährdungsbeurteilung"
        )

    def test_should_detect_subsections(self):
        text = (
            "3. Maßnahmen\n"
            "Überblick...\n"
            "3.1 Primärer Explosionsschutz\n"
            "Vermeidung explosionsfähiger Atmosphäre.\n"
            "3.2 Sekundärer Explosionsschutz\n"
            "Vermeidung wirksamer Zündquellen.\n"
        )
        template = extract_structure_from_text(text)
        assert len(template.sections) >= 2

    def test_should_fallback_to_single_section(self):
        text = "Just plain text without any numbered headings."
        template = extract_structure_from_text(text)
        assert len(template.sections) == 1
        assert template.sections[0].name == "section_1"

    def test_should_set_template_metadata(self):
        text = "1. Test\nContent."
        template = extract_structure_from_text(
            text,
            name="Mein Template",
            scope="explosionsschutz",
            version="2.0",
        )
        assert template.name == "Mein Template"
        assert template.scope == "explosionsschutz"
        assert template.version == "2.0"

    def test_should_analyze_content_types(self):
        text = (
            "1. Freitext-Abschnitt\n"
            "Einfacher Text ohne Tabelle.\n"
            "2. Tabellen-Abschnitt\n"
            "Anforderung\tEinschätzung\tBemerkung\n"
            "Test\tJa\tOk\n"
            "Test2\tNein\tNicht ok\n"
        )
        template = extract_structure_from_text(text)
        assert len(template.sections) == 2
        # First section: textarea
        s1_fields = template.sections[0].fields
        assert any(
            f.field_type == FieldType.TEXTAREA
            for f in s1_fields
        )
        # Second section: table
        s2_fields = template.sections[1].fields
        assert any(
            f.field_type == FieldType.TABLE
            for f in s2_fields
        )
