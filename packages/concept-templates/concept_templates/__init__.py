"""iil-concept-templates — Shared concept template schemas and frameworks.

See ADR-147 for architecture decisions.
"""

__version__ = "0.1.0"

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
]
