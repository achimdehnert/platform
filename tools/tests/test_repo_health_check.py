"""Tests für repo_health_check.py — gitignore-Cruft-SUGGEST-Checks (#517)."""
import importlib.util
import pathlib
import sys

_MOD = pathlib.Path(__file__).resolve().parents[1] / "repo_health_check.py"
_spec = importlib.util.spec_from_file_location("repo_health_check", _MOD)
rhc = importlib.util.module_from_spec(_spec)
sys.modules["repo_health_check"] = rhc  # required for @dataclass __module__ resolution
_spec.loader.exec_module(rhc)

CRUFT_ENTRIES = ("NEXT.md", ".windsurfignore", ".windsurf/")


def _make_package(tmp_path: pathlib.Path, gitignore_lines: list[str]) -> pathlib.Path:
    """Minimales Python-Package-Verzeichnis für check_python_package."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0.1.0"\n'
        '[project.urls]\nHomepage = "https://example.com"\n'
    )
    (tmp_path / "README.md").write_text("# x\n")
    (tmp_path / ".gitignore").write_text("\n".join(gitignore_lines) + "\n")
    src = tmp_path / "src" / "x"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_x.py").write_text("def test_should_pass(): pass\n")
    return tmp_path


def _make_django(tmp_path: pathlib.Path, gitignore_lines: list[str]) -> pathlib.Path:
    """Minimales Django-App-Verzeichnis für check_django_app."""
    for fname in ("manage.py", "Dockerfile", "docker-compose.prod.yml", "README.md"):
        (tmp_path / fname).write_text("")
    (tmp_path / ".gitignore").write_text("\n".join(gitignore_lines) + "\n")
    app = tmp_path / "app"
    app.mkdir()
    (app / "settings.py").write_text("")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text("def test_should_pass(): pass\n")
    return tmp_path


# ── check_python_package ────────────────────────────────────────────────────

def test_should_pass_gitignore_cruft_checks_python_package_when_entries_present(tmp_path):
    path = _make_package(tmp_path, list(CRUFT_ENTRIES))
    report = rhc.check_python_package(path)
    for entry in CRUFT_ENTRIES:
        result = next(r for r in report.results if r.name == f"gitignore:{entry}")
        assert result.passed, f"expected passed for {entry}"
        assert result.severity == "SUGGEST"


def test_should_fail_gitignore_cruft_checks_python_package_when_entries_missing(tmp_path):
    path = _make_package(tmp_path, [])
    report = rhc.check_python_package(path)
    for entry in CRUFT_ENTRIES:
        result = next(r for r in report.results if r.name == f"gitignore:{entry}")
        assert not result.passed, f"expected failed for {entry}"
        assert result.severity == "SUGGEST"


def test_should_not_block_python_package_when_gitignore_entries_missing(tmp_path):
    path = _make_package(tmp_path, [])
    report = rhc.check_python_package(path)
    # SUGGEST failures must not appear in blocks_failed
    block_names = {r.name for r in report.blocks_failed}
    for entry in CRUFT_ENTRIES:
        assert f"gitignore:{entry}" not in block_names


# ── check_django_app ────────────────────────────────────────────────────────

def test_should_pass_gitignore_cruft_checks_django_app_when_entries_present(tmp_path):
    path = _make_django(tmp_path, list(CRUFT_ENTRIES))
    report = rhc.check_django_app(path)
    for entry in CRUFT_ENTRIES:
        result = next(r for r in report.results if r.name == f"gitignore:{entry}")
        assert result.passed, f"expected passed for {entry}"
        assert result.severity == "SUGGEST"


def test_should_fail_gitignore_cruft_checks_django_app_when_entries_missing(tmp_path):
    path = _make_django(tmp_path, [])
    report = rhc.check_django_app(path)
    for entry in CRUFT_ENTRIES:
        result = next(r for r in report.results if r.name == f"gitignore:{entry}")
        assert not result.passed, f"expected failed for {entry}"
        assert result.severity == "SUGGEST"


def test_should_not_block_django_app_when_gitignore_entries_missing(tmp_path):
    path = _make_django(tmp_path, [])
    report = rhc.check_django_app(path)
    block_names = {r.name for r in report.blocks_failed}
    for entry in CRUFT_ENTRIES:
        assert f"gitignore:{entry}" not in block_names
