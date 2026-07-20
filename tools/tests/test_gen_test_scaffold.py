"""Tests für scripts/gen_test_scaffold.py (Issue #997, T-16).

Snapshot-Test der reinen Generierungslogik (`generate_scaffold()`) gegen
erwartete Datei-Inhalts-Strings — NICHT der Cross-Repo-PR-Teil (scaffold-tests.yml)
und NICHT der PyPI-Lookup (`get_latest_version`); beide bleiben ungetestet, weil
sie echte Netz-/gh-Calls bräuchten. `generate_scaffold()` nimmt die testkit-Version
als Parameter entgegen, macht selbst keinen Netzwerkzugriff.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "gen_test_scaffold.py"
_spec = importlib.util.spec_from_file_location("gen_test_scaffold", _SCRIPT)
gts = importlib.util.module_from_spec(_spec)
sys.modules["gen_test_scaffold"] = gts
_spec.loader.exec_module(gts)


def test_should_create_all_scaffold_files_on_fresh_repo(tmp_path):
    repo_dir = tmp_path / "myrepo"
    repo_dir.mkdir()

    results = gts.generate_scaffold(repo_dir, testkit_version="1.2.3")

    expected_files = {
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/factories.py",
        "tests/test_views_smoke.py",
        "tests/test_views_htmx.py",
        "requirements-test.txt",
        "renovate.json",
    }
    assert expected_files <= set(results.keys())
    assert all(results[f] == "CREATED" for f in expected_files)
    # kein pyproject.toml im Repo -> kein pyproject-Eintrag im Ergebnis
    assert "pyproject.toml" not in results

    assert (repo_dir / "tests" / "__init__.py").read_text(encoding="utf-8") == ""

    conftest = (repo_dir / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert 'pytest_plugins = ["iil_testkit.fixtures"]' in conftest

    factories = (repo_dir / "tests" / "factories.py").read_text(encoding="utf-8")
    assert "class UserFactory(DjangoModelFactory):" in factories
    assert "myrepo" in factories

    smoke = (repo_dir / "tests" / "test_views_smoke.py").read_text(encoding="utf-8")
    assert "discover_smoke_urls" in smoke
    assert "def test_should_view_return_200(" in smoke
    assert "def test_should_unauthenticated_redirect_to_login(" in smoke

    htmx = (repo_dir / "tests" / "test_views_htmx.py").read_text(encoding="utf-8")
    assert "HTMX_URLS: list[str] = [\n\n]" in htmx or "HTMX_URLS: list[str] = [\n]" in htmx
    assert "Keine hx-* Attribute in Templates gefunden" in htmx

    req = (repo_dir / "requirements-test.txt").read_text(encoding="utf-8")
    assert "iil-testkit[smoke]>=1.2.3,<2" in req

    renovate = (repo_dir / "renovate.json").read_text(encoding="utf-8")
    assert "achimdehnert/platform" in renovate


def test_should_skip_existing_files_without_update_flag(tmp_path):
    repo_dir = tmp_path / "myrepo"
    (repo_dir / "tests").mkdir(parents=True)
    custom = "# custom conftest, hand-edited\n"
    (repo_dir / "tests" / "conftest.py").write_text(custom, encoding="utf-8")

    results = gts.generate_scaffold(repo_dir, testkit_version="1.2.3")

    assert results["tests/conftest.py"] == "SKIP (exists)"
    assert (repo_dir / "tests" / "conftest.py").read_text(encoding="utf-8") == custom


def test_should_overwrite_existing_files_when_update_flag_set(tmp_path):
    repo_dir = tmp_path / "myrepo"
    (repo_dir / "tests").mkdir(parents=True)
    (repo_dir / "tests" / "conftest.py").write_text("# stale\n", encoding="utf-8")

    results = gts.generate_scaffold(repo_dir, testkit_version="1.2.3", update=True)

    assert results["tests/conftest.py"] == "UPDATED"
    updated = (repo_dir / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert 'pytest_plugins = ["iil_testkit.fixtures"]' in updated


def test_should_discover_htmx_urls_from_templates(tmp_path):
    repo_dir = tmp_path / "myrepo"
    templates_dir = repo_dir / "app" / "templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "widget.html").write_text(
        '<button hx-post="/widget/save/">Save</button>\n'
        '<div hx-get="/widget/{{ pk }}/">skip-me-has-braces</div>\n',
        encoding="utf-8",
    )

    results = gts.generate_scaffold(repo_dir, testkit_version="1.2.3")

    assert results["tests/test_views_htmx.py"] == "CREATED"
    htmx = (repo_dir / "tests" / "test_views_htmx.py").read_text(encoding="utf-8")
    assert '"/widget/save/",' in htmx
    assert "Auto-entdeckt aus Templates (1 URLs):" in htmx
    # URL mit Platzhalter ({{ pk }}) wird NICHT aufgenommen
    assert "/widget/{{ pk }}/" not in htmx


def test_should_add_pytest_ini_options_when_pyproject_has_none(tmp_path):
    repo_dir = tmp_path / "myrepo"
    repo_dir.mkdir()
    (repo_dir / "pyproject.toml").write_text(
        '[project]\nname = "myrepo"\n', encoding="utf-8"
    )

    results = gts.generate_scaffold(repo_dir, testkit_version="1.2.3")

    assert results["pyproject.toml"] == "UPDATED (pytest section added)"
    content = (repo_dir / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.pytest.ini_options]" in content
    assert 'DJANGO_SETTINGS_MODULE = "config.settings.test"' in content


def test_should_skip_pytest_ini_options_when_already_present(tmp_path):
    repo_dir = tmp_path / "myrepo"
    repo_dir.mkdir()
    original = (
        '[project]\nname = "myrepo"\n\n'
        '[tool.pytest.ini_options]\nDJANGO_SETTINGS_MODULE = "config.settings.test"\n'
    )
    (repo_dir / "pyproject.toml").write_text(original, encoding="utf-8")

    results = gts.generate_scaffold(repo_dir, testkit_version="1.2.3")

    assert results["pyproject.toml"] == "SKIP (pytest section exists)"
    assert (repo_dir / "pyproject.toml").read_text(encoding="utf-8") == original


def test_should_not_write_anything_in_dry_run_mode(tmp_path):
    repo_dir = tmp_path / "myrepo"
    repo_dir.mkdir()

    results = gts.generate_scaffold(repo_dir, testkit_version="1.2.3", dry_run=True)

    assert all(status == "DRY-RUN" for status in results.values())
    assert not (repo_dir / "tests").exists()


def test_should_detect_settings_module_from_pyproject_ini_options(tmp_path):
    repo_dir = tmp_path / "myrepo"
    repo_dir.mkdir()
    (repo_dir / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\n'
        'DJANGO_SETTINGS_MODULE = "config.settings.prod_like"\n',
        encoding="utf-8",
    )

    assert gts.detect_settings(repo_dir) == "config.settings.prod_like"


def test_should_fall_back_to_default_settings_module_when_undetectable(tmp_path):
    repo_dir = tmp_path / "myrepo"
    repo_dir.mkdir()

    assert gts.detect_settings(repo_dir) == "config.settings.test"
