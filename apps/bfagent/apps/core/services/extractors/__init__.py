"""
Core File Extractor Service

Unified file content extraction system with multiple format support.

Features:
    - Multiple formats: PDF, DOCX, PPTX, Excel, CSV, JSON, Text, Images
    - Text extraction with formatting
    - Table extraction
    - Metadata extraction
    - OCR support for images and scanned PDFs

Quick Start:
    from apps.core.services.extractors import extract_file

    # Auto-detect file type and extract
    result = extract_file("document.pdf")
    print(result.text)
    print(f"Words: {result.word_count}")

Supported Formats:
    - PDF: Text, tables, OCR (requires pdfplumber)
    - DOCX: Paragraphs, tables (requires python-docx)
    - PPTX: Slides, text elements (built-in)
    - Excel: Sheets, tables (requires openpyxl)
    - CSV: Tables (built-in)
    - JSON: Data, arrays (built-in)
    - Text/Markdown: Plain text, frontmatter (built-in)
    - Images: OCR (requires pytesseract, pillow)

Format-Specific Extraction:
    from apps.core.services.extractors import (
        PDFExtractor, DOCXExtractor, PPTXExtractor
    )

    # PDF with OCR
    extractor = PDFExtractor()
    result = extractor.extract(
        "scanned.pdf",
        config=ExtractorConfig(ocr_enabled=True)
    )

    # PowerPoint slides
    extractor = PPTXExtractor()
    result = extractor.extract("presentation.pptx")
    for slide in result.slides:
        print(f"Slide {slide.slide_number}: {slide.title}")

Migration from existing code:
    # Old: from apps.core.services.extractors import PPTXExtractor
    # New: from apps.core.services.extractors import PPTXExtractor

    # Old: from apps.core.services.extractors import PDFExtractor
    # New: from apps.core.services.extractors import PDFExtractor
"""

from pathlib import Path
from typing import Optional, Union

from .base import BaseExtractor, TableParser, TextCleaner
from .exceptions import (
    DependencyError,
    EncodingError,
    ExtractionError,
    ExtractorException,
    FileCorruptedError,
    FileNotFoundError,
    FileReadError,
    FileTooLargeError,
    InvalidFormatError,
    InvalidPasswordError,
    MetadataExtractionError,
    MissingDependencyError,
    OCRError,
    PageNotFoundError,
    PasswordRequiredError,
    SheetNotFoundError,
    TableExtractionError,
    TextExtractionError,
    UnsupportedFormatError,
    is_extractor_error,
    wrap_library_error,
)
from .extractors import (
    CSVExtractor,
    DOCXExtractor,
    ExcelExtractor,
    ImageExtractor,
    JSONExtractor,
    PDFExtractor,
    PPTXExtractor,
    TextExtractor,
    create_extractor,
    extract_file,
)
from .models import (
    ContentType,
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
# Convenience Functions
# =============================================================================


def extract_text(file_path: Union[str, Path], config: Optional[ExtractorConfig] = None) -> str:
    """
    Extract text content from file.

    Args:
        file_path: Path to file
        config: Extraction configuration

    Returns:
        Extracted text as string

    Example:
        text = extract_text("document.pdf")
        print(text)
    """
    result = extract_file(file_path, config)
    if result.success:
        return result.text
    else:
        raise ExtractorException(
            message=f"Extraction failed: {result.errors}", file_path=str(file_path)
        )


def extract_tables(file_path: Union[str, Path], config: Optional[ExtractorConfig] = None) -> list:
    """
    Extract tables from file.

    Args:
        file_path: Path to file
        config: Extraction configuration

    Returns:
        List of ExtractedTable objects

    Example:
        tables = extract_tables("data.xlsx")
        for table in tables:
            print(f"Sheet: {table.sheet_name}, Rows: {table.row_count}")
    """
    result = extract_file(file_path, config)
    if result.success:
        return result.tables
    else:
        raise ExtractorException(
            message=f"Extraction failed: {result.errors}", file_path=str(file_path)
        )


def extract_pdf(
    file_path: Union[str, Path], ocr: bool = False, pages: Optional[list] = None
) -> ExtractionResult:
    """
    Extract content from PDF file.

    Args:
        file_path: Path to PDF
        ocr: Enable OCR for scanned pages
        pages: Specific pages to extract (None = all)

    Returns:
        ExtractionResult

    Example:
        result = extract_pdf("document.pdf", ocr=True)
    """
    config = ExtractorConfig(ocr_enabled=ocr, page_range=pages)
    extractor = PDFExtractor(config)
    return extractor.extract(file_path)


def extract_docx(file_path: Union[str, Path]) -> ExtractionResult:
    """
    Extract content from Word document.

    Args:
        file_path: Path to DOCX

    Returns:
        ExtractionResult
    """
    extractor = DOCXExtractor()
    return extractor.extract(file_path)


def extract_pptx(file_path: Union[str, Path]) -> ExtractionResult:
    """
    Extract content from PowerPoint presentation.

    Args:
        file_path: Path to PPTX

    Returns:
        ExtractionResult with slides
    """
    extractor = PPTXExtractor()
    return extractor.extract(file_path)


def extract_excel(file_path: Union[str, Path], sheets: Optional[list] = None) -> ExtractionResult:
    """
    Extract content from Excel spreadsheet.

    Args:
        file_path: Path to XLSX
        sheets: Specific sheets to extract (None = all)

    Returns:
        ExtractionResult with tables
    """
    config = ExtractorConfig(sheet_names=sheets)
    extractor = ExcelExtractor(config)
    return extractor.extract(file_path)


def extract_csv(file_path: Union[str, Path], encoding: str = "utf-8") -> ExtractionResult:
    """
    Extract content from CSV file.

    Args:
        file_path: Path to CSV
        encoding: File encoding

    Returns:
        ExtractionResult with table
    """
    config = ExtractorConfig(encoding=encoding)
    extractor = CSVExtractor(config)
    return extractor.extract(file_path)


def extract_json(file_path: Union[str, Path]) -> ExtractionResult:
    """
    Extract content from JSON file.

    Args:
        file_path: Path to JSON

    Returns:
        ExtractionResult
    """
    extractor = JSONExtractor()
    return extractor.extract(file_path)


def extract_image(file_path: Union[str, Path], language: str = "eng") -> ExtractionResult:
    """
    Extract text from image using OCR.

    Args:
        file_path: Path to image
        language: OCR language (e.g., 'eng', 'deu')

    Returns:
        ExtractionResult with OCR text
    """
    config = ExtractorConfig(ocr_language=language)
    extractor = ImageExtractor(config)
    return extractor.extract(file_path)


# =============================================================================
# Backward Compatibility Aliases
# =============================================================================

# Alias for old code that imports SlideExtractor
SlideExtractor = PPTXExtractor
PDFContentExtractor = PDFExtractor
XMLTextExtractor = TextExtractor


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Main functions
    "extract_file",
    "extract_text",
    "extract_tables",
    # Backward compatibility
    "SlideExtractor",
    "PDFContentExtractor",
    "XMLTextExtractor",
    # Format-specific functions
    "extract_pdf",
    "extract_docx",
    "extract_pptx",
    "extract_excel",
    "extract_csv",
    "extract_json",
    "extract_image",
    # Models
    "FileType",
    "ContentType",
    "ExtractorConfig",
    "ExtractionResult",
    "FileMetadata",
    "ExtractedText",
    "ExtractedTable",
    "ExtractedSlide",
    "detect_file_type",
    "get_file_metadata",
    # Base classes
    "BaseExtractor",
    "TextCleaner",
    "TableParser",
    # Concrete extractors
    "PDFExtractor",
    "DOCXExtractor",
    "PPTXExtractor",
    "ExcelExtractor",
    "CSVExtractor",
    "JSONExtractor",
    "TextExtractor",
    "ImageExtractor",
    "create_extractor",
    # Exceptions
    "ExtractorException",
    "FileNotFoundError",
    "FileReadError",
    "FileTooLargeError",
    "FileCorruptedError",
    "UnsupportedFormatError",
    "InvalidFormatError",
    "ExtractionError",
    "TextExtractionError",
    "TableExtractionError",
    "MetadataExtractionError",
    "OCRError",
    "DependencyError",
    "MissingDependencyError",
    "PageNotFoundError",
    "SheetNotFoundError",
    "EncodingError",
    "PasswordRequiredError",
    "InvalidPasswordError",
    "is_extractor_error",
    "wrap_library_error",
]
