"""Tests für optimize_debt_radar.py (KONZ-platform-019).

Reiner Kern (`scan_repo`, `compute_deltas`, `discover_repos`) an synthetischen
tmp_path-Repos geprüft — kein echter Fleet-Klon, kein Netzwerk (Analogie
tools/tests/test_registry_coverage_drift.py::_canon-Pattern).

Run: `python3 -m pytest tools/tests/test_optimize_debt_radar.py -q`
"""
import importlib.util
import pathlib

import yaml

_SRC = pathlib.Path(__file__).resolve().parents[1] / "optimize_debt_radar.py"
_spec = importlib.util.spec_from_file_location("odr", _SRC)
odr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(odr)


def _write(path: pathlib.Path, content: str = ""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_should_report_zero_debt_for_clean_repo(tmp_path):
    repo = tmp_path / "clean-repo"
    for f in odr.REQUIRED_FILES:
        _write(repo / f)
    _write(repo / "app.py", "def handler():\n    return 1\n")
    _write(repo / "tests" / "test_app.py", "def test_should_work():\n    assert True\n")

    result = odr.scan_repo(repo)

    assert result["debt_total"] == 0
    assert result["missing_files"] == []
    assert result["is_django"] is False


def test_should_count_missing_required_files(tmp_path):
    repo = tmp_path / "sparse-repo"
    _write(repo / "README.md")  # nur 1 von 5 Pflichtdateien vorhanden

    result = odr.scan_repo(repo)

    assert result["signals"]["missing_required_files"] == len(odr.REQUIRED_FILES) - 1


def test_should_count_uuid_pk_os_environ_print_and_llm_imports_by_file_not_by_line(tmp_path):
    repo = tmp_path / "smelly-repo"
    _write(repo / "models.py", "class X:\n    id = UUIDField(primary_key=True)\n")
    _write(
        repo / "views.py",
        "import os\nprint('a')\nprint('b')\nprint('c')\nos.environ.get('X')\n",
    )
    _write(repo / "client.py", "import anthropic\nimport openai\n")

    result = odr.scan_repo(repo)

    assert result["signals"]["uuid_pk"] == 1
    assert result["signals"]["os_environ"] == 1
    # 3 print()-Aufrufe in EINER Datei -> Datei-Einheit zaehlt 1, nicht 3
    # (bewusste Normalisierung ggue. platform-audit's Zeilen-Grep, s. Modul-Docstring)
    assert result["signals"]["print_calls"] == 1
    # 2 verschiedene LLM-Imports in EINER Datei -> ebenfalls 1 Datei
    assert result["signals"]["direct_llm_imports"] == 1


def test_should_exclude_venv_node_modules_and_test_files_from_pattern_signals(tmp_path):
    repo = tmp_path / "excluded-paths-repo"
    _write(repo / ".venv" / "lib" / "site.py", "os.environ.get('X')\n")
    _write(repo / "node_modules" / "pkg" / "gen.py", "os.environ.get('X')\n")
    _write(repo / "tests" / "test_something.py", "os.environ.get('X')\n")

    result = odr.scan_repo(repo)

    assert result["signals"]["os_environ"] == 0


def test_should_flag_default_auto_field_missing_only_for_django_repos(tmp_path):
    non_django = tmp_path / "plain-repo"
    _write(non_django / "app.py", "x = 1\n")
    result_plain = odr.scan_repo(non_django)
    assert result_plain["signals"]["default_auto_field_missing"] == 0  # kein Django -> kein Signal

    django_missing = tmp_path / "django-repo-missing"
    _write(django_missing / "manage.py")
    _write(django_missing / "config" / "settings.py", "INSTALLED_APPS = []\n")
    result_missing = odr.scan_repo(django_missing)
    assert result_missing["signals"]["default_auto_field_missing"] == 1

    django_ok = tmp_path / "django-repo-ok"
    _write(django_ok / "manage.py")
    _write(django_ok / "config" / "settings.py", "DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'\n")
    result_ok = odr.scan_repo(django_ok)
    assert result_ok["signals"]["default_auto_field_missing"] == 0


def test_should_flag_zero_tests_when_no_test_files_present(tmp_path):
    repo = tmp_path / "no-tests-repo"
    _write(repo / "app.py", "x = 1\n")

    result = odr.scan_repo(repo)

    assert result["signals"]["zero_tests"] == 1
    assert result["test_file_count"] == 0


def test_should_compute_delta_against_prior_baseline(tmp_path):
    current = {"repo-a": 5, "repo-b": 2, "repo-c": 3}
    baseline = {"repo-a": 3, "repo-b": 2}  # repo-c neu, kein Baseline-Eintrag

    deltas = odr.compute_deltas(current, baseline)

    assert deltas["repo-a"] == 2
    assert deltas["repo-b"] == 0
    assert deltas["repo-c"] == 3  # neues Repo zaehlt komplett als Delta


def test_should_exclude_archived_repos_from_discovery(tmp_path):
    github_dir = tmp_path / "github"
    canonical = tmp_path / "canonical.yaml"

    for name in ("active-repo", "archived-repo", "no-clone-repo"):
        if name != "no-clone-repo":
            _write(github_dir / name / ".git" / "HEAD")

    canonical.write_text(yaml.safe_dump({
        "repos": {
            "active-repo": {"rich": {"lifecycle": "active"}},
            "archived-repo": {"rich": {"lifecycle": "archived"}},
            "no-clone-repo": {"rich": {"lifecycle": "active"}},
        }
    }))

    repos, skipped_no_clone, skipped_archived = odr.discover_repos(github_dir, canonical)

    assert list(repos) == ["active-repo"]
    assert skipped_no_clone == ["no-clone-repo"]
    assert skipped_archived == ["archived-repo"]


def test_should_render_top_n_flagged_repos_sorted_by_delta_descending():
    current_totals = {"repo-a": 5, "repo-b": 8, "repo-c": 1}
    deltas = {"repo-a": 2, "repo-b": 6, "repo-c": -1}  # repo-c verbessert sich -> nicht geflaggt

    text = odr.render_text(current_totals, deltas, [], [], top_n=5)

    assert "repo-b" in text
    assert text.index("repo-b") < text.index("repo-a")  # groesseres Delta zuerst
    assert "repo-c" not in text.split("TOP-5")[1]  # negatives Delta nicht geflaggt


def test_should_surface_missing_local_clones_as_attestation_not_silent_gap():
    text = odr.render_text({"repo-a": 0}, {"repo-a": 0}, ["repo-missing"], [], top_n=5)

    assert "ATTESTATION" in text
    assert "repo-missing" in text
