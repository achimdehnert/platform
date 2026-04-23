"""Tests for concept_templates.registry."""

from __future__ import annotations

import pytest

from concept_templates.registry import (
    clear_registry,
    get_framework,
    list_frameworks,
    register_framework,
    unregister_framework,
)
from concept_templates.schemas import ConceptScope, ConceptTemplate


@pytest.fixture()
def custom_template() -> ConceptTemplate:
    """A custom template for registration tests."""
    return ConceptTemplate(
        name="Custom Framework",
        scope=ConceptScope.BRANDSCHUTZ,
        framework="custom_test",
    )


class TestRegisterFramework:
    def test_should_register_custom_framework(self, custom_template):
        register_framework("custom_test", custom_template)
        result = get_framework("custom_test")
        assert result.name == "Custom Framework"

    def test_should_reject_duplicate_key(self, custom_template):
        register_framework("dup_test", custom_template)
        with pytest.raises(ValueError, match="already registered"):
            register_framework("dup_test", custom_template)

    def test_should_allow_overwrite(self, custom_template):
        register_framework("ow_test", custom_template)
        updated = ConceptTemplate(
            name="Updated",
            scope=ConceptScope.BRANDSCHUTZ,
        )
        register_framework("ow_test", updated, overwrite=True)
        result = get_framework("ow_test")
        assert result.name == "Updated"


class TestGetFramework:
    def test_should_get_builtin_brandschutz(self):
        fw = get_framework("brandschutz_mbo")
        assert fw.framework == "brandschutz_mbo"
        assert fw.scope == ConceptScope.BRANDSCHUTZ

    def test_should_get_builtin_exschutz(self):
        fw = get_framework("exschutz_trgs720")
        assert fw.framework == "exschutz_trgs720"

    def test_should_get_builtin_ausschreibung(self):
        fw = get_framework("ausschreibung_vob")
        assert fw.framework == "ausschreibung_vob"

    def test_should_raise_on_missing_key(self):
        with pytest.raises(KeyError, match="not found"):
            get_framework("nonexistent")

    def test_should_return_deep_copy(self):
        fw1 = get_framework("brandschutz_mbo")
        fw2 = get_framework("brandschutz_mbo")
        fw1.metadata["mutated"] = True
        assert "mutated" not in fw2.metadata


class TestUnregisterFramework:
    def test_should_unregister_existing(self, custom_template):
        register_framework("unreg_test", custom_template)
        removed = unregister_framework("unreg_test")
        assert removed is not None
        assert removed.name == "Custom Framework"
        with pytest.raises(KeyError):
            get_framework("unreg_test")

    def test_should_return_none_for_missing(self):
        result = unregister_framework("nonexistent")
        assert result is None


class TestListFrameworks:
    def test_should_list_all_builtins(self):
        all_fw = list_frameworks()
        assert len(all_fw) >= 3
        assert "brandschutz_mbo" in all_fw
        assert "exschutz_trgs720" in all_fw
        assert "ausschreibung_vob" in all_fw

    def test_should_filter_by_scope(self):
        bs_only = list_frameworks(scope=ConceptScope.BRANDSCHUTZ)
        assert all(
            fw.scope == ConceptScope.BRANDSCHUTZ
            for fw in bs_only.values()
        )
        assert "brandschutz_mbo" in bs_only
        assert "exschutz_trgs720" not in bs_only

    def test_should_filter_by_scope_string(self):
        ex_only = list_frameworks(scope="explosionsschutz")
        assert "exschutz_trgs720" in ex_only
        assert "brandschutz_mbo" not in ex_only

    def test_should_include_custom_after_register(self, custom_template):
        register_framework("custom_list", custom_template)
        all_fw = list_frameworks()
        assert "custom_list" in all_fw

    def test_should_return_deep_copies(self):
        all_fw = list_frameworks()
        all_fw["brandschutz_mbo"].metadata["mutated"] = True
        fresh = list_frameworks()
        assert "mutated" not in fresh["brandschutz_mbo"].metadata


class TestClearRegistry:
    def test_should_clear_all(self, custom_template):
        register_framework("clear_test", custom_template)
        clear_registry()
        # After clear, builtins should reload on next access
        all_fw = list_frameworks()
        assert "brandschutz_mbo" in all_fw
        assert "clear_test" not in all_fw
