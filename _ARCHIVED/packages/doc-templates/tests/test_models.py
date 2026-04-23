"""Tests for doc_templates models."""

import json
import uuid

import pytest
from doc_templates.models import DocumentInstance, DocumentTemplate


@pytest.fixture
def tenant_id():
    return str(uuid.uuid4())


@pytest.fixture
def template(tenant_id):
    structure = {
        "sections": [
            {
                "key": "section_1",
                "label": "1. Allgemeines",
                "fields": [
                    {"key": "inhalt", "label": "Inhalt", "type": "textarea"},
                    {"key": "datum", "label": "Datum", "type": "date"},
                ],
            },
            {
                "key": "section_2",
                "label": "2. Details",
                "fields": [
                    {"key": "tabelle", "label": "Tabelle", "type": "table",
                     "columns": ["Spalte 1", "Spalte 2"]},
                ],
            },
        ],
    }
    return DocumentTemplate.objects.create(
        tenant_id=tenant_id,
        name="Test Template",
        description="Test description",
        scope="explosionsschutz",
        structure_json=json.dumps(structure),
    )


@pytest.mark.django_db
class TestDocumentTemplate:
    def test_should_create_template(self, template):
        assert template.pk is not None
        assert template.uuid is not None
        assert template.name == "Test Template"
        assert template.status == "draft"

    def test_should_count_sections(self, template):
        assert template.section_count == 2

    def test_should_count_fields(self, template):
        assert template.field_count == 3

    def test_should_return_structure(self, template):
        structure = template.get_structure()
        assert "sections" in structure
        assert len(structure["sections"]) == 2

    def test_should_return_sections(self, template):
        sections = template.get_sections()
        assert len(sections) == 2
        assert sections[0]["key"] == "section_1"

    def test_should_handle_invalid_json(self, tenant_id):
        tmpl = DocumentTemplate.objects.create(
            tenant_id=tenant_id,
            name="Bad JSON",
            structure_json="not valid json",
        )
        assert tmpl.section_count == 0
        assert tmpl.field_count == 0
        assert tmpl.get_structure() == {"sections": []}

    def test_should_display_str(self, template):
        assert "Test Template" in str(template)
        assert "Entwurf" in str(template)


@pytest.mark.django_db
class TestDocumentInstance:
    def test_should_create_instance(self, template, tenant_id):
        instance = DocumentInstance.objects.create(
            tenant_id=tenant_id,
            template=template,
            name="Test Instance",
        )
        assert instance.pk is not None
        assert instance.status == "draft"
        assert instance.template == template

    def test_should_get_values(self, template, tenant_id):
        values = {"section_1": {"inhalt": "Test content"}}
        instance = DocumentInstance.objects.create(
            tenant_id=tenant_id,
            template=template,
            name="Filled",
            values_json=json.dumps(values),
        )
        assert instance.get_values() == values

    def test_should_handle_empty_values(self, template, tenant_id):
        instance = DocumentInstance.objects.create(
            tenant_id=tenant_id,
            template=template,
            name="Empty",
            values_json="{}",
        )
        assert instance.get_values() == {}

    def test_should_protect_on_delete(self, template, tenant_id):
        DocumentInstance.objects.create(
            tenant_id=tenant_id,
            template=template,
            name="Linked",
        )
        from django.db.models import ProtectedError
        with pytest.raises(ProtectedError):
            template.delete()

    def test_should_display_str(self, template, tenant_id):
        instance = DocumentInstance.objects.create(
            tenant_id=tenant_id,
            template=template,
            name="My Doc",
        )
        assert "My Doc" in str(instance)
