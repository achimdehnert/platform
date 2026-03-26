"""iil-concept-templates — Shared concept template schemas and frameworks.

See ADR-147 for architecture decisions.
"""

__version__ = "0.2.0"

from concept_templates.schemas import (
    AnalysisResult,
    ConceptScope,
    ConceptTemplate,
    ExtractionResult,
    FieldType,
    TemplateField,
    TemplateSection,
)

__all__ = [
    "AnalysisResult",
    "ConceptScope",
    "ConceptTemplate",
    "ExtractionResult",
    "FieldType",
    "TemplateField",
    "TemplateSection",
    # Phase C — lazy imports via analyzer/prompts modules
    # from concept_templates.analyzer import analyze_document_structure, merge_templates
    # from concept_templates.prompts import get_structure_analysis_prompts
]
