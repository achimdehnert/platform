"""Prompt rendering for concept structure analysis (ADR-147 Phase C).

Delegates to ``promptfw.concept_analysis`` for all prompt templates.
Requires the [llm] extra: ``pip install iil-concept-templates[llm]``

Public API (backward-compatible):
    - get_structure_analysis_prompts(context, language) -> (system, user)
    - get_merge_prompts(context, language) -> (system, user)
    - get_stack() -> PromptStack (for advanced usage)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "de"

try:
    from promptfw.concept_analysis import get_concept_analysis_stack

    _HAS_PROMPTFW = True
except ImportError:
    _HAS_PROMPTFW = False


def _get_scopes_string() -> str:
    """Build comma-separated scope list from the framework registry."""
    try:
        from concept_templates.registry import list_frameworks

        frameworks = list_frameworks()
        scopes = sorted({fw.scope for fw in frameworks.values()})
        if scopes:
            return ", ".join(s.capitalize() for s in scopes)
    except Exception:
        pass
    return "Brandschutz, Explosionsschutz, Ausschreibungen"


def _enrich_context(context: dict, language: str) -> dict:
    """Add scopes and language to the render context."""
    ctx = dict(context)
    ctx.setdefault("scopes", _get_scopes_string())
    ctx.setdefault("language", language)
    return ctx


def get_stack():
    """Return the shared concept-analysis PromptStack from promptfw."""
    if not _HAS_PROMPTFW:
        raise ImportError(
            "iil-promptfw is required for LLM analysis. "
            "Install: pip install iil-concept-templates[llm]"
        )
    return get_concept_analysis_stack()


def get_structure_analysis_prompts(
    context: dict,
    language: str = DEFAULT_LANGUAGE,
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for document structure analysis.

    Args:
        context: scope, title, page_count, text.
        language: "de" or "en".
    """
    if not _HAS_PROMPTFW:
        logger.warning("promptfw not installed — using minimal fallback")
        return _fallback_analysis(context, language)

    ctx = _enrich_context(context, language)
    stack = get_concept_analysis_stack()
    rendered = stack.render_stack(
        ["concept.system.analyst", "concept.task.analyze_structure"],
        context=ctx,
    )
    return rendered.system, rendered.user


def get_merge_prompts(
    context: dict,
    language: str = DEFAULT_LANGUAGE,
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for template merging.

    Args:
        context: template_count, scope, templates_json.
        language: "de" or "en".
    """
    if not _HAS_PROMPTFW:
        logger.warning("promptfw not installed — using minimal fallback")
        return _fallback_merge(context, language)

    ctx = _enrich_context(context, language)
    stack = get_concept_analysis_stack()
    rendered = stack.render_stack(
        ["concept.system.merger", "concept.task.merge_templates"],
        context=ctx,
    )
    return rendered.system, rendered.user


# ── Minimal fallback (no promptfw installed) ──────────────────────

def _fallback_analysis(
    context: dict, language: str,
) -> tuple[str, str]:
    """Plain-string fallback when promptfw is not available."""
    scopes = _get_scopes_string()
    lang = ("Antworte immer auf Deutsch."
            if language != "en"
            else "Always respond in English.")
    system = (
        f"Du bist ein Experte für die Strukturanalyse von "
        f"technischen Konzeptdokumenten ({scopes}).\n"
        f"{lang} Strukturiere deine Antwort als JSON."
    )
    user = (
        f"Analysiere den Text eines "
        f"{context.get('scope', '')}-Konzeptdokuments.\n"
        f"Titel: {context.get('title', 'Unbekannt')}\n"
        f"Seitenanzahl: {context.get('page_count', 0)}\n\n"
        f"Text:\n{context.get('text', '')}"
    )
    return system, user


def _fallback_merge(
    context: dict, language: str,
) -> tuple[str, str]:
    """Plain-string fallback when promptfw is not available."""
    lang = ("Antworte immer auf Deutsch."
            if language != "en"
            else "Always respond in English.")
    system = (
        "Du bist ein Experte für die Zusammenführung von "
        f"Dokumentvorlagen.\n{lang} Antworte als JSON."
    )
    user = (
        f"Führe {context.get('template_count', 0)} Templates "
        f"aus dem Bereich {context.get('scope', '')} zusammen.\n\n"
        f"{context.get('templates_json', '[]')}"
    )
    return system, user
