"""
Export Service Base Classes

Abstract base class for exporters.
Part of the consolidated Core Export Service.
"""

import logging
import shutil
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

try:
    from .exceptions import (
        EmptyContentError,
        ExportException,
        FileExistsError,
        OutputPathError,
        UnsupportedFormatError,
        WriteError,
    )
    from .models import (
        DocumentMetadata,
        ExportConfig,
        ExportFormat,
        ExportResult,
        generate_filename,
    )
except ImportError:
    from exceptions import (
        EmptyContentError,
        ExportException,
        FileExistsError,
        OutputPathError,
        UnsupportedFormatError,
        WriteError,
    )
    from models import DocumentMetadata, ExportConfig, ExportFormat, ExportResult, generate_filename


logger = logging.getLogger(__name__)


class BaseExporter(ABC):
    """
    Abstract base class for document exporters.

    All exporters must implement the `_export` method.
    Provides common functionality for file handling, validation,
    and metadata management.

    Abstract Methods (must implement):
        - _export(content, output_path, metadata) -> ExportResult

    Optional Methods (can override):
        - validate_content(content) -> bool
        - prepare_output_path(config) -> Path
    """

    # Class attributes - override in subclasses
    format: ExportFormat = None
    supported_content_types: List[str] = ["text", "dict"]
    file_extension: str = ""

    def __init__(self, config: Optional[ExportConfig] = None):
        """
        Initialize exporter.

        Args:
            config: Export configuration
        """
        self.config = config or ExportConfig()

    @property
    def name(self) -> str:
        """Get exporter name."""
        return self.__class__.__name__

    # =========================================================================
    # Abstract Methods (MUST implement)
    # =========================================================================

    @abstractmethod
    def _export(
        self, content: Any, output_path: Path, metadata: Optional[DocumentMetadata] = None
    ) -> ExportResult:
        """
        Perform the actual export.

        Args:
            content: Content to export
            output_path: Path to write output
            metadata: Document metadata

        Returns:
            ExportResult with export details
        """
        pass

    # =========================================================================
    # Public API
    # =========================================================================

    def export(
        self,
        content: Any,
        output_path: Optional[Union[str, Path]] = None,
        metadata: Optional[DocumentMetadata] = None,
        **kwargs,
    ) -> ExportResult:
        """
        Export content to file.

        Args:
            content: Content to export
            output_path: Output file path (optional)
            metadata: Document metadata
            **kwargs: Additional export options

        Returns:
            ExportResult with export details

        Example:
            exporter = DocxExporter()
            result = exporter.export(
                content="# My Document\\n\\nContent here.",
                output_path="output.docx",
                metadata=DocumentMetadata(title="My Doc")
            )
        """
        start_time = time.time()
        result = ExportResult(format=self.format)

        try:
            # Validate content
            if not self.validate_content(content):
                raise EmptyContentError()

            # Prepare output path
            if output_path:
                output_path = Path(output_path)
            else:
                output_path = self.prepare_output_path(metadata)

            # Check existing file
            if output_path.exists():
                if not self.config.overwrite:
                    raise FileExistsError(str(output_path))

                if self.config.create_backup:
                    self._create_backup(output_path)

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Perform export
            result = self._export(content, output_path, metadata)
            result.success = True
            result.output_path = str(output_path)
            result.format = self.format

            # Get file size
            if output_path.exists():
                result.file_size = output_path.stat().st_size

            logger.info(f"Export successful: {output_path} " f"({result.file_size} bytes)")

        except ExportException as e:
            result.success = False
            result.errors.append(str(e))
            logger.error(f"Export failed: {e}")

        except Exception as e:
            result.success = False
            result.errors.append(f"Unexpected error: {e}")
            logger.exception(f"Export failed with unexpected error: {e}")

        finally:
            result.duration_seconds = time.time() - start_time

        return result

    def export_to_bytes(self, content: Any, metadata: Optional[DocumentMetadata] = None) -> bytes:
        """
        Export content and return as bytes.

        Useful for streaming exports without writing to disk.

        Args:
            content: Content to export
            metadata: Document metadata

        Returns:
            Exported content as bytes
        """
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=f".{self.file_extension}", delete=True) as tmp:
            result = self.export(content, tmp.name, metadata)
            if result.success:
                return Path(tmp.name).read_bytes()
            else:
                raise ExportException(
                    message=f"Export failed: {result.errors}",
                    format=self.format.value if self.format else None,
                )

    # =========================================================================
    # Validation & Preparation
    # =========================================================================

    def validate_content(self, content: Any) -> bool:
        """
        Validate content before export.

        Override in subclasses for specific validation.

        Args:
            content: Content to validate

        Returns:
            True if content is valid
        """
        if content is None:
            return False

        if isinstance(content, str):
            return len(content.strip()) > 0

        if isinstance(content, (list, dict)):
            return len(content) > 0

        return True

    def prepare_output_path(self, metadata: Optional[DocumentMetadata] = None) -> Path:
        """
        Prepare output file path from config.

        Args:
            metadata: Document metadata for filename

        Returns:
            Output file path
        """
        output_dir = self.config.get_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        title = "export"
        if metadata and metadata.title:
            title = metadata.title

        filename = generate_filename(
            template=self.config.filename_template,
            title=title,
            timestamp=self.config.timestamp_files,
            extension=self.file_extension,
        )

        return output_dir / filename

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _create_backup(self, file_path: Path) -> Path:
        """Create backup of existing file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.parent / f"{file_path.stem}_{timestamp}_backup{file_path.suffix}"
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return backup_path


class ContentConverter:
    """
    Utility class for content format conversion.

    Handles conversion between:
    - Markdown ↔ HTML
    - Text → Markdown
    - Data → various formats
    """

    @staticmethod
    def markdown_to_html(markdown_text: str, extensions: Optional[List[str]] = None) -> str:
        """
        Convert Markdown to HTML.

        Args:
            markdown_text: Markdown content
            extensions: Markdown extensions to use

        Returns:
            HTML content
        """
        try:
            import markdown
        except ImportError:
            # Simple fallback
            return f"<p>{markdown_text}</p>"

        if extensions is None:
            extensions = ["extra", "meta", "toc"]

        md = markdown.Markdown(extensions=extensions)
        return md.convert(markdown_text)

    @staticmethod
    def html_to_markdown(html_text: str) -> str:
        """
        Convert HTML to Markdown.

        Args:
            html_text: HTML content

        Returns:
            Markdown content
        """
        try:
            from markdownify import markdownify

            return markdownify(html_text)
        except ImportError:
            # Simple fallback - strip tags
            import re

            return re.sub(r"<[^>]+>", "", html_text)

    @staticmethod
    def text_to_markdown(text: str, add_header: bool = True, title: str = "") -> str:
        """
        Convert plain text to Markdown.

        Args:
            text: Plain text content
            add_header: Add title header
            title: Document title

        Returns:
            Markdown content
        """
        lines = []

        if add_header and title:
            lines.append(f"# {title}")
            lines.append("")

        # Preserve paragraphs
        paragraphs = text.split("\n\n")
        for para in paragraphs:
            if para.strip():
                lines.append(para.strip())
                lines.append("")

        return "\n".join(lines)

    @staticmethod
    def add_yaml_frontmatter(content: str, metadata: Dict[str, Any]) -> str:
        """
        Add YAML frontmatter to Markdown content.

        Args:
            content: Markdown content
            metadata: Metadata to add

        Returns:
            Content with frontmatter
        """
        lines = ["---"]

        for key, value in metadata.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            elif isinstance(value, str) and any(c in value for c in [":", "#", "|", "\n"]):
                lines.append(f'{key}: "{value}"')
            else:
                lines.append(f"{key}: {value}")

        lines.append("---")
        lines.append("")
        lines.append(content)

        return "\n".join(lines)

    @staticmethod
    def dict_to_csv(data: List[Dict[str, Any]], delimiter: str = ",") -> str:
        """
        Convert list of dicts to CSV string.

        Args:
            data: List of dictionaries
            delimiter: Field delimiter

        Returns:
            CSV content
        """
        if not data:
            return ""

        import csv
        import io

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys(), delimiter=delimiter)
        writer.writeheader()
        writer.writerows(data)

        return output.getvalue()

    @staticmethod
    def dict_to_json(data: Any, indent: int = 2, ensure_ascii: bool = False) -> str:
        """
        Convert data to JSON string.

        Args:
            data: Data to convert
            indent: Indentation level
            ensure_ascii: ASCII-only output

        Returns:
            JSON content
        """
        import json

        return json.dumps(data, indent=indent, ensure_ascii=ensure_ascii, default=str)
