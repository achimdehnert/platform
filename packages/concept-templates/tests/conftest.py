"""Shared fixtures for concept-templates tests."""

from __future__ import annotations

import pytest

from concept_templates.schemas import (
    ConceptScope,
    ConceptTemplate,
    FieldType,
    TemplateField,
    TemplateSection,
)


@pytest.fixture()
def sample_section() -> TemplateSection:
    """A minimal template section with fields."""
    return TemplateSection(
        name="standort",
        title="1. Standortbeschreibung",
        required=True,
        order=1,
        fields=[
            TemplateField(
                name="address",
                label="Adresse",
                field_type=FieldType.TEXT,
                required=True,
            ),
            TemplateField(
                name="building_class",
                label="Gebäudeklasse",
                field_type=FieldType.CHOICE,
                choices=["GK1", "GK2", "GK3"],
            ),
        ],
    )


@pytest.fixture()
def sample_template(sample_section) -> ConceptTemplate:
    """A minimal concept template."""
    return ConceptTemplate(
        name="Test-Brandschutzkonzept",
        scope=ConceptScope.BRANDSCHUTZ,
        framework="brandschutz_mbo",
        is_master=False,
        sections=[sample_section],
    )


@pytest.fixture(autouse=True)
def _reset_registry():
    """Reset the framework registry before each test."""
    from concept_templates.registry import clear_registry

    clear_registry()
    yield
    clear_registry()
