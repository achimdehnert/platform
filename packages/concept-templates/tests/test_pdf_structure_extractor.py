"""Tests for pdf_structure_extractor module."""

from concept_templates.pdf_structure_extractor import (
    _filter_sequential_headings,
    _is_valid_heading,
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


class TestIsValidHeading:
    """Tests for heading validation filter."""

    def test_should_accept_normal_heading(self):
        assert _is_valid_heading(
            "1", "Anlagenbeschreibung",
            "1. Anlagenbeschreibung",
        )

    def test_should_accept_subsection(self):
        assert _is_valid_heading(
            "3.1", "Primärer Explosionsschutz",
            "3.1 Primärer Explosionsschutz",
        )

    def test_should_reject_large_section_number(self):
        assert not _is_valid_heading(
            "1000", "m3/h über Öffnungen zum Absaugen",
            "1000. m3/h über Öffnungen zum Absaugen",
        )

    def test_should_reject_plz(self):
        assert not _is_valid_heading(
            "89077", "Ulm",
            "89077. Ulm",
        )

    def test_should_reject_table_row_with_columns(self):
        assert not _is_valid_heading(
            "1",
            "Im Raum  Keine  Notmaßnahmen siehe Punkt",
            "1  Im Raum  Keine  Notmaßnahmen siehe Punkt",
        )

    def test_should_reject_measurement_unit(self):
        assert not _is_valid_heading(
            "1000", "m3/h über Öffnungen",
            "1000. m3/h über Öffnungen",
        )

    def test_should_reject_very_short_title(self):
        assert not _is_valid_heading("1", "x", "1 x")


class TestRegressionTableRowsAsHeadings:
    """Regression: table rows must not be parsed as headings.

    Fig 1+2: "4. Zoneneinteilung" contains a table with
    numbered rows (1, 2, 3) that were incorrectly parsed
    as section headings.
    """

    def test_should_not_split_table_rows_as_sections(self):
        text = (
            "4 Zoneneinteilung\n"
            "Für die geplanten Bereiche wurde eine "
            "Zoneneinteilung vorgenommen.\n"
            "Nr.  Anlagenteil  Zone  "
            "Bemerkungen/Schutzmaßnahmen\n"
            "1  Im Raum  Keine  "
            "Notmaßnahmen siehe Punkt 3.2\n"
            "2  Oberhalb der Anlage  Keine  "
            "Fackel verbrennt somit kann auch im "
            "Störfall keine Ex Zone\n"
            "3  Seitlich an den Einführöffnungen  "
            "Keine  Durch kontrollierte Zugabe\n"
        )
        template = extract_structure_from_text(text)
        # Should be 1 section (Zoneneinteilung), not 4
        assert len(template.sections) == 1
        assert "Zoneneinteilung" in template.sections[0].title

    def test_should_keep_table_content_in_section(self):
        text = (
            "4 Zoneneinteilung\n"
            "Beschreibung der Zonen.\n"
            "Nr.\tAnlagenteil\tZone\tBemerkungen\n"
            "1\tIm Raum\tKeine\tNotmaßnahmen\n"
            "2\tOberhalb\tKeine\tFackel verbrennt\n"
            "5 Arbeitsmittel\n"
            "Alle Arbeitsmittel kommen zum Einsatz.\n"
        )
        template = extract_structure_from_text(text)
        assert len(template.sections) == 2
        assert "Zoneneinteilung" in template.sections[0].title
        assert "Arbeitsmittel" in template.sections[1].title


class TestRegressionMeasurementsAsHeadings:
    """Regression: measurements must not be parsed as headings.

    Fig 3+4: "5. Arbeitsmittel" has table content with
    "1000. m3/h über Öffnungen" that was incorrectly
    parsed as section "1000".
    """

    def test_should_not_split_measurement_as_section(self):
        text = (
            "5 Arbeitsmittel\n"
            "Alle Arbeitsmittel die in den Zonenbereichen\n"
            "zum Einsatz kommen.\n"
            "Arbeitsmittel  Hersteller  Kommentar\n"
            "Technische Abluft  Helios RRK 250  "
            "1000 m3/h über Öffnungen\n"
            "Not-Aus-Relais  Pilz  Typ PNOZ X1\n"
        )
        template = extract_structure_from_text(text)
        # Should be 1 section only
        assert len(template.sections) == 1
        assert "Arbeitsmittel" in template.sections[0].title


class TestRegressionPostalCodeAsHeading:
    """Regression: PLZ codes must not be parsed as headings.

    "89077. Ulm" was incorrectly parsed as section "89077".
    """

    def test_should_not_create_section_for_plz(self):
        text = (
            "1 Anlagenbeschreibung\n"
            "Standort: Musterstr. 12\n"
            "89077 Ulm\n"
            "89079 Ulm\n"
            "Die Anlage befindet sich in Ulm.\n"
            "2 Gefährdungsbeurteilung\n"
            "Entsprechend § 6 GefStoffV.\n"
        )
        template = extract_structure_from_text(text)
        titles = [s.title for s in template.sections]
        assert len(template.sections) == 2
        assert any("Anlagenbeschreibung" in t for t in titles)
        assert any("Gefährdungsbeurteilung" in t for t in titles)
        # No PLZ sections
        assert not any("89077" in t for t in titles)
        assert not any("89079" in t for t in titles)


class TestLetterHeadings:
    """Letter headings (A. B. C. D. E.) from PDF TOC."""

    def test_should_detect_letter_headings(self):
        text = (
            "A. Angaben des Betriebsbereichs\n"
            "Betreiber: Firma Mustermann GmbH\n"
            "B. Betrachtete Anlage\n"
            "Wasserstoff-Elektrolyse im Gebäude 3.\n"
            "C. Rechtliche Grundlagen\n"
            "GefStoffV, BetrSichV, TRGS 720.\n"
        )
        template = extract_structure_from_text(text)
        titles = [s.title for s in template.sections]
        assert len(template.sections) == 3
        assert "A. Angaben des Betriebsbereichs" in titles
        assert "B. Betrachtete Anlage" in titles
        assert "C. Rechtliche Grundlagen" in titles

    def test_should_mix_letter_and_number_headings(self):
        text = (
            "A. Betreiber\n"
            "Viktor Rempel, Master of Engineering\n"
            "B. Betrachtete Anlage\n"
            "Wasserstoff-Elektrolyse.\n"
            "1 Anlagenbeschreibung\n"
            "Die Anlage befindet sich...\n"
            "2 Gefährdungsbeurteilung\n"
            "Entsprechend § 6 GefStoffV.\n"
        )
        template = extract_structure_from_text(text)
        titles = [s.title for s in template.sections]
        assert len(template.sections) == 4
        assert "A. Betreiber" in titles
        assert "B. Betrachtete Anlage" in titles
        assert any("Anlagenbeschreibung" in t for t in titles)

    def test_should_use_letter_as_section_name(self):
        text = (
            "A. Betreiber\n"
            "Content.\n"
        )
        template = extract_structure_from_text(text)
        assert template.sections[0].name == "section_a"


class TestSequentialFilter:
    """Sequential monotonicity filter for table row numbers."""

    def test_should_reject_backward_number_after_section_4(self):
        """After section 4, numbers 1/2/3 are table rows, not headings.

        This is the key regression from Fig 6: pdfplumber extracts
        table rows without column separators, so they look like
        '1 Im Raum Keine Notmaßnahmen...' which passes
        _is_valid_heading but fails the sequential check.
        """
        text = (
            "4 Zoneneinteilung\n"
            "Für die geplanten Bereiche wurde eine "
            "Zoneneinteilung vorgenommen.\n"
            "1 Im Raum Keine Notmaßnahmen "
            "siehe Punkt 3.2 Ausfall von Stickstoff\n"
            "2 Keine Fackel verbrennt somit kann "
            "auch im Störfall keine Ex Zone au-\n"
            "3 Seitlich an den Keine Durch "
            "kontrollierte Zugabe von Stickstoff\n"
            "5 Arbeitsmittel\n"
            "Alle Arbeitsmittel kommen zum Einsatz.\n"
        )
        template = extract_structure_from_text(text)
        titles = [s.title for s in template.sections]
        # Should be 2 sections: 4 + 5, NOT 4 + 1 + 2 + 3 + 5
        assert len(template.sections) == 2
        assert any("Zoneneinteilung" in t for t in titles)
        assert any("Arbeitsmittel" in t for t in titles)
        # Table rows must NOT appear as sections
        assert not any(
            "Im Raum" in t for t in titles
        )

    def test_should_allow_subsections_after_parent(self):
        """3.1 and 3.2 after section 3 are valid subsections."""
        text = (
            "3 Explosionsschutzkonzept\n"
            "Überblick über Schutzmaßnahmen.\n"
            "3.1 Zoneneinteilung\n"
            "Zone 1 und Zone 2.\n"
            "3.2 Schutzmaßnahmen\n"
            "Primärer und sekundärer Schutz.\n"
            "4 Zoneneinteilung\n"
            "Detaillierte Beschreibung.\n"
        )
        template = extract_structure_from_text(text)
        titles = [s.title for s in template.sections]
        assert len(template.sections) == 4
        assert any("3.1" in t for t in titles)
        assert any("3.2" in t for t in titles)


class TestFullDocumentExtraction:
    """Integration test mimicking the real PDF structure."""

    def test_should_parse_full_ex_document(self):
        text = (
            "Inhaltsverzeichnis\n"
            "A. Angaben des Betriebsbereichs ............. 4\n"
            "B. Betrachtete Anlage ............. 4\n"
            "C. Rechtliche Grundlagen ............. 4\n"
            "D. Mitgeltende Dokumente ............. 6\n"
            "E. Begriffe ............. 6\n"
            "1 Anlagenbeschreibung ............. 7\n"
            "2 Gefährdungsbeurteilung ............. 8\n"
            "3 Explosionsschutzkonzept ............. 9\n"
            "4 Zoneneinteilung ............. 14\n"
            "5 Arbeitsmittel ............. 18\n"
            "\n"
            "A. Angaben des Betriebsbereichs\n"
            "Erstellt durch: Viktor Rempel\n"
            "Nr.\tName\tAdresse\n"
            "1\tFirma Mustermann\tMusterstr. 12\n"
            "B. Betrachtete Anlage\n"
            "Wasserstoff-Elektrolyse im Gebäude 3.\n"
            "1 Anlagenbeschreibung\n"
            "Die Anlage befindet sich...\n"
            "2 Gefährdungsbeurteilung\n"
            "Entsprechend § 6 GefStoffV.\n"
            "3 Explosionsschutzkonzept\n"
            "Überblick über Schutzmaßnahmen.\n"
            "3.1 Zonenvermeidung\n"
            "Primärer Schutz.\n"
            "4 Zoneneinteilung\n"
            "Für die geplanten Bereiche.\n"
            "1 Im Raum Keine Notmaßnahmen\n"
            "2 Oberhalb Keine Fackel verbrennt\n"
            "3 Seitlich Keine Kontrollierte Zugabe\n"
            "5 Arbeitsmittel\n"
            "Alle Arbeitsmittel.\n"
        )
        template = extract_structure_from_text(text)
        titles = [s.title for s in template.sections]

        # Letter headings detected
        assert any("A." in t for t in titles)
        assert any("B." in t for t in titles)

        # Number headings detected
        assert any("Anlagenbeschreibung" in t for t in titles)
        assert any("Zoneneinteilung" in t for t in titles)
        assert any("Arbeitsmittel" in t for t in titles)

        # Table rows NOT detected as headings
        assert not any("Im Raum" in t for t in titles)
        assert not any("Oberhalb" in t for t in titles)
