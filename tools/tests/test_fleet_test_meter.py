"""Tests für tools/fleet_test_meter.py (platform#2428 Kriterium 1)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fleet_test_meter as meter  # noqa: E402


def _repo(
    root: Path,
    name: str,
    *,
    tests: int = 0,
    src: int = 0,
    workflow: str | None = None,
    pyproject: str = "",
    makefile: str = "",
    worktree: bool = False,
    test_body: str = "",
) -> Path:
    repo = root / name
    repo.mkdir()
    if worktree:
        (repo / ".git").write_text("gitdir: /elsewhere\n")
    else:
        (repo / ".git").mkdir()
    (repo / "tests").mkdir()
    for i in range(tests):
        (repo / "tests" / f"test_{i}.py").write_text(
            test_body or "def test_should_pass():\n    pass\n"
        )
    (repo / "app").mkdir()
    for i in range(src):
        (repo / "app" / f"mod{i}.py").write_text("x = 1\n")
    if workflow is not None:
        (repo / ".github" / "workflows").mkdir(parents=True)
        (repo / ".github" / "workflows" / "ci.yml").write_text(workflow)
    if pyproject:
        (repo / "pyproject.toml").write_text(pyproject)
    if makefile:
        (repo / "Makefile").write_text(makefile)
    return repo


@pytest.fixture
def fleet(tmp_path: Path) -> Path:
    root = tmp_path / "github"
    root.mkdir()
    _repo(
        root,
        "alpha",
        tests=2,
        src=5,
        workflow="jobs:\n  ci:\n    uses: iilgmbh/shared-ci/.github/workflows/_ci-python.yml@v1.1.12\n"
        "    with:\n      coverage_threshold: 42\n",
        pyproject='[project]\ndependencies = ["iil-testkit[smoke]>=0.6.0,<1"]\n',
        makefile="test:\n\tpytest\n",
        test_body="import pytest\n@pytest.mark.integration\ndef test_should_x():\n    pass\n",
    )
    _repo(
        root,
        "beta",
        tests=1,
        src=3,
        workflow="jobs:\n  lint:\n    steps:\n      - run: ruff check .\n",
        pyproject='dependencies = ["iil-testkit>=0.5.3,<1"]\n',
    )
    _repo(
        root,
        "gamma",
        tests=1,
        src=1,
        workflow="jobs:\n  t:\n    steps:\n      - run: |\n          pip install pytest\n          pytest tests/ -q\n",
        test_body="import pytest\n@pytest.mark.f1\ndef test_should_y():\n    pass\n",
    )
    _repo(root, "delta", tests=0, src=2)
    _repo(root, "alpha-pinned", tests=2, src=5, worktree=True)
    return root


def test_should_skip_linked_worktrees(fleet: Path) -> None:
    repos, skipped = meter.find_repos(fleet)
    assert [r.name for r in repos] == ["alpha", "beta", "delta", "gamma"]
    assert skipped == ["alpha-pinned"]


def test_should_measure_alpha_row(fleet: Path) -> None:
    row = meter.scan_repo(fleet / "alpha", use_git=False)
    assert (row.test_files, row.src_py, row.make_test) == (2, 5, True)
    assert row.testkit_pin == ">=0.6.0,<1"
    assert row.coverage == "42"
    assert row.ci_test == "shared:_ci-python@v1.1.12"
    assert (row.markers, row.contract_tests) == ("kanonisch", 0)


def test_should_detect_own_pytest_in_multiline_run_and_reqid_markers(
    fleet: Path,
) -> None:
    row = meter.scan_repo(fleet / "gamma", use_git=False)
    assert row.ci_test == "own-pytest"
    assert row.markers == "reqid"


def test_should_flag_tests_without_reader_and_old_pin(fleet: Path) -> None:
    rows = [meter.scan_repo(r, use_git=False) for r in meter.find_repos(fleet)[0]]
    meter.apply_findings(rows, {}, "0.6.0")
    by_name = {r.repo: r.findings for r in rows}
    assert by_name["alpha"] == []
    assert by_name["beta"] == ["B1 Test ohne Leser", "B2 Pin < 0.6.0"]
    assert by_name["delta"] == []


def test_should_accept_documented_exception_for_b1(fleet: Path) -> None:
    rows = [meter.scan_repo(r, use_git=False) for r in meter.find_repos(fleet)[0]]
    meter.apply_findings(
        rows, {"beta": {"reason": "Doku-Repo", "issue": "org/beta#1"}}, "0.6.0"
    )
    beta = next(r for r in rows if r.repo == "beta")
    assert beta.findings == ["B2 Pin < 0.6.0"]
    assert beta.exception == "Doku-Repo (org/beta#1)"


def test_should_be_reproducible_and_exit_one_on_violations(
    fleet: Path, tmp_path: Path
) -> None:
    out1, out2 = tmp_path / "m1.json", tmp_path / "m2.json"
    exc = tmp_path / "exc.json"
    exc.write_text(json.dumps({"repos": {}}))
    code1 = meter.main(
        [
            "--root",
            str(fleet),
            "--no-git",
            "--json",
            str(out1),
            "--exceptions",
            str(exc),
        ]
    )
    code2 = meter.main(
        [
            "--root",
            str(fleet),
            "--no-git",
            "--json",
            str(out2),
            "--exceptions",
            str(exc),
        ]
    )
    assert (code1, code2) == (1, 1)
    assert out1.read_text() == out2.read_text()
    assert "## Verletzungen" in meter.render_report(
        [meter.RepoRow(repo="x")], [], root=fleet, min_testkit="0.6.0"
    )


def test_should_return_two_on_missing_root(tmp_path: Path) -> None:
    assert meter.main(["--root", str(tmp_path / "nope"), "--no-git"]) == 2
