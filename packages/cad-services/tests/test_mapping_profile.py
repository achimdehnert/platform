import json

from cad_services.mapping import LayerMapping, MappingProfile
from cad_services.models import ElementCategory


def test_get_category_for_layer_matches():
    profile = MappingProfile(
        name="t",
        layer_mappings=[
            LayerMapping(pattern=r"WAND.*", category=ElementCategory.WALL),
        ],
    )

    assert profile.get_category_for_layer("WAND_A") == ElementCategory.WALL
    assert profile.get_category_for_layer("FOO") == ElementCategory.UNKNOWN


def test_compiled_patterns_cached():
    profile = MappingProfile(
        name="t",
        layer_mappings=[
            LayerMapping(pattern=r"WAND.*", category=ElementCategory.WALL),
        ],
    )

    first = profile._compiled_patterns
    second = profile._compiled_patterns
    assert first is second


def test_profile_from_json(tmp_path):
    data = {
        "name": "p1",
        "version": "1.0",
        "layer_mappings": [
            {"pattern": "WAND.*", "category": "wall", "properties": {}},
        ],
    }

    p = tmp_path / "p1.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    profile = MappingProfile.from_json(p)
    assert profile.name == "p1"
    assert profile.get_category_for_layer("WAND_1") == ElementCategory.WALL
