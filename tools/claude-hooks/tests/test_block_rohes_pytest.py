"""Drill für das Gate `rohes-pytest-statt-make-test`.

Realfall: Retro `increment-retro-767d40-incr` (platform#3859) Befund #18 — in
einer Sitzung liefen 49 rohe pytest-Aufrufe in Repo-Worktrees, obwohl die
Hausregel „Tests: `make test`, nie rohes `pytest`" lautet.

Positivkontrolle ist Teil des Drills: je Durchlass-Kriterium steht unten ein
Test, der zeigt, dass der Befehl NICHT gesperrt wird. Ein Gate, das nur seine
Treffer zeigt, belegt nicht, dass es zielt.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import block_rohes_pytest  # noqa: E402
from block_rohes_pytest import SLUG, entscheide  # noqa: E402

MAKEFILE_OHNE_ARGS = ".PHONY: test\ntest: ## Tests\n\t@python3 -m pytest tests/ -q\n"
MAKEFILE_MIT_ARGS = "test:\n\t@python3 -m pytest $(ARGS)\n"
MAKEFILE_OHNE_TEST = "build:\n\t@echo build\n"


def _repo(basis: Path, name: str, makefile: str | None) -> Path:
    repo = basis / name
    (repo / ".git").mkdir(parents=True)
    (repo / "tests").mkdir()
    if makefile is not None:
        (repo / "Makefile").write_text(makefile, encoding="utf-8")
    return repo


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _repo(tmp_path, "mit-test", MAKEFILE_OHNE_ARGS)


@pytest.fixture
def repo_args(tmp_path: Path) -> Path:
    return _repo(tmp_path, "mit-args", MAKEFILE_MIT_ARGS)


@pytest.fixture
def repo_ohne_test(tmp_path: Path) -> Path:
    return _repo(tmp_path, "ohne-test", MAKEFILE_OHNE_TEST)


def test_should_have_the_registered_slug():
    assert SLUG == "rohes-pytest-statt-make-test"


# ── Realfall + Familie ───────────────────────────────────────────────────────


def test_should_deny_realfall_cd_worktree_venv_python_pytest(repo: Path):
    grund = entscheide(f"cd {repo} && .venv/bin/python -m pytest tests/test_x.py -q", "/")
    assert grund is not None
    assert "make test" in grund


@pytest.mark.parametrize(
    "befehl",
    [
        "pytest tests/ -q",
        "python -m pytest tests/",
        "python3 -m pytest tests/",
        ".venv/bin/pytest tests/",
        ".venv/bin/python -m pytest tests/",
        "uv run pytest tests/",
        "DJANGO_SETTINGS_MODULE=x.test pytest tests/",
        "pytest tests/ 2>&1 | tail -5",
        "echo start; pytest tests/",
    ],
)
def test_should_deny_each_pytest_form_via_cwd(repo: Path, befehl: str):
    assert entscheide(befehl, str(repo)) is not None


def test_should_deny_in_a_worktree_with_git_file(tmp_path: Path):
    """Worktrees tragen `.git` als Datei, nicht als Ordner."""
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / ".git").write_text("gitdir: /irgendwo\n", encoding="utf-8")
    (wt / "Makefile").write_text(MAKEFILE_OHNE_ARGS, encoding="utf-8")
    assert entscheide("pytest -q", str(wt)) is not None


def test_should_deny_from_subdirectory_of_repo(repo: Path):
    assert entscheide("pytest -q", str(repo / "tests")) is not None


def test_should_use_target_of_last_cd_over_cwd(repo: Path, repo_ohne_test: Path):
    assert entscheide(f"cd {repo_ohne_test} && cd {repo} && pytest", str(repo_ohne_test)) is not None


def test_should_name_args_replacement_when_makefile_uses_args(repo_args: Path):
    grund = entscheide("pytest tests/test_x.py", str(repo_args))
    assert grund is not None
    assert 'make test ARGS="' in grund


def test_should_name_plain_make_test_when_makefile_has_no_args(repo: Path):
    grund = entscheide("pytest tests/test_x.py", str(repo))
    assert grund is not None
    assert "ARGS" not in grund
    assert "`make test`" in grund


# ── Negativproben: je Durchlass-Kriterium ────────────────────────────────────


def test_should_allow_make_test(repo: Path):
    assert entscheide("make test", str(repo)) is None
    assert entscheide('make test ARGS="tests/test_x.py"', str(repo)) is None


def test_should_allow_grep_for_pytest(repo: Path):
    assert entscheide("grep -rn pytest Makefile", str(repo)) is None


def test_should_allow_echo_pytest(repo: Path):
    assert entscheide("echo pytest", str(repo)) is None
    assert entscheide('echo "fertig && pytest"', str(repo)) is None


@pytest.mark.parametrize(
    "befehl",
    [
        "docker exec web pytest tests/",
        "docker compose exec web pytest tests/",
        "docker compose run --rm web python -m pytest tests/",
    ],
)
def test_should_allow_pytest_inside_container(repo: Path, befehl: str):
    assert entscheide(befehl, str(repo)) is None


def test_should_allow_repo_without_test_target(repo_ohne_test: Path):
    assert entscheide("pytest tests/ -q", str(repo_ohne_test)) is None
    assert entscheide(f"cd {repo_ohne_test} && .venv/bin/python -m pytest", "/") is None


def test_should_allow_repo_without_makefile(tmp_path: Path):
    kein_makefile = _repo(tmp_path, "kein-makefile", None)
    assert entscheide("pytest -q", str(kein_makefile)) is None


def test_should_allow_test_variable_target_that_is_not_a_target(tmp_path: Path):
    """`test := …` ist eine Variable, kein Ziel."""
    r = _repo(tmp_path, "variable", "test := 1\nbuild:\n\t@true\n")
    assert entscheide("pytest", str(r)) is None


def test_should_allow_outside_any_git_repo(tmp_path: Path):
    lose = tmp_path / "lose"
    lose.mkdir()
    (lose / "Makefile").write_text(MAKEFILE_OHNE_ARGS, encoding="utf-8")
    assert entscheide("pytest", str(lose)) is None


@pytest.mark.parametrize("befehl", ["pytest --version", "pytest --help", "python -m pytest -h"])
def test_should_allow_pytest_version_and_help(repo: Path, befehl: str):
    assert entscheide(befehl, str(repo)) is None


def test_should_fail_open_on_variable_in_cd_path(repo: Path):
    assert entscheide('cd "$WT" && pytest -q', str(repo)) is None
    assert entscheide("cd $(pwd)/x && pytest -q", str(repo)) is None


def test_should_fail_open_on_parse_error(repo: Path):
    assert entscheide("echo 'offen && pytest", str(repo)) is None


def test_should_fail_open_without_cwd_and_without_cd():
    assert entscheide("pytest -q", None) is None


def test_should_allow_pytest_before_cd_into_repo_without_test(repo: Path, repo_ohne_test: Path):
    """Wirksam ist das Verzeichnis zum Zeitpunkt des Aufrufs, nicht das spätere."""
    assert entscheide(f"pytest -q; cd {repo}", str(repo_ohne_test)) is None


# ── Hook-Schnittstelle ───────────────────────────────────────────────────────


def _hook(payload: dict | str) -> subprocess.CompletedProcess:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, block_rohes_pytest.__file__],
        input=text,
        capture_output=True,
        text=True,
        check=False,
    )


def test_should_exit_2_with_reason_on_stderr(repo: Path):
    res = _hook({"tool_input": {"command": "pytest -q"}, "cwd": str(repo)})
    assert res.returncode == 2
    assert "make test" in res.stderr


def test_should_exit_0_on_make_test(repo: Path):
    assert _hook({"tool_input": {"command": "make test"}, "cwd": str(repo)}).returncode == 0


def test_should_exit_0_on_invalid_json():
    assert _hook("kein json").returncode == 0
