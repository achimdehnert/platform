#!/usr/bin/env python3
"""gen_test_scaffold.py — Test-Scaffold für ein Django-Repo generieren.

Holt die aktuelle iil-testkit Version von PyPI und generiert alle
Test-Infrastruktur-Dateien für das Ziel-Repo.

Aufruf:
    python3 scripts/gen_test_scaffold.py <repo>           # schreibt Dateien
    python3 scripts/gen_test_scaffold.py <repo> --dry-run # nur anzeigen
    python3 scripts/gen_test_scaffold.py <repo> --update  # auch bestehende updaten

Verwendet von:
    - /teste-repo Workflow (wenn tests/ fehlt)
    - scaffold-tests.yml GitHub Action
    - Manuell beim Onboarding neuer Repos
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from string import Template

PLATFORM_ROOT = Path(__file__).parent.parent
FALLBACK_VERSION = "0.4.0"


# ── PyPI Version Lookup ───────────────────────────────────────────────────────

def get_latest_version(package: str, fallback: str = FALLBACK_VERSION) -> str:
    """Hole aktuelle Stable-Version von PyPI. Fallback bei Netzwerkfehler."""
    url = f"https://pypi.org/pypi/{package}/json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "gen_test_scaffold/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        version = data["info"]["version"]
        print(f"  PyPI {package}: {version}")
        return version
    except Exception as e:
        print(f"  ⚠️  PyPI-Lookup fehlgeschlagen ({e}) — Fallback: {fallback}")
        return fallback


# ── Scaffold-Templates ────────────────────────────────────────────────────────

def _requirements_test(testkit_version: str) -> str:
    return f"""\
iil-testkit[smoke]>={testkit_version},<{int(testkit_version.split('.')[0]) + 1}
pytest>=8.0
pytest-django>=4.8
pytest-cov>=5.0
pytest-xdist>=3.0
beautifulsoup4>=4.12
factory-boy>=3.3
"""


def _conftest() -> str:
    return '''\
"""conftest.py — iil-testkit Fixtures laden.

Stellt bereit: auth_client, staff_client, api_client,
               db_user, staff_user, admin_user
"""
pytest_plugins = ["iil_testkit.fixtures"]
'''


def _test_views_smoke(repo_name: str) -> str:
    return f'''\
"""test_views_smoke.py — Automatischer HTTP-200-Test aller Views.

Nutzt discover_smoke_urls() — kein manuelles URL-Pflegen nötig.
Neue Views werden automatisch aufgenommen.
"""
import pytest

from iil_testkit.smoke import discover_smoke_urls


@pytest.mark.parametrize("url", discover_smoke_urls())
@pytest.mark.django_db
def test_should_view_return_200(url: str, auth_client) -> None:
    """Alle parameterfreien Views müssen HTTP 200 oder 302 liefern."""
    response = auth_client.get(url)
    assert response.status_code in (200, 302), (
        f"{{url}} → HTTP {{response.status_code}} (erwartet: 200 oder 302)"
    )


@pytest.mark.parametrize("url", discover_smoke_urls())
@pytest.mark.django_db
def test_should_unauthenticated_access_redirect(url: str, api_client) -> None:
    """Geschützte Views müssen unauthentifiziert auf Login weiterleiten."""
    from iil_testkit.assertions import assert_redirects_to_login
    response = api_client.get(url)
    if response.status_code == 302:
        location = response.get("Location", "")
        if "/login" in location or "/accounts/login" in location:
            assert_redirects_to_login(response)
'''


def _test_views_htmx(repo_name: str) -> str:
    return '''\
"""test_views_htmx.py — HTMX-Partials und data-testid Enforcement (ADR-048).

Prüft:
  1. HTMX-Responses liefern Fragmente, keine vollen HTML-Seiten
  2. Alle hx-* Elemente haben data-testid

HTMX_URLS befüllen: URLs die auf HX-Request mit Partial antworten.
"""
import pytest

from iil_testkit.assertions import assert_data_testids, assert_htmx_response


HTMX_URLS: list[str] = [
    # Hier HTMX-Endpoints eintragen, z.B.:
    # "/dashboard/items/",
    # "/projects/list/",
]


@pytest.mark.skipif(not HTMX_URLS, reason="HTMX_URLS nicht konfiguriert")
@pytest.mark.parametrize("url", HTMX_URLS)
@pytest.mark.django_db
def test_should_htmx_response_be_fragment(url: str, auth_client) -> None:
    """HTMX-Endpoints müssen Fragmente liefern, keine vollen Seiten."""
    response = auth_client.get(url, HTTP_HX_REQUEST="true")
    assert_htmx_response(response)


@pytest.mark.skipif(not HTMX_URLS, reason="HTMX_URLS nicht konfiguriert")
@pytest.mark.parametrize("url", HTMX_URLS)
@pytest.mark.django_db
def test_should_htmx_elements_have_data_testid(url: str, auth_client) -> None:
    """Alle hx-* Elemente müssen data-testid haben (ADR-048)."""
    response = auth_client.get(url)
    assert_data_testids(response)
'''


def _factories(repo_name: str) -> str:
    return f'''\
"""factories.py — Test-Factories für {repo_name}.

Ergänze hier repo-spezifische Factories für deine Domain-Models.
"""
import factory
from factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):
    class Meta:
        model = "auth.User"

    username = factory.Sequence(lambda n: f"user_{{n}}")
    email = factory.LazyAttribute(lambda obj: f"{{obj.username}}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    is_active = True


# TODO: Hier Domain-Factories ergänzen, z.B.:
# class ProjectFactory(DjangoModelFactory):
#     class Meta:
#         model = "projects.Project"
#     name = factory.Sequence(lambda n: f"Project {{n}}")
#     owner = factory.SubFactory(UserFactory)
'''


def _pytest_ini_options(settings_module: str) -> str:
    return f"""\
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "{settings_module}"
python_files = ["test_*.py"]
python_functions = ["test_should_*"]
addopts = [
    "--strict-markers",
    "--tb=short",
    "-ra",
    "--no-header",
    "--cov",
    "--cov-report=term-missing:skip-covered",
    "--cov-fail-under=80",
]
markers = [
    "unit: Unit-Tests (kein DB-Zugriff)",
    "integration: Integration-Tests (Django Test Client, DB)",
    "contract: Contract-Tests (Schemathesis, API)",
    "slow: Tests die laenger als 5s dauern",
]
testpaths = ["tests"]
"""


# ── Settings-Modul auto-detect ────────────────────────────────────────────────

def detect_settings(repo_dir: Path) -> str:
    """Ermittle DJANGO_SETTINGS_MODULE aus pyproject.toml oder Verzeichnisstruktur."""
    pyproject = repo_dir / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib
            cfg = tomllib.loads(pyproject.read_text())
            s = cfg.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("DJANGO_SETTINGS_MODULE", "")
            if s:
                return s
        except Exception:
            pass

    for candidate in [
        "config.settings.test",
        "config.settings.base",
        "config.settings",
        "settings.test",
        "settings",
    ]:
        module_path = repo_dir / candidate.replace(".", "/")
        if (Path(str(module_path) + ".py")).exists():
            return candidate

    return "config.settings.test"


# ── Hauptlogik ────────────────────────────────────────────────────────────────

SCAFFOLD_FILES = {
    "tests/__init__.py": lambda ctx: "",
    "tests/conftest.py": lambda ctx: _conftest(),
    "tests/factories.py": lambda ctx: _factories(ctx["repo_name"]),
    "tests/test_views_smoke.py": lambda ctx: _test_views_smoke(ctx["repo_name"]),
    "tests/test_views_htmx.py": lambda ctx: _test_views_htmx(ctx["repo_name"]),
    "requirements-test.txt": lambda ctx: _requirements_test(ctx["testkit_version"]),
}


def generate_scaffold(
    repo_dir: Path,
    testkit_version: str,
    dry_run: bool = False,
    update: bool = False,
) -> dict[str, str]:
    """Generiere alle Scaffold-Dateien. Gibt {path: status} zurück."""
    settings = detect_settings(repo_dir)
    ctx = {
        "repo_name": repo_dir.name,
        "testkit_version": testkit_version,
        "settings_module": settings,
    }

    results: dict[str, str] = {}

    for rel_path, content_fn in SCAFFOLD_FILES.items():
        target = repo_dir / rel_path
        content = content_fn(ctx)

        if target.exists() and not update:
            results[rel_path] = "SKIP (exists)"
            continue

        if dry_run:
            results[rel_path] = "DRY-RUN"
            print(f"\n--- {rel_path} ---")
            print(content[:200] + ("..." if len(content) > 200 else ""))
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        results[rel_path] = "CREATED" if not target.exists() else "UPDATED"

    # pyproject.toml: pytest-Sektion prüfen / hinzufügen
    pyproject = repo_dir / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        if "tool.pytest.ini_options" not in content:
            ini = _pytest_ini_options(settings)
            if not dry_run:
                pyproject.write_text(content.rstrip() + "\n\n" + ini, encoding="utf-8")
                results["pyproject.toml"] = "UPDATED (pytest section added)"
            else:
                results["pyproject.toml"] = "DRY-RUN (would add pytest section)"
        else:
            results["pyproject.toml"] = "SKIP (pytest section exists)"

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Test-Scaffold für ein Django-Repo generieren")
    parser.add_argument("repo", help="Repo-Name oder absoluter Pfad")
    parser.add_argument("--dry-run", action="store_true", help="Nur anzeigen, nichts schreiben")
    parser.add_argument("--update", action="store_true", help="Bestehende Dateien überschreiben")
    parser.add_argument("--version", default=None, help="iil-testkit Version (default: PyPI latest)")
    args = parser.parse_args()

    # Repo-Pfad bestimmen
    repo_dir = Path(args.repo)
    if not repo_dir.is_absolute():
        github_dir = Path(os.environ.get("GITHUB_DIR", Path.home() / "github"))
        repo_dir = github_dir / args.repo

    if not repo_dir.exists():
        print(f"❌ Repo nicht gefunden: {repo_dir}")
        return 1

    print(f"\n🔧  Generiere Test-Scaffold für: {repo_dir.name}")
    print(f"    Pfad:    {repo_dir}")
    print(f"    Modus:   {'DRY-RUN' if args.dry_run else 'UPDATE' if args.update else 'ERSTELLEN (neu)'}\n")

    # Version von PyPI holen
    testkit_version = args.version or get_latest_version("iil-testkit", FALLBACK_VERSION)

    # Scaffold generieren
    results = generate_scaffold(repo_dir, testkit_version, dry_run=args.dry_run, update=args.update)

    # Report
    print(f"\n{'='*55}")
    for path, status in results.items():
        icon = "✅" if "CREAT" in status or "UPDATE" in status or "DRY" in status else "⏭️ "
        print(f"  {icon}  {path:<35} {status}")
    print(f"{'='*55}")

    if not args.dry_run:
        print(f"\nNächste Schritte für {repo_dir.name}:")
        print(f"  1. DJANGO_SETTINGS_MODULE in pyproject.toml prüfen")
        print(f"  2. tests/factories.py um Domain-Models ergänzen")
        print(f"  3. tests/test_views_htmx.py: HTMX_URLS befüllen")
        print(f"  4. python3 {PLATFORM_ROOT}/scripts/teste_repo.py {repo_dir.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
