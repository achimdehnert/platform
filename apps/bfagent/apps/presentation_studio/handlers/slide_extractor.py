"""
================================================================================
DEPRECATED - DO NOT USE
================================================================================

This file has been deprecated and replaced by the consolidated Core Services.

Replacement: apps.core.services.extractors.PPTXExtractor
Deprecated: 2025-12-07
Migration Phase: 6

This file is kept for reference only. All new code should use the replacement.

To migrate existing code, run:
    python manage.py migrate_to_core --apply

================================================================================
"""

"""
Enhanced Slide Extractor for PPTX Studio
Extracts slides with shape-based grouping and formatting preservation
"""

import logging
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SlideExtractor:
    """Extract slides with shape grouping and formatting"""

    def __init__(self):
        self.namespace_map = {
            "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
            "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
            "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        }

    def extract_slides_with_shapes(self, pptx_path: str) -> Dict[str, Any]:
        """
        Extract all slides with shape-based text grouping

        Returns:
            {
                'success': bool,
                'slides': [
                    {
                        'slide_number': int,
                        'shapes': [
                            {
                                'shape_id': str,
                                'shape_type': str,
                                'paragraphs': [
                                    {
                                        'level': int,
                                        'text': str,
                                        'bullet': bool,
                                        'bullet_char': str
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        """
        results = {"success": False, "slides": [], "errors": []}

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Extract PPTX
                with zipfile.ZipFile(pptx_path, "r") as zip_ref:
                    zip_ref.extractall(temp_path)

                # Find all slide XML files
                slides_dir = temp_path / "ppt" / "slides"
                if not slides_dir.exists():
                    results["errors"].append("No slides directory found")
                    return results

                slide_files = sorted(slides_dir.glob("slide*.xml"))
                logger.info(f"Found {len(slide_files)} slide files")

                # Process each slide
                for slide_idx, slide_file in enumerate(slide_files, 1):
                    slide_data = self._extract_slide_shapes(slide_file, slide_idx)
                    if slide_data["shapes"]:
                        results["slides"].append(slide_data)

                results["success"] = True
                logger.info(f"Extracted {len(results['slides'])} slides with shapes")

        except Exception as e:
            error_msg = f"Failed to extract slides: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        return results

    def _extract_slide_shapes(self, slide_file: Path, slide_number: int) -> Dict[str, Any]:
        """Extract shapes from a single slide"""

        slide_data = {"slide_number": slide_number, "slide_file": slide_file.name, "shapes": []}

        try:
            # Register namespaces
            for prefix, uri in self.namespace_map.items():
                ET.register_namespace(prefix, uri)

            # Parse XML
            tree = ET.parse(slide_file)
            root = tree.getroot()

            # Find all shapes
            shapes = root.findall(".//p:sp", self.namespace_map)

            # Extract shapes with position info
            shapes_with_pos = []
            for shape_idx, shape in enumerate(shapes, 1):
                shape_data = self._extract_shape_content(shape, shape_idx)
                if shape_data["paragraphs"]:
                    # Get Y position for sorting
                    y_pos = self._get_shape_y_position(shape)
                    shapes_with_pos.append((y_pos, shape_data))

            # Sort by Y position (top to bottom)
            shapes_with_pos.sort(key=lambda x: x[0])

            # Extract sorted shapes
            slide_data["shapes"] = [shape_data for _, shape_data in shapes_with_pos]

        except Exception as e:
            logger.error(f"Error processing slide {slide_number}: {str(e)}")

        return slide_data

    def _get_shape_y_position(self, shape) -> int:
        """Extract Y position of a shape for sorting"""
        try:
            # Find transform offset
            off = shape.find(".//a:off", self.namespace_map)
            if off is not None:
                y = off.get("y")
                if y:
                    return int(y)
        except Exception:
            pass
        return 0

    def _extract_shape_content(self, shape, shape_idx: int) -> Dict[str, Any]:
        """Extract content from a single shape"""

        shape_data = {
            "shape_id": f"shape_{shape_idx}",
            "shape_type": self._get_shape_type(shape),
            "paragraphs": [],
        }

        # Find text frame
        txBody = shape.find(".//p:txBody", self.namespace_map)
        if txBody is None:
            return shape_data

        # Extract all paragraphs
        paragraphs = txBody.findall(".//a:p", self.namespace_map)

        for para in paragraphs:
            para_data = self._extract_paragraph(para)
            if para_data["text"]:
                shape_data["paragraphs"].append(para_data)

        return shape_data

    def _extract_paragraph(self, paragraph) -> Dict[str, Any]:
        """Extract content from a paragraph with formatting"""

        para_data = {"level": 0, "text": "", "bullet": False, "bullet_char": "", "text_runs": []}

        # Get paragraph properties
        pPr = paragraph.find(".//a:pPr", self.namespace_map)
        if pPr is not None:
            # Check indentation level
            level_attr = pPr.get("lvl")
            if level_attr:
                para_data["level"] = int(level_attr)

            # Check for bullets
            buFont = pPr.find(".//a:buFont", self.namespace_map)
            buChar = pPr.find(".//a:buChar", self.namespace_map)
            buAutoNum = pPr.find(".//a:buAutoNum", self.namespace_map)

            if buChar is not None:
                para_data["bullet"] = True
                para_data["bullet_char"] = buChar.get("char", "•")
            elif buAutoNum is not None:
                para_data["bullet"] = True
                # Could extract numbering type here
                para_data["bullet_char"] = "1."

        # Extract all text runs
        text_runs = paragraph.findall(".//a:r", self.namespace_map)
        text_parts = []

        for run in text_runs:
            text_elem = run.find(".//a:t", self.namespace_map)
            if text_elem is not None and text_elem.text:
                text_parts.append(text_elem.text)

        # Also check for direct text elements (without runs)
        if not text_parts:
            text_elems = paragraph.findall(".//a:t", self.namespace_map)
            text_parts = [t.text for t in text_elems if t.text]

        para_data["text"] = "".join(text_parts)

        return para_data

    def _get_shape_type(self, shape) -> str:
        """Determine shape type (title, body, etc.)"""

        # Check for placeholder type
        nvSpPr = shape.find(".//p:nvSpPr", self.namespace_map)
        if nvSpPr is not None:
            ph = nvSpPr.find(".//p:ph", self.namespace_map)
            if ph is not None:
                ph_type = ph.get("type", "body")
                return ph_type

        return "textbox"
