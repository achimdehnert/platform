"""Tests fuer tools/repo_readiness.py (backt /repo-ready, ADR-211/216/225).

Issue #1199 TEST-6 (M): 0 Tests. Muster analog tools/tests/test_repo_checker.py
(importlib-Load, tmp_path-Fixtures) -- hier zusaetzlich mit `sh()` gemockt,
weil repo_readiness.py durchgehend ueber subprocess.run auf git/pip/ruff/
teste_repo.py delegiert; kein echter Subprozess/Netzwerk-Call in den Tests.

Kernpfad: read_repo_type() (project-facts.md-Feld vs. Heuristik),
pyproject_name_version(), check_git() (clean/dirty/behind), und
check_install_consistency() (installiert vs. Source-Version, editable-Stale-
Target) -- das laut Docstring zentrale Novum dieses Tools.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

_SPEC = importlib.util.spec_from_file_location(
    "repo_readiness",
    pathlib.Path(__file__).resolve().parents[1] / "repo_readiness.py",
)
rr = importlib.util.module_from_spec(_SPEC)
sys.modules["repo_readiness"] = rr
_SPEC.loader.exec_module(rr)


# ---------------------------------------------------------------------------
# read_repo_type
# ---------------------------------------------------------------------------


def test_should_read_type_from_project_facts_field(tmp_path):
    wf = tmp_path / ".windsurf" / "rules"
    wf.mkdir(parents=True)
    (wf / "project-facts.md").write_text(
        "**Type**: `python-package`\n", encoding="utf-8"
    )

    assert rr.read_repo_type(tmp_path) == "python-package"


def test_should_fall_back_to_django_heuristic_when_no_project_facts(tmp_path):
    (tmp_path / "manage.py").write_text("", encoding="utf-8")

    assert rr.read_repo_type(tmp_path) == "django"


def test_should_fall_back_to_python_package_heuristic(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    assert rr.read_repo_type(tmp_path) == "python-package"


def test_should_return_unknown_when_no_signal_present(tmp_path):
    assert rr.read_repo_type(tmp_path) == "unknown"


def test_should_ignore_project_facts_type_unknown_and_use_heuristic(tmp_path):
    wf = tmp_path / ".windsurf" / "rules"
    wf.mkdir(parents=True)
    (wf / "project-facts.md").write_text("**Type**: `unknown`\n", encoding="utf-8")
    (tmp_path / "manage.py").write_text("", encoding="utf-8")

    assert rr.read_repo_type(tmp_path) == "django"


# ---------------------------------------------------------------------------
# pyproject_name_version
# ---------------------------------------------------------------------------


def test_should_extract_name_and_version_from_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "widget-fw"\nversion = "1.2.3"\n', encoding="utf-8"
    )

    assert rr.pyproject_name_version(tmp_path) == ("widget-fw", "1.2.3")


def test_should_return_none_none_when_pyproject_missing(tmp_path):
    assert rr.pyproject_name_version(tmp_path) == (None, None)


# ---------------------------------------------------------------------------
# check_git — Golden Path (clean, up to date) + Fehlerpfad (dirty tree)
# ---------------------------------------------------------------------------


def test_should_report_ok_for_clean_up_to_date_repo(tmp_path, monkeypatch):
    def fake_sh(cmd, cwd=None, timeout=120):
        joined = " ".join(cmd)
        if "fetch" in joined:
            return 0, ""
        if "rev-parse" in joined:
            return 0, "main\n"
        if "status" in joined:
            return 0, ""  # clean
        if "rev-list" in joined:
            return 0, "0\t0\n"
        return 0, ""

    monkeypatch.setattr(rr, "sh", fake_sh)
    findings: list[dict] = []
    rr.check_git(tmp_path, fix=True, findings=findings)

    assert len(findings) == 1
    assert findings[0]["status"] == "ok"
    assert "dirty=False" in findings[0]["detail"]


def test_should_warn_and_not_autofix_dirty_tree(tmp_path, monkeypatch):
    """Dirty Working-Tree darf NIE auto-gefixt werden (Datenverlust-Schutz)."""

    def fake_sh(cmd, cwd=None, timeout=120):
        joined = " ".join(cmd)
        if "fetch" in joined:
            return 0, ""
        if "rev-parse" in joined:
            return 0, "main\n"
        if "status" in joined:
            return 0, " M some_file.py\n"  # dirty
        if "rev-list" in joined:
            return 0, "0\t2\n"
        return 0, ""

    calls = []

    def tracking_sh(cmd, cwd=None, timeout=120):
        calls.append(cmd)
        return fake_sh(cmd, cwd, timeout)

    monkeypatch.setattr(rr, "sh", tracking_sh)
    findings: list[dict] = []
    rr.check_git(tmp_path, fix=True, findings=findings)

    assert findings[0]["status"] == "warn"
    assert "dirty" in findings[0]["action"].lower()
    assert not any("pull" in " ".join(c) for c in calls)


# ---------------------------------------------------------------------------
# check_install_consistency — Kern-Novum: installierte Version == Source?
# ---------------------------------------------------------------------------


def test_should_skip_install_check_when_no_pyproject(tmp_path):
    findings: list[dict] = []
    rr.check_install_consistency(tmp_path, fix=False, findings=findings)

    assert findings[0]["status"] == "skip"


def test_should_warn_when_package_not_installed_and_no_fix(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "totally-unshipped-pkg"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    findings: list[dict] = []
    rr.check_install_consistency(tmp_path, fix=False, findings=findings)

    assert findings[0]["status"] == "warn"
    assert "nicht installiert" in findings[0]["action"]
