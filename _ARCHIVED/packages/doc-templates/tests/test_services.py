"""Tests for doc_templates services (#6 — KI-Features)."""

import json
import uuid
from unittest.mock import MagicMock

import pytest

from doc_templates.constants import (
    AI_SOURCE_SHORT_LABELS,
    AI_SOURCE_TYPES,
    AI_SOURCE_TYPES_JS,
    DEFAULT_MAX_TOKENS,
    MAX_TOKENS_BY_FIELD_TYPE,
)
from doc_templates.models import DocumentInstance, DocumentTemplate
from doc_templates.services.llm_service import (
    build_prefill_prompt,
    parse_table_response,
)
from doc_templates.services.retriever import (
    get_all_source_content,
    get_source_content,
    list_registered_retrievers,
    register_source_retriever,
    _RETRIEVERS,
)
from doc_templates.services.template_service import (
    get_ai_enabled_fields,
    merge_values_into_structure,
    parse_form_values,
)


@pytest.fixture
def tenant_id():
    return str(uuid.uuid4())


@pytest.fixture
def ai_template(tenant_id):
    """Template with AI-configured fields."""
    structure = {
        "sections": [
            {
                "key": "sec_1",
                "label": "1. Zoneneinteilung",
                "fields": [
                    {
                        "key": "inhalt",
                        "label": "Zoneneinteilung Inhalt",
                        "type": "textarea",
                        "ai_enabled": True,
                        "ai_prompt": "Erstelle die Zoneneinteilung basierend auf SDS.",
                        "ai_sources": ["sds", "zonenplan"],
                        "ai_prompt_visible": True,
                    },
                    {
                        "key": "datum",
                        "label": "Datum",
                        "type": "date",
                    },
                ],
            },
            {
                "key": "sec_2",
                "label": "2. Stoffe",
                "fields": [
                    {
                        "key": "stofftabelle",
                        "label": "Stoffliste",
                        "type": "table",
                        "columns": ["Stoff", "CAS-Nr", "Flammpunkt"],
                        "ai_enabled": True,
                        "ai_prompt": "Liste alle Gefahrstoffe auf.",
                        "ai_sources": ["sds"],
                        "ai_prompt_visible": False,
                    },
                ],
            },
            {
                "key": "sec_3",
                "label": "3. Bewertung",
                "fields": [
                    {
                        "key": "ergebnis",
                        "label": "Bewertungsergebnis",
                        "type": "boolean",
                        "ai_enabled": True,
                        "ai_prompt": "Ist Explosionsschutz erforderlich?",
                        "ai_sources": [],
                        "ai_prompt_visible": False,
                    },
                ],
            },
        ],
    }
    return DocumentTemplate.objects.create(
        tenant_id=tenant_id,
        name="AI Test Template",
        scope="explosionsschutz",
        structure_json=json.dumps(structure),
        source_text="Referenztext: Zone 1 Bereich A...",
    )


@pytest.fixture
def ai_instance(ai_template, tenant_id):
    values = {
        "sec_1": {"inhalt": "Bestehender Inhalt", "datum": "2026-03-29"},
        "sec_2": {"stofftabelle": [["Ethanol", "64-17-5", "13°C"]]},
    }
    return DocumentInstance.objects.create(
        tenant_id=tenant_id,
        template=ai_template,
        name="AI Test Instance",
        values_json=json.dumps(values),
    )


# ── Constants Tests ─────────────────────────────────────────────


class TestConstants:
    def test_should_have_12_source_types(self):
        assert len(AI_SOURCE_TYPES) == 12

    def test_should_have_matching_short_labels(self):
        for key in AI_SOURCE_TYPES:
            assert key in AI_SOURCE_SHORT_LABELS

    def test_should_have_js_format(self):
        assert len(AI_SOURCE_TYPES_JS) == 12
        for item in AI_SOURCE_TYPES_JS:
            assert "value" in item
            assert "label" in item

    def test_should_have_max_tokens_for_all_field_types(self):
        for ft in ["textarea", "table", "text", "number", "date", "boolean"]:
            assert ft in MAX_TOKENS_BY_FIELD_TYPE

    def test_should_have_default_max_tokens(self):
        assert DEFAULT_MAX_TOKENS == 500


# ── Template Service Tests ──────────────────────────────────────


@pytest.mark.django_db
class TestMergeValuesIntoStructure:
    def test_should_merge_textarea_values(self, ai_template):
        structure = ai_template.get_structure()
        values = {"sec_1": {"inhalt": "Test content", "datum": "2026-01-01"}}
        merge_values_into_structure(structure, values)

        field = structure["sections"][0]["fields"][0]
        assert field["field_value"] == "Test content"

    def test_should_merge_table_values(self, ai_template):
        structure = ai_template.get_structure()
        rows = [["Ethanol", "64-17-5", "13°C"]]
        values = {"sec_2": {"stofftabelle": rows}}
        merge_values_into_structure(structure, values)

        field = structure["sections"][1]["fields"][0]
        assert field["table_rows"] == rows

    def test_should_add_ai_sources_csv(self, ai_template):
        structure = ai_template.get_structure()
        merge_values_into_structure(structure, {})

        field = structure["sections"][0]["fields"][0]
        assert field["ai_sources_csv"] == "sds,zonenplan"
        assert "SDS" in field["ai_sources_labels"]

    def test_should_pad_table_rows_to_minimum_3(self, ai_template):
        structure = ai_template.get_structure()
        merge_values_into_structure(structure, {})

        field = structure["sections"][1]["fields"][0]
        assert len(field["table_rows"]) >= 3


@pytest.mark.django_db
class TestGetAiEnabledFields:
    def test_should_return_only_ai_enabled_fields(self, ai_template):
        structure = ai_template.get_structure()
        fields = get_ai_enabled_fields(structure)

        assert len(fields) == 3
        keys = [f["field_key"] for f in fields]
        assert "inhalt" in keys
        assert "stofftabelle" in keys
        assert "ergebnis" in keys
        assert "datum" not in keys

    def test_should_include_form_key(self, ai_template):
        structure = ai_template.get_structure()
        fields = get_ai_enabled_fields(structure)

        assert fields[0]["form_key"] == "sec_1__inhalt"

    def test_should_include_visibility_flag(self, ai_template):
        structure = ai_template.get_structure()
        fields = get_ai_enabled_fields(structure)

        visible = {f["field_key"]: f["ai_prompt_visible"] for f in fields}
        assert visible["inhalt"] is True
        assert visible["stofftabelle"] is False
        assert visible["ergebnis"] is False

    def test_should_include_columns_for_table(self, ai_template):
        structure = ai_template.get_structure()
        fields = get_ai_enabled_fields(structure)

        table_field = [f for f in fields if f["field_key"] == "stofftabelle"][0]
        assert table_field["columns"] == ["Stoff", "CAS-Nr", "Flammpunkt"]


class TestParseFormValues:
    def test_should_parse_textarea(self):
        structure = {
            "sections": [{
                "key": "s1",
                "fields": [{"key": "f1", "type": "textarea"}],
            }],
        }
        post = {"s1__f1": "Hello World"}
        values = parse_form_values(post, structure)
        assert values["s1"]["f1"] == "Hello World"

    def test_should_parse_boolean(self):
        structure = {
            "sections": [{
                "key": "s1",
                "fields": [{"key": "flag", "type": "boolean"}],
            }],
        }

        class FakePost(dict):
            def getlist(self, key):
                return self.get(key, [])

        post = FakePost({"s1__flag": ["true"]})
        values = parse_form_values(post, structure)
        assert values["s1"]["flag"] == "true"


# ── LLM Service Tests ──────────────────────────────────────────


class TestBuildPrefillPrompt:
    def test_should_return_three_parts(self):
        sys_p, usr_p, max_tok = build_prefill_prompt(
            field_key="inhalt",
            field_type="textarea",
            llm_hint="Erstelle die Zoneneinteilung.",
            ai_sources=["sds"],
            scope="explosionsschutz",
            existing_values={},
            source_text="",
            tenant_id="tid",
        )
        assert "explosionsschutz" in sys_p
        assert "Zoneneinteilung" in usr_p
        assert max_tok == 1500  # textarea

    def test_should_use_field_type_max_tokens(self):
        _, _, max_tok = build_prefill_prompt(
            field_key="flag",
            field_type="boolean",
            llm_hint="Ja oder Nein?",
            ai_sources=[],
            scope="test",
            existing_values={},
            source_text="",
            tenant_id="tid",
        )
        assert max_tok == 10

    def test_should_include_table_columns_in_prompt(self):
        _, usr_p, max_tok = build_prefill_prompt(
            field_key="tabelle",
            field_type="table",
            llm_hint="Liste Stoffe.",
            ai_sources=[],
            scope="test",
            existing_values={},
            source_text="",
            tenant_id="tid",
            table_columns=["Stoff", "CAS-Nr"],
        )
        assert "Stoff" in usr_p
        assert "CAS-Nr" in usr_p
        assert max_tok == 2000

    def test_should_include_field_type_instruction_for_boolean(self):
        sys_p, _, _ = build_prefill_prompt(
            field_key="flag",
            field_type="boolean",
            llm_hint="Check",
            ai_sources=[],
            scope="test",
            existing_values={},
            source_text="",
            tenant_id="tid",
        )
        assert "Ja" in sys_p and "Nein" in sys_p

    def test_should_include_existing_values_in_context(self):
        _, usr_p, _ = build_prefill_prompt(
            field_key="inhalt",
            field_type="textarea",
            llm_hint="Write something.",
            ai_sources=[],
            scope="test",
            existing_values={"sec1": {"key1": "existing text"}},
            source_text="",
            tenant_id="tid",
        )
        assert "existing text" in usr_p

    def test_should_include_source_text(self):
        _, usr_p, _ = build_prefill_prompt(
            field_key="inhalt",
            field_type="textarea",
            llm_hint="Write.",
            ai_sources=[],
            scope="test",
            existing_values={},
            source_text="PDF source text content",
            tenant_id="tid",
        )
        assert "PDF source text" in usr_p

    def test_should_include_source_labels(self):
        _, usr_p, _ = build_prefill_prompt(
            field_key="inhalt",
            field_type="textarea",
            llm_hint="Write.",
            ai_sources=["sds", "zonenplan"],
            scope="test",
            existing_values={},
            source_text="",
            tenant_id="tid",
        )
        assert "Sicherheitsdatenblätter" in usr_p
        assert "Zonenpläne" in usr_p


class TestParseTableResponse:
    def test_should_parse_json_array(self):
        raw = '[["Ethanol", "64-17-5", "13"], ["Methanol", "67-56-1", "11"]]'
        rows = parse_table_response(raw, 3)
        assert len(rows) == 2
        assert rows[0] == ["Ethanol", "64-17-5", "13"]

    def test_should_pad_short_rows(self):
        raw = '[["Ethanol", "64-17-5"]]'
        rows = parse_table_response(raw, 3)
        assert len(rows[0]) == 3
        assert rows[0][2] == ""

    def test_should_trim_long_rows(self):
        raw = '[["a", "b", "c", "d"]]'
        rows = parse_table_response(raw, 2)
        assert len(rows[0]) == 2

    def test_should_fallback_to_pipe_split(self):
        raw = "Ethanol | 64-17-5 | 13\nMethanol | 67-56-1 | 11"
        rows = parse_table_response(raw, 3)
        assert len(rows) >= 2
        assert "Ethanol" in rows[0][0]

    def test_should_handle_empty_input(self):
        rows = parse_table_response("", 3)
        assert rows == []


# ── Retriever Tests ─────────────────────────────────────────────


class TestRetriever:
    def setup_method(self):
        _RETRIEVERS.clear()

    def test_should_register_retriever(self):
        def my_retriever(tid, inst):
            return ["content"]
        register_source_retriever("sds", my_retriever)
        assert "sds" in list_registered_retrievers()

    def test_should_get_source_content(self):
        register_source_retriever(
            "sds", lambda tid, inst: ["SDS Text"],
        )
        result = get_source_content("sds", "tid", None)
        assert result == ["SDS Text"]

    def test_should_return_empty_for_unregistered(self):
        result = get_source_content("unknown", "tid", None)
        assert result == []

    def test_should_handle_retriever_exception(self):
        def bad_retriever(tid, inst):
            raise ValueError("DB error")
        register_source_retriever("sds", bad_retriever)
        result = get_source_content("sds", "tid", None)
        assert result == []

    def test_should_wrap_string_return(self):
        register_source_retriever(
            "cad", lambda tid, inst: "single string",
        )
        result = get_source_content("cad", "tid", None)
        assert result == ["single string"]

    def test_should_get_all_source_content(self):
        register_source_retriever(
            "sds", lambda tid, inst: ["SDS1"],
        )
        register_source_retriever(
            "cad", lambda tid, inst: ["CAD1"],
        )
        result = get_all_source_content(["sds", "cad", "unknown"], "t", None)
        assert "sds" in result
        assert "cad" in result
        assert "unknown" not in result

    def test_should_inject_retrieved_content_into_prompt(self):
        _RETRIEVERS.clear()
        register_source_retriever(
            "sds", lambda tid, inst: ["Ethanol: Flammpunkt 13°C"],
        )
        _, usr_p, _ = build_prefill_prompt(
            field_key="inhalt",
            field_type="textarea",
            llm_hint="Beschreibe die Gefahrstoffe.",
            ai_sources=["sds"],
            scope="test",
            existing_values={},
            source_text="",
            tenant_id="tid",
            instance=MagicMock(),
        )
        assert "Ethanol: Flammpunkt 13°C" in usr_p
        assert "Quellen-Dokumente" in usr_p
        _RETRIEVERS.clear()
