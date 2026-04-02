"""
outlinefw/src/outlinefw/parser.py

Robust JSON parser for LLM outline responses.

Fixes KRITISCH K-4:
  - Never raises — always returns ParseResult
  - Distinguishes EMPTY, MALFORMED_JSON, PARTIAL, SCHEMA_MISMATCH, SUCCESS
  - Centralises all 3x edge-case implementations from bfagent/travel-beat/writing-hub

Edge cases handled:
  - Markdown code fences (```json ... ```)
  - Trailing commas in JSON (via regex pre-cleaning)
  - LLM wrapping response in {"outline": [...]} or {"nodes": [...]}
  - Mixed valid/invalid nodes (PARTIAL status)
  - BOM and whitespace-only responses
  - Single object (not list) responses
  - Python-style booleans (True/False) in JSON
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from schemas import ActPhase, OutlineNode, ParseResult, ParseStatus, TensionLevel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pre-processing: clean common LLM response artifacts
# ---------------------------------------------------------------------------


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences: ```json ... ``` or ``` ... ```"""
    text = re.sub(r"```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```", "", text)
    return text.strip()


def _strip_bom(text: str) -> str:
    return text.lstrip("\ufeff").lstrip("\u200b")


def _fix_trailing_commas(text: str) -> str:
    """
    Remove trailing commas before } or ] — common LLM JSON error.
    E.g. {"key": "value",} → {"key": "value"}
    """
    return re.sub(r",\s*([}\]])", r"\1", text)


def _fix_python_booleans(text: str) -> str:
    """Replace Python-style True/False/None with JSON true/false/null."""
    text = re.sub(r"\bTrue\b", "true", text)
    text = re.sub(r"\bFalse\b", "false", text)
    text = re.sub(r"\bNone\b", "null", text)
    return text


def _preprocess(raw: str) -> str:
    text = _strip_bom(raw)
    text = _strip_code_fences(text)
    text = _fix_python_booleans(text)
    text = _fix_trailing_commas(text)
    return text.strip()


# ---------------------------------------------------------------------------
# Unwrapping: extract the list from common wrapper patterns
# ---------------------------------------------------------------------------


def _unwrap_nodes(data: Any) -> list[Any] | None:
    """
    LLMs often wrap the list in a parent object.
    Tries common keys in order. Returns None if no list found.
    """
    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return None

    # Try common wrapper keys (ordered by frequency)
    for key in ("nodes", "outline", "beats", "result", "data", "items"):
        if key in data and isinstance(data[key], list):
            logger.debug("Unwrapped nodes from key: %r", key)
            return data[key]

    # Single beat as dict (not list) — wrap in list
    if "beat_name" in data or "title" in data:
        return [data]

    return None


# ---------------------------------------------------------------------------
# Node coercion: map LLM output to OutlineNode schema
# ---------------------------------------------------------------------------

_ACT_ALIASES: dict[str, ActPhase] = {
    "act1": ActPhase.ACT_1,
    "act_1": ActPhase.ACT_1,
    "act 1": ActPhase.ACT_1,
    "act2a": ActPhase.ACT_2A,
    "act_2a": ActPhase.ACT_2A,
    "act 2a": ActPhase.ACT_2A,
    "act2b": ActPhase.ACT_2B,
    "act_2b": ActPhase.ACT_2B,
    "act 2b": ActPhase.ACT_2B,
    "act3": ActPhase.ACT_3,
    "act_3": ActPhase.ACT_3,
    "act 3": ActPhase.ACT_3,
    # For frameworks without strict act splits
    "open": ActPhase.ACT_OPEN,
    "act_open": ActPhase.ACT_OPEN,
    "close": ActPhase.ACT_CLOSE,
    "act_close": ActPhase.ACT_CLOSE,
    # Fall-through
    "act2": ActPhase.ACT_2A,
    "act 2": ActPhase.ACT_2A,
}

_TENSION_ALIASES: dict[str, TensionLevel] = {
    "low": TensionLevel.LOW,
    "medium": TensionLevel.MEDIUM,
    "med": TensionLevel.MEDIUM,
    "high": TensionLevel.HIGH,
    "peak": TensionLevel.PEAK,
    "climax": TensionLevel.PEAK,
    "max": TensionLevel.PEAK,
}


def _coerce_act(value: Any) -> ActPhase:
    if isinstance(value, ActPhase):
        return value
    normalized = str(value).lower().strip()
    if normalized in _ACT_ALIASES:
        return _ACT_ALIASES[normalized]
    # Last resort: try direct enum lookup
    try:
        return ActPhase(normalized)
    except ValueError:
        logger.warning("Unknown act value %r, defaulting to ACT_1", value)
        return ActPhase.ACT_1


def _coerce_tension(value: Any) -> TensionLevel:
    if isinstance(value, TensionLevel):
        return value
    normalized = str(value).lower().strip()
    if normalized in _TENSION_ALIASES:
        return _TENSION_ALIASES[normalized]
    try:
        return TensionLevel(normalized)
    except ValueError:
        logger.warning("Unknown tension value %r, defaulting to MEDIUM", value)
        return TensionLevel.MEDIUM


def _coerce_node(raw_node: dict[str, Any]) -> OutlineNode:
    """
    Coerce a raw dict from LLM output to OutlineNode.
    Handles common key aliases (beat, beat_key, node_name → beat_name etc.)
    """
    # Normalise beat_name
    beat_name = (
        raw_node.get("beat_name")
        or raw_node.get("beat")
        or raw_node.get("beat_key")
        or raw_node.get("name")
        or raw_node.get("id")
        or "unknown"
    )

    # Normalise position
    position = float(raw_node.get("position", raw_node.get("pos", 0.0)))

    # Normalise act with alias mapping
    act_raw = raw_node.get("act", raw_node.get("act_phase", "act_1"))
    act = _coerce_act(act_raw)

    # Normalise tension
    tension_raw = raw_node.get("tension", raw_node.get("tension_level", "medium"))
    tension = _coerce_tension(tension_raw)

    return OutlineNode(
        beat_name=str(beat_name),
        position=position,
        act=act,
        title=str(raw_node.get("title", raw_node.get("heading", beat_name))),
        summary=str(raw_node.get("summary", raw_node.get("description", raw_node.get("content", "")))),
        tension=tension,
        scene_count=raw_node.get("scene_count"),
        key_events=raw_node.get("key_events", []),
        character_arcs=raw_node.get("character_arcs", {}),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_nodes(raw_content: str) -> ParseResult:
    """
    Parse LLM response into a list of OutlineNodes.

    Always returns a ParseResult — never raises.
    Caller inspects ParseResult.status to determine outcome.

    Status meanings:
      SUCCESS         → All nodes parsed and valid
      EMPTY           → LLM returned empty / whitespace / null
      MALFORMED_JSON  → Could not parse JSON even after preprocessing
      PARTIAL         → Some nodes valid, some failed (failed_nodes populated)
      SCHEMA_MISMATCH → JSON parsed but structure not recognisable as node list
    """
    if not raw_content or not raw_content.strip():
        return ParseResult(
            status=ParseStatus.EMPTY,
            raw_content=raw_content,
            error_message="LLM returned empty response",
        )

    preprocessed = _preprocess(raw_content)

    if not preprocessed:
        return ParseResult(
            status=ParseStatus.EMPTY,
            raw_content=raw_content,
            error_message="Response was empty after preprocessing",
        )

    # --- JSON Parsing ---
    try:
        data = json.loads(preprocessed)
    except json.JSONDecodeError as e:
        logger.warning("JSON parse failed: %s (first 200 chars: %r)", e, preprocessed[:200])
        return ParseResult(
            status=ParseStatus.MALFORMED_JSON,
            raw_content=raw_content,
            error_message=f"JSON parse error: {e}",
        )

    # --- Unwrap list ---
    node_list = _unwrap_nodes(data)
    if node_list is None:
        return ParseResult(
            status=ParseStatus.SCHEMA_MISMATCH,
            raw_content=raw_content,
            error_message=(
                f"Could not find node list in response. "
                f"Top-level type: {type(data).__name__}, "
                f"keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}"
            ),
        )

    if len(node_list) == 0:
        return ParseResult(
            status=ParseStatus.EMPTY,
            raw_content=raw_content,
            error_message="Node list was empty",
        )

    # --- Coerce each node ---
    nodes: list[OutlineNode] = []
    failed_nodes: list[dict[str, Any]] = []

    for raw_node in node_list:
        if not isinstance(raw_node, dict):
            failed_nodes.append({"raw": raw_node, "error": "Not a dict"})
            continue
        try:
            node = _coerce_node(raw_node)
            nodes.append(node)
        except (ValidationError, ValueError, TypeError) as e:
            logger.warning("Node coercion failed: %s for raw: %r", e, raw_node)
            failed_nodes.append({"raw": raw_node, "error": str(e)})

    if not nodes and failed_nodes:
        return ParseResult(
            status=ParseStatus.SCHEMA_MISMATCH,
            raw_content=raw_content,
            failed_nodes=failed_nodes,
            error_message=f"All {len(failed_nodes)} nodes failed coercion",
        )

    if failed_nodes:
        logger.warning(
            "Partial parse: %d nodes OK, %d failed", len(nodes), len(failed_nodes)
        )
        return ParseResult(
            status=ParseStatus.PARTIAL,
            nodes=nodes,
            raw_content=raw_content,
            failed_nodes=failed_nodes,
            error_message=f"{len(failed_nodes)} of {len(node_list)} nodes failed",
        )

    return ParseResult(
        status=ParseStatus.SUCCESS,
        nodes=nodes,
        raw_content=raw_content,
    )
