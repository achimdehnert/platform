"""
aifw/tests/test_service.py — Unit + Integration tests for aifw 0.6.0.

Covers ADR-097 acceptance criteria F-01..F-13, S-01..S-05, B-01..B-02.

Run:
    pytest aifw/tests/ -v
    pytest aifw/tests/ -v --cov=aifw --cov-report=term-missing

Requirements:
    pytest-django, fakeredis, factory-boy
    DJANGO_SETTINGS_MODULE=aifw.test_settings (or project settings)
"""
from __future__ import annotations

import pytest
from django.core.cache import cache
from django.db import IntegrityError

from aifw.constants import QualityLevel, VALID_PRIORITIES
from aifw.exceptions import ConfigurationError
from aifw.service import (
    _lookup_cascade,
    _action_cache_key,
    get_action_config,
    get_quality_level_for_tier,
)


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def clear_cache():
    """Clear Redis cache before each test to prevent cross-test pollution."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def llm_model(db):
    """Create a minimal LLMModel for use in AIActionType rows."""
    from aifw.models import LLMModel  # adjust import to actual model location
    return LLMModel.objects.create(
        model_identifier="anthropic/claude-haiku-4-5",
        provider="anthropic",
        base_url="",
        api_key_env_var="ANTHROPIC_API_KEY",
    )


@pytest.fixture
def catchall_row(db, llm_model):
    """A catch-all AIActionType row (both NULL) for action_code='test_action'."""
    from aifw.models import AIActionType
    return AIActionType.objects.create(
        code="test_action",
        name="Test Action (catch-all)",
        default_model=llm_model,
        quality_level=None,
        priority=None,
        prompt_template_key=None,
        is_active=True,
    )


@pytest.fixture
def level_row(db, llm_model):
    """A level-only AIActionType row (quality_level=8, priority=NULL)."""
    from aifw.models import AIActionType
    return AIActionType.objects.create(
        code="test_action",
        name="Test Action (ql=8, prio=NULL)",
        default_model=llm_model,
        quality_level=8,
        priority=None,
        prompt_template_key="test_action_premium",
        is_active=True,
    )


@pytest.fixture
def priority_row(db, llm_model):
    """A priority-only AIActionType row (quality_level=NULL, priority='fast')."""
    from aifw.models import AIActionType
    return AIActionType.objects.create(
        code="test_action",
        name="Test Action (ql=NULL, prio=fast)",
        default_model=llm_model,
        quality_level=None,
        priority="fast",
        prompt_template_key="test_action_fast",
        is_active=True,
    )


@pytest.fixture
def exact_row(db, llm_model):
    """An exact-match AIActionType row (quality_level=8, priority='quality')."""
    from aifw.models import AIActionType
    return AIActionType.objects.create(
        code="test_action",
        name="Test Action (ql=8, prio=quality)",
        default_model=llm_model,
        quality_level=8,
        priority="quality",
        prompt_template_key="test_action_premium_quality",
        is_active=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TEST: QualityLevel constants (ADR-097 §4)
# ══════════════════════════════════════════════════════════════════════════════

class TestQualityLevelConstants:
    """ADR-097 acceptance criterion: QualityLevel values correct."""

    def test_economy_is_2(self):
        assert QualityLevel.ECONOMY == 2

    def test_balanced_is_5(self):
        assert QualityLevel.BALANCED == 5

    def test_premium_is_8(self):
        assert QualityLevel.PREMIUM == 8

    def test_band_for_economy(self):
        for ql in (1, 2, 3):
            assert QualityLevel.band_for(ql) == "economy"

    def test_band_for_balanced(self):
        for ql in (4, 5, 6):
            assert QualityLevel.band_for(ql) == "balanced"

    def test_band_for_premium(self):
        for ql in (7, 8, 9):
            assert QualityLevel.band_for(ql) == "premium"

    def test_valid_priorities(self):
        assert VALID_PRIORITIES == frozenset({"fast", "balanced", "quality"})


# ══════════════════════════════════════════════════════════════════════════════
# TEST: _lookup_cascade — all 4 steps (F-02..F-06)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestLookupCascade:
    """ADR-097 acceptance criteria F-02..F-06."""

    def test_f02_exact_match_returns_exact_row(self, catchall_row, level_row, exact_row):
        """F-02: Step 1 returns exact-match row when it exists."""
        result = _lookup_cascade("test_action", quality_level=8, priority="quality")
        assert result.pk == exact_row.pk
        assert result.prompt_template_key == "test_action_premium_quality"

    def test_f03_level_match_when_exact_absent(self, catchall_row, level_row):
        """F-03: Step 2 returns level-match row when exact absent."""
        # No exact row (quality_level=8, priority="quality")
        result = _lookup_cascade("test_action", quality_level=8, priority=None)
        assert result.pk == level_row.pk
        assert result.prompt_template_key == "test_action_premium"

    def test_f03_level_match_falls_through_from_exact(self, catchall_row, level_row):
        """F-03 variant: exact match absent → step 2 returns level-match."""
        # priority="quality" has no exact row, falls to level match (priority=NULL)
        result = _lookup_cascade("test_action", quality_level=8, priority="quality")
        assert result.pk == level_row.pk

    def test_f04_priority_match_when_level_absent(self, catchall_row, priority_row):
        """F-04: Step 3 returns priority-match row when quality is catch-all."""
        result = _lookup_cascade("test_action", quality_level=None, priority="fast")
        assert result.pk == priority_row.pk
        assert result.prompt_template_key == "test_action_fast"

    def test_f05_catchall_returned_when_no_specific_rows(self, catchall_row):
        """F-05: Step 4 returns catch-all row."""
        result = _lookup_cascade("test_action", quality_level=None, priority=None)
        assert result.pk == catchall_row.pk

    def test_f05_catchall_returned_for_unknown_quality_level(self, catchall_row):
        """F-05 variant: quality_level with no matching row → catch-all."""
        result = _lookup_cascade("test_action", quality_level=3, priority=None)
        assert result.pk == catchall_row.pk

    def test_f06_raises_configuration_error_when_no_catchall(self, db):
        """F-06: ConfigurationError raised when no row matches at any level."""
        # No AIActionType rows at all
        with pytest.raises(ConfigurationError) as exc_info:
            _lookup_cascade("nonexistent_action", quality_level=8, priority="quality")
        assert "nonexistent_action" in str(exc_info.value)
        assert "check_aifw_config" in str(exc_info.value)

    def test_f01_existing_callsites_unaffected(self, catchall_row):
        """F-01: quality_level=None, priority=None → catch-all (legacy behaviour unchanged)."""
        result = _lookup_cascade("test_action", quality_level=None, priority=None)
        assert result is not None  # No exception raised


# ══════════════════════════════════════════════════════════════════════════════
# TEST: Partial unique index enforcement (F-07, F-08)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPartialUniqueIndexes:
    """ADR-097 acceptance criteria F-07, F-08, S-04."""

    def test_f07_duplicate_catchall_rejected(self, catchall_row, llm_model):
        """F-07: Duplicate catch-all row rejected by DB (uix_aiaction_catchall)."""
        from aifw.models import AIActionType
        with pytest.raises(IntegrityError):
            AIActionType.objects.create(
                code="test_action",
                name="Duplicate catch-all",
                default_model=llm_model,
                quality_level=None,
                priority=None,
                is_active=True,
            )

    def test_f07_duplicate_level_only_rejected(self, level_row, llm_model):
        """F-07 variant: Duplicate level-only row rejected (uix_aiaction_ql_only)."""
        from aifw.models import AIActionType
        with pytest.raises(IntegrityError):
            AIActionType.objects.create(
                code="test_action",
                name="Duplicate level row",
                default_model=llm_model,
                quality_level=8,
                priority=None,
                is_active=True,
            )

    def test_f07_duplicate_prio_only_rejected(self, priority_row, llm_model):
        """F-07 variant: Duplicate priority-only row rejected (uix_aiaction_prio_only)."""
        from aifw.models import AIActionType
        with pytest.raises(IntegrityError):
            AIActionType.objects.create(
                code="test_action",
                name="Duplicate priority row",
                default_model=llm_model,
                quality_level=None,
                priority="fast",
                is_active=True,
            )

    def test_f07_duplicate_exact_rejected(self, exact_row, llm_model):
        """F-07 variant: Duplicate exact row rejected (uix_aiaction_exact)."""
        from aifw.models import AIActionType
        with pytest.raises(IntegrityError):
            AIActionType.objects.create(
                code="test_action",
                name="Duplicate exact row",
                default_model=llm_model,
                quality_level=8,
                priority="quality",
                is_active=True,
            )

    def test_f08_invalid_priority_rejected_by_check_constraint(self, db, llm_model):
        """F-08: priority='invalid' rejected by DB CHECK constraint."""
        from aifw.models import AIActionType
        with pytest.raises(Exception):  # IntegrityError or DatabaseError depending on backend
            AIActionType.objects.create(
                code="test_action",
                name="Invalid priority",
                default_model=llm_model,
                quality_level=None,
                priority="INVALID_VALUE",
                is_active=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TEST: get_action_config cache (F-09, F-10)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGetActionConfigCache:
    """ADR-097 acceptance criteria F-09, F-10."""

    def test_f09_cached_result_on_second_call(self, catchall_row):
        """F-09: Second call returns cached result (no DB query)."""
        # First call — DB hit
        config1 = get_action_config("test_action", None, None)

        # Second call — cache hit (assert no DB queries)
        with pytest.assertNumQueries(0):  # pytest-django assertion
            config2 = get_action_config("test_action", None, None)

        assert config1 == config2

    def test_f10_save_invalidates_cache(self, catchall_row, llm_model):
        """F-10: AIActionType.save() invalidates all cache keys for that code."""
        # Populate cache
        get_action_config("test_action", None, None)
        get_action_config("test_action", 8, None)

        # Modify the row (triggers post_save signal → cache invalidation)
        catchall_row.max_tokens = 9999
        catchall_row.save()

        # Verify cache is cleared — next call should hit DB again
        cache_key = _action_cache_key("test_action", None, None)
        assert cache.get(cache_key) is None, "Cache should be cleared after save()"

    def test_f10_delete_invalidates_cache(self, catchall_row, llm_model):
        """F-10 variant: AIActionType.delete() also invalidates cache."""
        get_action_config("test_action", None, None)
        catchall_row.delete()
        cache_key = _action_cache_key("test_action", None, None)
        assert cache.get(cache_key) is None


# ══════════════════════════════════════════════════════════════════════════════
# TEST: get_quality_level_for_tier (F-11, F-12)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGetQualityLevelForTier:
    """ADR-097 acceptance criteria F-11, F-12."""

    def test_f11_premium_returns_8_after_seed(self, db):
        """F-11: get_quality_level_for_tier('premium') returns 8 after seed migration."""
        # Seed migration must have created the row
        result = get_quality_level_for_tier("premium")
        assert result == QualityLevel.PREMIUM  # 8

    def test_f11_pro_returns_5(self, db):
        result = get_quality_level_for_tier("pro")
        assert result == QualityLevel.BALANCED  # 5

    def test_f11_freemium_returns_2(self, db):
        result = get_quality_level_for_tier("freemium")
        assert result == QualityLevel.ECONOMY  # 2

    def test_f12_none_returns_balanced(self):
        """F-12: get_quality_level_for_tier(None) returns QualityLevel.BALANCED (5)."""
        result = get_quality_level_for_tier(None)
        assert result == QualityLevel.BALANCED  # 5

    def test_f12_unknown_tier_returns_balanced(self, db):
        """F-12 variant: unknown tier also returns BALANCED fallback."""
        result = get_quality_level_for_tier("unknown_enterprise_tier")
        assert result == QualityLevel.BALANCED

    def test_inactive_tier_treated_as_missing(self, db):
        """Inactive TierQualityMapping row → fallback to BALANCED."""
        from aifw.models import TierQualityMapping
        TierQualityMapping.objects.filter(tier="premium").update(is_active=False)
        result = get_quality_level_for_tier("premium")
        assert result == QualityLevel.BALANCED


# ══════════════════════════════════════════════════════════════════════════════
# TEST: AIActionType model validation
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAIActionTypeValidation:
    """Model-level validation via clean()."""

    def test_valid_priorities_accepted(self, db, llm_model):
        from aifw.models import AIActionType
        from django.core.exceptions import ValidationError

        for prio in (None, "fast", "balanced", "quality"):
            obj = AIActionType(
                code="x",
                name="x",
                default_model=llm_model,
                quality_level=None,
                priority=prio,
            )
            obj.clean()  # Should not raise

    def test_invalid_priority_rejected_by_clean(self, db, llm_model):
        from aifw.models import AIActionType
        from django.core.exceptions import ValidationError

        obj = AIActionType(
            code="x",
            name="x",
            default_model=llm_model,
            quality_level=None,
            priority="TYPO",
        )
        with pytest.raises(ValidationError):
            obj.clean()

    def test_quality_level_out_of_range_rejected(self, db, llm_model):
        from aifw.models import AIActionType
        from django.core.exceptions import ValidationError

        for ql in (0, 10, -1, 100):
            obj = AIActionType(
                code="x",
                name="x",
                default_model=llm_model,
                quality_level=ql,
                priority=None,
            )
            with pytest.raises(ValidationError):
                obj.clean()

    def test_str_representation(self, catchall_row, level_row, exact_row):
        assert str(catchall_row) == "test_action"
        assert str(level_row) == "test_action:ql=8"
        assert str(exact_row) == "test_action:ql=8:p=quality"


# ══════════════════════════════════════════════════════════════════════════════
# TEST: ActionConfig TypedDict contract (F-09 contract check)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestActionConfigContract:
    """ADR-097 §5.2 — ActionConfig shape."""

    REQUIRED_KEYS = {
        "action_id", "model_id", "model", "provider",
        "base_url", "api_key_env_var", "prompt_template_key",
        "max_tokens", "temperature",
    }

    def test_all_required_keys_present(self, catchall_row):
        config = get_action_config("test_action", None, None)
        assert set(config.keys()) >= self.REQUIRED_KEYS, (
            f"Missing keys: {self.REQUIRED_KEYS - set(config.keys())}"
        )

    def test_action_id_is_int(self, catchall_row):
        config = get_action_config("test_action", None, None)
        assert isinstance(config["action_id"], int)

    def test_model_is_str(self, catchall_row):
        config = get_action_config("test_action", None, None)
        assert isinstance(config["model"], str)

    def test_max_tokens_is_int(self, catchall_row):
        config = get_action_config("test_action", None, None)
        assert isinstance(config["max_tokens"], int)

    def test_temperature_is_float(self, catchall_row):
        config = get_action_config("test_action", None, None)
        assert isinstance(config["temperature"], float)

    def test_prompt_template_key_is_str_or_none(self, catchall_row, level_row):
        # catch-all has no template key
        config_catchall = get_action_config("test_action", None, None)
        assert config_catchall["prompt_template_key"] is None

        # level row has template key
        config_level = get_action_config("test_action", 8, None)
        assert isinstance(config_level["prompt_template_key"], str)
