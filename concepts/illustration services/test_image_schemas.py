"""
Unit Tests: Image Generation Schemas
====================================

Tests für creative_services.prompts.schemas_image

Testet:
- Validierung aller Pydantic-Modelle
- Farbpaletten-Logik
- SD-Parameter
- Style-Spec Build-Funktionen
- Migrator
- Prompt-Validierung

Ausführung:
    pytest test_image_schemas.py -v
    pytest test_image_schemas.py -v -k "test_color"  # Nur Farb-Tests
"""

import pytest
from datetime import datetime
from typing import Any

# Import der zu testenden Module
# In der echten Implementierung:
# from creative_services.prompts.schemas_image import ...

# Für diesen Test importieren wir direkt aus der Datei
import sys
sys.path.insert(0, '/home/claude')

from creative_services_prompts_image_schemas import (
    # Enums
    OutputFormat,
    TemplateType,
    ImageFunction,
    LightingType,
    ContrastLevel,
    CompositionType,
    PerspectiveType,
    StyleStatus,
    ColorRole,
    SDSampler,
    
    # Color Schemas
    ColorSpec,
    ForbiddenColorSpec,
    ColorPalette,
    
    # SD Schemas
    SDParameters,
    
    # Style Schemas
    MediumSpec,
    LightingSpec,
    CompositionSpec,
    StyleAnchor,
    IllustrationStyleSpec,
    
    # Template Schemas
    ImageGenerationParams,
    PromptVariable,
    StylePartialTemplate,
    
    # Execution
    ImagePromptExecution,
    
    # Utilities
    StyleSpecMigrator,
    PromptValidator,
)


# =============================================================================
# SECTION 1: Enum Tests
# =============================================================================

class TestEnums:
    """Tests für alle Enum-Definitionen."""
    
    def test_output_format_has_image(self):
        """OutputFormat muss IMAGE enthalten."""
        assert OutputFormat.IMAGE.value == "image"
        assert OutputFormat.TEXT.value == "text"
    
    def test_template_type_has_style_partial(self):
        """TemplateType muss STYLE_PARTIAL enthalten."""
        assert TemplateType.STYLE_PARTIAL.value == "style_partial"
    
    def test_image_function_german_values(self):
        """ImageFunction hat deutsche Werte."""
        assert ImageFunction.NARRATIVE.value == "erzählend"
        assert ImageFunction.ATMOSPHERIC.value == "atmosphärisch"
    
    def test_sd_sampler_values(self):
        """SDSampler hat korrekte Sampler-Namen."""
        assert "DPM++" in SDSampler.DPM_PP_2M_KARRAS.value
        assert "Karras" in SDSampler.DPM_PP_2M_KARRAS.value


# =============================================================================
# SECTION 2: Color Schema Tests
# =============================================================================

class TestColorSpec:
    """Tests für ColorSpec."""
    
    def test_valid_color_spec(self):
        """Gültige Farb-Spezifikation."""
        color = ColorSpec(
            hex_code="#5B6E7A",
            name="dusty_blue",
            role=ColorRole.PRIMARY,
            semantic="Ruhe, Weite",
        )
        assert color.hex_code == "#5B6E7A"  # Normalisiert zu Großbuchstaben
        assert color.name == "dusty_blue"
    
    def test_hex_code_validation(self):
        """Ungültiger Hex-Code wird abgelehnt."""
        with pytest.raises(ValueError):
            ColorSpec(
                hex_code="invalid",
                name="test",
                role=ColorRole.PRIMARY,
            )
    
    def test_hex_code_normalization(self):
        """Hex-Codes werden zu Großbuchstaben normalisiert."""
        color = ColorSpec(
            hex_code="#5b6e7a",  # Kleinbuchstaben
            name="test",
            role=ColorRole.PRIMARY,
        )
        assert color.hex_code == "#5B6E7A"
    
    def test_name_validation_snake_case(self):
        """Name muss snake_case oder kebab-case sein."""
        # Gültig
        ColorSpec(hex_code="#000001", name="dusty_blue", role=ColorRole.PRIMARY)
        ColorSpec(hex_code="#000002", name="dusty-blue", role=ColorRole.PRIMARY)
        
        # Ungültig
        with pytest.raises(ValueError):
            ColorSpec(hex_code="#000003", name="Dusty Blue", role=ColorRole.PRIMARY)
        with pytest.raises(ValueError):
            ColorSpec(hex_code="#000004", name="123invalid", role=ColorRole.PRIMARY)
    
    def test_color_spec_is_frozen(self):
        """ColorSpec ist immutable."""
        color = ColorSpec(
            hex_code="#5B6E7A",
            name="test",
            role=ColorRole.PRIMARY,
        )
        with pytest.raises(Exception):  # Pydantic ValidationError oder AttributeError
            color.hex_code = "#FFFFFF"


class TestForbiddenColorSpec:
    """Tests für ForbiddenColorSpec."""
    
    def test_valid_with_hex(self):
        """Gültig mit Hex-Code."""
        forbidden = ForbiddenColorSpec(
            hex_code="#000000",
            reason="Kein reines Schwarz",
        )
        assert forbidden.hex_code == "#000000"
    
    def test_valid_with_pattern(self):
        """Gültig mit Pattern."""
        forbidden = ForbiddenColorSpec(
            pattern="neon",
            reason="Zu grell",
        )
        assert forbidden.pattern == "neon"
    
    def test_requires_hex_or_pattern(self):
        """Muss entweder hex_code oder pattern haben."""
        with pytest.raises(ValueError, match="hex_code oder pattern"):
            ForbiddenColorSpec(reason="Ohne Ziel")


class TestColorPalette:
    """Tests für ColorPalette."""
    
    @pytest.fixture
    def valid_palette(self) -> ColorPalette:
        """Fixture für gültige Farbpalette."""
        return ColorPalette(
            primary=[
                ColorSpec(hex_code="#5B6E7A", name="dusty_blue", role=ColorRole.PRIMARY),
                ColorSpec(hex_code="#8A8F94", name="muted_grey", role=ColorRole.PRIMARY),
            ],
            accent=[
                ColorSpec(hex_code="#6FAFB2", name="cool_cyan", role=ColorRole.ACCENT),
            ],
            forbidden=[
                ForbiddenColorSpec(pattern="neon", reason="Zu grell"),
                ForbiddenColorSpec(hex_code="#000000", reason="Kein reines Schwarz"),
            ],
        )
    
    def test_valid_palette(self, valid_palette):
        """Gültige Palette wird akzeptiert."""
        assert len(valid_palette.primary) == 2
        assert len(valid_palette.accent) == 1
        assert len(valid_palette.forbidden) == 2
    
    def test_primary_must_have_primary_role(self):
        """Primary-Farben müssen role=PRIMARY haben."""
        with pytest.raises(ValueError, match="role=PRIMARY"):
            ColorPalette(
                primary=[
                    ColorSpec(hex_code="#5B6E7A", name="test", role=ColorRole.ACCENT),
                ],
            )
    
    def test_get_all_hex_codes(self, valid_palette):
        """get_all_hex_codes gibt alle erlaubten Hex-Codes zurück."""
        hex_codes = valid_palette.get_all_hex_codes()
        assert "#5B6E7A" in hex_codes
        assert "#8A8F94" in hex_codes
        assert "#6FAFB2" in hex_codes
        assert len(hex_codes) == 3
    
    def test_get_forbidden_patterns(self, valid_palette):
        """get_forbidden_patterns gibt alle verbotenen Patterns zurück."""
        patterns = valid_palette.get_forbidden_patterns()
        assert "neon" in patterns
        assert "#000000" in patterns


# =============================================================================
# SECTION 3: SD Parameters Tests
# =============================================================================

class TestSDParameters:
    """Tests für SDParameters."""
    
    def test_valid_params(self):
        """Gültige SD-Parameter."""
        params = SDParameters(
            base_model="sd_xl_base_1.0",
            sampler=SDSampler.DPM_PP_2M_KARRAS,
            steps=30,
            cfg_scale=5.5,
            width=768,
            height=1024,
        )
        assert params.base_model == "sd_xl_base_1.0"
        assert params.steps == 30
    
    def test_steps_range(self):
        """Steps müssen zwischen 10 und 100 sein."""
        with pytest.raises(ValueError):
            SDParameters(base_model="test", steps=5)
        with pytest.raises(ValueError):
            SDParameters(base_model="test", steps=150)
    
    def test_resolution_multiple_of_64(self):
        """Auflösung muss durch 64 teilbar sein."""
        with pytest.raises(ValueError):
            SDParameters(base_model="test", width=700)  # Nicht durch 64 teilbar
    
    def test_resolution_property(self):
        """resolution Property gibt Tuple zurück."""
        params = SDParameters(base_model="test", width=768, height=1024)
        assert params.resolution == (768, 1024)
    
    def test_aspect_ratio_property(self):
        """aspect_ratio Property berechnet korrekt."""
        params = SDParameters(base_model="test", width=768, height=1024)
        assert params.aspect_ratio == 0.75
    
    def test_lora_prompt_tag_with_lora(self):
        """LoRA-Tag wird korrekt generiert."""
        params = SDParameters(
            base_model="test",
            lora_key="my_style_lora",
            lora_strength=1.2,
        )
        assert params.get_lora_prompt_tag() == "<my_style_lora:1.2>"
    
    def test_lora_prompt_tag_without_lora(self):
        """Ohne LoRA: leerer String."""
        params = SDParameters(base_model="test")
        assert params.get_lora_prompt_tag() == ""


# =============================================================================
# SECTION 4: Style Spec Tests
# =============================================================================

class TestIllustrationStyleSpec:
    """Tests für IllustrationStyleSpec."""
    
    @pytest.fixture
    def minimal_spec(self) -> IllustrationStyleSpec:
        """Fixture für minimale gültige Spec."""
        return IllustrationStyleSpec(
            style_key="test_style",
            name="Test Style",
            emotion=["ruhig"],
            target_audience="Test Audience",
            image_function=[ImageFunction.ATMOSPHERIC],
            medium=MediumSpec(
                medium="test medium",
                line_character="test lines",
                color_application="test colors",
                texture="test texture",
            ),
            colors=ColorPalette(
                primary=[
                    ColorSpec(hex_code="#5B6E7A", name="test", role=ColorRole.PRIMARY),
                ],
            ),
            lighting=LightingSpec(),
            composition=CompositionSpec(),
        )
    
    def test_minimal_spec_is_valid(self, minimal_spec):
        """Minimale Spec ist gültig."""
        assert minimal_spec.style_key == "test_style"
        assert minimal_spec.schema_version == 1
    
    def test_style_key_validation(self):
        """style_key muss snake_case sein."""
        with pytest.raises(ValueError):
            IllustrationStyleSpec(
                style_key="Invalid Style",  # Spaces nicht erlaubt
                name="Test",
                emotion=["test"],
                target_audience="test",
                image_function=[ImageFunction.ATMOSPHERIC],
                medium=MediumSpec(
                    medium="test", line_character="test",
                    color_application="test", texture="test"
                ),
                colors=ColorPalette(primary=[
                    ColorSpec(hex_code="#000001", name="test", role=ColorRole.PRIMARY)
                ]),
                lighting=LightingSpec(),
                composition=CompositionSpec(),
            )
    
    def test_version_format(self, minimal_spec):
        """Version muss semantisches Format haben."""
        assert minimal_spec.version == "1.0"
        
        # Gültige Versionen
        minimal_spec.model_copy(update={"version": "1.0"})
        minimal_spec.model_copy(update={"version": "1.0.0"})
        minimal_spec.model_copy(update={"version": "12.34.56"})
    
    def test_build_style_block(self, minimal_spec):
        """build_style_block generiert gültigen Style-Block."""
        style_block = minimal_spec.build_style_block()
        assert "test medium" in style_block
        assert "test lines" in style_block
        assert "#5B6E7A" in style_block
    
    def test_build_style_block_with_lora(self, minimal_spec):
        """Style-Block enthält LoRA-Tag wenn vorhanden."""
        spec_with_lora = minimal_spec.model_copy(
            update={"sd_params": SDParameters(
                base_model="test",
                lora_key="my_lora",
                lora_strength=1.0,
            )}
        )
        style_block = spec_with_lora.build_style_block()
        assert "<my_lora:1.0>" in style_block
    
    def test_build_negative_prompt(self, minimal_spec):
        """build_negative_prompt generiert Negative-Prompt."""
        spec_with_forbidden = minimal_spec.model_copy(
            update={"forbidden_elements": ["photorealistic", "3d render"]}
        )
        negative = spec_with_forbidden.build_negative_prompt()
        assert "photorealistic" in negative
        assert "3d render" in negative
    
    def test_get_full_version(self, minimal_spec):
        """get_full_version kombiniert key und version."""
        assert minimal_spec.get_full_version() == "test_style:1.0"


# =============================================================================
# SECTION 5: Image Generation Params Tests
# =============================================================================

class TestImageGenerationParams:
    """Tests für ImageGenerationParams."""
    
    def test_valid_with_partial_key(self):
        """Gültig mit style_partial_key."""
        params = ImageGenerationParams(
            style_partial_key="illustration.style.test",
        )
        assert params.style_partial_key == "illustration.style.test"
    
    def test_valid_with_inline_style(self):
        """Gültig mit inline_style."""
        inline = IllustrationStyleSpec(
            style_key="inline_test",
            name="Inline Test",
            emotion=["test"],
            target_audience="test",
            image_function=[ImageFunction.ATMOSPHERIC],
            medium=MediumSpec(
                medium="test", line_character="test",
                color_application="test", texture="test"
            ),
            colors=ColorPalette(primary=[
                ColorSpec(hex_code="#000001", name="test", role=ColorRole.PRIMARY)
            ]),
            lighting=LightingSpec(),
            composition=CompositionSpec(),
        )
        params = ImageGenerationParams(inline_style=inline)
        assert params.inline_style is not None
    
    def test_requires_style_source(self):
        """Muss entweder partial_key oder inline_style haben."""
        with pytest.raises(ValueError, match="style_partial_key oder inline_style"):
            ImageGenerationParams()
    
    def test_cannot_have_both_style_sources(self):
        """Kann nicht beide Style-Quellen haben."""
        inline = IllustrationStyleSpec(
            style_key="test",
            name="Test",
            emotion=["test"],
            target_audience="test",
            image_function=[ImageFunction.ATMOSPHERIC],
            medium=MediumSpec(
                medium="test", line_character="test",
                color_application="test", texture="test"
            ),
            colors=ColorPalette(primary=[
                ColorSpec(hex_code="#000001", name="test", role=ColorRole.PRIMARY)
            ]),
            lighting=LightingSpec(),
            composition=CompositionSpec(),
        )
        with pytest.raises(ValueError, match="nur.*ODER"):
            ImageGenerationParams(
                style_partial_key="illustration.style.test",
                inline_style=inline,
            )


# =============================================================================
# SECTION 6: Execution Tests
# =============================================================================

class TestImagePromptExecution:
    """Tests für ImagePromptExecution."""
    
    @pytest.fixture
    def execution(self) -> ImagePromptExecution:
        """Fixture für Execution."""
        return ImagePromptExecution(
            template_key="test.template",
            template_version="1.0",
            style_version="test_style:1.0",
            positive_prompt="<lora:test:1.0>, watercolor, astronaut in corridor",
            negative_prompt="photorealistic, 3d render",
            sd_params=SDParameters(
                base_model="sd_xl_base_1.0",
                width=768,
                height=1024,
                steps=30,
                cfg_scale=7.0,
            ),
        )
    
    def test_execution_has_uuid(self, execution):
        """Execution hat automatisch generierte UUID."""
        assert execution.execution_id is not None
        assert len(execution.execution_id) == 36  # UUID Format
    
    def test_to_sd_request(self, execution):
        """to_sd_request generiert korrektes Dict."""
        request = execution.to_sd_request()
        
        assert request["prompt"] == execution.positive_prompt
        assert request["negative_prompt"] == execution.negative_prompt
        assert request["width"] == 768
        assert request["height"] == 1024
        assert request["steps"] == 30
        assert request["cfg_scale"] == 7.0
        assert request["seed"] == -1  # None wird zu -1
    
    def test_to_comfyui_workflow(self, execution):
        """to_comfyui_workflow generiert Workflow."""
        workflow = execution.to_comfyui_workflow()
        
        assert "prompt" in workflow
        assert "3" in workflow["prompt"]  # KSampler
        assert "6" in workflow["prompt"]  # CLIPTextEncode positive
        assert "7" in workflow["prompt"]  # CLIPTextEncode negative


# =============================================================================
# SECTION 7: Migrator Tests
# =============================================================================

class TestStyleSpecMigrator:
    """Tests für StyleSpecMigrator."""
    
    def test_detect_version_with_version(self):
        """Erkennt Version wenn vorhanden."""
        data = {"schema_version": 2, "other": "data"}
        assert StyleSpecMigrator.detect_version(data) == 2
    
    def test_detect_version_default(self):
        """Default Version ist 1."""
        data = {"other": "data"}
        assert StyleSpecMigrator.detect_version(data) == 1
    
    def test_migrate_same_version(self):
        """Migration zur gleichen Version ändert nichts."""
        data = {"schema_version": 1, "other": "data"}
        migrated = StyleSpecMigrator.migrate(data, target_version=1)
        assert migrated == data


# =============================================================================
# SECTION 8: Prompt Validator Tests
# =============================================================================

class TestPromptValidator:
    """Tests für PromptValidator."""
    
    def test_valid_prompt(self):
        """Gültiger Prompt passiert Validierung."""
        params = ImageGenerationParams(
            style_partial_key="test.style",
            forbidden_terms=["photorealistic", "anime"],
            required_terms=["illustration"],
        )
        prompt = "watercolor illustration of astronaut"
        
        is_valid, errors = PromptValidator.validate_prompt(prompt, params)
        
        assert is_valid is True
        assert errors == []
    
    def test_forbidden_term_detected(self):
        """Verbotener Term wird erkannt."""
        params = ImageGenerationParams(
            style_partial_key="test.style",
            forbidden_terms=["photorealistic"],
        )
        prompt = "photorealistic illustration of astronaut"
        
        is_valid, errors = PromptValidator.validate_prompt(prompt, params)
        
        assert is_valid is False
        assert len(errors) == 1
        assert "photorealistic" in errors[0]
    
    def test_required_term_missing(self):
        """Fehlender erforderlicher Term wird erkannt."""
        params = ImageGenerationParams(
            style_partial_key="test.style",
            required_terms=["watercolor"],
        )
        prompt = "digital painting of astronaut"
        
        is_valid, errors = PromptValidator.validate_prompt(prompt, params)
        
        assert is_valid is False
        assert len(errors) == 1
        assert "watercolor" in errors[0]
    
    def test_case_insensitive(self):
        """Validierung ist case-insensitive."""
        params = ImageGenerationParams(
            style_partial_key="test.style",
            forbidden_terms=["PHOTOREALISTIC"],
            required_terms=["ILLUSTRATION"],
        )
        prompt = "watercolor illustration of astronaut"
        
        is_valid, errors = PromptValidator.validate_prompt(prompt, params)
        
        assert is_valid is True
    
    def test_with_style_spec_forbidden(self):
        """Style-Spec verbotene Elemente werden geprüft."""
        params = ImageGenerationParams(style_partial_key="test.style")
        style_spec = IllustrationStyleSpec(
            style_key="test",
            name="Test",
            emotion=["test"],
            target_audience="test",
            image_function=[ImageFunction.ATMOSPHERIC],
            medium=MediumSpec(
                medium="test", line_character="test",
                color_application="test", texture="test"
            ),
            colors=ColorPalette(primary=[
                ColorSpec(hex_code="#000001", name="test", role=ColorRole.PRIMARY)
            ]),
            lighting=LightingSpec(),
            composition=CompositionSpec(),
            forbidden_elements=["dramatic lighting"],
        )
        prompt = "watercolor with dramatic lighting"
        
        is_valid, errors = PromptValidator.validate_prompt(
            prompt, params, style_spec=style_spec
        )
        
        assert is_valid is False
        assert "dramatic lighting" in errors[0]


# =============================================================================
# SECTION 9: Integration Tests
# =============================================================================

class TestFullWorkflow:
    """Integration-Tests für den gesamten Workflow."""
    
    def test_create_style_and_generate_prompt(self):
        """Erstellt Style und generiert Prompt."""
        # 1. Style-Spec erstellen
        style = IllustrationStyleSpec(
            style_key="integration_test",
            version="1.0",
            name="Integration Test Style",
            emotion=["ruhig", "kontemplativ"],
            target_audience="Test",
            image_function=[ImageFunction.ATMOSPHERIC],
            medium=MediumSpec(
                medium="ink and watercolor illustration",
                line_character="thin, precise ink lines",
                color_application="soft watercolor washes",
                texture="natural paper grain",
            ),
            colors=ColorPalette(
                primary=[
                    ColorSpec(hex_code="#5B6E7A", name="dusty_blue", role=ColorRole.PRIMARY),
                ],
                accent=[
                    ColorSpec(hex_code="#6FAFB2", name="cool_cyan", role=ColorRole.ACCENT),
                ],
                forbidden=[
                    ForbiddenColorSpec(pattern="neon", reason="Zu grell"),
                ],
            ),
            lighting=LightingSpec(
                lighting=LightingType.DIFFUSE,
                lighting_description="diffuse, global lighting",
                contrast=ContrastLevel.MODERATE,
            ),
            composition=CompositionSpec(
                composition=CompositionType.CENTERED,
                perspective=PerspectiveType.EYE_LEVEL,
                negative_space="generous",
            ),
            forbidden_elements=["photorealistic", "3d render", "anime"],
            sd_params=SDParameters(
                base_model="sd_xl_base_1.0",
                lora_key="test_lora",
                lora_strength=1.0,
                steps=30,
                cfg_scale=5.5,
                width=768,
                height=1024,
            ),
        )
        
        # 2. Style-Block generieren
        style_block = style.build_style_block()
        assert "<test_lora:1.0>" in style_block
        assert "ink and watercolor illustration" in style_block
        assert "#5B6E7A" in style_block
        
        # 3. Negative-Prompt generieren
        negative = style.build_negative_prompt()
        assert "photorealistic" in negative
        assert "neon" in negative
        
        # 4. Vollständigen Prompt zusammenbauen
        content = "illustration of a lone astronaut standing quietly in an empty corridor"
        full_prompt = f"{style_block},\n\n{content},\n\ncalm atmosphere"
        
        # 5. Validieren
        params = ImageGenerationParams(
            style_partial_key="integration.test",
            forbidden_terms=style.forbidden_elements,
            required_terms=["illustration"],
        )
        is_valid, errors = PromptValidator.validate_prompt(
            full_prompt, params, style_spec=style
        )
        assert is_valid is True, f"Validation errors: {errors}"
        
        # 6. Execution erstellen
        execution = ImagePromptExecution(
            template_key="test.template",
            template_version="1.0",
            style_version=style.get_full_version(),
            positive_prompt=full_prompt,
            negative_prompt=negative,
            sd_params=style.sd_params,
            variables_used={"subject": "astronaut", "environment": "corridor"},
        )
        
        # 7. SD-Request generieren
        sd_request = execution.to_sd_request()
        assert sd_request["prompt"] == full_prompt
        assert sd_request["negative_prompt"] == negative
        assert sd_request["width"] == 768
        assert sd_request["height"] == 1024
        
        print("\n=== Integration Test Output ===")
        print(f"\nStyle Block:\n{style_block}")
        print(f"\nNegative Prompt:\n{negative}")
        print(f"\nFull Prompt:\n{full_prompt}")
        print(f"\nSD Request:\n{sd_request}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # Für schnellen lokalen Test ohne pytest
    print("Running basic tests...")
    
    # Enum test
    assert OutputFormat.IMAGE.value == "image"
    print("✓ Enums OK")
    
    # Color test
    color = ColorSpec(hex_code="#5b6e7a", name="test", role=ColorRole.PRIMARY)
    assert color.hex_code == "#5B6E7A"
    print("✓ ColorSpec OK")
    
    # SD Params test
    params = SDParameters(base_model="test", lora_key="lora", lora_strength=1.0)
    assert params.get_lora_prompt_tag() == "<lora:1.0>"
    print("✓ SDParameters OK")
    
    # Integration test
    test = TestFullWorkflow()
    test.test_create_style_and_generate_prompt()
    print("✓ Integration OK")
    
    print("\n✅ All basic tests passed!")
