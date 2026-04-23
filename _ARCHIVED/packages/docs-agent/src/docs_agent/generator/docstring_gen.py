"""LLM-based docstring generator.

Generates Google-style docstrings for undocumented Python code items
using the llm_mcp HTTP gateway or direct OpenAI API.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from docs_agent.llm_client import LLMConfig, LLMResponse, generate
from docs_agent.models import CodeItem
from docs_agent.prompts import PROMPT_DOCSTRING_BATCH, SYSTEM_DOCSTRING

logger = logging.getLogger(__name__)

BATCH_SIZE = 10


@dataclass
class GeneratedDocstring:
    """A generated docstring for a code item."""

    item: CodeItem
    docstring: str
    confidence: float
    source_code: str = ""


def _extract_item_source(file_path: Path, item: CodeItem) -> str:
    """Extract source code for a single item from its file.

    Args:
        file_path: Path to the Python file.
        item: The code item to extract.

    Returns:
        Source code string (up to 30 lines).
    """
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""

    start = item.line - 1
    end = min(start + 30, len(lines))

    # For functions/methods, find the end by indentation
    if start < len(lines):
        base_indent = len(lines[start]) - len(lines[start].lstrip())
        for i in range(start + 1, end):
            if lines[i].strip() and (
                len(lines[i]) - len(lines[i].lstrip()) <= base_indent
            ):
                end = i
                break

    return "\n".join(lines[start:end])


def _build_batch_items(
    items: list[CodeItem],
    file_path: Path,
) -> list[dict[str, str]]:
    """Build batch items JSON for the LLM prompt.

    Args:
        items: Undocumented code items.
        file_path: Path to source file.

    Returns:
        List of dicts with name, kind, code for the prompt.
    """
    result = []
    for item in items:
        code = _extract_item_source(file_path, item)
        if code:
            result.append({
                "name": item.name,
                "kind": item.kind.value,
                "code": code,
            })
    return result


async def generate_docstrings(
    items: list[CodeItem],
    *,
    config: Optional[LLMConfig] = None,
) -> list[GeneratedDocstring]:
    """Generate docstrings for a list of undocumented code items.

    Args:
        items: Undocumented CodeItem instances (from AST scanner).
        config: LLM configuration.

    Returns:
        List of GeneratedDocstring results.
    """
    if not items:
        return []

    results: list[GeneratedDocstring] = []

    # Group items by file
    by_file: dict[Path, list[CodeItem]] = {}
    for item in items:
        by_file.setdefault(item.file_path, []).append(item)

    for file_path, file_items in by_file.items():
        # Process in batches
        for i in range(0, len(file_items), BATCH_SIZE):
            batch = file_items[i:i + BATCH_SIZE]
            batch_results = await _generate_batch(
                batch, file_path, config=config
            )
            results.extend(batch_results)

    return results


async def _generate_batch(
    items: list[CodeItem],
    file_path: Path,
    *,
    config: Optional[LLMConfig] = None,
) -> list[GeneratedDocstring]:
    """Generate docstrings for a batch of items from one file.

    Args:
        items: Batch of undocumented items.
        file_path: Source file path.
        config: LLM configuration.

    Returns:
        List of GeneratedDocstring for this batch.
    """
    batch_data = _build_batch_items(items, file_path)
    if not batch_data:
        return []

    prompt = PROMPT_DOCSTRING_BATCH.format(
        items_json=json.dumps(batch_data, indent=2)
    )

    response: LLMResponse = await generate(
        prompt,
        system_prompt=SYSTEM_DOCSTRING,
        config=config,
    )

    if not response.success:
        logger.warning(
            "LLM call failed for %s: %s",
            file_path, response.error,
        )
        return []

    return _parse_batch_response(response, items, file_path)


def _parse_batch_response(
    response: LLMResponse,
    items: list[CodeItem],
    file_path: Path,
) -> list[GeneratedDocstring]:
    """Parse LLM batch response into GeneratedDocstring list.

    Args:
        response: LLM response.
        items: Original code items.
        file_path: Source file path.

    Returns:
        Parsed GeneratedDocstring list.
    """
    content = response.content
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from LLM response")
            return []

    if not isinstance(content, dict):
        return []

    docstrings_data = content.get("docstrings", [])
    if not isinstance(docstrings_data, list):
        return []

    # Build lookup by name
    item_map = {item.name: item for item in items}
    results: list[GeneratedDocstring] = []

    for entry in docstrings_data:
        name = entry.get("name", "")
        docstring = entry.get("docstring", "")
        confidence = float(entry.get("confidence", 0.5))

        item = item_map.get(name)
        if item and docstring:
            results.append(
                GeneratedDocstring(
                    item=item,
                    docstring=docstring,
                    confidence=confidence,
                    source_code=_extract_item_source(file_path, item),
                )
            )

    return results
