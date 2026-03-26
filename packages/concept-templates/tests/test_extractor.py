"""Tests for PDF text extraction (ADR-147 Phase B)."""

from __future__ import annotations

from pathlib import Path

import pytest

from concept_templates.extractor import extract_text_from_bytes, extract_text_from_pdf
from concept_templates.schemas import ExtractionResult

FIXTURE_DIR = Path(__file__).parent / "fixtures"
SAMPLE_PDF = FIXTURE_DIR / "sample_brandschutz.pdf"


class TestExtractTextFromPdf:
    """Tests for extract_text_from_pdf()."""

    def test_extract_from_path(self):
        result = extract_text_from_pdf(SAMPLE_PDF)
        assert isinstance(result, ExtractionResult)
        assert result.page_count == 2
        assert "Objektbeschreibung" in result.text
        assert "Brandabschnitt" in result.text

    def test_extract_from_string_path(self):
        result = extract_text_from_pdf(str(SAMPLE_PDF))
        assert result.page_count == 2
        assert len(result.text) > 100

    def test_extract_from_bytes(self):
        pdf_bytes = SAMPLE_PDF.read_bytes()
        result = extract_text_from_pdf(pdf_bytes)
        assert result.page_count == 2
        assert "Loescheinrichtungen" in result.text

    def test_metadata_extracted(self):
        result = extract_text_from_pdf(SAMPLE_PDF)
        assert result.metadata["total_pages"] == 2
        assert result.metadata["extracted_pages"] == 2
        assert "char_count" in result.metadata

    def test_author_in_metadata(self):
        result = extract_text_from_pdf(SAMPLE_PDF)
        assert result.metadata.get("author") == "IIL GmbH"

    def test_specific_pages(self):
        result = extract_text_from_pdf(SAMPLE_PDF, pages=[1])
        assert result.page_count == 1
        assert "Loescheinrichtungen" in result.text
        assert "Objektbeschreibung" not in result.text

    def test_page_out_of_range_warning(self):
        result = extract_text_from_pdf(SAMPLE_PDF, pages=[0, 99])
        assert result.page_count == 1
        assert any("out of range" in w for w in result.warnings)

    def test_empty_bytes_raises(self):
        with pytest.raises(ValueError, match="Empty PDF bytes"):
            extract_text_from_pdf(b"")

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            extract_text_from_pdf("/nonexistent/file.pdf")

    def test_non_pdf_extension_warning(self):
        """Non-.pdf extension should produce a warning but still work if valid PDF."""
        import shutil
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            shutil.copy(SAMPLE_PDF, tmp.name)
            result = extract_text_from_pdf(tmp.name)
            assert any(".txt" in w for w in result.warnings)
            assert result.page_count == 2
            Path(tmp.name).unlink()

    def test_max_pages_limit(self):
        result = extract_text_from_pdf(SAMPLE_PDF, max_pages=1)
        assert result.page_count == 1
        assert result.metadata["extracted_pages"] == 1
        assert any("limiting to 1" in w for w in result.warnings)


class TestExtractTextFromBytes:
    """Tests for the convenience wrapper."""

    def test_pdf_content_type(self):
        pdf_bytes = SAMPLE_PDF.read_bytes()
        result = extract_text_from_bytes(pdf_bytes, content_type="application/pdf")
        assert isinstance(result, ExtractionResult)
        assert result.page_count == 2

    def test_x_pdf_content_type(self):
        pdf_bytes = SAMPLE_PDF.read_bytes()
        result = extract_text_from_bytes(pdf_bytes, content_type="application/x-pdf")
        assert result.page_count == 2

    def test_unsupported_content_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported content type"):
            extract_text_from_bytes(b"data", content_type="text/plain")

    def test_passes_kwargs_to_extractor(self):
        pdf_bytes = SAMPLE_PDF.read_bytes()
        result = extract_text_from_bytes(pdf_bytes, pages=[0])
        assert result.page_count == 1
