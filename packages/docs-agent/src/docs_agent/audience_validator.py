"""
Pydantic v2 Schema-Validierung für audience.yaml-Dateien.

Wird verwendet in:
  - `load_audience_config` Management Command (dev-hub)
  - `/session-docu --audit`
  - docs-agent CLI

Löst Review-Befund H-01 (keine Validation) und H-02 (fragiler query-String).
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Annotated, Union

import yaml
from pydantic import BaseModel, Discriminator, Field, Tag, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums (Review-Fix H-02: keine freien Strings mehr)
# ---------------------------------------------------------------------------


class SourceType(str, Enum):
    GITHUB = "github"
    OUTLINE = "outline"
    TECHDOCS = "techdocs"
    DEVHUB = "devhub"


class AudienceRole(str, Enum):
    USER = "user"
    DEVELOPER = "developer"
    ARCHITECT = "architect"
    OPERATOR = "operator"


# ---------------------------------------------------------------------------
# Source Models (role-spezifisch für klarere Validierung)
# ---------------------------------------------------------------------------


class GitHubSource(BaseModel):
    type: SourceType = SourceType.GITHUB
    paths: list[str] = Field(
        min_length=1,
        description="Relative Pfade im Repo, z.B. ['docs/guides/', 'README.md']",
    )

    @field_validator("paths")
    @classmethod
    def paths_not_empty_strings(cls, v: list[str]) -> list[str]:
        if any(not p.strip() for p in v):
            raise ValueError("paths darf keine leeren Strings enthalten")
        return v


class OutlineSource(BaseModel):
    type: SourceType = SourceType.OUTLINE
    # Review-Fix H-02: collections als typisiertes Array statt freier query-String
    collections: list[str] = Field(
        min_length=1,
        description="Outline-Collection-Namen (exakte Bezeichnungen aus Outline).",
    )


class TechDocsSource(BaseModel):
    type: SourceType = SourceType.TECHDOCS
    site_slug: str = Field(
        min_length=1,
        max_length=120,
        description="TechDocs site_slug, z.B. 'platform' oder 'risk-hub'.",
    )
    filter: str = Field(
        default="",
        description="Optionaler Pfad-Filter, z.B. 'explanation/'.",
    )


class DevHubSource(BaseModel):
    type: SourceType = SourceType.DEVHUB
    apps: list[str] = Field(
        min_length=1,
        description="dev-hub App-Namen, z.B. ['health', 'operations'].",
    )


# ---------------------------------------------------------------------------
# Discriminated Union (Discriminator-Fix: Pydantic v2 routet nach type-Feld)
# ---------------------------------------------------------------------------


def _source_discriminator(v: dict | BaseModel) -> str:
    """Extracts the 'type' field for discriminated union routing."""
    if isinstance(v, dict):
        return v.get("type", "github")
    return getattr(v, "type", "github").value


AudienceSourceModel = Annotated[
    Annotated[GitHubSource, Tag("github")]
    | Annotated[OutlineSource, Tag("outline")]
    | Annotated[TechDocsSource, Tag("techdocs")]
    | Annotated[DevHubSource, Tag("devhub")],
    Discriminator(_source_discriminator),
]


# ---------------------------------------------------------------------------
# Audience Entry
# ---------------------------------------------------------------------------


class AudienceEntry(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    icon: str = Field(min_length=1, max_length=50)
    sources: list[AudienceSourceModel] = Field(min_length=1)

    def get_sources_by_type(self, source_type: SourceType) -> list[AudienceSourceModel]:
        return [s for s in self.sources if s.type == source_type]


# ---------------------------------------------------------------------------
# Top-Level AudienceYaml Schema
# ---------------------------------------------------------------------------


class AudienceYamlSchema(BaseModel):
    """
    Vollständiges Schema für audience.yaml.

    Beispiel:
        schema_version: 1
        audiences:
          user:
            title: "Für Anwender"
            icon: "users"
            sources:
              - type: github
                paths: ["docs/tutorials/", "README.md"]
    """

    schema_version: Annotated[int, Field(ge=1, le=99)] = 1
    audiences: dict[AudienceRole, AudienceEntry] = Field(
        min_length=1,
        description="Mindestens eine Audience-Konfiguration erforderlich.",
    )

    @model_validator(mode="after")
    def validate_operator_sources(self) -> "AudienceYamlSchema":
        """
        Review-Fix M-04: AGENT_HANDOVER.md darf nicht in operator-Sources sein.
        """
        operator = self.audiences.get(AudienceRole.OPERATOR)
        if operator:
            for source in operator.get_sources_by_type(SourceType.GITHUB):
                assert isinstance(source, GitHubSource)
                if "AGENT_HANDOVER.md" in source.paths:
                    raise ValueError(
                        "AGENT_HANDOVER.md ist eine Agent-Kontext-Datei (ADR-154) "
                        "und darf nicht in operator-Sources stehen. "
                        "Nur in 'developer'-Sources erlaubt."
                    )
        return self


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_and_validate(path: Path) -> AudienceYamlSchema:
    """
    Lädt und validiert eine audience.yaml-Datei.

    Raises:
        FileNotFoundError: Datei nicht vorhanden.
        yaml.YAMLError: Ungültiges YAML.
        pydantic.ValidationError: Schema-Verletzung (mit detaillierten Fehlern).
    """
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if raw is None:
        raise ValueError(f"audience.yaml ist leer: {path}")

    return AudienceYamlSchema.model_validate(raw)


def validate_from_string(content: str) -> AudienceYamlSchema:
    """Validiert audience.yaml-Inhalt als String (für Tests)."""
    raw = yaml.safe_load(content)
    return AudienceYamlSchema.model_validate(raw)
