"""
File Extractor Models

Typed dataclasses for extraction configuration and results.
Part of the consolidated Core File Extractor Service.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class FileType(str, Enum):
    """Supported file types for extraction."""

    # Documents
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    TXT = "txt"

    # Presentations
    PPTX = "pptx"
    PPT = "ppt"

    # Spreadsheets
    XLSX = "xlsx"
    XLS = "xls"
    CSV = "csv"

    # Data
    JSON = "json"
    XML = "xml"

    # Text
    MARKDOWN = "md"
    HTML = "html"

    # Images (for OCR)
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    TIFF = "tiff"

    @classmethod
    def from_extension(cls, ext: str) -> Optional["FileType"]:
        """Get FileType from file extension."""
        ext = ext.lower().lstrip(".")
        mapping = {
            "pdf": cls.PDF,
            "docx": cls.DOCX,
            "doc": cls.DOC,
            "txt": cls.TXT,
            "pptx": cls.PPTX,
            "ppt": cls.PPT,
            "xlsx": cls.XLSX,
            "xls": cls.XLS,
            "csv": cls.CSV,
            "json": cls.JSON,
            "xml": cls.XML,
            "md": cls.MARKDOWN,
            "markdown": cls.MARKDOWN,
            "html": cls.HTML,
            "htm": cls.HTML,
            "png": cls.PNG,
            "jpg": cls.JPG,
            "jpeg": cls.JPEG,
            "tiff": cls.TIFF,
            "tif": cls.TIFF,
        }
        return mapping.get(ext)


class ContentType(str, Enum):
    """Types of extracted content."""

    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    SLIDE = "slide"
    SHEET = "sheet"
    METADATA = "metadata"


@dataclass
class ExtractorConfig:
    """
    Configuration for file extraction.

    Attributes:
        preserve_formatting: Maintain text formatting
        extract_metadata: Include file metadata
        extract_images: Extract embedded images
        ocr_enabled: Use OCR for images/scanned PDFs
        ocr_language: Language for OCR (e.g., 'eng', 'deu')
        page_range: Pages to extract (None = all)
        sheet_names: Sheets to extract (None = all)
        encoding: Text file encoding
        max_file_size: Maximum file size in bytes
    """

    preserve_formatting: bool = True
    extract_metadata: bool = True
    extract_images: bool = False
    ocr_enabled: bool = False
    ocr_language: str = "eng"
    page_range: Optional[List[int]] = None
    sheet_names: Optional[List[str]] = None
    encoding: str = "utf-8"
    max_file_size: int = 100 * 1024 * 1024  # 100 MB


@dataclass
class FileMetadata:
    """
    Metadata extracted from a file.

    Attributes:
        filename: Original filename
        file_type: Detected file type
        file_size: File size in bytes
        created_at: File creation timestamp
        modified_at: File modification timestamp
        author: Document author
        title: Document title
        page_count: Number of pages
        word_count: Number of words
        custom: Additional metadata
    """

    filename: str
    file_type: Optional[FileType] = None
    file_size: int = 0
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    author: str = ""
    title: str = ""
    page_count: int = 0
    word_count: int = 0
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "filename": self.filename,
            "file_type": self.file_type.value if self.file_type else None,
            "file_size": self.file_size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "author": self.author,
            "title": self.title,
            "page_count": self.page_count,
            "word_count": self.word_count,
            **self.custom,
        }


@dataclass
class ExtractedText:
    """
    Extracted text content.

    Attributes:
        text: Extracted text content
        page_number: Page/slide number (if applicable)
        section: Section identifier
        formatting: Formatting information
    """

    text: str
    page_number: Optional[int] = None
    section: str = ""
    formatting: Dict[str, Any] = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        """Calculate word count."""
        return len(self.text.split())


@dataclass
class ExtractedTable:
    """
    Extracted table content.

    Attributes:
        headers: Table headers
        rows: Table rows (list of dicts)
        page_number: Page number (if applicable)
        sheet_name: Sheet name (for spreadsheets)
    """

    headers: List[str] = field(default_factory=list)
    rows: List[Dict[str, Any]] = field(default_factory=list)
    page_number: Optional[int] = None
    sheet_name: str = ""

    @property
    def row_count(self) -> int:
        """Get number of rows."""
        return len(self.rows)

    def to_list(self) -> List[List[Any]]:
        """Convert to list of lists."""
        result = [self.headers]
        for row in self.rows:
            result.append([row.get(h, "") for h in self.headers])
        return result


@dataclass
class ExtractedSlide:
    """
    Extracted presentation slide.

    Attributes:
        slide_number: Slide number
        title: Slide title
        content: Slide content
        notes: Speaker notes
        texts: Individual text elements
    """

    slide_number: int
    title: str = ""
    content: str = ""
    notes: str = ""
    texts: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "slide_number": self.slide_number,
            "title": self.title,
            "content": self.content,
            "notes": self.notes,
            "texts": self.texts,
        }


@dataclass
class ExtractionResult:
    """
    Result of a file extraction operation.

    Attributes:
        success: Whether extraction succeeded
        file_type: Detected file type
        metadata: File metadata
        texts: Extracted text content
        tables: Extracted tables
        slides: Extracted slides (for presentations)
        raw_content: Raw content string
        errors: List of errors
        warnings: List of warnings
        duration_seconds: Time taken
    """

    success: bool = False
    file_type: Optional[FileType] = None
    metadata: Optional[FileMetadata] = None
    texts: List[ExtractedText] = field(default_factory=list)
    tables: List[ExtractedTable] = field(default_factory=list)
    slides: List[ExtractedSlide] = field(default_factory=list)
    raw_content: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def text(self) -> str:
        """Get all extracted text as single string."""
        if self.raw_content:
            return self.raw_content
        return "\n\n".join(t.text for t in self.texts)

    @property
    def word_count(self) -> int:
        """Get total word count."""
        return sum(t.word_count for t in self.texts)

    @property
    def page_count(self) -> int:
        """Get page count from metadata or texts."""
        if self.metadata and self.metadata.page_count:
            return self.metadata.page_count
        if self.texts:
            pages = {t.page_number for t in self.texts if t.page_number}
            return len(pages) if pages else 1
        return 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "file_type": self.file_type.value if self.file_type else None,
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "text": self.text,
            "word_count": self.word_count,
            "page_count": self.page_count,
            "table_count": len(self.tables),
            "slide_count": len(self.slides),
            "errors": self.errors,
            "warnings": self.warnings,
            "duration_seconds": self.duration_seconds,
        }


def detect_file_type(file_path: Union[str, Path]) -> Optional[FileType]:
    """
    Detect file type from path.

    Args:
        file_path: Path to file

    Returns:
        FileType or None
    """
    path = Path(file_path)
    ext = path.suffix.lower().lstrip(".")
    return FileType.from_extension(ext)


def get_file_metadata(file_path: Union[str, Path]) -> FileMetadata:
    """
    Get basic file metadata.

    Args:
        file_path: Path to file

    Returns:
        FileMetadata with basic info
    """
    path = Path(file_path)

    stat = path.stat() if path.exists() else None

    return FileMetadata(
        filename=path.name,
        file_type=detect_file_type(path),
        file_size=stat.st_size if stat else 0,
        modified_at=datetime.fromtimestamp(stat.st_mtime) if stat else None,
    )
