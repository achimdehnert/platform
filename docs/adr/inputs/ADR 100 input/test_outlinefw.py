"""
tests/test_outlinefw.py

Production test suite for iil-outlinefw.

Covers:
  - schemas.py: Beat position validation, OutlineResult states
  - frameworks.py: All 5 frameworks pass validation, versioned
  - parser.py: All 6 ParseStatus outcomes with real LLM-like inputs
  - generator.py: LLMRouter Protocol, error propagation
  - django_adapter.py: ABC enforcement, InMemoryOutlineService

Run: pytest tests/test_outlinefw.py -v --tb=short
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# Allow running from review directory without install
sys.path.insert(0, str(Path(__file__).parent))

from schemas import (
    ActPhase,
    BeatDefinition,
    FrameworkDefinition,
    GenerationStatus,
    LLMQuality,
    OutlineGenerationError,
    OutlineNode,
    OutlineResult,
    ParseResult,
    ParseStatus,
    ProjectContext,
    TensionLevel,
)
from frameworks import (
    DAN_HARMON,
    FIVE_ACT,
    FRAMEWORKS,
    HEROS_JOURNEY,
    SAVE_THE_CAT,
    THREE_ACT,
    get_framework,
    list_frameworks,
)
from parser import _preprocess, parse_nodes
from generator import LLMRouter, LLMRouterError, LLMRouterTimeout, OutlineGenerator
from django_adapter import InMemoryOutlineService, OutlineServiceBase


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_context() -> ProjectContext:
    return ProjectContext(
        title="Der Verrat",
        genre="Thriller",
        logline="Ein Detektiv entdeckt, dass sein Partner ein Maulwurf ist.",
        protagonist="Kommissar Berger",
        setting="München, Gegenwart",
        themes=["Verrat", "Loyalität"],
        tone="dunkel, spannungsgeladen",
        language_code="de",
    )


def _make_nodes_json(framework: FrameworkDefinition) -> str:
    """Generate valid JSON mimicking an LLM response for a given framework."""
    nodes = [
        {
            "beat_name": beat.name,
            "position": beat.position,
            "act": beat.act.value,
            "title": f"Titel für {beat.name}",
            "summary": f"Zusammenfassung für den Beat '{beat.name}' mit ausreichend Text.",
            "tension": beat.tension.value,
            "key_events": ["Ereignis A", "Ereignis B"],
        }
        for beat in framework.beats
    ]
    return json.dumps(nodes)


class GoodRouter:
    """Test double: always returns valid JSON for the requested framework."""

    def __init__(self, framework_key: str = "three_act") -> None:
        self._fw = get_framework(framework_key)

    def completion(
        self,
        action_code: str,
        messages: list[dict[str, str]],
        quality: LLMQuality = LLMQuality.STANDARD,
        priority: str = "balanced",
    ) -> str:
        return _make_nodes_json(self._fw)


class ErrorRouter:
    """Test double: always raises LLMRouterError."""

    def completion(self, action_code, messages, quality=LLMQuality.STANDARD, priority="balanced") -> str:
        raise LLMRouterError("simulated LLM failure")


class TimeoutRouter:
    """Test double: always raises LLMRouterTimeout."""

    def completion(self, action_code, messages, quality=LLMQuality.STANDARD, priority="balanced") -> str:
        raise LLMRouterTimeout("simulated timeout")


class EmptyRouter:
    """Test double: always returns empty string."""

    def completion(self, action_code, messages, quality=LLMQuality.STANDARD, priority="balanced") -> str:
        return ""


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------


class TestBeatDefinition:
    def test_valid_beat(self):
        beat = BeatDefinition(
            name="setup",
            position=0.0,
            act=ActPhase.ACT_1,
            description="Setup beat.",
            tension=TensionLevel.LOW,
        )
        assert beat.name == "setup"
        assert beat.position == 0.0

    def test_position_rounded_to_2dp(self):
        beat = BeatDefinition(
            name="test",
            position=0.123456789,
            act=ActPhase.ACT_1,
            description="x",
            tension=TensionLevel.LOW,
        )
        assert beat.position == 0.12

    def test_frozen(self):
        beat = BeatDefinition(
            name="x", position=0.0, act=ActPhase.ACT_1, description="x", tension=TensionLevel.LOW
        )
        with pytest.raises(Exception):
            beat.name = "y"  # type: ignore[misc]


class TestFrameworkDefinition:
    def test_duplicate_positions_rejected(self):
        with pytest.raises(ValueError, match="duplicate beat positions"):
            FrameworkDefinition(
                key="test_fw",
                name="Test",
                description="Test framework",
                beats=[
                    BeatDefinition(name="a", position=0.0, act=ActPhase.ACT_1, description="a", tension=TensionLevel.LOW),
                    BeatDefinition(name="b", position=0.0, act=ActPhase.ACT_1, description="b", tension=TensionLevel.LOW),
                    BeatDefinition(name="c", position=1.0, act=ActPhase.ACT_3, description="c", tension=TensionLevel.LOW),
                ],
            )

    def test_unsorted_positions_rejected(self):
        with pytest.raises(ValueError, match="ordered by position"):
            FrameworkDefinition(
                key="test_fw",
                name="Test",
                description="Test framework",
                beats=[
                    BeatDefinition(name="a", position=0.5, act=ActPhase.ACT_1, description="a", tension=TensionLevel.LOW),
                    BeatDefinition(name="b", position=0.0, act=ActPhase.ACT_1, description="b", tension=TensionLevel.LOW),
                    BeatDefinition(name="c", position=1.0, act=ActPhase.ACT_3, description="c", tension=TensionLevel.LOW),
                ],
            )

    def test_first_beat_too_late_rejected(self):
        with pytest.raises(ValueError, match="first beat position"):
            FrameworkDefinition(
                key="test_fw",
                name="Test",
                description="Test framework",
                beats=[
                    BeatDefinition(name="a", position=0.2, act=ActPhase.ACT_1, description="a", tension=TensionLevel.LOW),
                    BeatDefinition(name="b", position=1.0, act=ActPhase.ACT_3, description="b", tension=TensionLevel.LOW),
                ],
            )

    def test_excessive_gap_rejected(self):
        with pytest.raises(ValueError, match="gap of"):
            FrameworkDefinition(
                key="test_fw",
                name="Test",
                description="Test framework",
                beats=[
                    BeatDefinition(name="a", position=0.0, act=ActPhase.ACT_1, description="a", tension=TensionLevel.LOW),
                    BeatDefinition(name="b", position=0.5, act=ActPhase.ACT_2A, description="b", tension=TensionLevel.LOW),
                    BeatDefinition(name="c", position=1.0, act=ActPhase.ACT_3, description="c", tension=TensionLevel.LOW),
                ],
            )


class TestOutlineResult:
    def test_success_property(self):
        result = OutlineResult(
            status=GenerationStatus.SUCCESS,
            framework_key="three_act",
            framework_name="Drei-Akt",
            project_title="Test",
            nodes=[],
        )
        assert result.success is True

    def test_failed_status(self):
        result = OutlineResult(
            status=GenerationStatus.LLM_ERROR,
            framework_key="three_act",
            framework_name="Drei-Akt",
            project_title="Test",
            error_message="API down",
        )
        assert result.success is False

    def test_raise_if_failed(self):
        result = OutlineResult(
            status=GenerationStatus.PARSE_ERROR,
            framework_key="three_act",
            framework_name="Drei-Akt",
            project_title="Test",
            error_message="bad JSON",
        )
        with pytest.raises(OutlineGenerationError, match="bad JSON"):
            result.raise_if_failed()

    def test_raise_if_failed_no_raise_on_success(self):
        result = OutlineResult(
            status=GenerationStatus.SUCCESS,
            framework_key="three_act",
            framework_name="Drei-Akt",
            project_title="Test",
        )
        result.raise_if_failed()  # Should not raise

    def test_completion_ratio(self):
        result = OutlineResult(
            status=GenerationStatus.PARTIAL,
            framework_key="three_act",
            framework_name="Drei-Akt",
            project_title="Test",
            total_beats=7,
            generated_beats=5,
        )
        assert result.completion_ratio == pytest.approx(5 / 7)


# ---------------------------------------------------------------------------
# Framework Tests
# ---------------------------------------------------------------------------


class TestFrameworks:
    @pytest.mark.parametrize("framework", [THREE_ACT, SAVE_THE_CAT, HEROS_JOURNEY, FIVE_ACT, DAN_HARMON])
    def test_framework_validates(self, framework: FrameworkDefinition):
        """All 5 frameworks must pass FrameworkDefinition validation."""
        assert framework.key != ""
        assert len(framework.beats) >= 2

    @pytest.mark.parametrize("key,expected_beats", [
        ("three_act", 7),
        ("save_the_cat", 15),
        ("heros_journey", 12),
        ("five_act", 5),
        ("dan_harmon", 8),
    ])
    def test_beat_counts(self, key: str, expected_beats: int):
        fw = get_framework(key)
        assert len(fw.beats) == expected_beats

    def test_all_frameworks_in_registry(self):
        assert set(FRAMEWORKS.keys()) == {
            "three_act", "save_the_cat", "heros_journey", "five_act", "dan_harmon"
        }

    def test_framework_positions_monotone(self):
        for fw in FRAMEWORKS.values():
            positions = [b.position for b in fw.beats]
            assert positions == sorted(positions), f"{fw.key}: positions not sorted"

    def test_get_framework_unknown_raises_key_error(self):
        with pytest.raises(KeyError, match="Unknown framework key"):
            get_framework("nonexistent")

    def test_list_frameworks_returns_all(self):
        listing = list_frameworks()
        assert len(listing) == 5
        keys = {f["key"] for f in listing}
        assert "dan_harmon" in keys  # Was missing from ADR Package-Struktur

    def test_framework_has_version(self):
        for fw in FRAMEWORKS.values():
            assert fw.version, f"{fw.key}: no version defined"


# ---------------------------------------------------------------------------
# Parser Tests
# ---------------------------------------------------------------------------


class TestPreprocess:
    def test_strips_json_fence(self):
        result = _preprocess("```json\n[]\n```")
        assert result == "[]"

    def test_strips_bare_fence(self):
        result = _preprocess("```\n[]\n```")
        assert result == "[]"

    def test_fixes_trailing_comma(self):
        result = _preprocess('{"key": "val",}')
        assert result == '{"key": "val"}'

    def test_fixes_python_booleans(self):
        result = _preprocess('{"flag": True, "other": False, "null": None}')
        assert "true" in result
        assert "false" in result
        assert "null" in result


class TestParseNodes:
    def test_success_with_valid_json(self):
        fw = THREE_ACT
        raw = _make_nodes_json(fw)
        result = parse_nodes(raw)
        assert result.status == ParseStatus.SUCCESS
        assert len(result.nodes) == len(fw.beats)

    def test_empty_response(self):
        result = parse_nodes("")
        assert result.status == ParseStatus.EMPTY

    def test_whitespace_only(self):
        result = parse_nodes("   \n\t  ")
        assert result.status == ParseStatus.EMPTY

    def test_malformed_json(self):
        result = parse_nodes("{not: valid json}")
        assert result.status == ParseStatus.MALFORMED_JSON

    def test_json_fence_stripped(self):
        fw = THREE_ACT
        raw = f"```json\n{_make_nodes_json(fw)}\n```"
        result = parse_nodes(raw)
        assert result.status == ParseStatus.SUCCESS

    def test_wrapped_in_outline_key(self):
        fw = THREE_ACT
        nodes = json.loads(_make_nodes_json(fw))
        raw = json.dumps({"outline": nodes})
        result = parse_nodes(raw)
        assert result.status == ParseStatus.SUCCESS
        assert len(result.nodes) == len(fw.beats)

    def test_wrapped_in_nodes_key(self):
        fw = THREE_ACT
        nodes = json.loads(_make_nodes_json(fw))
        raw = json.dumps({"nodes": nodes})
        result = parse_nodes(raw)
        assert result.status == ParseStatus.SUCCESS

    def test_partial_parse(self):
        fw = THREE_ACT
        nodes = json.loads(_make_nodes_json(fw))
        # Corrupt one node
        nodes[2] = {"completely_wrong": "structure"}
        result = parse_nodes(json.dumps(nodes))
        assert result.status == ParseStatus.PARTIAL
        assert len(result.nodes) == len(fw.beats) - 1
        assert len(result.failed_nodes) == 1

    def test_act_alias_mapping(self):
        nodes = [
            {
                "beat_name": "test",
                "position": 0.0,
                "act": "act1",  # alias, not canonical "act_1"
                "title": "Test",
                "summary": "A test summary with enough characters.",
                "tension": "low",
            }
        ]
        result = parse_nodes(json.dumps(nodes))
        assert result.status == ParseStatus.SUCCESS
        assert result.nodes[0].act == ActPhase.ACT_1

    def test_tension_alias_mapping(self):
        nodes = [
            {
                "beat_name": "test",
                "position": 0.0,
                "act": "act_1",
                "title": "Test",
                "summary": "A test summary with enough characters.",
                "tension": "climax",  # alias for "peak"
            }
        ]
        result = parse_nodes(json.dumps(nodes))
        assert result.status == ParseStatus.SUCCESS
        assert result.nodes[0].tension == TensionLevel.PEAK

    def test_parse_result_has_raw_content(self):
        raw = "this is not json at all"
        result = parse_nodes(raw)
        assert result.raw_content == raw


# ---------------------------------------------------------------------------
# Generator Tests
# ---------------------------------------------------------------------------


class TestOutlineGenerator:
    def test_requires_llm_router_protocol(self):
        with pytest.raises(TypeError, match="LLMRouter Protocol"):
            OutlineGenerator(router="not a router")  # type: ignore[arg-type]

    def test_successful_generation(self, sample_context: ProjectContext):
        router = GoodRouter("three_act")
        gen = OutlineGenerator(router=router)
        result = gen.generate("three_act", sample_context)
        assert result.status == GenerationStatus.SUCCESS
        assert len(result.nodes) == 7
        assert result.framework_key == "three_act"

    def test_llm_error_returns_error_result(self, sample_context: ProjectContext):
        gen = OutlineGenerator(router=ErrorRouter())
        result = gen.generate("three_act", sample_context)
        assert result.status == GenerationStatus.LLM_ERROR
        assert "simulated LLM failure" in result.error_message

    def test_timeout_returns_error_result(self, sample_context: ProjectContext):
        gen = OutlineGenerator(router=TimeoutRouter())
        result = gen.generate("three_act", sample_context)
        assert result.status == GenerationStatus.LLM_ERROR
        assert "timeout" in result.error_message.lower()

    def test_empty_response_returns_parse_error(self, sample_context: ProjectContext):
        gen = OutlineGenerator(router=EmptyRouter())
        result = gen.generate("three_act", sample_context)
        assert result.status == GenerationStatus.PARSE_ERROR

    def test_unknown_framework_returns_validation_error(self, sample_context: ProjectContext):
        gen = OutlineGenerator(router=GoodRouter())
        result = gen.generate("nonexistent_framework", sample_context)
        assert result.status == GenerationStatus.VALIDATION_ERROR

    def test_result_has_timing(self, sample_context: ProjectContext):
        gen = OutlineGenerator(router=GoodRouter())
        result = gen.generate("three_act", sample_context)
        assert result.generation_time_ms is not None
        assert result.generation_time_ms >= 0

    def test_result_has_total_beats(self, sample_context: ProjectContext):
        gen = OutlineGenerator(router=GoodRouter("save_the_cat"))
        result = gen.generate("save_the_cat", sample_context)
        assert result.total_beats == 15


# ---------------------------------------------------------------------------
# Django Adapter Tests
# ---------------------------------------------------------------------------


class TestOutlineServiceBaseABC:
    def test_cannot_instantiate_abstract_base(self):
        with pytest.raises(TypeError):
            OutlineServiceBase()  # type: ignore[abstract]

    def test_missing_get_tenant_id_raises(self):
        class IncompleteService(OutlineServiceBase):
            def persist_outline(self, result, context, tenant_id):
                pass

            def get_llm_router(self, tenant_id):
                pass
            # Missing get_tenant_id

        with pytest.raises(TypeError):
            IncompleteService()


class TestInMemoryOutlineService:
    def test_generates_and_persists(self, sample_context: ProjectContext):
        router = GoodRouter("three_act")
        service = InMemoryOutlineService(router=router, tenant_id=42)
        result = service.generate_and_persist("three_act", sample_context, request=None)

        assert result.success
        assert len(service.persisted) == 1
        assert service.persisted[0]["tenant_id"] == 42
        assert service.persisted[0]["framework_key"] == "three_act"

    def test_does_not_persist_on_failure(self, sample_context: ProjectContext):
        service = InMemoryOutlineService(router=ErrorRouter(), tenant_id=1)
        result = service.generate_and_persist("three_act", sample_context, request=None)

        assert not result.success
        assert len(service.persisted) == 0

    def test_get_tenant_id(self):
        service = InMemoryOutlineService(router=GoodRouter(), tenant_id=99)
        assert service.get_tenant_id(request=None) == 99
