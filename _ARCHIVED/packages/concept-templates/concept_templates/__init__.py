"""iil-concept-templates — Shared concept template schemas and frameworks.

See ADR-147 for architecture decisions.
"""

__version__ = "0.5.0"

from concept_templates.pdf_structure_extractor import (
    analyze_section_content,
    clean_toc_title,
    detect_table_columns,
    extract_structure_from_text,
)
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
    # Phase F — PDF structure extraction
    "extract_structure_from_text",
    "clean_toc_title",
    "detect_table_columns",
    "analyze_section_content",
]
