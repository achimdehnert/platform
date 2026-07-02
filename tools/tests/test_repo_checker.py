"""Tests fuer tools/repo_checker.py (ADR-022 Repository Consistency Checker).

Golden-Path-Test je check_*-Funktion: ein Fixture-Repo (tmp_path) ohne Verstoss
(nur OK-Results) + ein Fixture-Repo mit gezieltem Verstoss (ERROR/WARNING).

F-1 (repo-optimize 2026-07-02): das Modul laedt registry/repos.yaml beim Import
(_load_repo_config() fuellt das Modul-globale REPO_CONFIG). Die check_*-Funktionen
selbst sind aber rein (repo_path, config) -> list[CheckResult] und nehmen ihre
Config als Parameter entgegen -- wir reichen hier ausschliesslich selbstgebaute
config-dicts durch, sodass der Inhalt der echten registry/repos.yaml keine Tests
beeinflusst. Fuer die Orchestrierungs-Funktionen (check_repo/check_all_repos), die
REPO_CONFIG lesen, wird REPO_CONFIG explizit gemonkeypatched (Isolation von der
echten Registry-Datei).

Muster: tools/tests/test_check_publish_gate.py (importlib-Load, tmp_path-Fixtures).
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

_SPEC = importlib.util.spec_from_file_location(
    "repo_checker",
    pathlib.Path(__file__).resolve().parents[1] / "repo_checker.py",
)
rc = importlib.util.module_from_spec(_SPEC)
# repo_checker.py definiert @dataclass-Klassen; dataclasses._is_type() greift auf
# sys.modules[cls.__module__] zu, das VOR exec_module() registriert sein muss
# (sonst AttributeError: 'NoneType' object has no attribute '__dict__').
sys.modules["repo_checker"] = rc
_SPEC.loader.exec_module(rc)


def _severities(results, check_name):
    return [r.severity for r in results if r.check == check_name]


# ─────────────────────────────────────────────────────────────────────────────
# check_compose
# ─────────────────────────────────────────────────────────────────────────────

_COMPOSE_GOLDEN = """\
services:
  web:
    image: ghcr.io/x/y:${IMAGE_TAG:-latest}
    env_file:
      - .env.prod
    healthcheck:
      test: ["CMD", "python3", "-c", "urllib.request.urlopen('http://127.0.0.1:8000/livez/')"]
"""

_COMPOSE_VIOLATION = """\
services:
  web:
    image: ghcr.io/x/y:${OLD_TAG_IMAGE_TAG:-latest}
    environment:
      ${SOME_VAR}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/livez/"]
"""


def test_should_pass_compose_golden_path(tmp_path):
    (tmp_path / "docker-compose.prod.yml").write_text(_COMPOSE_GOLDEN, encoding="utf-8")
    results = rc.check_compose(tmp_path, {})
    by_check = {r.check: r.severity for r in results}
    assert by_check["file_exists"] == rc.Severity.OK
    assert by_check["image_tag"] == rc.Severity.OK
    assert by_check["hc_ip"] == rc.Severity.OK
    assert by_check["hc_livez"] == rc.Severity.OK
    assert by_check["env_file"] == rc.Severity.OK
    assert not any(r.severity == rc.Severity.ERROR for r in results)


def test_should_flag_compose_violations(tmp_path):
    (tmp_path / "docker-compose.prod.yml").write_text(_COMPOSE_VIOLATION, encoding="utf-8")
    results = rc.check_compose(tmp_path, {})
    by_check = {r.check: r.severity for r in results}
    assert by_check["image_tag"] == rc.Severity.ERROR
    assert by_check["hc_ip"] == rc.Severity.ERROR
    assert by_check["hc_urllib"] == rc.Severity.WARNING
    assert by_check["env_file"] == rc.Severity.WARNING


def test_should_flag_missing_compose_file(tmp_path):
    results = rc.check_compose(tmp_path, {})
    assert len(results) == 1
    assert results[0].check == "file_exists"
    assert results[0].severity == rc.Severity.ERROR


# ─────────────────────────────────────────────────────────────────────────────
# check_dockerfile
# ─────────────────────────────────────────────────────────────────────────────

_DOCKERFILE_GOLDEN = """\
FROM python:3.12-slim
LABEL org.opencontainers.image.source="https://github.com/x/y"
LABEL org.opencontainers.image.description="desc"
HEALTHCHECK --interval=30s CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/livez/')"
USER appuser
"""

_DOCKERFILE_VIOLATION = """\
FROM python:3.12-slim
USER root
"""


def test_should_pass_dockerfile_golden_path(tmp_path):
    (tmp_path / "Dockerfile").write_text(_DOCKERFILE_GOLDEN, encoding="utf-8")
    results = rc.check_dockerfile(tmp_path, {})
    by_check = {r.check: r.severity for r in results}
    assert by_check["oci_labels"] == rc.Severity.OK
    assert by_check["healthcheck"] == rc.Severity.OK
    assert by_check["nonroot_user"] == rc.Severity.OK
    assert not any(r.severity == rc.Severity.ERROR for r in results)


def test_should_flag_dockerfile_violations(tmp_path):
    (tmp_path / "Dockerfile").write_text(_DOCKERFILE_VIOLATION, encoding="utf-8")
    results = rc.check_dockerfile(tmp_path, {})
    by_check = {r.check: r.severity for r in results}
    assert by_check["oci_labels"] == rc.Severity.ERROR
    assert by_check["healthcheck"] == rc.Severity.ERROR
    assert by_check["nonroot_user"] == rc.Severity.WARNING


def test_should_treat_nonroot_exemption_as_info(tmp_path):
    (tmp_path / "Dockerfile").write_text(_DOCKERFILE_VIOLATION, encoding="utf-8")
    results = rc.check_dockerfile(
        tmp_path, {"nonroot_exempt": True, "nonroot_reason": "Python 3.11 risk"}
    )
    by_check = {r.check: r.severity for r in results}
    assert by_check["nonroot_user"] == rc.Severity.INFO


def test_should_flag_missing_dockerfile(tmp_path):
    results = rc.check_dockerfile(tmp_path, {})
    assert len(results) == 1
    assert results[0].severity == rc.Severity.ERROR


# ─────────────────────────────────────────────────────────────────────────────
# check_cicd
# ─────────────────────────────────────────────────────────────────────────────

_CICD_GOLDEN = """\
jobs:
  deploy:
    uses: achimdehnert/platform/.github/workflows/_deploy.yml@v1
    with:
      health_url: https://x.example.com/livez/
"""

_CICD_VIOLATION = """\
jobs:
  deploy:
    with:
      health_url: https://x.example.com/health
"""


def test_should_pass_cicd_golden_path(tmp_path):
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "deploy.yml").write_text(_CICD_GOLDEN, encoding="utf-8")
    results = rc.check_cicd(tmp_path, {"deployed": True})
    by_check = {r.check: r.severity for r in results}
    assert by_check["platform_workflows"] == rc.Severity.OK
    assert by_check["health_url"] == rc.Severity.OK
    assert not any(r.severity == rc.Severity.ERROR for r in results)


def test_should_flag_cicd_violations(tmp_path):
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "deploy.yml").write_text(_CICD_VIOLATION, encoding="utf-8")
    results = rc.check_cicd(tmp_path, {"deployed": True})
    by_check = {r.check: r.severity for r in results}
    assert by_check["health_url"] == rc.Severity.ERROR
    assert by_check["platform_workflows"] == rc.Severity.WARNING


def test_should_flag_missing_workflows_dir(tmp_path):
    results = rc.check_cicd(tmp_path, {"deployed": True})
    assert len(results) == 1
    assert results[0].check == "workflows_dir"
    assert results[0].severity == rc.Severity.ERROR


# ─────────────────────────────────────────────────────────────────────────────
# check_health_endpoints
# ─────────────────────────────────────────────────────────────────────────────

_HEALTHZ_GOLDEN = """\
HEALTH_PATHS = frozenset(["/livez/"])


@csrf_exempt
@require_GET
def livez(request):
    return HttpResponse("ok")
"""

_HEALTHZ_PARTIAL = """\
def livez(request):
    return HttpResponse("ok")
"""


def test_should_pass_health_endpoints_golden_path(tmp_path, monkeypatch):
    # check_health_endpoints filtert Pfade, die "test" enthalten (Test-Datei-
    # Ausschluss) -- pytest's tmp_path liegt aber IMMER unter .../pytest-.../,
    # und "pytest" enthaelt selbst die Substring "test" (p-y-T-E-S-T). Absolute
    # tmp_path-Pfade wuerden also faelschlich als Testdatei ausgeschlossen.
    # Fix: ins tmp_path chdirn und mit relativem Pfad "." aufrufen, dann liefert
    # glob() relative Treffer ("config/healthz.py") ohne den tmp-Praefix.
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "healthz.py").write_text(_HEALTHZ_GOLDEN, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    results = rc.check_health_endpoints(pathlib.Path("."), {})
    by_check = {r.check: r.severity for r in results}
    assert by_check["health_module"] == rc.Severity.OK
    assert by_check["health_paths"] == rc.Severity.OK
    assert by_check["csrf_exempt"] == rc.Severity.OK
    assert by_check["require_get"] == rc.Severity.OK


def test_should_flag_health_endpoints_missing_decorators(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "healthz.py").write_text(_HEALTHZ_PARTIAL, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    results = rc.check_health_endpoints(pathlib.Path("."), {})
    by_check = {r.check: r.severity for r in results}
    assert by_check["health_paths"] == rc.Severity.WARNING
    assert by_check["csrf_exempt"] == rc.Severity.ERROR
    assert by_check["require_get"] == rc.Severity.WARNING


def test_should_flag_missing_health_module(tmp_path):
    results = rc.check_health_endpoints(tmp_path, {})
    assert len(results) == 1
    assert results[0].check == "health_module"
    assert results[0].severity == rc.Severity.ERROR


# ─────────────────────────────────────────────────────────────────────────────
# check_deploy_script
# ─────────────────────────────────────────────────────────────────────────────


def test_should_pass_deploy_script_golden_path(tmp_path):
    script_dir = tmp_path / "deployment" / "scripts"
    script_dir.mkdir(parents=True)
    (script_dir / "deploy-remote.sh").write_text(
        '#!/bin/bash\nTAG_VAR="IMAGE_TAG"\n', encoding="utf-8"
    )
    results = rc.check_deploy_script(tmp_path, {"deployed": True})
    by_check = {r.check: r.severity for r in results}
    assert by_check["deploy_script"] == rc.Severity.OK
    assert by_check["deploy_image_tag"] == rc.Severity.OK


def test_should_skip_deploy_script_when_not_deployed(tmp_path):
    results = rc.check_deploy_script(tmp_path, {"deployed": False})
    assert len(results) == 1
    assert results[0].severity == rc.Severity.SKIP


def test_should_flag_missing_deploy_script(tmp_path):
    results = rc.check_deploy_script(tmp_path, {"deployed": True})
    assert len(results) == 1
    assert results[0].severity == rc.Severity.ERROR


def test_should_flag_nonstandard_tag_var(tmp_path):
    script_dir = tmp_path / "deployment" / "scripts"
    script_dir.mkdir(parents=True)
    (script_dir / "deploy-remote.sh").write_text(
        '#!/bin/bash\nTAG_VAR="LEGACY_TAG"\n', encoding="utf-8"
    )
    results = rc.check_deploy_script(tmp_path, {"deployed": True})
    by_check = {r.check: r.severity for r in results}
    assert by_check["deploy_script"] == rc.Severity.OK
    assert by_check["deploy_image_tag"] == rc.Severity.ERROR


# ─────────────────────────────────────────────────────────────────────────────
# check_django_config
# ─────────────────────────────────────────────────────────────────────────────


def test_should_pass_django_config_golden_path(tmp_path):
    (tmp_path / "manage.py").write_text(
        "import config.settings\n", encoding="utf-8"
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "wsgi.py").write_text("app = None\n", encoding="utf-8")
    (config_dir / "urls.py").write_text("urlpatterns = ['livez']\n", encoding="utf-8")

    results = rc.check_django_config(tmp_path, {"type": "django"})
    by_check = {r.check: r.severity for r in results}
    assert by_check["manage_settings"] == rc.Severity.OK
    assert by_check["wsgi"] == rc.Severity.OK
    assert by_check["urls_livez"] == rc.Severity.OK


def test_should_skip_django_config_for_non_django_repo(tmp_path):
    results = rc.check_django_config(tmp_path, {"type": "python"})
    assert results == []


def test_should_flag_missing_wsgi_and_urls(tmp_path):
    results = rc.check_django_config(tmp_path, {"type": "django"})
    by_check = {r.check: r.severity for r in results}
    assert by_check["wsgi"] == rc.Severity.ERROR
    assert by_check["urls"] == rc.Severity.ERROR
    # manage.py fehlt komplett -> kein manage_settings-Result (kein content == kein Check)
    assert "manage_settings" not in by_check


# ─────────────────────────────────────────────────────────────────────────────
# check_testing
# ─────────────────────────────────────────────────────────────────────────────


def test_should_pass_testing_golden_path(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "conftest.py").write_text(
        "import platform_context.testing\n", encoding="utf-8"
    )
    (tests_dir / "test_auth.py").write_text(
        "def test_x():\n    assert_login_required()\n", encoding="utf-8"
    )
    (tmp_path / "requirements-test.txt").write_text(
        "platform-context[testing]\n", encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\n", encoding="utf-8"
    )

    results = rc.check_testing(tmp_path, {})
    by_check = {r.check: r.severity for r in results}
    assert by_check["tests_dir"] == rc.Severity.OK
    assert by_check["conftest_platform"] == rc.Severity.OK
    assert by_check["test_auth"] == rc.Severity.OK
    assert by_check["requirements_platform"] == rc.Severity.OK
    assert by_check["pytest_config"] == rc.Severity.OK


def test_should_flag_missing_tests_dir(tmp_path):
    results = rc.check_testing(tmp_path, {})
    assert len(results) == 1
    assert results[0].check == "tests_dir"
    assert results[0].severity == rc.Severity.WARNING


def test_should_flag_empty_tests_dir(tmp_path):
    (tmp_path / "tests").mkdir()
    results = rc.check_testing(tmp_path, {})
    by_check = {r.check: r.severity for r in results}
    assert by_check["tests_dir"] == rc.Severity.OK
    assert by_check["conftest"] == rc.Severity.WARNING
    assert by_check["test_auth"] == rc.Severity.WARNING
    assert by_check["requirements_test"] == rc.Severity.WARNING
    # kein pyproject.toml -> kein pytest_config-Result
    assert "pytest_config" not in by_check


# ─────────────────────────────────────────────────────────────────────────────
# check_repo / check_all_repos — Orchestrierung, REPO_CONFIG isoliert gemonkeypatcht
# (F-1: Modul laedt registry/repos.yaml beim Import; hier explizit unabhaengig davon)
# ─────────────────────────────────────────────────────────────────────────────


def test_should_use_default_config_for_unknown_repo(tmp_path, monkeypatch):
    monkeypatch.setattr(rc, "REPO_CONFIG", {})
    report = rc.check_repo(tmp_path, "totally-unknown-repo")
    assert report.repo == "totally-unknown-repo"
    # Default-Config type=django -> check_django_config laeuft und meldet Fehler
    assert any(r.category == "config" for r in report.results)


def test_should_report_missing_repo_dir_in_check_all_repos(tmp_path, monkeypatch):
    monkeypatch.setattr(
        rc, "REPO_CONFIG", {"ghost-repo": {"type": "python", "deployed": False}}
    )
    reports = rc.check_all_repos(tmp_path)
    assert len(reports) == 1
    assert reports[0].repo == "ghost-repo"
    assert reports[0].errors == 1
    assert "not found" in reports[0].results[0].message
