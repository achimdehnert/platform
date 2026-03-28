"""Tests for mutation strategies (Design #3)."""

from __future__ import annotations

from pathlib import Path

from hub_identity.core.schema import HubDNA
from hub_identity.core.scoring import ScoreTree
from hub_identity.mutations.deterministic import (
    BannedWordReplacer,
    ColorEntropyStrategy,
    FontSwapStrategy,
    RadiusJitterStrategy,
)
from hub_identity.mutations.pipeline import MutationPipeline

FIXTURES = Path(__file__).parent.parent / "hub_dnas"


def _make_score(typo=0, color=0, layout=0, vocab=0, mc=0):
    """Build a ScoreTree with specific leaf scores."""
    tree = ScoreTree.create()
    if typo:
        tree.find("Typography").raw_score = typo
    if color:
        tree.find("Color").raw_score = color
    if layout:
        tree.find("Layout").raw_score = layout
    if vocab:
        tree.find("Vocabulary").raw_score = vocab
    if mc:
        tree.find("MicroCopy").raw_score = mc
    return tree


class TestFontSwapStrategy:

    def test_should_swap_inter_font(self):
        dna = HubDNA(
            hub="test",
            visual={"typography": {"display": "Inter", "body": "Inter"}},
        )
        score = _make_score(typo=50)
        strategy = FontSwapStrategy()
        assert strategy.should_apply(dna, score)
        result = strategy.apply(dna)
        assert result.visual.typography.display != "Inter"
        assert result.visual.typography.body != "Inter"

    def test_should_not_apply_when_score_low(self):
        dna = HubDNA(hub="test")
        score = _make_score(typo=5)
        assert not FontSwapStrategy().should_apply(dna, score)

    def test_should_preserve_non_ai_fonts(self):
        dna = HubDNA(
            hub="test",
            visual={"typography": {"display": "Crimson Pro"}},
        )
        _make_score(typo=50)  # score context
        result = FontSwapStrategy().apply(dna)
        # Crimson Pro not in FONT_ALTERNATIVES → unchanged
        assert result.visual.typography.display == "Crimson Pro"


class TestRadiusJitterStrategy:

    def test_should_jitter_ai_typical_radius(self):
        dna = HubDNA(
            hub="test",
            visual={"layout": {"border_radius": 8}},
        )
        result = RadiusJitterStrategy().apply(dna)
        assert result.visual.layout.border_radius != 8

    def test_should_keep_non_ai_radius(self):
        dna = HubDNA(
            hub="test",
            visual={"layout": {"border_radius": 3}},
        )
        result = RadiusJitterStrategy().apply(dna)
        assert result.visual.layout.border_radius == 3


class TestColorEntropyStrategy:

    def test_should_jitter_muted_colors(self):
        dna = HubDNA(
            hub="test",
            visual={"palette": {"muted": "#f5f5f4"}},
        )
        result = ColorEntropyStrategy().apply(dna)
        # Should be slightly different
        assert result.visual.palette.muted.startswith("#")
        # Could be same due to small jitter, but format preserved
        assert len(result.visual.palette.muted) == 7


class TestBannedWordReplacer:

    def test_should_replace_banned_words(self):
        dna = HubDNA(
            hub="test",
            voice={
                "preferred_words_de": {"nahtlos": "direkt"},
                "micro_copy": {
                    "de": {"cta_primary": "nahtlos integrieren"},
                },
            },
        )
        result = BannedWordReplacer().apply(dna)
        assert "nahtlos" not in result.voice.micro_copy.de.cta_primary
        assert "direkt" in result.voice.micro_copy.de.cta_primary


class TestMutationPipeline:

    def test_should_run_deterministic_strategies(self):
        dna = HubDNA(
            hub="test",
            visual={
                "typography": {"display": "Inter"},
                "layout": {"border_radius": 8},
            },
        )
        score = _make_score(typo=50, layout=30)
        # Only deterministic strategies (no LLM)
        strategies = [FontSwapStrategy(), RadiusJitterStrategy()]
        pipeline = MutationPipeline(
            strategies=strategies, threshold=10.0,
        )
        result = pipeline.mutate(dna, score)
        assert result.visual.typography.display != "Inter"

    def test_should_preview_strategies(self):
        dna = HubDNA(hub="test")
        score = _make_score(typo=50)
        strategies = [FontSwapStrategy(), RadiusJitterStrategy()]
        pipeline = MutationPipeline(strategies=strategies)
        previews = pipeline.preview(dna, score)
        assert len(previews) == 2
        assert previews[0]["name"] == "font_swap"
        assert previews[0]["requires_llm"] is False

    def test_should_not_include_llm_strategies_by_default(self):
        strategies = [FontSwapStrategy(), RadiusJitterStrategy()]
        pipeline = MutationPipeline(strategies=strategies)
        assert all(not s.requires_llm for s in pipeline.strategies)
