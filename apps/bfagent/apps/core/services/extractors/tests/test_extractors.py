"""
Tests for Core File Extractor Service

Run with: pytest apps/core/services/extractors/tests/ -v
"""

import csv
import json
import tempfile
from pathlib import Path

import pytest

from .. import extract_file, extract_text
from ..base import TableParser, TextCleaner
from ..exceptions import (
    ExtractorException,
    FileNotFoundError,
    MissingDependencyError,
    UnsupportedFormatError,
)
from ..extractors import CSVExtractor, JSONExtractor, TextExtractor, create_extractor
from ..models import (
    ExtractedSlide,
    ExtractedTable,
    ExtractedText,
    ExtractionResult,
    ExtractorConfig,
    FileMetadata,
    FileType,
    detect_file_type,
    get_file_metadata,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_text_file(temp_dir):
    """Create sample text file."""
    path = temp_dir / "sample.txt"
    path.write_text("Hello World\n\nThis is a test file.\n\nAnother paragraph.")
    return path


@pytest.fixture
def sample_markdown_file(temp_dir):
    """Create sample markdown file."""
    content = """---
title: Test Document
author: Test Author
---

# Heading 1

This is a paragraph.

## Heading 2

Another paragraph.
"""
    path = temp_dir / "sample.md"
    path.write_text(content)
    return path


@pytest.fixture
def sample_json_file(temp_dir):
    """Create sample JSON file."""
    data = {"name": "Test", "items": [{"id": 1, "value": "A"}, {"id": 2, "value": "B"}]}
    path = temp_dir / "sample.json"
    path.write_text(json.dumps(data, indent=2))
    return path


@pytest.fixture
def sample_csv_file(temp_dir):
    """Create sample CSV file."""
    path = temp_dir / "sample.csv"
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "age", "city"])
        writer.writerow(["Alice", "30", "NYC"])
        writer.writerow(["Bob", "25", "LA"])
    return path


# =============================================================================
# Model Tests
# =============================================================================


class TestFileType:
    def test_from_extension(self):
        assert FileType.from_extension("pdf") == FileType.PDF
        assert FileType.from_extension(".docx") == FileType.DOCX
        assert FileType.from_extension("XLSX") == FileType.XLSX
        assert FileType.from_extension("md") == FileType.MARKDOWN
        assert FileType.from_extension("unknown") is None


class TestDetectFileType:
    def test_detect_from_path(self, temp_dir):
        assert detect_file_type(temp_dir / "doc.pdf") == FileType.PDF
        assert detect_file_type(temp_dir / "doc.docx") == FileType.DOCX
        assert detect_file_type(temp_dir / "data.csv") == FileType.CSV


class TestExtractorConfig:
    def test_default_values(self):
        config = ExtractorConfig()
        assert config.preserve_formatting is True
        assert config.ocr_enabled is False
        assert config.encoding == "utf-8"

    def test_custom_values(self):
        config = ExtractorConfig(ocr_enabled=True, ocr_language="deu", page_range=[1, 2, 3])
        assert config.ocr_enabled is True
        assert config.ocr_language == "deu"
        assert config.page_range == [1, 2, 3]


class TestExtractionResult:
    def test_text_property(self):
        result = ExtractionResult()
        result.texts = [ExtractedText(text="Hello"), ExtractedText(text="World")]
        assert result.text == "Hello\n\nWorld"

    def test_word_count(self):
        result = ExtractionResult()
        result.texts = [ExtractedText(text="Hello World Test")]
        assert result.word_count == 3

    def test_to_dict(self):
        result = ExtractionResult(success=True, file_type=FileType.PDF)
        d = result.to_dict()
        assert d["success"] is True
        assert d["file_type"] == "pdf"


class TestFileMetadata:
    def test_to_dict(self):
        meta = FileMetadata(filename="test.pdf", file_type=FileType.PDF, page_count=10)
        d = meta.to_dict()
        assert d["filename"] == "test.pdf"
        assert d["page_count"] == 10


# =============================================================================
# TextCleaner Tests
# =============================================================================


class TestTextCleaner:
    def test_clean_whitespace(self):
        text = "Hello   World\n\n\n\nTest"
        cleaned = TextCleaner.clean(text)
        assert "   " not in cleaned
        assert "\n\n\n" not in cleaned

    def test_normalize_whitespace(self):
        text = "Hello   World\n\nTest"
        normalized = TextCleaner.normalize_whitespace(text)
        assert normalized == "Hello World Test"


# =============================================================================
# TableParser Tests
# =============================================================================


class TestTableParser:
    def test_rows_to_dicts(self):
        rows = [["name", "age"], ["Alice", 30], ["Bob", 25]]
        result = TableParser.rows_to_dicts(rows)

        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[1]["age"] == 25

    def test_normalize_headers(self):
        headers = ["First Name", "Last Name", "First Name"]
        normalized = TableParser.normalize_headers(headers)

        assert normalized[0] == "first_name"
        assert normalized[2] == "first_name_1"  # Duplicate handling


# =============================================================================
# Extractor Tests
# =============================================================================


class TestTextExtractor:
    def test_extract_text_file(self, sample_text_file):
        extractor = TextExtractor()
        result = extractor.extract(sample_text_file)

        assert result.success
        assert "Hello World" in result.text
        assert result.file_type == FileType.TXT

    def test_extract_markdown(self, sample_markdown_file):
        extractor = TextExtractor()
        result = extractor.extract(sample_markdown_file)

        assert result.success
        assert "Heading 1" in result.text
        assert result.metadata.title == "Test Document"


class TestJSONExtractor:
    def test_extract_json(self, sample_json_file):
        extractor = JSONExtractor()
        result = extractor.extract(sample_json_file)

        assert result.success
        assert "Test" in result.raw_content
        assert result.file_type == FileType.JSON


class TestCSVExtractor:
    def test_extract_csv(self, sample_csv_file):
        extractor = CSVExtractor()
        result = extractor.extract(sample_csv_file)

        assert result.success
        assert len(result.tables) == 1

        table = result.tables[0]
        assert table.headers == ["name", "age", "city"]
        assert table.row_count == 2
        assert table.rows[0]["name"] == "Alice"


# =============================================================================
# Factory Tests
# =============================================================================


class TestCreateExtractor:
    def test_create_by_file_type(self):
        extractor = create_extractor(FileType.TXT)
        assert isinstance(extractor, TextExtractor)

        extractor = create_extractor(FileType.JSON)
        assert isinstance(extractor, JSONExtractor)

    def test_create_by_string(self):
        extractor = create_extractor("csv")
        assert isinstance(extractor, CSVExtractor)

    def test_create_by_path(self, sample_text_file):
        extractor = create_extractor(sample_text_file)
        assert isinstance(extractor, TextExtractor)

    def test_unsupported_format(self):
        with pytest.raises(UnsupportedFormatError):
            create_extractor("unknown_format")


# =============================================================================
# High-Level Function Tests
# =============================================================================


class TestExtractFile:
    def test_extract_text_file(self, sample_text_file):
        result = extract_file(sample_text_file)

        assert result.success
        assert "Hello World" in result.text

    def test_extract_json_file(self, sample_json_file):
        result = extract_file(sample_json_file)

        assert result.success
        assert result.file_type == FileType.JSON


class TestExtractText:
    def test_extract_text_convenience(self, sample_text_file):
        text = extract_text(sample_text_file)

        assert "Hello World" in text


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    def test_file_not_found(self, temp_dir):
        extractor = TextExtractor()
        result = extractor.extract(temp_dir / "nonexistent.txt")

        assert not result.success
        assert len(result.errors) > 0

    def test_unsupported_format_extraction(self, temp_dir):
        # Create file with unsupported extension
        path = temp_dir / "file.xyz"
        path.write_text("content")

        # TextExtractor doesn't support .xyz
        extractor = TextExtractor()
        result = extractor.extract(path)

        assert not result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
