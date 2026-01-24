"""
Core Export Service

Unified document export system with multiple format support.

Features:
    - Multiple formats: DOCX, PDF, EPUB, Markdown, HTML, JSON, CSV
    - Content conversion: Markdown ↔ HTML
    - Metadata support
    - Template-based filenames
    - Backup existing files

Quick Start:
    from apps.core.services.export import export_to, ExportFormat

    # Simple export
    result = export_to("docx", content="# My Document\\n\\nContent here.")

    # With metadata
    from apps.core.services.export import export_to, DocumentMetadata

    result = export_to(
        "pdf",
        content=markdown_content,
        metadata=DocumentMetadata(
            title="My Book",
            author="John Doe"
        ),
        output_path="exports/my-book.pdf"
    )

Supported Formats:
    - DOCX: Microsoft Word documents
    - PDF: PDF documents (requires reportlab)
    - EPUB: E-book format (requires ebooklib)
    - Markdown: Markdown files with optional frontmatter
    - HTML: HTML documents with styling
    - JSON: JSON data files
    - CSV: CSV data files

Book Export:
    from apps.core.services.export import BookExporter, BookContent, ChapterContent

    book = BookContent(
        title="My Novel",
        author="Jane Doe",
        chapters=[
            ChapterContent(number=1, title="The Beginning", content="..."),
            ChapterContent(number=2, title="The Journey", content="..."),
        ]
    )

    exporter = BookExporter()
    results = exporter.export_all_formats(book)

Migration from existing code:
    # Old: from apps.core.services.export import BookExporter
    # New: from apps.core.services.export import BookExporter
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

from .base import BaseExporter, ContentConverter
from .exceptions import (
    ContentError,
    ContentParseError,
    DependencyError,
    DependencyVersionError,
    EmptyContentError,
    ExporterConfigError,
    ExporterError,
    ExporterNotFoundError,
    ExportException,
    FileError,
    FileExistsError,
    FormatConversionError,
    InvalidContentError,
    MissingDependencyError,
    OutputPathError,
    PermissionError,
    TemplateError,
    TemplateNotFoundError,
    TemplateRenderError,
    UnsupportedFormatError,
    WriteError,
    is_export_error,
    wrap_library_error,
)
from .exporters import (
    CSVExporter,
    DOCXExporter,
    EPUBExporter,
    HTMLExporter,
    JSONExporter,
    MarkdownExporter,
    PDFExporter,
    create_exporter,
)
from .models import (
    BookContent,
    ChapterContent,
    ContentType,
    DocumentMetadata,
    DOCXExportConfig,
    EPUBExportConfig,
    ExportConfig,
    ExportFormat,
    ExportResult,
    MarkdownExportConfig,
    PDFExportConfig,
    generate_filename,
)

# =============================================================================
# High-Level Export Functions
# =============================================================================


def export_to(
    format: Union[str, ExportFormat],
    content: Any,
    output_path: Optional[Union[str, Path]] = None,
    metadata: Optional[DocumentMetadata] = None,
    config: Optional[ExportConfig] = None,
    **kwargs,
) -> ExportResult:
    """
    Export content to specified format.

    This is the main entry point for all export operations.

    Args:
        format: Target format (docx, pdf, epub, md, html, json, csv)
        content: Content to export
        output_path: Output file path (optional)
        metadata: Document metadata
        config: Export configuration
        **kwargs: Additional options

    Returns:
        ExportResult with export details

    Example:
        result = export_to("docx", "# My Doc\\n\\nContent here.")
        print(f"Exported to: {result.output_path}")
    """
    if config is None:
        config = ExportConfig(format=ExportFormat(format) if isinstance(format, str) else format)

    exporter = create_exporter(format, config)
    return exporter.export(content, output_path, metadata, **kwargs)


def export_markdown(
    content: Any,
    output_path: Optional[Union[str, Path]] = None,
    add_frontmatter: bool = True,
    metadata: Optional[DocumentMetadata] = None,
    **kwargs,
) -> ExportResult:
    """
    Export content to Markdown file.

    Args:
        content: Content to export
        output_path: Output file path
        add_frontmatter: Add YAML frontmatter
        metadata: Document metadata

    Returns:
        ExportResult
    """
    config = ExportConfig(format=ExportFormat.MARKDOWN, add_metadata=add_frontmatter)
    return export_to("md", content, output_path, metadata, config, **kwargs)


def export_html(
    content: Any,
    output_path: Optional[Union[str, Path]] = None,
    metadata: Optional[DocumentMetadata] = None,
    css: Optional[str] = None,
    **kwargs,
) -> ExportResult:
    """
    Export content to HTML file.

    Args:
        content: Content to export (markdown or HTML)
        output_path: Output file path
        metadata: Document metadata
        css: Custom CSS styling

    Returns:
        ExportResult
    """
    config = ExportConfig(format=ExportFormat.HTML, html_options={"css": css} if css else {})
    return export_to("html", content, output_path, metadata, config, **kwargs)


def export_json(
    data: Any, output_path: Optional[Union[str, Path]] = None, **kwargs
) -> ExportResult:
    """
    Export data to JSON file.

    Args:
        data: Data to export
        output_path: Output file path

    Returns:
        ExportResult
    """
    return export_to("json", data, output_path, **kwargs)


def export_csv(
    data: list, output_path: Optional[Union[str, Path]] = None, **kwargs
) -> ExportResult:
    """
    Export data to CSV file.

    Args:
        data: List of dictionaries to export
        output_path: Output file path

    Returns:
        ExportResult
    """
    return export_to("csv", data, output_path, **kwargs)


# =============================================================================
# Book Exporter
# =============================================================================


class BookExporter:
    """
    High-level book export service.

    Exports books to multiple formats (DOCX, PDF, EPUB).
    Compatible with existing BookExporter API.

    Example:
        exporter = BookExporter()

        book = BookContent(
            title="My Novel",
            author="Jane Doe",
            chapters=[...]
        )

        # Export to single format
        result = exporter.export_to_docx(book)

        # Export to all formats
        results = exporter.export_all_formats(book)
    """

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize book exporter.

        Args:
            output_dir: Base directory for exports
        """
        self.output_dir = output_dir

    def export_to_docx(self, book: BookContent, output_path: Optional[Path] = None) -> ExportResult:
        """Export book to DOCX format."""
        config = ExportConfig(format=ExportFormat.DOCX, output_dir=self.output_dir)

        metadata = DocumentMetadata(title=book.title, author=book.author, subject=book.genre)

        return export_to("docx", book, output_path, metadata, config)

    def export_to_pdf(self, book: BookContent, output_path: Optional[Path] = None) -> ExportResult:
        """Export book to PDF format."""
        config = ExportConfig(format=ExportFormat.PDF, output_dir=self.output_dir)

        metadata = DocumentMetadata(title=book.title, author=book.author, subject=book.genre)

        return export_to("pdf", book, output_path, metadata, config)

    def export_to_epub(self, book: BookContent, output_path: Optional[Path] = None) -> ExportResult:
        """Export book to EPUB format."""
        config = ExportConfig(format=ExportFormat.EPUB, output_dir=self.output_dir)

        metadata = DocumentMetadata(title=book.title, author=book.author, subject=book.genre)

        return export_to("epub", book, output_path, metadata, config)

    def export_all_formats(self, book: BookContent) -> Dict[str, ExportResult]:
        """
        Export book to all supported formats.

        Args:
            book: Book content to export

        Returns:
            Dictionary with format as key, ExportResult as value
        """
        results = {}

        for format_name, method in [
            ("docx", self.export_to_docx),
            ("pdf", self.export_to_pdf),
            ("epub", self.export_to_epub),
        ]:
            try:
                results[format_name] = method(book)
            except Exception as e:
                results[format_name] = ExportResult(
                    success=False, format=ExportFormat(format_name), errors=[str(e)]
                )

        return results


# =============================================================================
# Conversion Utilities
# =============================================================================


def markdown_to_html(markdown_text: str) -> str:
    """Convert Markdown to HTML."""
    return ContentConverter.markdown_to_html(markdown_text)


def html_to_markdown(html_text: str) -> str:
    """Convert HTML to Markdown."""
    return ContentConverter.html_to_markdown(html_text)


def add_frontmatter(content: str, metadata: Dict[str, Any]) -> str:
    """Add YAML frontmatter to Markdown content."""
    return ContentConverter.add_yaml_frontmatter(content, metadata)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Main functions
    "export_to",
    "export_markdown",
    "export_html",
    "export_json",
    "export_csv",
    # High-level exporters
    "BookExporter",
    # Models
    "ExportFormat",
    "ContentType",
    "ExportConfig",
    "ExportResult",
    "DocumentMetadata",
    "ChapterContent",
    "BookContent",
    "MarkdownExportConfig",
    "PDFExportConfig",
    "DOCXExportConfig",
    "EPUBExportConfig",
    "generate_filename",
    # Base classes
    "BaseExporter",
    "ContentConverter",
    # Concrete exporters
    "DOCXExporter",
    "PDFExporter",
    "EPUBExporter",
    "MarkdownExporter",
    "HTMLExporter",
    "JSONExporter",
    "CSVExporter",
    "create_exporter",
    # Conversion utilities
    "markdown_to_html",
    "html_to_markdown",
    "add_frontmatter",
    # Exceptions
    "ExportException",
    "UnsupportedFormatError",
    "FormatConversionError",
    "ContentError",
    "EmptyContentError",
    "InvalidContentError",
    "ContentParseError",
    "FileError",
    "OutputPathError",
    "FileExistsError",
    "WriteError",
    "PermissionError",
    "DependencyError",
    "MissingDependencyError",
    "DependencyVersionError",
    "TemplateError",
    "TemplateNotFoundError",
    "TemplateRenderError",
    "ExporterError",
    "ExporterNotFoundError",
    "ExporterConfigError",
    "is_export_error",
    "wrap_library_error",
]
