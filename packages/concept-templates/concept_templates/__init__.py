"""iil-concept-templates — Shared concept template schemas and frameworks.

See ADR-147 for architecture decisions.
"""

__version__ = "0.4.0"

from concept_templates.schemas import (
    AnalysisResult,
    ConceptScope,
    ConceptTemplate,
    ExtractionResult,
    FieldType,
    TemplateField,
    TemplateSection,
    known_scopes,
)

__all__ = [
    "AnalysisResult",
    "ConceptScope",
    "ConceptTemplate",
    "ExtractionResult",
    "FieldType",
    "TemplateField",
    "TemplateSection",
    "known_scopes",
    # Phase C — lazy imports via analyzer/prompts modules
    # from concept_templates.analyzer import analyze_document_structure, merge_templates
    # from concept_templates.prompts import get_structure_analysis_prompts
]
