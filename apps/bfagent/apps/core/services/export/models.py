"""
Export Service Models

Typed dataclasses for export configuration and metadata.
Part of the consolidated Core Export Service.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class ExportFormat(str, Enum):
    """Supported export formats."""

    # Documents
    DOCX = "docx"
    PDF = "pdf"
    EPUB = "epub"

    # Text
    MARKDOWN = "md"
    HTML = "html"
    TXT = "txt"

    # Data
    JSON = "json"
    CSV = "csv"
    XLSX = "xlsx"


class ContentType(str, Enum):
    """Types of content being exported."""

    BOOK = "book"
    CHAPTER = "chapter"
    DOCUMENT = "document"
    REPORT = "report"
    DATA = "data"
    PRESENTATION = "presentation"


@dataclass
class ExportConfig:
    """
    Configuration for export operations.

    Attributes:
        format: Target export format
        output_dir: Output directory path
        filename_template: Template for filename generation
        overwrite: Allow overwriting existing files
        create_backup: Create backup of existing files
        add_metadata: Include metadata in exports
        timestamp_files: Add timestamp to filenames
        compress: Compress output (where applicable)
    """

    format: ExportFormat = ExportFormat.DOCX
    output_dir: Optional[str] = None
    filename_template: str = "{title}_{timestamp}"
    overwrite: bool = True
    create_backup: bool = True
    add_metadata: bool = True
    timestamp_files: bool = True
    compress: bool = False

    # Format-specific options
    pdf_options: Dict[str, Any] = field(default_factory=dict)
    docx_options: Dict[str, Any] = field(default_factory=dict)
    html_options: Dict[str, Any] = field(default_factory=dict)

    def get_output_dir(self) -> Path:
        """Get resolved output directory."""
        if self.output_dir:
            return Path(self.output_dir)
        return Path.cwd() / "exports"


@dataclass
class DocumentMetadata:
    """
    Metadata for exported documents.

    Attributes:
        title: Document title
        author: Document author
        subject: Document subject
        keywords: List of keywords
        language: Document language (ISO code)
        created_at: Creation timestamp
        modified_at: Last modification timestamp
        custom: Additional custom metadata
    """

    title: str = ""
    author: str = ""
    subject: str = ""
    keywords: List[str] = field(default_factory=list)
    language: str = "en"
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "author": self.author,
            "subject": self.subject,
            "keywords": self.keywords,
            "language": self.language,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            **self.custom,
        }


@dataclass
class ExportResult:
    """
    Result of an export operation.

    Attributes:
        success: Whether export succeeded
        output_path: Path to exported file
        format: Export format used
        file_size: Size of exported file in bytes
        duration_seconds: Time taken for export
        metadata: Document metadata
        errors: List of errors encountered
        warnings: List of warnings
    """

    success: bool = False
    output_path: Optional[str] = None
    format: Optional[ExportFormat] = None
    file_size: int = 0
    duration_seconds: float = 0.0
    metadata: Optional[DocumentMetadata] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output_path": self.output_path,
            "format": self.format.value if self.format else None,
            "file_size": self.file_size,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class ChapterContent:
    """
    Content for a single chapter.

    Attributes:
        number: Chapter number
        title: Chapter title
        content: Chapter content (markdown or text)
        word_count: Number of words
        metadata: Additional metadata
    """

    number: int
    title: str = ""
    content: str = ""
    word_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.word_count and self.content:
            self.word_count = len(self.content.split())


@dataclass
class BookContent:
    """
    Content for a complete book.

    Attributes:
        title: Book title
        author: Book author
        genre: Book genre
        chapters: List of chapters
        outline: Book outline
        metadata: Additional metadata
    """

    title: str
    author: str = ""
    genre: str = ""
    chapters: List[ChapterContent] = field(default_factory=list)
    outline: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_words(self) -> int:
        """Calculate total word count."""
        return sum(ch.word_count for ch in self.chapters)

    @property
    def chapter_count(self) -> int:
        """Get number of chapters."""
        return len(self.chapters)


@dataclass
class MarkdownExportConfig:
    """
    Configuration for Markdown exports.

    Attributes:
        add_frontmatter: Add YAML frontmatter
        frontmatter_fields: Fields to include in frontmatter
        preserve_structure: Maintain heading hierarchy
    """

    add_frontmatter: bool = True
    frontmatter_fields: List[str] = field(
        default_factory=lambda: ["title", "author", "date", "tags"]
    )
    preserve_structure: bool = True


@dataclass
class PDFExportConfig:
    """
    Configuration for PDF exports.

    Attributes:
        page_size: Page size (letter, A4, etc.)
        margin_inches: Page margins
        font_family: Font family name
        font_size: Base font size
        include_toc: Include table of contents
        include_cover: Include cover page
    """

    page_size: str = "letter"
    margin_inches: float = 1.0
    font_family: str = "Helvetica"
    font_size: int = 12
    include_toc: bool = True
    include_cover: bool = True


@dataclass
class DOCXExportConfig:
    """
    Configuration for DOCX exports.

    Attributes:
        template: Path to template document
        style: Document style name
        include_toc: Include table of contents
        include_cover: Include cover page
        page_numbers: Include page numbers
    """

    template: Optional[str] = None
    style: str = "Normal"
    include_toc: bool = True
    include_cover: bool = True
    page_numbers: bool = True


@dataclass
class EPUBExportConfig:
    """
    Configuration for EPUB exports.

    Attributes:
        cover_image: Path to cover image
        css_file: Path to custom CSS
        include_toc: Include table of contents
        language: Book language code
    """

    cover_image: Optional[str] = None
    css_file: Optional[str] = None
    include_toc: bool = True
    language: str = "en"


def generate_filename(
    template: str, title: str = "export", timestamp: bool = True, extension: str = "", **kwargs
) -> str:
    """
    Generate filename from template.

    Args:
        template: Filename template with placeholders
        title: Document title
        timestamp: Include timestamp
        extension: File extension
        **kwargs: Additional template values

    Returns:
        Generated filename

    Example:
        name = generate_filename(
            "{title}_{date}",
            title="My Book",
            extension=".docx"
        )
        # Returns: "my-book_20240101.docx"
    """
    import re
    from datetime import datetime

    # Sanitize title
    safe_title = re.sub(r"[^\w\s-]", "", title).strip()
    safe_title = re.sub(r"[-\s]+", "-", safe_title).lower()

    now = datetime.now()

    replacements = {
        "{title}": safe_title,
        "{date}": now.strftime("%Y%m%d"),
        "{timestamp}": now.strftime("%Y%m%d_%H%M%S"),
        "{year}": str(now.year),
        "{month}": f"{now.month:02d}",
        "{day}": f"{now.day:02d}",
        **{f"{{{k}}}": str(v) for k, v in kwargs.items()},
    }

    filename = template
    for placeholder, value in replacements.items():
        filename = filename.replace(placeholder, value)

    # Add extension if not present
    if extension and not filename.endswith(extension):
        if not extension.startswith("."):
            extension = f".{extension}"
        filename += extension

    return filename
