import pytest


def test_get_setting_default():
    from iil_commons.settings import get_setting

    assert get_setting("CACHE_DEFAULT_TTL") == 300


def test_get_setting_override(settings):
    settings.IIL_COMMONS = {"CACHE_DEFAULT_TTL": 600}
    from iil_commons.settings import get_setting

    assert get_setting("CACHE_DEFAULT_TTL") == 600


def test_get_setting_explicit_default():
    from iil_commons.settings import get_setting

    assert get_setting("NONEXISTENT_KEY", "fallback") == "fallback"
