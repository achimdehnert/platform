"""File validation for concept document uploads."""

from __future__ import annotations

import logging
from pathlib import PurePath

logger = logging.getLogger(__name__)

# 50 MB max
MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({
    ".pdf", ".docx", ".doc", ".xlsx", ".xls",
    ".dxf", ".dwg",
    ".jpg", ".jpeg", ".png", ".tiff",
    ".txt", ".csv",
})

ALLOWED_MIME_PREFIXES: tuple[str, ...] = (
    "application/pdf",
    "application/vnd.openxmlformats",
    "application/msword",
    "application/vnd.ms-excel",
    "image/",
    "text/",
    "application/octet-stream",
)


class FileValidationError(ValueError):
    """Raised when file validation fails."""


def validate_upload_file(
    filename: str,
    size_bytes: int,
    content_type: str = "",
) -> None:
    """Validate an uploaded file for concept document upload.

    Checks file extension against allowlist and size against maximum.
    Logs a warning for unexpected MIME types but does not reject.

    Raises:
        FileValidationError: On invalid extension or oversized file.
    """
    ext = PurePath(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"Dateityp '{ext}' nicht erlaubt. "
            f"Erlaubt: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    if size_bytes > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        actual_mb = size_bytes / (1024 * 1024)
        raise FileValidationError(
            f"Datei zu groß ({actual_mb:.1f} MB). "
            f"Maximum: {max_mb} MB."
        )

    if content_type:
        if not any(
            content_type.startswith(prefix)
            for prefix in ALLOWED_MIME_PREFIXES
        ):
            logger.warning(
                "Unexpected MIME type: %s for %s",
                content_type,
                filename,
            )
