"""Pydantic v2 schemas for concept templates."""

from __future__ import annotations

import sys
from datetime import date

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        """Backport for Python 3.10."""

from pydantic import BaseModel, Field


class ConceptScope(StrEnum):
    """Fachbereich eines Konzepts."""

    BRANDSCHUTZ = "brandschutz"
    EXPLOSIONSSCHUTZ = "explosionsschutz"
    AUSSCHREIBUNG = "ausschreibung"


class FieldType(StrEnum):
    """Unterstützte Feldtypen in Template-Sektionen."""

    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    DATE = "date"
    CHOICE = "choice"
    FILE = "file"
    BOOLEAN = "boolean"


class TemplateField(BaseModel):
    """Einzelnes Feld innerhalb einer Template-Sektion."""

    name: str
    label: str
    field_type: FieldType
    required: bool = False
    default: str | None = None
    choices: list[str] | None = None
    help_text: str = ""


class TemplateSection(BaseModel):
    """Kapitel/Abschnitt eines Konzept-Templates."""

    name: str
    title: str
    description: str = ""
    required: bool = True
    order: int = 0
    fields: list[TemplateField] = Field(default_factory=list)
    subsections: list[TemplateSection] = Field(default_factory=list)


class ConceptTemplate(BaseModel):
    """Vollständiges Konzept-Template (Master oder Kunden-Variante)."""

    name: str
    scope: ConceptScope
    version: str = "1.0"
    is_master: bool = False
    framework: str = ""
    framework_version: str = "1.0"
    valid_from: date | None = None
    valid_until: date | None = None
    sections: list[TemplateSection] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ExtractionResult(BaseModel):
    """Ergebnis einer PDF-Text-Extraktion."""

    text: str
    page_count: int
    metadata: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """Ergebnis einer LLM-Strukturanalyse."""

    proposed_template: ConceptTemplate
    confidence: float = Field(ge=0.0, le=1.0)
    gaps: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
