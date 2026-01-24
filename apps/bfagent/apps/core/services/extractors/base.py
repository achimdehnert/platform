"""
File Extractor Base Classes

Abstract base class for file extractors.
Part of the consolidated Core File Extractor Service.
"""

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Union

try:
    from .exceptions import (
        ExtractorException,
        FileNotFoundError,
        FileReadError,
        FileTooLargeError,
        UnsupportedFormatError,
    )
    from .models import (
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
except ImportError:
    from exceptions import (
        ExtractorException,
        FileNotFoundError,
        FileReadError,
        FileTooLargeError,
        UnsupportedFormatError,
    )
    from models import (
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


logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """
    Abstract base class for file extractors.

    All extractors must implement the `_extract` method.
    Provides common functionality for file validation and result handling.

    Abstract Methods (must implement):
        - _extract(file_path, config) -> ExtractionResult

    Optional Methods (can override):
        - validate_file(file_path) -> bool
        - get_metadata(file_path) -> FileMetadata
    """

    # Class attributes - override in subclasses
    supported_types: List[FileType] = []
    file_extensions: List[str] = []

    def __init__(self, config: Optional[ExtractorConfig] = None):
        """
        Initialize extractor.

        Args:
            config: Extraction configuration
        """
        self.config = config or ExtractorConfig()

    @property
    def name(self) -> str:
        """Get extractor name."""
        return self.__class__.__name__

    # =========================================================================
    # Abstract Methods (MUST implement)
    # =========================================================================

    @abstractmethod
    def _extract(self, file_path: Path, config: ExtractorConfig) -> ExtractionResult:
        """
        Perform the actual extraction.

        Args:
            file_path: Path to file
            config: Extraction configuration

        Returns:
            ExtractionResult with extracted content
        """
        pass

    # =========================================================================
    # Public API
    # =========================================================================

    def extract(
        self, file_path: Union[str, Path], config: Optional[ExtractorConfig] = None, **kwargs
    ) -> ExtractionResult:
        """
        Extract content from file.

        Args:
            file_path: Path to file
            config: Optional extraction configuration
            **kwargs: Additional options

        Returns:
            ExtractionResult with extracted content

        Example:
            extractor = PDFExtractor()
            result = extractor.extract("document.pdf")
            print(result.text)
        """
        start_time = time.time()
        config = config or self.config
        result = ExtractionResult()

        try:
            file_path = Path(file_path)

            # Validate file
            self._validate_file(file_path, config)

            # Detect file type
            result.file_type = detect_file_type(file_path)

            # Get basic metadata
            result.metadata = get_file_metadata(file_path)

            # Perform extraction
            result = self._extract(file_path, config)
            result.success = True

            # Ensure metadata is set
            if not result.metadata:
                result.metadata = get_file_metadata(file_path)

            logger.info(f"Extraction successful: {file_path.name} " f"({result.word_count} words)")

        except ExtractorException as e:
            result.success = False
            result.errors.append(str(e))
            logger.error(f"Extraction failed: {e}")

        except Exception as e:
            result.success = False
            result.errors.append(f"Unexpected error: {e}")
            logger.exception(f"Extraction failed with unexpected error: {e}")

        finally:
            result.duration_seconds = time.time() - start_time

        return result

    def extract_text(self, file_path: Union[str, Path], **kwargs) -> str:
        """
        Extract text content only.

        Args:
            file_path: Path to file
            **kwargs: Additional options

        Returns:
            Extracted text as string
        """
        result = self.extract(file_path, **kwargs)
        if result.success:
            return result.text
        else:
            raise ExtractorException(
                message=f"Extraction failed: {result.errors}", file_path=str(file_path)
            )

    def extract_from_bytes(
        self, data: bytes, filename: str = "unknown", config: Optional[ExtractorConfig] = None
    ) -> ExtractionResult:
        """
        Extract content from bytes.

        Args:
            data: File content as bytes
            filename: Optional filename for type detection
            config: Extraction configuration

        Returns:
            ExtractionResult
        """
        import tempfile

        # Get extension from filename
        ext = Path(filename).suffix or ".tmp"

        with tempfile.NamedTemporaryFile(suffix=ext, delete=True) as tmp:
            tmp.write(data)
            tmp.flush()
            return self.extract(tmp.name, config)

    # =========================================================================
    # Validation
    # =========================================================================

    def _validate_file(self, file_path: Path, config: ExtractorConfig) -> None:
        """
        Validate file before extraction.

        Args:
            file_path: Path to file
            config: Extraction configuration

        Raises:
            FileNotFoundError: If file doesn't exist
            FileTooLargeError: If file exceeds size limit
            UnsupportedFormatError: If format not supported
        """
        # Check existence
        if not file_path.exists():
            raise FileNotFoundError(str(file_path))

        # Check size
        file_size = file_path.stat().st_size
        if file_size > config.max_file_size:
            raise FileTooLargeError(str(file_path), file_size, config.max_file_size)

        # Check format
        file_type = detect_file_type(file_path)
        if self.supported_types and file_type not in self.supported_types:
            raise UnsupportedFormatError(
                file_type.value if file_type else "unknown",
                supported=[t.value for t in self.supported_types],
            )

    def supports(self, file_path: Union[str, Path]) -> bool:
        """
        Check if extractor supports file type.

        Args:
            file_path: Path to file

        Returns:
            True if file type is supported
        """
        file_type = detect_file_type(file_path)
        if not file_type:
            return False
        return file_type in self.supported_types


class TextCleaner:
    """
    Utility class for cleaning extracted text.
    """

    @staticmethod
    def clean(text: str) -> str:
        """
        Clean extracted text.

        - Remove excessive whitespace
        - Normalize line endings
        - Strip leading/trailing whitespace
        """
        import re

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove excessive spaces
        text = re.sub(r" {2,}", " ", text)

        # Strip each line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)

        return text.strip()

    @staticmethod
    def remove_special_chars(text: str, keep_newlines: bool = True) -> str:
        """Remove special characters."""
        import re

        if keep_newlines:
            text = re.sub(r"[^\w\s\n.,!?;:\-\'\"()[\]{}]", "", text)
        else:
            text = re.sub(r"[^\w\s.,!?;:\-\'\"()[\]{}]", " ", text)

        return text

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize all whitespace to single spaces."""
        import re

        return re.sub(r"\s+", " ", text).strip()


class TableParser:
    """
    Utility class for parsing table data.
    """

    @staticmethod
    def rows_to_dicts(
        rows: List[List[Any]], headers: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Convert list of lists to list of dicts.

        Args:
            rows: Table rows as lists
            headers: Optional headers (uses first row if None)

        Returns:
            List of dictionaries
        """
        if not rows:
            return []

        if headers is None:
            headers = [str(h) for h in rows[0]]
            rows = rows[1:]

        result = []
        for row in rows:
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i] if i < len(row) else None
            result.append(row_dict)

        return result

    @staticmethod
    def normalize_headers(headers: List[str]) -> List[str]:
        """
        Normalize table headers.

        - Strip whitespace
        - Handle duplicates
        - Convert to snake_case
        """
        import re

        normalized = []
        seen = {}

        for header in headers:
            # Clean
            h = str(header).strip()
            h = re.sub(r"\s+", "_", h.lower())
            h = re.sub(r"[^\w]", "", h)

            # Handle duplicates
            if h in seen:
                seen[h] += 1
                h = f"{h}_{seen[h]}"
            else:
                seen[h] = 0

            normalized.append(h or f"column_{len(normalized)}")

        return normalized
