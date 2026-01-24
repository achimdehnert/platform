"""
Extract Texts Handler V2.0
Professional refactored version with type safety and service layer
"""

import logging
from typing import Any, Dict, List, Optional, TypedDict

from django.db import transaction
from pydantic import BaseModel, Field, validator

from apps.genagent.handlers import BaseHandler

from . import register_medtrans_handler

logger = logging.getLogger(__name__)


# ============================================================================
# TYPE DEFINITIONS
# ============================================================================


class ExtractContext(TypedDict):
    """Type-safe context for extraction"""

    pptx_file: str
    presentation_id: int
    customer_id: Optional[str]


class ExtractConfig(BaseModel):
    """Validated configuration for extraction"""

    skip_short_texts: bool = Field(True, description="Skip texts shorter than min_text_length")
    include_speaker_notes: bool = Field(False, description="Include speaker notes in extraction")
    min_text_length: int = Field(2, ge=1, le=100, description="Minimum text length to extract")

    @validator("min_text_length")
    def validate_length(cls, v, values):
        if values.get("skip_short_texts") and v < 1:
            raise ValueError("min_text_length must be >= 1 when skip_short_texts is True")
        return v


class ExtractResult(TypedDict):
    """Type-safe result from extraction"""

    success: bool
    output: Optional[Dict[str, Any]]
    total_texts: int
    slides_processed: int
    error: Optional[str]
    test_mode: bool


# ============================================================================
# SERVICE LAYER
# ============================================================================


class PresentationTextService:
    """Service for managing presentation text operations"""

    @staticmethod
    @transaction.atomic
    def store_extracted_texts(
        extraction_result: Dict[str, Any], presentation_id: int, config: ExtractConfig
    ) -> Dict[str, int]:
        """
        Store extracted texts in database with transaction safety

        Returns:
            dict: {'stored': int, 'skipped': int}
        """
        from apps.medtrans.models import Presentation, PresentationText

        try:
            presentation = Presentation.objects.select_for_update().get(id=presentation_id)

            slides_data = extraction_result.get("slides", [])
            stored_count = 0
            skipped_count = 0

            for slide in slides_data:
                slide_number = slide.get("slide_number")
                texts = slide.get("texts", [])

                for text_obj in texts:
                    text_id = text_obj.get("id")
                    original_text = text_obj.get("original_text", "").strip()

                    # Apply config filters
                    if not original_text:
                        skipped_count += 1
                        continue

                    if config.skip_short_texts and len(original_text) < config.min_text_length:
                        skipped_count += 1
                        logger.debug(
                            "text_skipped_too_short",
                            text_id=text_id,
                            length=len(original_text),
                            min_length=config.min_text_length,
                        )
                        continue

                    # Store text
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
                    stored_count += 1

            # Update presentation stats
            presentation.total_texts = stored_count
            presentation.save()

            logger.info(
                "texts_stored_successfully",
                presentation_id=presentation_id,
                stored=stored_count,
                skipped=skipped_count,
            )

            return {"stored": stored_count, "skipped": skipped_count}

        except Exception as e:
            logger.error(
                "storage_failed", presentation_id=presentation_id, error=str(e), exc_info=True
            )
            raise


# ============================================================================
# HANDLER
# ============================================================================


@register_medtrans_handler
class ExtractTextsHandler(BaseHandler):
    """
    Extract all translatable texts from PowerPoint presentation

    Input Context:
        - pptx_file: Path to PowerPoint file (required)
        - presentation_id: Database presentation ID (required)
        - customer_id: Customer ID (optional)

    Output:
        - success: bool - Operation success status
        - output: dict - Extraction result with slides and texts
        - total_texts: int - Number of texts extracted
        - slides_processed: int - Number of slides processed
        - error: str - Error message (if failed)
    """

    def execute(
        self,
        context: ExtractContext,
        test_mode: bool = False,
        config: Optional[ExtractConfig] = None,
    ) -> ExtractResult:
        """Execute text extraction from PowerPoint"""

        # Initialize config with defaults
        config = config or ExtractConfig()

        try:
            # Validate required context
            required = ["pptx_file", "presentation_id"]
            missing = [f for f in required if f not in context]
            if missing:
                logger.warning("missing_required_fields", missing_fields=missing)
                return ExtractResult(
                    success=False,
                    output=None,
                    total_texts=0,
                    slides_processed=0,
                    error=f"Missing required fields: {', '.join(missing)}",
                    test_mode=test_mode,
                )

            pptx_file = context["pptx_file"]
            presentation_id = context["presentation_id"]
            customer_id = context.get("customer_id")

            logger.info(
                "extraction_started",
                pptx_file=pptx_file,
                presentation_id=presentation_id,
                test_mode=test_mode,
            )

            # Test mode: Return mock data
            if test_mode:
                return self._mock_extraction_result()

            # Real execution: Import and use XML Text Extractor
            from apps.core.services.extractors import PPTXExtractor

            extractor = PPTXExtractor()
            result = extractor.extract_texts_from_pptx(pptx_file)

            if not result.get("success"):
                logger.error(
                    "extraction_failed", pptx_file=pptx_file, errors=result.get("errors", [])
                )
                return ExtractResult(
                    success=False,
                    output=None,
                    total_texts=0,
                    slides_processed=0,
                    error="Text extraction failed",
                    test_mode=False,
                )

            # Store extracted texts using service layer
            storage_result = PresentationTextService.store_extracted_texts(
                result, presentation_id, config
            )

            logger.info(
                "extraction_completed",
                presentation_id=presentation_id,
                total_texts=result["total_texts"],
                slides_processed=len(result["slides"]),
                stored=storage_result["stored"],
                skipped=storage_result["skipped"],
            )

            return ExtractResult(
                success=True,
                output=result,
                total_texts=result["total_texts"],
                slides_processed=len(result["slides"]),
                error=None,
                test_mode=False,
            )

        except Exception as e:
            logger.error("extract_handler_failed", error=str(e), exc_info=True)
            return ExtractResult(
                success=False,
                output=None,
                total_texts=0,
                slides_processed=0,
                error=str(e),
                test_mode=test_mode,
            )

    def _mock_extraction_result(self) -> ExtractResult:
        """Generate mock data for test mode"""
        return ExtractResult(
            success=True,
            output={
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
            total_texts=1,
            slides_processed=1,
            error=None,
            test_mode=True,
        )

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Return JSON schema for configuration validation"""
        return ExtractConfig.schema()

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> ExtractConfig:
        """Validate and parse configuration"""
        return ExtractConfig(**config)
