"""
outlinefw/src/outlinefw/generator.py

OutlineGenerator — orchestrates LLM call + parse_nodes().

Fixes:
  - BLOCKER B-2: LLMRouter Protocol has full error contract
    (LLMRouterError, timeout, retry semantics defined)
  - KRITISCH K-3: Always returns OutlineResult, never raises
  - Platform standard: asgiref.async_to_sync for any async LLM call bridging
  - No asyncio.run() anywhere

LLMRouter Protocol:
  Anything implementing completion() is compatible —
  iil-aifw, test doubles, custom routers.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Protocol, runtime_checkable

from frameworks import get_framework
from parser import parse_nodes
from schemas import (
    FrameworkDefinition,
    GenerationStatus,
    LLMQuality,
    OutlineResult,
    ParseStatus,
    ProjectContext,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLMRouter Protocol (Fixes BLOCKER B-2)
# ---------------------------------------------------------------------------


class LLMRouterError(Exception):
    """Raised by LLMRouter.completion() on unrecoverable failure."""
    pass


class LLMRouterTimeout(LLMRouterError):
    """Raised when LLM call exceeds the allowed timeout."""
    pass


@runtime_checkable
class LLMRouter(Protocol):
    """
    Structural protocol for LLM routing.
    Compatible with iil-aifw and any custom router.

    action_code:  Semantic identifier for prompt routing (e.g. "outline.generate")
    messages:     OpenAI-compatible message list [{"role": ..., "content": ...}]
    quality:      LLMQuality enum (DRAFT=1, STANDARD=2, PREMIUM=3)
    priority:     "speed" | "balanced" | "quality"

    Returns:
        str — the LLM completion text

    Raises:
        LLMRouterError    — on any unrecoverable LLM failure
        LLMRouterTimeout  — on timeout
    """

    def completion(
        self,
        action_code: str,
        messages: list[dict[str, str]],
        quality: LLMQuality = LLMQuality.STANDARD,
        priority: str = "balanced",
    ) -> str: ...


# ---------------------------------------------------------------------------
# Prompt Builder
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
Du bist ein professioneller Story-Struktur-Assistent.
Erstelle eine vollständige Story-Outline im angegebenen Framework.
Antworte AUSSCHLIESSLICH mit einem JSON-Array von Beat-Objekten.
Kein erklärender Text, kein Markdown außer dem JSON selbst.

Jedes Beat-Objekt muss folgende Felder enthalten:
- beat_name: string (Framework-Beat-Identifier)
- position: float (0.0 bis 1.0)
- act: string (act_1 | act_2a | act_2b | act_3)
- title: string (prägnanter Titel für diesen Beat)
- summary: string (150-300 Zeichen, konkreter Inhalt für diese Geschichte)
- tension: string (low | medium | high | peak)
- key_events: array of strings (2-4 konkrete Ereignisse)
"""


def _build_user_prompt(
    framework: FrameworkDefinition,
    context: ProjectContext,
) -> str:
    beats_overview = "\n".join(
        f"  {i+1}. [{b.position:.2f}] {b.name}: {b.description}"
        for i, b in enumerate(framework.beats)
    )
    themes_str = ", ".join(context.themes) if context.themes else "nicht spezifiziert"

    return f"""\
Framework: {framework.name} ({len(framework.beats)} Beats)

Beats in Reihenfolge:
{beats_overview}

Projekt-Kontext:
- Titel: {context.title}
- Genre: {context.genre}
- Logline: {context.logline}
- Protagonist: {context.protagonist}
- Setting: {context.setting}
- Themen: {themes_str}
- Ton: {context.tone or 'nicht spezifiziert'}
- Ausgabesprache: {context.language_code}

Erstelle jetzt das vollständige JSON-Array mit allen {len(framework.beats)} Beats.
Jeder Beat muss konkret auf diese spezifische Geschichte zugeschnitten sein.
"""


# ---------------------------------------------------------------------------
# OutlineGenerator
# ---------------------------------------------------------------------------


class OutlineGenerator:
    """
    Generates story outlines by calling an LLMRouter and parsing the response.

    Usage:
        generator = OutlineGenerator(router=my_aifw_router)
        result = generator.generate(
            framework_key="save_the_cat",
            context=ProjectContext(...),
        )
        if result.success:
            for node in result.nodes:
                print(node.title)
        else:
            logger.error(result.error_message)
    """

    def __init__(self, router: LLMRouter) -> None:
        if not isinstance(router, LLMRouter):
            raise TypeError(
                f"router must implement the LLMRouter Protocol. Got: {type(router).__name__}"
            )
        self._router = router

    def generate(
        self,
        framework_key: str,
        context: ProjectContext,
        quality: LLMQuality = LLMQuality.STANDARD,
        priority: str = "balanced",
    ) -> OutlineResult:
        """
        Generate a complete outline. Always returns OutlineResult — never raises.

        On failure: OutlineResult.status is PARSE_ERROR, LLM_ERROR, or VALIDATION_ERROR.
        On partial: OutlineResult.status is PARTIAL.
        On success: OutlineResult.status is SUCCESS.
        """
        start_ms = int(time.time() * 1000)

        # Resolve framework
        try:
            framework = get_framework(framework_key)
        except KeyError as e:
            return OutlineResult(
                status=GenerationStatus.VALIDATION_ERROR,
                framework_key=framework_key,
                framework_name="",
                project_title=context.title,
                error_message=str(e),
                total_beats=0,
            )

        # Build prompt
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(framework, context)},
        ]

        # Call LLM
        raw_response = ""
        try:
            raw_response = self._router.completion(
                action_code="outline.generate",
                messages=messages,
                quality=quality,
                priority=priority,
            )
        except LLMRouterTimeout as e:
            logger.warning("LLM timeout for outline generation: %s", e)
            return OutlineResult(
                status=GenerationStatus.LLM_ERROR,
                framework_key=framework_key,
                framework_name=framework.name,
                project_title=context.title,
                error_message=f"LLM timeout: {e}",
                raw_llm_response="",
                total_beats=len(framework.beats),
                generation_time_ms=int(time.time() * 1000) - start_ms,
            )
        except LLMRouterError as e:
            logger.error("LLM error for outline generation: %s", e)
            return OutlineResult(
                status=GenerationStatus.LLM_ERROR,
                framework_key=framework_key,
                framework_name=framework.name,
                project_title=context.title,
                error_message=str(e),
                raw_llm_response="",
                total_beats=len(framework.beats),
                generation_time_ms=int(time.time() * 1000) - start_ms,
            )

        # Parse response
        parse_result = parse_nodes(raw_response)
        elapsed_ms = int(time.time() * 1000) - start_ms

        base: dict[str, Any] = {
            "framework_key": framework_key,
            "framework_name": framework.name,
            "project_title": context.title,
            "raw_llm_response": raw_response,
            "parse_result": parse_result,
            "total_beats": len(framework.beats),
            "generation_time_ms": elapsed_ms,
        }

        if parse_result.status == ParseStatus.SUCCESS:
            return OutlineResult(
                status=GenerationStatus.SUCCESS,
                nodes=parse_result.nodes,
                generated_beats=len(parse_result.nodes),
                **base,
            )

        if parse_result.status == ParseStatus.PARTIAL:
            return OutlineResult(
                status=GenerationStatus.PARTIAL,
                nodes=parse_result.nodes,
                generated_beats=len(parse_result.nodes),
                error_message=parse_result.error_message,
                **base,
            )

        if parse_result.status == ParseStatus.EMPTY:
            return OutlineResult(
                status=GenerationStatus.PARSE_ERROR,
                error_message=f"LLM returned empty response: {parse_result.error_message}",
                generated_beats=0,
                **base,
            )

        # MALFORMED_JSON or SCHEMA_MISMATCH
        return OutlineResult(
            status=GenerationStatus.PARSE_ERROR,
            error_message=parse_result.error_message,
            generated_beats=0,
            **base,
        )
