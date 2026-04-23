"""Tests for LLM-based document structure analysis (ADR-147 Phase C)."""

from __future__ import annotations

import json

import pytest

from concept_templates.analyzer import (
    _extract_json_fallback,
    _merge_templates_rule_based,
    analyze_document_structure,
    merge_templates,
)
from concept_templates.schemas import (
    AnalysisResult,
    ConceptScope,
    ConceptTemplate,
    FieldType,
    TemplateField,
    TemplateSection,
)

# ── Fixtures ────────────────────────────────────────────────────────


def _make_llm_response(template_name: str = "Test-Template", confidence: float = 0.85) -> str:
    """Create a mock LLM JSON response."""
    return json.dumps({
        "name": template_name,
        "scope": "brandschutz",
        "version": "1.0",
        "is_master": False,
        "framework": "MBO",
        "sections": [
            {
                "name": "objektbeschreibung",
                "title": "Objektbeschreibung",
                "description": "Beschreibung des Gebäudes",
                "required": True,
                "order": 1,
                "fields": [
                    {
                        "name": "gebaeude_name",
                        "label": "Gebäudename",
                        "field_type": "text",
                        "required": True,
                        "help_text": "Name des Gebäudes",
                    }
                ],
                "subsections": [],
            },
            {
                "name": "brandabschnitte",
                "title": "Brandabschnitte",
                "description": "Einteilung in Brandabschnitte",
                "required": True,
                "order": 2,
                "fields": [],
                "subsections": [],
            },
        ],
        "confidence": confidence,
        "gaps": ["Fehlender Abschnitt: Fluchtwege"],
        "recommendations": ["Fluchtwegeplan ergänzen"],
    })


def _mock_llm_fn(system: str, user: str) -> str:
    """Mock LLM callable that returns a valid analysis response."""
    return _make_llm_response()


def _mock_llm_fn_markdown(system: str, user: str) -> str:
    """Mock LLM that wraps response in markdown code fence."""
    return f"Hier ist die Analyse:\n```json\n{_make_llm_response()}\n```\nFertig."


def _mock_llm_fn_invalid(system: str, user: str) -> str:
    """Mock LLM that returns garbage."""
    return "Das kann ich leider nicht analysieren."


def _make_template(name: str, sections: list[str]) -> ConceptTemplate:
    """Create a minimal ConceptTemplate with named sections."""
    return ConceptTemplate(
        name=name,
        scope=ConceptScope.BRANDSCHUTZ,
        sections=[
            TemplateSection(
                name=s,
                title=s.replace("_", " ").title(),
                order=i + 1,
            )
            for i, s in enumerate(sections)
        ],
    )


# ── Tests: analyze_document_structure ───────────────────────────────


class TestAnalyzeDocumentStructure:
    def test_should_return_analysis_result(self):
        result = analyze_document_structure(
            text="1. Objektbeschreibung\nDas Gebäude...",
            scope="brandschutz",
            title="Test-Konzept",
            page_count=5,
            llm_fn=_mock_llm_fn,
        )
        assert isinstance(result, AnalysisResult)
        assert result.confidence == 0.85
        assert len(result.proposed_template.sections) == 2

    def test_should_set_template_scope(self):
        result = analyze_document_structure(
            text="Test",
            scope=ConceptScope.BRANDSCHUTZ,
            llm_fn=_mock_llm_fn,
        )
        assert result.proposed_template.scope == ConceptScope.BRANDSCHUTZ

    def test_should_extract_gaps(self):
        result = analyze_document_structure(
            text="Test",
            scope="brandschutz",
            llm_fn=_mock_llm_fn,
        )
        assert "Fluchtwege" in result.gaps[0]

    def test_should_extract_recommendations(self):
        result = analyze_document_structure(
            text="Test",
            scope="brandschutz",
            llm_fn=_mock_llm_fn,
        )
        assert len(result.recommendations) > 0

    def test_should_raise_without_llm_fn(self):
        with pytest.raises(ValueError, match="llm_fn is required"):
            analyze_document_structure(text="Test", scope="brandschutz")

    def test_should_handle_markdown_wrapped_response(self):
        result = analyze_document_structure(
            text="Test",
            scope="brandschutz",
            llm_fn=_mock_llm_fn_markdown,
        )
        assert isinstance(result, AnalysisResult)
        assert len(result.proposed_template.sections) == 2

    def test_should_raise_on_unparseable_response(self):
        with pytest.raises(ValueError, match="Could not parse"):
            analyze_document_structure(
                text="Test",
                scope="brandschutz",
                llm_fn=_mock_llm_fn_invalid,
            )

    def test_should_truncate_long_text(self):
        long_text = "A" * 20000
        calls = []

        def capturing_llm(system: str, user: str) -> str:
            calls.append(user)
            return _make_llm_response()

        analyze_document_structure(
            text=long_text,
            scope="brandschutz",
            llm_fn=capturing_llm,
        )
        # The user prompt should contain truncated text (8000 chars max)
        assert len(calls) == 1
        assert "AAAA" in calls[0]

    def test_should_clamp_confidence(self):
        def llm_high_confidence(s, u):
            return json.dumps({
                "name": "Test",
                "scope": "brandschutz",
                "sections": [],
                "confidence": 1.5,
                "gaps": [],
                "recommendations": [],
            })

        result = analyze_document_structure(
            text="Test", scope="brandschutz", llm_fn=llm_high_confidence
        )
        assert result.confidence == 1.0


# ── Tests: merge_templates ──────────────────────────────────────────


class TestMergeTemplates:
    def test_should_raise_on_empty_list(self):
        with pytest.raises(ValueError, match="At least one"):
            merge_templates([], scope="brandschutz")

    def test_should_promote_single_template_to_master(self):
        tmpl = _make_template("Konzept A", ["intro", "brandabschnitte"])
        result = merge_templates([tmpl], scope="brandschutz")
        assert result.proposed_template.is_master is True
        assert result.confidence == 0.95

    def test_should_merge_rule_based_without_llm(self):
        t1 = _make_template("A", ["intro", "brandabschnitte"])
        t2 = _make_template("B", ["intro", "fluchtwege"])
        result = merge_templates([t1, t2], scope="brandschutz")
        assert result.proposed_template.is_master is True
        names = [s.name for s in result.proposed_template.sections]
        assert "intro" in names
        assert "brandabschnitte" in names
        assert "fluchtwege" in names

    def test_should_merge_with_llm_when_provided(self):
        t1 = _make_template("A", ["intro"])
        t2 = _make_template("B", ["intro", "fazit"])
        result = merge_templates([t1, t2], scope="brandschutz", llm_fn=_mock_llm_fn)
        assert isinstance(result, AnalysisResult)

    def test_rule_based_merge_deduplicates_sections(self):
        t1 = _make_template("A", ["intro", "details"])
        t2 = _make_template("B", ["intro", "details"])
        result = _merge_templates_rule_based([t1, t2], "brandschutz")
        names = [s.name for s in result.proposed_template.sections]
        assert names.count("intro") == 1
        assert names.count("details") == 1

    def test_rule_based_merge_merges_fields(self):
        t1 = ConceptTemplate(
            name="A",
            scope=ConceptScope.BRANDSCHUTZ,
            sections=[
                TemplateSection(
                    name="intro",
                    title="Intro",
                    fields=[TemplateField(name="title", label="Titel", field_type=FieldType.TEXT)],
                )
            ],
        )
        t2 = ConceptTemplate(
            name="B",
            scope=ConceptScope.BRANDSCHUTZ,
            sections=[
                TemplateSection(
                    name="intro",
                    title="Intro",
                    fields=[TemplateField(name="author", label="Autor", field_type=FieldType.TEXT)],
                )
            ],
        )
        result = _merge_templates_rule_based([t1, t2], "brandschutz")
        intro = next(s for s in result.proposed_template.sections if s.name == "intro")
        field_names = [f.name for f in intro.fields]
        assert "title" in field_names
        assert "author" in field_names


# ── Tests: _extract_json_fallback ───────────────────────────────────


class TestExtractJsonFallback:
    def test_should_parse_plain_json(self):
        result = _extract_json_fallback('{"key": "value"}')
        assert result == {"key": "value"}

    def test_should_parse_markdown_fenced_json(self):
        text = "Some text\n```json\n{\"key\": \"value\"}\n```\nMore text"
        result = _extract_json_fallback(text)
        assert result == {"key": "value"}

    def test_should_parse_embedded_json(self):
        text = "Here is the result: {\"name\": \"test\"} done."
        result = _extract_json_fallback(text)
        assert result == {"name": "test"}

    def test_should_return_none_for_garbage(self):
        assert _extract_json_fallback("no json here") is None

    def test_should_handle_nested_braces(self):
        text = '{"outer": {"inner": 1}}'
        result = _extract_json_fallback(text)
        assert result == {"outer": {"inner": 1}}
