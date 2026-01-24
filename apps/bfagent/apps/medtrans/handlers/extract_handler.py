"""
Extract Texts Handler
Extracts translatable texts from PowerPoint XML
"""

import logging
from typing import Any, Dict

from apps.genagent.handlers import BaseHandler

from . import register_medtrans_handler

logger = logging.getLogger(__name__)


@register_medtrans_handler
class ExtractTextsHandler(BaseHandler):
    """
    Extract all translatable texts from PowerPoint presentation

    Input Context:
        - pptx_file: Path to PowerPoint file
        - presentation_id: Database presentation ID
        - customer_id: Customer ID

    Output:
        - success: bool
        - output: Extraction result
        - total_texts: Number of texts extracted
        - slides_processed: Number of slides processed
    """

    def execute(self, context: Dict[str, Any], test_mode: bool = False) -> Dict[str, Any]:
        """Execute text extraction from PowerPoint"""

        try:
            # Validate required context
            required = ["pptx_file", "presentation_id"]
            missing = [f for f in required if f not in context]
            if missing:
                return {"success": False, "error": f"Missing required fields: {', '.join(missing)}"}

            pptx_file = context["pptx_file"]
            presentation_id = context["presentation_id"]
            customer_id = context.get("customer_id")

            logger.info(f"Extracting texts from {pptx_file}")

            if test_mode:
                # Test mode: Return mock data
                return {
                    "success": True,
                    "output": {
                        "slides": [
                            {
                                "slide_number": 1,
                                "texts": [
                                    {
                                        "id": "slide_1_text_1",
                                        "original_text": "Test Title",
                                        "clean_text": "Test Title",
                                    }
                                ],
                            }
                        ],
                        "total_texts": 1,
                    },
                    "total_texts": 1,
                    "slides_processed": 1,
                    "test_mode": True,
                }

            # Real execution: Import and use XML Text Extractor
            from apps.core.services.extractors import PPTXExtractor

            extractor = PPTXExtractor()
            result = extractor.extract_texts_from_pptx(pptx_file)

            if not result.get("success"):
                return {
                    "success": False,
                    "error": "Text extraction failed",
                    "details": result.get("errors", []),
                }

            # Store extracted texts in database
            self._store_extracted_texts(result, presentation_id, customer_id)

            logger.info(
                f"Extracted {result['total_texts']} texts from {len(result['slides'])} slides"
            )

            return {
                "success": True,
                "output": result,
                "total_texts": result["total_texts"],
                "slides_processed": len(result["slides"]),
            }

        except Exception as e:
            logger.error(f"Extract texts handler failed: {e}")
            return {"success": False, "error": str(e)}

    def _store_extracted_texts(
        self, extraction_result: Dict[str, Any], presentation_id: int, customer_id: str
    ):
        """Store extracted texts in database"""

        from apps.medtrans.models import Presentation, PresentationText

        try:
            presentation = Presentation.objects.get(id=presentation_id)
            slides_data = extraction_result.get("slides", [])

            for slide in slides_data:
                slide_number = slide.get("slide_number")
                texts = slide.get("texts", [])

                for text_obj in texts:
                    text_id = text_obj.get("id")
                    original_text = text_obj.get("original_text", "").strip()

                    # Skip empty texts
                    if not original_text:
                        continue

                    # Create or update PresentationText
                    PresentationText.objects.update_or_create(
                        presentation=presentation,
                        text_id=text_id,
                        defaults={
                            "slide_number": slide_number,
                            "original_text": original_text,
                            "translated_text": "",
                            "translation_method": "pending",
                        },
                    )

            # Update presentation stats
            presentation.total_texts = extraction_result["total_texts"]
            presentation.save()

            logger.info(
                f"Stored {extraction_result['total_texts']} texts for presentation {presentation_id}"
            )

        except Exception as e:
            logger.error(f"Failed to store extracted texts: {e}")
            raise

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Return configuration schema"""
        return {
            "type": "object",
            "properties": {
                "skip_short_texts": {
                    "type": "boolean",
                    "default": True,
                    "description": "Skip texts shorter than 2 characters",
                },
                "include_speaker_notes": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include speaker notes in extraction",
                },
            },
        }
