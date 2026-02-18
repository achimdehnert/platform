"""LLM-based DIATAXIS classifier for low-confidence documents.

Re-classifies documents where the heuristic classifier has
confidence < threshold, using the llm_mcp HTTP gateway or
direct OpenAI API.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from docs_agent.llm_client import LLMConfig, generate
from docs_agent.models import DiaxisClassification, DiaxisQuadrant
from docs_agent.prompts import PROMPT_DIATAXIS_CLASSIFY, SYSTEM_DIATAXIS

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 0.7
PREVIEW_CHARS = 500


async def reclassify_low_confidence(
    classifications: list[DiaxisClassification],
    *,
    threshold: float = DEFAULT_THRESHOLD,
    config: Optional[LLMConfig] = None,
) -> list[DiaxisClassification]:
    """Re-classify documents with confidence below threshold via LLM.

    Args:
        classifications: Heuristic classification results.
        threshold: Confidence threshold for re-classification.
        config: LLM configuration.

    Returns:
        Updated list with LLM-refined classifications replacing
        low-confidence entries.
    """
    results: list[DiaxisClassification] = []

    for classification in classifications:
        if classification.confidence >= threshold:
            results.append(classification)
            continue

        refined = await _classify_with_llm(
            classification.file_path, config=config
        )
        if refined is not None:
            results.append(refined)
        else:
            results.append(classification)

    return results


async def _classify_with_llm(
    file_path: Path,
    *,
    config: Optional[LLMConfig] = None,
) -> Optional[DiaxisClassification]:
    """Classify a single document via LLM.

    Args:
        file_path: Path to the document.
        config: LLM configuration.

    Returns:
        DiaxisClassification or None if LLM call fails.
    """
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("Cannot read %s: %s", file_path, exc)
        return None

    title = file_path.stem.replace("-", " ").replace("_", " ")
    preview = text[:PREVIEW_CHARS]

    prompt = PROMPT_DIATAXIS_CLASSIFY.format(
        title=title,
        preview=preview,
    )

    response = await generate(
        prompt,
        system_prompt=SYSTEM_DIATAXIS,
        config=config,
    )

    if not response.success:
        logger.warning(
            "LLM classification failed for %s: %s",
            file_path, response.error,
        )
        return None

    return _parse_classification_response(response.content, file_path)


def _parse_classification_response(
    content: str | dict | list | None,
    file_path: Path,
) -> Optional[DiaxisClassification]:
    """Parse LLM classification response.

    Args:
        content: LLM response content.
        file_path: Path to the classified document.

    Returns:
        DiaxisClassification or None on parse failure.
    """
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from LLM response")
            return None

    if not isinstance(content, dict):
        return None

    quadrant_str = content.get("quadrant", "").lower().strip()
    confidence = float(content.get("confidence", 0.5))

    quadrant_map = {
        "tutorial": DiaxisQuadrant.TUTORIAL,
        "guide": DiaxisQuadrant.GUIDE,
        "reference": DiaxisQuadrant.REFERENCE,
        "explanation": DiaxisQuadrant.EXPLANATION,
    }

    quadrant = quadrant_map.get(quadrant_str)
    if quadrant is None:
        logger.warning(
            "Unknown quadrant from LLM: %s", quadrant_str
        )
        return None

    return DiaxisClassification(
        file_path=file_path,
        quadrant=quadrant,
        confidence=round(confidence, 3),
        triggers=[f"llm: {content.get('reasoning', '')}"],
    )
