"""
================================================================================
DEPRECATED - DO NOT USE
================================================================================

This file has been deprecated and replaced by the consolidated Core Services.

Replacement: apps.core.services.extractors.PDFExtractor
Deprecated: 2025-12-07
Migration Phase: 6

This file is kept for reference only. All new code should use the replacement.

To migrate existing code, run:
    python manage.py migrate_to_core --apply

================================================================================
"""

"""
PDF Content Extractor for PPTX Enhancement
Extracts structured content from PDF files for slide generation
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract and structure content from PDF files"""

    def extract_content(self, pdf_path: str) -> Dict:
        """
        Extract content from PDF and structure it for slide generation

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dict with extracted content structure
        """
        try:
            import pdfplumber

            slides_content = []

            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text from page
                    text = page.extract_text()

                    if not text:
                        continue

                    # Split into lines
                    lines = text.strip().split("\n")

                    # Try to identify structure
                    slide_data = self._parse_page_content(lines, page_num)

                    if slide_data:
                        slides_content.append(slide_data)

            return {"success": True, "slides": slides_content, "total_slides": len(slides_content)}

        except ImportError:
            return {
                "success": False,
                "error": "pdfplumber not installed. Run: pip install pdfplumber",
                "slides": [],
            }
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e), "slides": []}

    def _parse_page_content(self, lines: List[str], page_num: int) -> Dict:
        """
        Parse page content into structured slide data

        Args:
            lines: Text lines from page
            page_num: Page number

        Returns:
            Structured slide data
        """
        if not lines:
            return None

        # First non-empty line is usually the title
        title = None
        content_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if not title:
                # First non-empty line is title
                title = line
            else:
                # Rest is content
                content_lines.append(line)

        # Join content
        content = "\n".join(content_lines)

        return {"title": title or f"Slide {page_num}", "content": content, "page_number": page_num}

    def extract_to_json(self, pdf_path: str, json_output_path: str) -> Dict:
        """
        Extract PDF content and save as JSON

        Args:
            pdf_path: Path to PDF file
            json_output_path: Path to save JSON

        Returns:
            Result dict
        """
        result = self.extract_content(pdf_path)

        if result["success"]:
            try:
                with open(json_output_path, "w", encoding="utf-8") as f:
                    json.dump(result["slides"], f, indent=2, ensure_ascii=False)

                return {
                    "success": True,
                    "json_path": json_output_path,
                    "slides_count": result["total_slides"],
                }
            except Exception as e:
                return {"success": False, "error": f"Failed to save JSON: {str(e)}"}
        else:
            return result

    def get_available_concepts(self, pdf_path: str) -> List[Dict]:
        """
        Get available concepts from PDF for enhancement

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of concept dicts ready for enhancement
        """
        result = self.extract_content(pdf_path)

        if result["success"]:
            return result["slides"]
        else:
            return []
