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

#!/usr/bin/env python3
"""
XML Text Extractor for V6.5 Pipeline
Extracts all translatable texts from PowerPoint XML for preview and editing
"""

import logging
import re
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class PPTXExtractor:
    """Extract and preview texts from PowerPoint XML before translation"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.namespace_map = {
            "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
            "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
            "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        }

    def extract_texts_from_pptx(self, pptx_path: str) -> Dict[str, Any]:
        """
        Extract all translatable texts from PowerPoint for preview/editing
        Returns structured data for UI display
        """

        results = {"success": False, "slides": [], "total_texts": 0, "errors": []}

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
                self.logger.info(f"Found {len(slide_files)} slide files")

                # Process each slide
                for slide_idx, slide_file in enumerate(slide_files, 1):
                    slide_data = self._extract_texts_from_slide(slide_file, slide_idx)
                    if slide_data["texts"]:
                        results["slides"].append(slide_data)
                        results["total_texts"] += len(slide_data["texts"])

                results["success"] = True
                self.logger.info(
                    f"Extracted {results['total_texts']} texts from {len(results['slides'])} slides"
                )

        except Exception as e:
            error_msg = f"Failed to extract texts: {str(e)}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)

        return results

    def _extract_texts_from_slide(self, slide_file: Path, slide_number: int) -> Dict[str, Any]:
        """Extract texts from a single slide XML file"""

        slide_data = {"slide_number": slide_number, "slide_file": slide_file.name, "texts": []}

        try:
            # Register namespaces
            for prefix, uri in self.namespace_map.items():
                ET.register_namespace(prefix, uri)

            # Parse XML
            tree = ET.parse(slide_file)
            root = tree.getroot()

            # Find all text elements
            text_elements = root.findall(".//a:t", self.namespace_map)

            for idx, text_elem in enumerate(text_elements):
                if text_elem.text and text_elem.text.strip():
                    original_text = text_elem.text

                    # Skip very short texts or special characters only
                    if len(original_text.strip()) < 2:
                        continue

                    # Skip if no translatable content
                    if not re.search(
                        r"[a-zA-ZäöüÄÖÜßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]", original_text
                    ):
                        continue

                    # Extract leading/trailing spaces
                    leading_spaces = len(original_text) - len(original_text.lstrip())
                    trailing_spaces = len(original_text) - len(original_text.rstrip())
                    clean_text = original_text.strip()

                    text_data = {
                        "id": f"slide_{slide_number}_text_{idx + 1}",
                        "original_text": original_text,
                        "clean_text": clean_text,
                        "leading_spaces": leading_spaces,
                        "trailing_spaces": trailing_spaces,
                        "xml_path": f".//a:t[{idx + 1}]",
                        "selected_for_translation": True,  # Default: translate all
                        "custom_translation": None,  # User can provide custom translation
                    }

                    slide_data["texts"].append(text_data)

        except Exception as e:
            self.logger.error(f"Error processing slide {slide_number}: {str(e)}")

        return slide_data

    def get_translation_preview(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate preview data for translation interface"""

        preview = {
            "total_slides": len(extracted_data["slides"]),
            "total_texts": extracted_data["total_texts"],
            "selected_texts": 0,
            "slides_summary": [],
        }

        for slide in extracted_data["slides"]:
            selected_count = sum(1 for text in slide["texts"] if text["selected_for_translation"])
            preview["selected_texts"] += selected_count

            slide_summary = {
                "slide_number": slide["slide_number"],
                "total_texts": len(slide["texts"]),
                "selected_texts": selected_count,
                "sample_text": (
                    slide["texts"][0]["clean_text"][:50] + "..." if slide["texts"] else ""
                ),
            }
            preview["slides_summary"].append(slide_summary)

        return preview


class XMLTextUpdater:
    """Update extracted texts based on user modifications"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def update_text_selections(
        self, extracted_data: Dict[str, Any], updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update text selections and custom translations based on user input"""

        updated_data = extracted_data.copy()

        for slide in updated_data["slides"]:
            for text_item in slide["texts"]:
                text_id = text_item["id"]

                # Update selection status
                if text_id in updates.get("selections", {}):
                    text_item["selected_for_translation"] = updates["selections"][text_id]

                # Update custom translation
                if text_id in updates.get("custom_translations", {}):
                    custom_text = updates["custom_translations"][text_id]
                    if custom_text and custom_text.strip():
                        text_item["custom_translation"] = custom_text.strip()
                    else:
                        text_item["custom_translation"] = None

        # Recalculate totals
        updated_data["total_selected"] = sum(
            1
            for slide in updated_data["slides"]
            for text in slide["texts"]
            if text["selected_for_translation"]
        )

        return updated_data

    def prepare_translation_data(self, extracted_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepare data for V6.5 XML Direct Translation pipeline"""

        translation_items = []

        for slide in extracted_data["slides"]:
            for text_item in slide["texts"]:
                if text_item["selected_for_translation"]:
                    # Use custom translation if provided, otherwise use original
                    text_to_translate = (
                        text_item["custom_translation"]
                        if text_item["custom_translation"]
                        else text_item["clean_text"]
                    )

                    translation_items.append(
                        {
                            "slide_number": slide["slide_number"],
                            "text_id": text_item["id"],
                            "original_text": text_item["original_text"],
                            "text_to_translate": text_to_translate,
                            "leading_spaces": text_item["leading_spaces"],
                            "trailing_spaces": text_item["trailing_spaces"],
                            "xml_path": text_item["xml_path"],
                            "is_custom": bool(text_item["custom_translation"]),
                        }
                    )

        return translation_items
