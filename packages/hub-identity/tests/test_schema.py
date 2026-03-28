"""Tests for HubDNA schema, inheritance, and I/O."""

from __future__ import annotations

from pathlib import Path

import pytest

from hub_identity.core.schema import HubDNA


FIXTURES = Path(__file__).parent.parent / "hub_dnas"


class TestHubDNAInheritance:
    """Design #4: _base.yaml + overrides."""

    def test_should_load_base_yaml(self):
        dna = HubDNA.from_yaml(FIXTURES / "_base.yaml")
        assert dna.hub == "_base"
        assert dna.display_name == "iil-Platform"
        assert dna.visual.typography.display == "Figtree"

    def test_should_load_hub_with_inheritance(self):
        dna = HubDNA.from_yaml(FIXTURES / "risk-hub.yaml")
        assert dna.hub == "risk-hub"
        assert dna.display_name == "Schutztat"
        # Overridden
        assert dna.visual.typography.display == "JetBrains Mono"
        assert dna.visual.layout.border_radius == 3
        # Inherited from _base
        assert dna.visual.motion.duration_fast == "120ms"
        assert dna.voice.use_formal_address is True

    def test_should_override_palette_partially(self):
        dna = HubDNA.from_yaml(FIXTURES / "risk-hub.yaml")
        # Overridden
        assert dna.visual.palette.accent == "#dc2626"
        # Inherited from _base
        assert dna.visual.palette.secondary == "#f1f5f9"
        assert dna.visual.palette.ring == "#3b82f6"

    def test_should_override_voice_tone(self):
        dna = HubDNA.from_yaml(FIXTURES / "risk-hub.yaml")
        tone_values = [t.value for t in dna.voice.tone]
        assert "precise" in tone_values
        assert "technical" in tone_values

    def test_should_merge_micro_copy(self):
        dna = HubDNA.from_yaml(FIXTURES / "risk-hub.yaml")
        # Overridden in risk-hub
        assert dna.voice.micro_copy.de.cta_primary == "Sichern"
        # Inherited from _base
        assert dna.voice.micro_copy.de.nav_back == "Zurück"

    def test_should_fail_on_missing_base(self, tmp_path):
        yaml_content = "extends: nonexistent\nhub: test\n"
        p = tmp_path / "test.yaml"
        p.write_text(yaml_content)
        with pytest.raises(FileNotFoundError):
            HubDNA.from_yaml(p)


class TestHubDNAImmutable:
    """Design #6: No mutation_history in schema."""

    def test_should_not_have_mutation_history_field(self):
        fields = HubDNA.model_fields
        assert "mutation_history" not in fields

    def test_should_forbid_extra_fields(self):
        with pytest.raises(Exception):
            HubDNA(hub="test", mutation_history=[])


class TestHubDNAIO:
    """Roundtrip YAML I/O."""

    def test_should_roundtrip_yaml(self, tmp_path):
        dna = HubDNA.from_yaml(FIXTURES / "risk-hub.yaml")
        out = tmp_path / "out.yaml"
        dna.to_yaml(out)
        reloaded = HubDNA.from_yaml(out)
        assert reloaded.hub == dna.hub
        assert reloaded.display_name == dna.display_name

    def test_should_load_all_hubs(self):
        hubs = HubDNA.load_all(FIXTURES)
        hub_names = [h.hub for h in hubs]
        assert "risk-hub" in hub_names
        assert "_base" not in hub_names  # Skipped

    def test_should_generate_css_filename(self):
        dna = HubDNA(hub="risk-hub")
        assert dna.get_css_filename() == "pui-tokens-risk-hub.css"
