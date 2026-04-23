"""PDF text extraction using pdfplumber (ADR-147 Phase B).

Requires the [pdf] extra: pip install iil-concept-templates[pdf]
"""

from __future__ import annotations

import logging
from pathlib import Path

from concept_templates.schemas import ExtractionResult

logger = logging.getLogger(__name__)


def extract_text_from_pdf(
    source: str | Path | bytes,
    *,
    pages: list[int] | None = None,
    max_pages: int = 500,
) -> ExtractionResult:
    """Extract text from a PDF file or bytes.

    Args:
        source: File path (str/Path) or raw PDF bytes.
        pages: Optional list of 0-indexed page numbers to extract.
        max_pages: Safety limit to prevent OOM on huge PDFs.

    Returns:
        ExtractionResult with extracted text and metadata.

    Raises:
        ImportError: If pdfplumber is not installed.
        FileNotFoundError: If source is a path that doesn't exist.
        ValueError: If source is empty or not a valid PDF.
    """
    try:
        import pdfplumber
    except ImportError as exc:
        raise ImportError(
            "pdfplumber is required for PDF extraction. "
            "Install with: pip install iil-concept-templates[pdf]"
        ) from exc

    warnings: list[str] = []
    metadata: dict = {}

    # Open PDF from bytes or path
    if isinstance(source, bytes):
        if not source:
            raise ValueError("Empty PDF bytes provided.")
        import io

        pdf = pdfplumber.open(io.BytesIO(source))
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        if not path.suffix.lower() == ".pdf":
            warnings.append(f"File extension is '{path.suffix}', expected '.pdf'.")
        pdf = pdfplumber.open(path)

    try:
        total_pages = len(pdf.pages)
        metadata["total_pages"] = total_pages

        if total_pages > max_pages:
            warnings.append(
                f"PDF has {total_pages} pages, limiting to {max_pages}."
            )

        # Extract PDF metadata
        if pdf.metadata:
            for key in ("Title", "Author", "Creator", "Producer", "Subject"):
                val = pdf.metadata.get(key)
                if val:
                    metadata[key.lower()] = str(val)

        # Determine which pages to extract
        if pages is not None:
            target_pages = [
                i for i in pages if 0 <= i < total_pages
            ]
            if len(target_pages) < len(pages):
                warnings.append(
                    f"Some page indices out of range (0-{total_pages - 1})."
                )
        else:
            target_pages = list(range(min(total_pages, max_pages)))

        # Extract text page by page
        text_parts: list[str] = []
        empty_pages = 0

        for page_idx in target_pages:
            page = pdf.pages[page_idx]
            page_text = page.extract_text() or ""
            if not page_text.strip():
                empty_pages += 1
            text_parts.append(page_text)

        if empty_pages > 0:
            warnings.append(
                f"{empty_pages} of {len(target_pages)} pages had no extractable text."
            )

        full_text = "\n\n".join(text_parts)
        metadata["extracted_pages"] = len(target_pages)
        metadata["empty_pages"] = empty_pages
        metadata["char_count"] = len(full_text)

    finally:
        pdf.close()

    return ExtractionResult(
        text=full_text,
        page_count=len(target_pages),
        metadata=metadata,
        warnings=warnings,
    )


def extract_text_from_bytes(
    data: bytes,
    content_type: str = "application/pdf",
    **kwargs,
) -> ExtractionResult:
    """Convenience wrapper for extracting text from raw bytes.

    Currently only supports PDF. Raises ValueError for unsupported types.
    """
    if content_type not in ("application/pdf", "application/x-pdf"):
        raise ValueError(
            f"Unsupported content type: {content_type}. Only PDF is supported."
        )
    return extract_text_from_pdf(data, **kwargs)
