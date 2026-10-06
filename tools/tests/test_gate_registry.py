"""Tests fuer tools/gate_registry.py (Gate-Registry aus Einzeldateien, #1944 K7)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gate_registry  # noqa: E402

SAMMEL = {
    "_doc": "Doku",
    "gates": [
        {"slug": "zwei", "mode": "advisory"},
        {"slug": "eins", "mode": "blocking"},
    ],
    "declined": [{"slug": "eins", "reason": "Verzicht"}],
    "widerrufen": [],
    "kandidaten": [{"slug": "drei"}],
}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    return repo


def test_should_round_trip_split_registry_without_losing_entries(tmp_path):
    ziel = tmp_path / "gates"
    assert gate_registry.aufteilen(SAMMEL, str(ziel)) == 4
    geladen = gate_registry.laden(str(ziel))
    assert geladen["_doc"] == "Doku"
    assert [g["slug"] for g in geladen["gates"]] == ["eins", "zwei"]
    assert geladen["declined"] == SAMMEL["declined"]
    assert geladen["widerrufen"] == []
    assert (ziel / "declined" / "eins.json").is_file()


def test_should_keep_same_slug_apart_across_sections(tmp_path):
    ziel = tmp_path / "gates"
    gate_registry.aufteilen(SAMMEL, str(ziel))
    geladen = gate_registry.laden(str(ziel))
    assert {"eins"} <= {g["slug"] for g in geladen["gates"]}
    assert {"eins"} == {d["slug"] for d in geladen["declined"]}


def test_should_reject_duplicate_slug_within_a_section(tmp_path):
    kaputt = {**SAMMEL, "gates": [{"slug": "a"}, {"slug": "a"}]}
    with pytest.raises(ValueError, match="doppelt"):
        gate_registry.aufteilen(kaputt, str(tmp_path / "gates"))


def test_should_reject_slug_that_is_no_safe_file_name():
    with pytest.raises(ValueError):
        gate_registry.eintrag_pfad("gates", "../weg")


def test_should_read_single_json_file_unchanged(tmp_path):
    datei = tmp_path / "fixture.json"
    datei.write_text(json.dumps(SAMMEL))
    assert gate_registry.laden(str(datei)) == SAMMEL


def test_should_redirect_legacy_file_path_to_directory(tmp_path):
    ziel = tmp_path / "governance" / "gates"
    gate_registry.aufteilen(SAMMEL, str(ziel))
    alt = tmp_path / "governance" / "gate-registry.json"
    assert not alt.exists()
    assert len(gate_registry.laden(str(alt))["gates"]) == 2


def test_should_raise_instead_of_returning_empty_registry(tmp_path):
    with pytest.raises(FileNotFoundError):
        gate_registry.laden(str(tmp_path / "gibtsnicht"))


def test_should_read_split_registry_from_git_ref(tmp_path):
    repo = _repo(tmp_path)
    gate_registry.aufteilen(SAMMEL, str(repo / "docs" / "governance" / "gates"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "geteilt")
    # Arbeitsbaum weicht ab — gelesen wird der Ref.
    (repo / "docs" / "governance" / "gates" / "gates" / "eins.json").unlink()
    geladen = gate_registry.laden(ref="main", repo=str(repo))
    assert [g["slug"] for g in geladen["gates"]] == ["eins", "zwei"]
    assert geladen["_doc"] == "Doku"


def test_should_fall_back_to_legacy_file_on_base_before_the_split(tmp_path):
    repo = _repo(tmp_path)
    alt = repo / "docs" / "governance" / "gate-registry.json"
    alt.parent.mkdir(parents=True)
    alt.write_text(json.dumps(SAMMEL))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "alt")
    assert gate_registry.laden(ref="main", repo=str(repo)) == SAMMEL


def test_should_raise_when_ref_has_no_registry(tmp_path):
    repo = _repo(tmp_path)
    (repo / "x").write_text("x")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "leer")
    with pytest.raises(RuntimeError):
        gate_registry.laden(ref="main", repo=str(repo))


def test_should_match_real_registry_sections():
    geladen = gate_registry.laden()
    for abschnitt in gate_registry.ABSCHNITTE:
        slugs = [e["slug"] for e in geladen[abschnitt]]
        assert slugs == sorted(slugs)
        assert len(slugs) == len(set(slugs)), abschnitt
    assert geladen["gates"], "echte Registry ohne Gates waere ein blinder Melder"
