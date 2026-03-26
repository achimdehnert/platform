"""LLM-based field prefill for concept templates (ADR-147 Phase E).

Provides a reusable service function that any consumer app can call
to get an AI-suggested value for a single template field.

Usage:
    from concept_templates.prefill import prefill_field

    value = prefill_field(
        field_key="standort__adresse",
        llm_hint="Beschreibe die Adresse des Gebäudes",
        context_values={"standort": {"name": "Rathaus"}},
        extracted_texts=["Rathaus, Marktplatz 1, 12345 Musterstadt..."],
        scope="brandschutz",
        llm_fn=my_llm_wrapper,
    )
"""

from __future__ import annotations

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)

LLMCallable = Callable[[str, str], str]

SYSTEM_PROMPT_DE = (
    "Du bist ein Experte für {scope}-Konzepte. "
    "Fülle das angeforderte Feld basierend auf dem Kontext aus. "
    "Antworte NUR mit dem Feldwert, keine Erklärung, kein Markdown."
)

SYSTEM_PROMPT_EN = (
    "You are an expert for {scope} concepts. "
    "Fill the requested field based on the context. "
    "Reply ONLY with the field value, no explanation, no markdown."
)

MAX_CONTEXT_CHARS = 4000
MAX_EXTRACTED_CHARS = 3000


def prefill_field(
    field_key: str,
    llm_hint: str,
    llm_fn: LLMCallable,
    context_values: dict[str, dict[str, str]] | None = None,
    extracted_texts: list[str] | None = None,
    scope: str = "brandschutz",
    language: str = "de",
) -> str:
    """Generate an AI-suggested value for a single template field.

    Args:
        field_key: Form field key (section__field format).
        llm_hint: The prompt hint for this field (from TemplateField.llm_hint).
        llm_fn: Callable (system_prompt, user_prompt) -> raw_response.
        context_values: Already filled values {section: {field: value}}.
        extracted_texts: Raw texts from analyzed documents.
        scope: Fachbereich for the system prompt.
        language: "de" or "en" for system prompt language.

    Returns:
        The suggested value (stripped), or empty string on failure.
    """
    if not llm_hint:
        return ""

    # Build context
    context_parts: list[str] = []

    if context_values:
        for _section, fields in context_values.items():
            for fname, fval in fields.items():
                if fval:
                    context_parts.append(f"{fname}: {fval}")

    context_text = "\n".join(context_parts)[:MAX_CONTEXT_CHARS]

    # Add extracted document texts
    if extracted_texts:
        for i, text in enumerate(extracted_texts[:3]):
            if text:
                context_text += f"\n\n--- Dokument {i + 1} ---\n"
                context_text += text[:MAX_EXTRACTED_CHARS]

    # Select system prompt
    template = SYSTEM_PROMPT_DE if language == "de" else SYSTEM_PROMPT_EN
    system_prompt = template.format(scope=scope)

    user_prompt = (
        f"Kontext:\n{context_text}\n\n"
        f"Aufgabe: {llm_hint}\n\n"
        f"Feld: {field_key}\n"
        f"Wert:"
    )

    try:
        result = llm_fn(system_prompt, user_prompt)
        return result.strip()
    except Exception as exc:
        logger.warning("LLM prefill failed for %s: %s", field_key, exc)
        return ""
