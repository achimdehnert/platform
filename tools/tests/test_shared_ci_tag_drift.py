"""Tests für die shared-ci-Tag-Drift-Regeln in scripts/drift_check.py.

🌀 Drift-Klasse „Tag ≠ main" (3 Vorfälle, zuletzt 2026-06-12 ADR-242 Phase 3):
shared-ci-Tags wurden vor Fixes in der kanonischen platform-Quelle geschnitten
bzw. Consumer pinnen veraltete Tags. Zwei Regeln:
  shared-ci-tag-outdated (warn)  — Consumer pinnt nicht-neuesten Tag
  shared-ci-tag-stale    (error) — neuester Tag ≠ platform-main-Kanon

Rein (kein Token nötig): GitHub-Zugriffe werden gemockt bzw. der State
explizit injiziert.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "drift_check.py"
_spec = importlib.util.spec_from_file_location("drift_check", _SCRIPT)
dc = importlib.util.module_from_spec(_spec)
sys.modules["drift_check"] = dc
_spec.loader.exec_module(dc)


CI_YML = "jobs:\n  ci:\n    uses: iilgmbh/shared-ci/.github/workflows/_ci-python.yml@{ref}\n"


def _mock_repo_files(monkeypatch, content):
    monkeypatch.setattr(dc, "_get_dir_files", lambda repo, path, token: ["ci.yml"])
    monkeypatch.setattr(dc, "_get_file_content", lambda repo, path, token: content)


def test_should_parse_pins_with_file_and_ref():
    pins = dc.parse_shared_ci_pins(CI_YML.format(ref="v1.0.4"))
    assert pins == [("_ci-python.yml", "v1.0.4")]


def test_should_pick_latest_tag_by_semver_not_list_order():
    assert dc.latest_shared_ci_tag(["v1.0.4", "v1.0.10", "v1.0.2"]) == "v1.0.10"
    assert dc.latest_shared_ci_tag(["egal", "kein-semver"]) is None


def test_should_warn_on_outdated_pin(monkeypatch):
    _mock_repo_files(monkeypatch, CI_YML.format(ref="v1.0.2"))
    state = {"latest_tag": "v1.0.5", "stale_files": []}
    drifts = dc.check_shared_ci_tag_drift("demo-hub", "", state=state)
    assert [d.rule for d in drifts] == ["shared-ci-tag-outdated"]
    assert drifts[0].severity == "warn"
    assert "v1.0.5" in drifts[0].message
    assert "v1.0.2" in drifts[0].fix_hint


def test_should_pass_when_pin_is_latest_and_tag_matches_canon(monkeypatch):
    _mock_repo_files(monkeypatch, CI_YML.format(ref="v1.0.5"))
    state = {"latest_tag": "v1.0.5", "stale_files": []}
    assert dc.check_shared_ci_tag_drift("demo-hub", "", state=state) == []


def test_should_error_when_latest_tag_is_stale_vs_canon(monkeypatch):
    _mock_repo_files(monkeypatch, CI_YML.format(ref="v1.0.5"))
    state = {"latest_tag": "v1.0.5", "stale_files": ["_ci-python.yml"]}
    drifts = dc.check_shared_ci_tag_drift("demo-hub", "", state=state)
    assert [d.rule for d in drifts] == ["shared-ci-tag-stale"]
    assert drifts[0].severity == "error"
    assert "Kanon" in drifts[0].message


def test_should_not_warn_on_branch_refs_only_semver_tags(monkeypatch):
    # @main-Pins sind kein Tag-Drift (eigene Konvention: Kanon direkt)
    _mock_repo_files(monkeypatch, CI_YML.format(ref="main"))
    state = {"latest_tag": "v1.0.5", "stale_files": []}
    assert dc.check_shared_ci_tag_drift("demo-hub", "", state=state) == []


def test_should_return_empty_for_repos_without_pins(monkeypatch):
    _mock_repo_files(monkeypatch, "jobs:\n  test:\n    runs-on: ubuntu-latest\n")
    called = {"n": 0}

    def boom(token):
        called["n"] += 1
        raise AssertionError("state darf ohne Pins nicht berechnet werden")

    monkeypatch.setattr(dc, "_shared_ci_state", boom)
    assert dc.check_shared_ci_tag_drift("demo-hub", "") == []
    assert called["n"] == 0


def test_should_not_flag_mirror_path_rewrite_as_stale(monkeypatch):
    """Der shared-ci-Mirror schreibt nur Repo-Pfade um — das ist kein Drift."""
    canonical = "uses: achimdehnert/platform/.github/actions/x@main\n"
    mirrored = "uses: iilgmbh/shared-ci/.github/actions/x@main\n"

    def fake_api_get(path, token):
        if path.endswith("/tags"):
            return [{"name": "v1.0.4"}]
        if "contents/.github/workflows?ref=" in path:
            return [{"name": "_ci-python.yml", "type": "file"}]
        return None

    def fake_content_at(owner_repo, path, ref, token):
        return canonical if owner_repo.endswith("/platform") else mirrored

    monkeypatch.setattr(dc, "_api_get", fake_api_get)
    monkeypatch.setattr(dc, "_get_content_at", fake_content_at)
    monkeypatch.setattr(dc, "_SHARED_CI_STATE", None)
    state = dc._shared_ci_state("")
    assert state == {"latest_tag": "v1.0.4", "stale_files": []}


def test_should_flag_genuine_content_difference_as_stale(monkeypatch):
    def fake_api_get(path, token):
        if path.endswith("/tags"):
            return [{"name": "v1.0.4"}]
        if "contents/.github/workflows?ref=" in path:
            return [{"name": "_ci-python.yml", "type": "file"}]
        return None

    def fake_content_at(owner_repo, path, ref, token):
        if owner_repo.endswith("/platform"):
            return "jobs:\n  gate:\n    runs-on: x\n"
        return "jobs: {}\n"

    monkeypatch.setattr(dc, "_api_get", fake_api_get)
    monkeypatch.setattr(dc, "_get_content_at", fake_content_at)
    monkeypatch.setattr(dc, "_SHARED_CI_STATE", None)
    assert dc._shared_ci_state("")["stale_files"] == ["_ci-python.yml"]
