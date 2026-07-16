"""Tests fuer tools/publish_gate_meter.py — reine Logik (Scan/Backlog/Registry), keine API."""

import importlib.util
import pathlib

_SPEC = importlib.util.spec_from_file_location(
    "publish_gate_meter",
    pathlib.Path(__file__).resolve().parents[1] / "publish_gate_meter.py",
)
m = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(m)


_GATED = """
jobs:
  test:
    steps:
      - run: pytest
  publish:
    needs: test
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
"""

_UNGATED_TWINE = """
jobs:
  publish:
    steps:
      - run: python -m build
      - run: twine upload dist/*
"""

_NON_UPLOAD = """
jobs:
  lint:
    steps:
      - run: ruff check .
"""


def test_should_return_no_offenders_for_gated_files():
    assert m.scan_files({"publish.yml": _GATED}) == []


def test_should_return_offender_for_ungated_twine():
    assert m.scan_files({"publish.yml": _UNGATED_TWINE}) == [{"file": "publish.yml", "job": "publish"}]


def test_should_ignore_non_upload_workflows():
    assert m.scan_files({"ci.yml": _NON_UPLOAD}) == []


def test_should_sort_files_deterministically():
    files = {"b-publish.yml": _UNGATED_TWINE, "a-publish.yml": _UNGATED_TWINE}
    result = m.scan_files(files)
    assert [o["file"] for o in result] == ["a-publish.yml", "b-publish.yml"]


def test_should_render_empty_backlog_when_no_offenders():
    body = m.build_backlog({"aifw": [], "promptfw": []}, {"aifw": "achimdehnert", "promptfw": "achimdehnert"})
    assert "Backlog leer" in body
    assert "|" not in body  # keine Tabelle


def test_should_render_table_for_offenders():
    body = m.build_backlog(
        {"iil-codeguard": [{"file": "publish.yml", "job": "publish"}], "clean": []},
        {"iil-codeguard": "achimdehnert", "clean": "achimdehnert"},
    )
    assert "1 ungegatete Upload-Job(s) in 1 Repo(s)" in body
    assert "| achimdehnert/iil-codeguard | `publish.yml` | `publish` |" in body
    assert "clean" not in body  # leere Repos erscheinen nicht


def test_should_render_table_with_per_repo_owner():
    """FUNC-3 (#1202): --all-types kann iilgmbh-Repos mitziehen — Owner-Spalte
    muss den tatsächlichen Repo-Owner zeigen, nicht den achimdehnert-Fallback."""
    body = m.build_backlog(
        {"risk-hub": [{"file": "publish.yml", "job": "publish"}]},
        {"risk-hub": "iilgmbh"},
    )
    assert "| iilgmbh/risk-hub | `publish.yml` | `publish` |" in body


def test_should_count_jobs_across_repos():
    body = m.build_backlog(
        {
            "r1": [{"file": "p.yml", "job": "a"}, {"file": "p.yml", "job": "b"}],
            "r2": [{"file": "q.yml", "job": "c"}],
        },
        {"r1": "achimdehnert", "r2": "achimdehnert"},
    )
    assert "3 ungegatete Upload-Job(s) in 2 Repo(s)" in body


def test_should_select_only_library_types_by_default():
    repos = {
        "aifw": {"type": "library"},
        "risk-hub": {"type": "django"},
        "iil-ingest": {"type": "library"},
    }
    assert m.registry_repos(repos, all_types=False) == ["aifw", "iil-ingest"]


def test_should_select_all_types_when_requested():
    repos = {"aifw": {"type": "library"}, "risk-hub": {"type": "django"}}
    assert m.registry_repos(repos, all_types=True) == ["aifw", "risk-hub"]


def test_should_read_local_workflows(tmp_path):
    wf = tmp_path / "myrepo" / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "publish.yml").write_text(_UNGATED_TWINE, encoding="utf-8")
    (wf / "notes.md").write_text("ignored", encoding="utf-8")
    files = m.fetch_repo_workflows_local(tmp_path, "myrepo")
    assert set(files) == {"publish.yml"}


def test_should_return_empty_for_repo_without_workflows(tmp_path):
    (tmp_path / "norepo").mkdir()
    assert m.fetch_repo_workflows_local(tmp_path, "norepo") == {}


def test_should_not_update_issue_when_title_and_body_unchanged():
    existing = {"title": "T", "body": "B"}
    assert m.issue_needs_update(existing, "T", "B") is False


def test_should_update_issue_when_body_changed():
    existing = {"title": "T", "body": "alt"}
    assert m.issue_needs_update(existing, "T", "neu") is True


def test_should_update_issue_when_title_changed():
    existing = {"title": "alt", "body": "B"}
    assert m.issue_needs_update(existing, "neu", "B") is True


def test_should_update_issue_when_existing_body_is_none():
    # GitHub liefert body=None für leere Issues → muss als Änderung gelten, wenn neuer Body da ist.
    assert m.issue_needs_update({"title": "T", "body": None}, "T", "B") is True
    assert m.issue_needs_update({"title": "T", "body": None}, "T", "") is False


def test_should_return_2_when_local_upsert_without_token(tmp_path, monkeypatch):
    # Regression F4 (Retro-Increment 2026-06-30): --local ohne --dry-run + ohne GH_TOKEN
    # traf `os.environ["GH_TOKEN"]` direkt → KeyError. Muss jetzt sauber mit rc=2 abbrechen.
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    rc = m.main(["--local", str(tmp_path)])
    assert rc == 2
