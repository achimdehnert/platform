"""LLM prefill service — prompt building and execution.

Covers optimizations:
  #1 — Real source content via retriever hooks
  #5 — max_tokens per field type
  #7 — Field-type-specific LLM output instructions
"""

import json
import logging

from ..constants import (
    AI_SOURCE_TYPES,
    DEFAULT_MAX_TOKENS,
    MAX_TOKENS_BY_FIELD_TYPE,
)
from .retriever import get_all_source_content

logger = logging.getLogger(__name__)


# ── Field-type-specific instructions (#7) ───────────────────────

_FIELD_TYPE_INSTRUCTIONS: dict[str, str] = {
    "textarea": (
        "Antworte NUR mit dem Feldinhalt als Fließtext. "
        "Keine Erklärungen, keine Überschriften."
    ),
    "text": (
        "Antworte NUR mit einem kurzen, prägnanten Text (1-2 Sätze). "
        "Keine Erklärungen."
    ),
    "table": (
        "Antworte NUR mit einer JSON-Liste von Zeilen. "
        "Jede Zeile ist eine Liste von Zellwerten. "
        'Beispiel: [["Wert1", "Wert2"], ["Wert3", "Wert4"]] '
        "Keine Erklärungen, nur valides JSON."
    ),
    "number": "Antworte NUR mit einer Zahl. Keine Einheit, keine Erklärung.",
    "date": "Antworte NUR mit einem Datum im Format YYYY-MM-DD.",
    "boolean": "Antworte NUR mit 'Ja' oder 'Nein'.",
}


def build_prefill_prompt(
    *,
    field_key: str,
    field_type: str,
    llm_hint: str,
    ai_sources: list[str],
    scope: str,
    existing_values: dict,
    source_text: str,
    tenant_id: str,
    instance=None,
    table_columns: list[str] | None = None,
) -> tuple[str, str, int]:
    """Build system prompt, user prompt, and max_tokens for LLM prefill.

    Returns:
        (system_prompt, user_prompt, max_tokens)
    """
    # System prompt with scope and field-type instruction
    field_instruction = _FIELD_TYPE_INSTRUCTIONS.get(
        field_type, _FIELD_TYPE_INSTRUCTIONS["textarea"],
    )
    system_prompt = (
        f"Du bist ein Experte für {scope or 'Fachbereich'} "
        "und technische Dokumentation. "
        "Schreibe fachlich korrekte, präzise Texte auf Deutsch. "
        f"{field_instruction}"
    )

    # User prompt: template-defined prompt as primary instruction
    user_prompt = f"Aufgabe: {llm_hint}\n"

    # Table-specific column info (#7)
    if field_type == "table" and table_columns:
        cols_str = ", ".join(f'"{c}"' for c in table_columns)
        user_prompt += (
            f"\nTabellen-Spalten: [{cols_str}]\n"
            "Jede Zeile muss genau diese Anzahl Spalten haben.\n"
        )

    # Real source content via retriever hooks (#1)
    if ai_sources and instance is not None:
        retrieved = get_all_source_content(
            ai_sources, tenant_id, instance,
        )
        if retrieved:
            user_prompt += "\n--- Quellen-Dokumente ---\n"
            for src_type, texts in retrieved.items():
                label = AI_SOURCE_TYPES.get(src_type, src_type)
                for i, txt in enumerate(texts[:3]):  # max 3 per type
                    user_prompt += (
                        f"\n[{label}"
                        f"{f' ({i+1})' if len(texts) > 1 else ''}]:\n"
                        f"{txt[:3000]}\n"
                    )

    # Fallback: source type labels if no real content retrieved
    if ai_sources:
        src_names = [AI_SOURCE_TYPES.get(s, s) for s in ai_sources]
        user_prompt += (
            "\nBerücksichtige folgende Dokumenttypen "
            "als fachliche Grundlage:\n- "
            + "\n- ".join(src_names) + "\n"
        )

    # Existing field values as context
    if existing_values:
        context_parts = []
        for skey, svals in existing_values.items():
            if not isinstance(svals, dict):
                continue
            for fkey, fval in svals.items():
                if isinstance(fval, str) and fval.strip():
                    context_parts.append(f"{fkey}: {fval[:300]}")
        if context_parts:
            user_prompt += (
                "\nBereits ausgefüllte Felder:\n"
                + "\n".join(context_parts[:10]) + "\n"
            )

    # Template source text as reference
    if source_text:
        user_prompt += (
            f"\nReferenz-Dokument:\n{source_text[:5000]}\n"
        )

    user_prompt += f"\nSchreibe den Inhalt für das Feld '{field_key}'."

    # max_tokens per field type (#5)
    max_tokens = MAX_TOKENS_BY_FIELD_TYPE.get(
        field_type, DEFAULT_MAX_TOKENS,
    )

    return system_prompt, user_prompt, max_tokens


def execute_llm_prefill(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
) -> str:
    """Execute LLM call and return generated text.

    Raises:
        ImportError: If no LLM backend available.
        Exception: On LLM call failure.
    """
    try:
        from aifw.service import sync_completion
        return sync_completion(
            prompt=user_prompt,
            system=system_prompt,
            action_code="doc_template_prefill",
            temperature=0.3,
            max_tokens=max_tokens,
        )
    except ImportError:
        pass

    try:
        from ai_analysis.llm_client import llm_complete_sync
        return llm_complete_sync(
            prompt=user_prompt,
            system=system_prompt,
            action_code="doc_template_prefill",
            temperature=0.3,
            max_tokens=max_tokens,
        )
    except ImportError:
        pass

    raise ImportError(
        "LLM nicht verfügbar (iil-aifw oder ai_analysis benötigt)"
    )


def parse_table_response(raw: str, num_columns: int) -> list[list[str]]:
    """Parse LLM table response (JSON array) into rows.

    Falls back to splitting by lines if JSON parsing fails.
    """
    raw = raw.strip()

    # Try JSON parse first
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            rows = []
            for row in data:
                if isinstance(row, list):
                    # Pad or trim to num_columns
                    cells = [str(c) for c in row]
                    while len(cells) < num_columns:
                        cells.append("")
                    rows.append(cells[:num_columns])
            if rows:
                return rows
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: line-based splitting
    rows = []
    for line in raw.split("\n"):
        line = line.strip().strip("|").strip()
        if not line or line.startswith("---"):
            continue
        cells = [c.strip() for c in line.split("|")]
        if not cells:
            cells = [c.strip() for c in line.split("\t")]
        while len(cells) < num_columns:
            cells.append("")
        rows.append(cells[:num_columns])

    return rows
