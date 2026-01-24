"""
Tests for Core Export Service

Run with: pytest apps/core/services/export/tests/ -v
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from .. import export_csv, export_json, export_markdown, export_to
from ..base import BaseExporter, ContentConverter
from ..exceptions import (
    EmptyContentError,
    ExportException,
    MissingDependencyError,
    UnsupportedFormatError,
)
from ..exporters import CSVExporter, HTMLExporter, JSONExporter, MarkdownExporter, create_exporter
from ..models import (
    BookContent,
    ChapterContent,
    DocumentMetadata,
    ExportConfig,
    ExportFormat,
    ExportResult,
    generate_filename,
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
def sample_content():
    """Sample markdown content."""
    return """# Test Document

This is a test paragraph.

## Section 1

Content for section 1.

## Section 2

Content for section 2.
"""


@pytest.fixture
def sample_metadata():
    """Sample document metadata."""
    return DocumentMetadata(
        title="Test Document", author="Test Author", subject="Testing", language="en"
    )


@pytest.fixture
def sample_book():
    """Sample book content."""
    return BookContent(
        title="Test Book",
        author="Test Author",
        genre="Fiction",
        chapters=[
            ChapterContent(number=1, title="Chapter One", content="This is chapter one content."),
            ChapterContent(number=2, title="Chapter Two", content="This is chapter two content."),
        ],
    )


# =============================================================================
# Model Tests
# =============================================================================


class TestExportConfig:
    def test_default_values(self):
        config = ExportConfig()
        assert config.format == ExportFormat.DOCX
        assert config.overwrite is True
        assert config.create_backup is True

    def test_custom_values(self):
        config = ExportConfig(
            format=ExportFormat.PDF, output_dir="/custom/path", timestamp_files=False
        )
        assert config.format == ExportFormat.PDF
        assert config.output_dir == "/custom/path"


class TestDocumentMetadata:
    def test_to_dict(self, sample_metadata):
        result = sample_metadata.to_dict()
        assert result["title"] == "Test Document"
        assert result["author"] == "Test Author"
        assert "created_at" in result


class TestBookContent:
    def test_total_words(self, sample_book):
        assert sample_book.total_words > 0

    def test_chapter_count(self, sample_book):
        assert sample_book.chapter_count == 2


class TestGenerateFilename:
    def test_basic_filename(self):
        filename = generate_filename("{title}", title="My Document", extension=".docx")
        assert filename == "my-document.docx"

    def test_with_timestamp(self):
        filename = generate_filename("{title}_{timestamp}", title="Report")
        assert "report_" in filename
        assert len(filename) > 10

    def test_with_date(self):
        filename = generate_filename("{title}_{date}", title="Log", extension=".txt")
        today = datetime.now().strftime("%Y%m%d")
        assert today in filename


# =============================================================================
# Content Converter Tests
# =============================================================================


class TestContentConverter:
    def test_markdown_to_html(self):
        md = "# Title\n\nParagraph"
        html = ContentConverter.markdown_to_html(md)
        assert "<h1>" in html or "Title" in html

    def test_text_to_markdown(self):
        text = "This is a paragraph.\n\nThis is another."
        md = ContentConverter.text_to_markdown(text, add_header=True, title="Test")
        assert "# Test" in md

    def test_add_yaml_frontmatter(self):
        content = "# Document"
        result = ContentConverter.add_yaml_frontmatter(content, {"title": "Test", "author": "Me"})
        assert "---" in result
        assert "title: Test" in result

    def test_dict_to_json(self):
        data = {"key": "value", "number": 42}
        json_str = ContentConverter.dict_to_json(data)
        assert '"key": "value"' in json_str

    def test_dict_to_csv(self):
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        csv_str = ContentConverter.dict_to_csv(data)
        assert "name,age" in csv_str
        assert "Alice,30" in csv_str


# =============================================================================
# Exporter Tests
# =============================================================================


class TestMarkdownExporter:
    def test_export_string(self, temp_dir, sample_content):
        exporter = MarkdownExporter()
        output_path = temp_dir / "test.md"

        result = exporter.export(sample_content, output_path)

        assert result.success
        assert output_path.exists()
        assert output_path.read_text() == sample_content

    def test_export_with_metadata(self, temp_dir, sample_content, sample_metadata):
        config = ExportConfig(add_metadata=True)
        exporter = MarkdownExporter(config)
        output_path = temp_dir / "test.md"

        result = exporter.export(sample_content, output_path, sample_metadata)

        assert result.success
        content = output_path.read_text()
        assert "---" in content  # Frontmatter


class TestHTMLExporter:
    def test_export_basic(self, temp_dir, sample_content):
        exporter = HTMLExporter()
        output_path = temp_dir / "test.html"

        result = exporter.export(sample_content, output_path)

        assert result.success
        assert output_path.exists()
        content = output_path.read_text()
        assert "<!DOCTYPE html>" in content
        assert "<title>" in content


class TestJSONExporter:
    def test_export_dict(self, temp_dir):
        exporter = JSONExporter()
        output_path = temp_dir / "test.json"

        data = {"key": "value", "list": [1, 2, 3]}
        result = exporter.export(data, output_path)

        assert result.success
        assert output_path.exists()

        import json

        loaded = json.loads(output_path.read_text())
        assert loaded == data


class TestCSVExporter:
    def test_export_list_of_dicts(self, temp_dir):
        exporter = CSVExporter()
        output_path = temp_dir / "test.csv"

        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        result = exporter.export(data, output_path)

        assert result.success
        assert output_path.exists()

        content = output_path.read_text()
        assert "name,age" in content

    def test_validate_invalid_content(self):
        exporter = CSVExporter()

        # Not a list
        assert exporter.validate_content("string") is False

        # Empty list
        assert exporter.validate_content([]) is False

        # Valid
        assert exporter.validate_content([{"a": 1}]) is True


# =============================================================================
# Factory Tests
# =============================================================================


class TestCreateExporter:
    def test_create_by_format_enum(self):
        exporter = create_exporter(ExportFormat.MARKDOWN)
        assert isinstance(exporter, MarkdownExporter)

    def test_create_by_string(self):
        exporter = create_exporter("json")
        assert isinstance(exporter, JSONExporter)

    def test_unsupported_format(self):
        with pytest.raises(UnsupportedFormatError):
            create_exporter("unsupported_format")


# =============================================================================
# High-Level Function Tests
# =============================================================================


class TestExportTo:
    def test_export_markdown(self, temp_dir, sample_content):
        output_path = temp_dir / "test.md"
        result = export_to("md", sample_content, output_path)

        assert result.success
        assert output_path.exists()

    def test_export_json(self, temp_dir):
        output_path = temp_dir / "test.json"
        data = {"test": True}
        result = export_to("json", data, output_path)

        assert result.success


class TestExportMarkdown:
    def test_basic_export(self, temp_dir):
        output_path = temp_dir / "doc.md"
        result = export_markdown("# Test", output_path)

        assert result.success
        assert output_path.exists()


class TestExportJson:
    def test_basic_export(self, temp_dir):
        output_path = temp_dir / "data.json"
        result = export_json({"key": "value"}, output_path)

        assert result.success


class TestExportCsv:
    def test_basic_export(self, temp_dir):
        output_path = temp_dir / "data.csv"
        data = [{"col1": "a", "col2": "b"}]
        result = export_csv(data, output_path)

        assert result.success


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    def test_empty_content_error(self, temp_dir):
        exporter = MarkdownExporter()
        output_path = temp_dir / "test.md"

        result = exporter.export("", output_path)

        assert not result.success
        assert len(result.errors) > 0

    def test_file_exists_no_overwrite(self, temp_dir, sample_content):
        output_path = temp_dir / "test.md"
        output_path.write_text("existing")

        config = ExportConfig(overwrite=False)
        exporter = MarkdownExporter(config)

        result = exporter.export(sample_content, output_path)

        assert not result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
