import json

from cad_services.repositories import FileProfileRepository


def test_file_profile_repository_get_by_name(tmp_path):
    (tmp_path / "p1.json").write_text(
        json.dumps(
            {
                "name": "p1",
                "version": "1.0",
                "layer_mappings": [
                    {"pattern": "WAND.*", "category": "wall", "properties": {}},
                ],
            }
        ),
        encoding="utf-8",
    )

    repo = FileProfileRepository(tmp_path)
    profile = repo.get_by_name("p1")

    assert profile.name == "p1"
