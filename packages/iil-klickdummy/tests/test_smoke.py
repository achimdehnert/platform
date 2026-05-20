"""Smoke tests for iil-klickdummy package — every public surface importable + callable."""
from __future__ import annotations

import json
from importlib.resources import files

import pytest


def test_package_imports():
    import iil_klickdummy
    assert iil_klickdummy.__version__ == "1.0.0"


def test_all_modules_present():
    import iil_klickdummy
    for mod in ("check_i1", "check_i2", "check_i3", "check_i4",
                "extract_requirements", "inventory"):
        assert hasattr(iil_klickdummy, mod), f"missing module: {mod}"


def test_all_main_cli_endpoints():
    import iil_klickdummy
    for mod_name in ("check_i1", "check_i2", "check_i3", "check_i4",
                     "extract_requirements", "inventory"):
        mod = getattr(iil_klickdummy, mod_name)
        assert callable(getattr(mod, "main_cli", None)), \
            f"{mod_name}.main_cli missing"


def test_schemas_resource():
    schemas_dir = files("iil_klickdummy.schemas")
    names = sorted(p.name for p in schemas_dir.iterdir())
    assert "screens-spec.schema.json" in names
    assert "module-manifest.schema.json" in names
    assert "feedback-payload.schema.json" in names


def test_screens_spec_schema_is_valid_json():
    text = files("iil_klickdummy.schemas").joinpath("screens-spec.schema.json").read_text()
    schema = json.loads(text)
    assert schema["properties"]["class"]["enum"] == \
        ["mock", "stub-demo", "story", "spec-demo"]


def test_feedback_payload_schema_required_fields():
    text = files("iil_klickdummy.schemas").joinpath("feedback-payload.schema.json").read_text()
    schema = json.loads(text)
    required = set(schema["required"])
    assert {"screen", "category", "text", "spec_id",
            "klickdummy_class", "timestamp"}.issubset(required)


def test_check_i2_strict_mode():
    """LEGACY must be empty per ADR-211 Rev 12 S11-Strict-Mode."""
    from iil_klickdummy import check_i2
    assert check_i2.LEGACY == {}, \
        "iil-klickdummy ships strict-mode (LEGACY={}). Repos with legacy values must migrate first."
    assert check_i2.ALLOWED == {"mock", "stub-demo", "story", "spec-demo"}


def test_inventory_runs_clean_on_default_base():
    """Inventory should at minimum import and run without crashing."""
    import sys
    from iil_klickdummy import inventory
    # nonexistent base → all "NOT PRESENT", exit 0
    exit_code = inventory.main(["--base", "/nonexistent/path/does/not/exist"])
    assert exit_code == 0
