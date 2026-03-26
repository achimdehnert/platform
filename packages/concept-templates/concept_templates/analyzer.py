"""LLM-based document structure analysis (ADR-147 Phase C).

Accepts a callable ``llm_fn(system, user) -> str`` so the package stays
free of direct aifw dependency. risk-hub wires this with
``aifw.service.sync_completion`` via Celery tasks.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable

from concept_templates.schemas import AnalysisResult, ConceptScope, ConceptTemplate

logger = logging.getLogger(__name__)

# Type alias for the LLM callable: (system_prompt, user_prompt) -> raw_response
LLMCallable = Callable[[str, str], str]

MAX_TEXT_CHARS = 8000


def analyze_document_structure(
    text: str,
    scope: str | ConceptScope,
    title: str = "",
    page_count: int = 0,
    llm_fn: LLMCallable | None = None,
) -> AnalysisResult:
    """Analyze extracted document text and produce a ConceptTemplate.

    Args:
        text: Extracted text from PDF (may be truncated to MAX_TEXT_CHARS).
        scope: Fachbereich (brandschutz, explosionsschutz, ausschreibung).
        title: Document title for context.
        page_count: Number of pages extracted.
        llm_fn: Callable that takes (system_prompt, user_prompt) and returns
                 the raw LLM response string. If None, raises ValueError.

    Returns:
        AnalysisResult with proposed ConceptTemplate and confidence.

    Raises:
        ValueError: If llm_fn is None or LLM response cannot be parsed.
    """
    if llm_fn is None:
        raise ValueError("llm_fn is required for structure analysis.")

    scope_str = scope.value if isinstance(scope, ConceptScope) else str(scope)
    truncated_text = text[:MAX_TEXT_CHARS]

    # Build prompts
    from concept_templates.prompts import get_structure_analysis_prompts

    system_prompt, user_prompt = get_structure_analysis_prompts({
        "scope": scope_str,
        "title": title or "Unbekannt",
        "page_count": str(page_count),
        "text": truncated_text,
    })

    # Call LLM
    raw_response = llm_fn(system_prompt, user_prompt)

    # Parse response
    return _parse_analysis_response(raw_response, scope_str)


def merge_templates(
    templates: list[ConceptTemplate],
    scope: str | ConceptScope,
    llm_fn: LLMCallable | None = None,
) -> AnalysisResult:
    """Merge multiple analyzed templates into a master template.

    This is the key function for the "viele Dokumente → ein Template" workflow.

    Args:
        templates: List of ConceptTemplate instances to merge.
        scope: Target scope for the master template.
        llm_fn: LLM callable for intelligent merging.

    Returns:
        AnalysisResult with the merged master template.
    """
    if not templates:
        raise ValueError("At least one template is required for merging.")

    if len(templates) == 1:
        # Single template — just promote to master
        template = templates[0].model_copy(update={"is_master": True})
        return AnalysisResult(
            proposed_template=template,
            confidence=0.95,
            gaps=[],
            recommendations=["Nur ein Dokument analysiert — mehr Dokumente für bessere Abdeckung empfohlen."],
        )

    if llm_fn is None:
        # Fallback: rule-based merge without LLM
        return _merge_templates_rule_based(templates, scope)

    scope_str = scope.value if isinstance(scope, ConceptScope) else str(scope)

    # Serialize templates for the LLM
    from concept_templates.export import to_dict

    templates_data = [to_dict(t) for t in templates]
    templates_json = json.dumps(templates_data, ensure_ascii=False, indent=2)

    # Truncate if too long
    if len(templates_json) > MAX_TEXT_CHARS:
        templates_json = templates_json[:MAX_TEXT_CHARS] + "\n... (gekürzt)"

    from concept_templates.prompts import get_merge_prompts

    system_prompt, user_prompt = get_merge_prompts({
        "template_count": str(len(templates)),
        "scope": scope_str,
        "templates_json": templates_json,
    })

    raw_response = llm_fn(system_prompt, user_prompt)
    return _parse_analysis_response(raw_response, scope_str)


def _parse_analysis_response(raw: str, scope: str) -> AnalysisResult:
    """Parse LLM JSON response into AnalysisResult."""
    # Try promptfw.extract_json first
    parsed = None
    try:
        from promptfw import extract_json

        parsed = extract_json(raw)
    except ImportError:
        pass

    if parsed is None:
        parsed = _extract_json_fallback(raw)

    if parsed is None:
        raise ValueError(f"Could not parse LLM response as JSON. Raw: {raw[:200]}...")

    # Extract confidence, gaps, recommendations from top level
    confidence = float(parsed.pop("confidence", 0.7))
    confidence = max(0.0, min(1.0, confidence))
    gaps = parsed.pop("gaps", [])
    recommendations = parsed.pop("recommendations", [])

    # Ensure scope is set
    parsed.setdefault("scope", scope)
    parsed.setdefault("name", f"Analysiertes Template ({scope})")

    # Build ConceptTemplate
    try:
        template = ConceptTemplate.model_validate(parsed)
    except Exception as exc:
        logger.warning("Failed to validate ConceptTemplate: %s", exc)
        # Attempt minimal template
        template = ConceptTemplate(
            name=parsed.get("name", f"Template ({scope})"),
            scope=ConceptScope(scope),
        )
        gaps.append(f"Template-Validierung fehlgeschlagen: {exc}")
        confidence = max(0.1, confidence - 0.3)

    return AnalysisResult(
        proposed_template=template,
        confidence=confidence,
        gaps=gaps,
        recommendations=recommendations,
    )


def _extract_json_fallback(text: str) -> dict | None:
    """Extract JSON from text, handling markdown code fences."""
    # Try direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try extracting from markdown fences
    import re

    pattern = r"```(?:json)?\s*\n(.*?)\n```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass

    # Try finding first { ... } block
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except (json.JSONDecodeError, TypeError):
                        pass
                    break

    return None


def _merge_templates_rule_based(
    templates: list[ConceptTemplate],
    scope: str | ConceptScope,
) -> AnalysisResult:
    """Simple rule-based merge: union of all sections, deduplicate by name."""
    scope_str = scope.value if isinstance(scope, ConceptScope) else str(scope)

    seen_sections: dict[str, dict] = {}
    for tmpl in templates:
        for section in tmpl.sections:
            key = section.name.lower().strip()
            if key not in seen_sections:
                seen_sections[key] = section.model_dump()
            else:
                # Merge fields
                existing_fields = {f["name"] for f in seen_sections[key].get("fields", [])}
                for field in section.model_dump().get("fields", []):
                    if field["name"] not in existing_fields:
                        seen_sections[key]["fields"].append(field)

    from concept_templates.schemas import TemplateSection

    merged_sections = []
    for i, section_data in enumerate(seen_sections.values()):
        section_data["order"] = i + 1
        merged_sections.append(TemplateSection.model_validate(section_data))

    framework = templates[0].framework if templates else ""
    merged = ConceptTemplate(
        name=f"Master-Template {scope_str} (regelbasiert)",
        scope=ConceptScope(scope_str),
        is_master=True,
        framework=framework,
        sections=merged_sections,
    )

    return AnalysisResult(
        proposed_template=merged,
        confidence=0.6,
        gaps=["Regelbasierte Zusammenführung ohne LLM — Qualität eingeschränkt."],
        recommendations=[
            "LLM-basierte Analyse für bessere Ergebnisse empfohlen.",
            f"{len(templates)} Dokumente analysiert, {len(merged_sections)} Abschnitte zusammengeführt.",
        ],
    )
