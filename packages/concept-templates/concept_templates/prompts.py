"""Prompt templates for concept structure analysis — powered by iil-promptfw (ADR-147 Phase C).

Requires the [llm] extra: pip install iil-concept-templates[llm]

Falls back to plain dicts if promptfw is not installed (for testing).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from promptfw import PromptStack, PromptTemplate, TemplateLayer

    _HAS_PROMPTFW = True
except ImportError:
    _HAS_PROMPTFW = False


# ── System prompts ──────────────────────────────────────────────────

SYSTEM_STRUCTURE_ANALYSIS = (
    "Du bist ein Experte für die Strukturanalyse von technischen Konzeptdokumenten "
    "(Brandschutz, Explosionsschutz, Ausschreibungen).\n"
    "Du analysierst den extrahierten Text eines Dokuments und identifizierst "
    "die Kapitelstruktur, Pflichtabschnitte und Formularfelder.\n"
    "Antworte immer auf Deutsch. Strukturiere deine Antwort ausschließlich als JSON."
)

SYSTEM_TEMPLATE_MERGE = (
    "Du bist ein Experte für die Zusammenführung von Dokumentvorlagen.\n"
    "Du erhältst mehrere analysierte Konzept-Strukturen und erstellst daraus "
    "ein konsolidiertes Master-Template mit den häufigsten Abschnitten und Feldern.\n"
    "Antworte immer auf Deutsch. Strukturiere deine Antwort ausschließlich als JSON."
)

# ── Task prompts ────────────────────────────────────────────────────

TASK_ANALYZE_STRUCTURE = """Analysiere den folgenden extrahierten Text eines {{ scope }}-Konzeptdokuments \
und identifiziere die Struktur:

**Dokumenttitel:** {{ title }}
**Fachbereich:** {{ scope }}
**Seitenanzahl:** {{ page_count }}

**Extrahierter Text (gekürzt auf max. 8000 Zeichen):**
{{ text }}

Erstelle eine Strukturanalyse im folgenden JSON-Format:
{
  "name": "Template-Name basierend auf dem Dokument",
  "scope": "{{ scope }}",
  "version": "1.0",
  "is_master": false,
  "framework": "Erkanntes Regelwerk (z.B. MBO, TRGS 720, VOB)",
  "sections": [
    {
      "name": "abschnitt_id",
      "title": "Kapiteltitel",
      "description": "Kurzbeschreibung des Abschnitts",
      "required": true,
      "order": 1,
      "fields": [
        {
          "name": "feld_id",
          "label": "Feldbezeichnung",
          "field_type": "text|textarea|number|date|choice|boolean",
          "required": true,
          "help_text": "Hinweis zum Feld"
        }
      ],
      "subsections": []
    }
  ],
  "confidence": 0.85,
  "gaps": ["Fehlender Abschnitt X", "Unklare Struktur bei Y"],
  "recommendations": ["Empfehlung 1", "Empfehlung 2"]
}"""

TASK_MERGE_TEMPLATES = """Du erhältst {{ template_count }} analysierte Konzept-Strukturen \
aus dem Fachbereich {{ scope }}.

Erstelle daraus ein konsolidiertes Master-Template, das die häufigsten und \
wichtigsten Abschnitte und Felder enthält.

**Analysierte Strukturen:**
{{ templates_json }}

Erstelle das Master-Template im folgenden JSON-Format:
{
  "name": "Master-Template {{ scope }}",
  "scope": "{{ scope }}",
  "version": "1.0",
  "is_master": true,
  "framework": "Hauptsächlich verwendetes Regelwerk",
  "sections": [
    {
      "name": "abschnitt_id",
      "title": "Kapiteltitel",
      "description": "Beschreibung",
      "required": true,
      "order": 1,
      "fields": [
        {
          "name": "feld_id",
          "label": "Feldbezeichnung",
          "field_type": "text|textarea|number|date|choice|boolean",
          "required": true,
          "help_text": "Hinweis"
        }
      ],
      "subsections": []
    }
  ],
  "confidence": 0.9,
  "gaps": [],
  "recommendations": ["Empfehlung"]
}"""


def _build_stack() -> PromptStack:
    """Build and return the PromptStack for concept analysis."""
    if not _HAS_PROMPTFW:
        raise ImportError(
            "promptfw is required for LLM analysis. "
            "Install with: pip install iil-concept-templates[llm]"
        )

    stack = PromptStack()

    stack.register(
        PromptTemplate(
            id="concept.structure.system",
            layer=TemplateLayer.SYSTEM,
            template=SYSTEM_STRUCTURE_ANALYSIS,
            variables=[],
        )
    )

    stack.register(
        PromptTemplate(
            id="concept.structure.task",
            layer=TemplateLayer.TASK,
            template=TASK_ANALYZE_STRUCTURE,
            variables=["scope", "title", "page_count", "text"],
        )
    )

    stack.register(
        PromptTemplate(
            id="concept.merge.system",
            layer=TemplateLayer.SYSTEM,
            template=SYSTEM_TEMPLATE_MERGE,
            variables=[],
        )
    )

    stack.register(
        PromptTemplate(
            id="concept.merge.task",
            layer=TemplateLayer.TASK,
            template=TASK_MERGE_TEMPLATES,
            variables=["template_count", "scope", "templates_json"],
        )
    )

    return stack


# Lazy singleton
_STACK: PromptStack | None = None


def get_stack() -> PromptStack:
    """Get the shared PromptStack (lazy-loaded)."""
    global _STACK
    if _STACK is None:
        _STACK = _build_stack()
    return _STACK


def get_structure_analysis_messages(context: dict) -> list[dict]:
    """Returns OpenAI-compatible messages for document structure analysis."""
    return get_stack().render_to_messages(
        ["concept.structure.system", "concept.structure.task"],
        context=context,
    )


def get_merge_messages(context: dict) -> list[dict]:
    """Returns OpenAI-compatible messages for template merging."""
    return get_stack().render_to_messages(
        ["concept.merge.system", "concept.merge.task"],
        context=context,
    )


def get_structure_analysis_prompts(context: dict) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt) tuple for structure analysis.

    Fallback for environments without promptfw — uses simple string formatting.
    """
    if _HAS_PROMPTFW:
        messages = get_structure_analysis_messages(context)
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user = next((m["content"] for m in messages if m["role"] == "user"), "")
        return system, user

    # Fallback: simple string interpolation
    from string import Template

    system = SYSTEM_STRUCTURE_ANALYSIS
    user = Template(TASK_ANALYZE_STRUCTURE.replace("{{", "${").replace("}}", "")).safe_substitute(context)
    return system, user


def get_merge_prompts(context: dict) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt) tuple for template merging."""
    if _HAS_PROMPTFW:
        messages = get_merge_messages(context)
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user = next((m["content"] for m in messages if m["role"] == "user"), "")
        return system, user

    from string import Template

    system = SYSTEM_TEMPLATE_MERGE
    user = Template(TASK_MERGE_TEMPLATES.replace("{{", "${").replace("}}", "")).safe_substitute(context)
    return system, user
