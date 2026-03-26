"""Tests for concept_templates.prefill."""

from __future__ import annotations

from concept_templates.prefill import prefill_field


class TestPrefillField:
    def test_should_return_empty_without_hint(self):
        result = prefill_field(
            field_key="standort__adresse",
            llm_hint="",
            llm_fn=lambda s, u: "should not be called",
        )
        assert result == ""

    def test_should_call_llm_fn_with_hint(self):
        calls = []

        def mock_llm(system: str, user: str) -> str:
            calls.append((system, user))
            return "  Marktplatz 1, 12345 Musterstadt  "

        result = prefill_field(
            field_key="standort__adresse",
            llm_hint="Adresse des Gebäudes",
            llm_fn=mock_llm,
            scope="brandschutz",
        )
        assert result == "Marktplatz 1, 12345 Musterstadt"
        assert len(calls) == 1
        assert "brandschutz" in calls[0][0]
        assert "Adresse des Gebäudes" in calls[0][1]

    def test_should_include_context_values(self):
        captured_user = []

        def mock_llm(system: str, user: str) -> str:
            captured_user.append(user)
            return "42"

        prefill_field(
            field_key="gebaeude__flaeche",
            llm_hint="Gesamtfläche berechnen",
            llm_fn=mock_llm,
            context_values={"standort": {"name": "Rathaus", "ort": "Berlin"}},
        )
        assert "Rathaus" in captured_user[0]
        assert "Berlin" in captured_user[0]

    def test_should_include_extracted_texts(self):
        captured_user = []

        def mock_llm(system: str, user: str) -> str:
            captured_user.append(user)
            return "Wert"

        prefill_field(
            field_key="x__y",
            llm_hint="Beschreibe",
            llm_fn=mock_llm,
            extracted_texts=["Das Gebäude befindet sich in Musterstadt."],
        )
        assert "Musterstadt" in captured_user[0]

    def test_should_return_empty_on_llm_error(self):
        def failing_llm(system: str, user: str) -> str:
            raise RuntimeError("LLM down")

        result = prefill_field(
            field_key="x__y",
            llm_hint="Beschreibe",
            llm_fn=failing_llm,
        )
        assert result == ""

    def test_should_use_english_system_prompt(self):
        captured_system = []

        def mock_llm(system: str, user: str) -> str:
            captured_system.append(system)
            return "value"

        prefill_field(
            field_key="x__y",
            llm_hint="Describe",
            llm_fn=mock_llm,
            language="en",
        )
        assert "expert" in captured_system[0].lower()
