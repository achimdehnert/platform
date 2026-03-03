"""repo_health_check.py

Maschinenausführbarer Vollständigkeits-Check für Platform-Repos und -Packages.
Prüft alle BLOCK-Items des /repo-health-check Workflows.

Usage:
    python3 tools/repo_health_check.py --profile python-package --path /path/to/repo
    python3 tools/repo_health_check.py --profile django-app --path /path/to/repo
    python3 tools/repo_health_check.py --profile python-package --path . --owner achimdehnert --repo myrepo

Exit codes:
    0 = alle BLOCK-Items OK
    1 = ein oder mehr BLOCK-Items fehlgeschlagen
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


Profile = Literal["python-package", "django-app"]
Severity = Literal["BLOCK", "SUGGEST"]


@dataclass
class CheckResult:
    name: str
    severity: Severity
    passed: bool
    detail: str = ""


@dataclass
class HealthReport:
    profile: Profile
    path: Path
    results: list[CheckResult] = field(default_factory=list)

    @property
    def blocks_failed(self) -> list[CheckResult]:
        return [r for r in self.results if r.severity == "BLOCK" and not r.passed]

    @property
    def suggests_failed(self) -> list[CheckResult]:
        return [r for r in self.results if r.severity == "SUGGEST" and not r.passed]

    @property
    def ok(self) -> bool:
        return len(self.blocks_failed) == 0


def _file_exists(path: Path, rel: str) -> bool:
    return (path / rel).exists()


def _file_contains(path: Path, rel: str, pattern: str) -> bool:
    f = path / rel
    if not f.exists():
        return False
    return pattern in f.read_text(encoding="utf-8", errors="ignore")


def _read_pyproject(path: Path) -> dict:
    toml_path = path / "pyproject.toml"
    if not toml_path.exists():
        return {}
    with open(toml_path, "rb") as fh:
        return tomllib.load(fh)


def _check_test_count(path: Path, min_count: int = 1) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "--tb=no"],
        capture_output=True,
        text=True,
        cwd=str(path),
    )
    output = result.stdout + result.stderr
    for line in output.splitlines():
        if "selected" in line or "test" in line.lower():
            try:
                count = int(line.strip().split()[0])
                if count >= min_count:
                    return True, f"{count} tests collected"
                return False, f"only {count} tests (need >= {min_count})"
            except (ValueError, IndexError):
                continue
    return False, "could not collect tests (check pytest config)"


# ─────────────────────────────────────────────
# Python Package Checks
# ─────────────────────────────────────────────

def check_python_package(path: Path) -> HealthReport:
    report = HealthReport(profile="python-package", path=path)
    add = report.results.append

    data = _read_pyproject(path)
    project = data.get("project", {})

    # ── pyproject.toml fields ──
    required_fields = [
        "name", "version", "description", "readme",
        "requires-python", "license", "authors", "keywords", "classifiers",
    ]
    for f in required_fields:
        val = project.get(f)
        passed = bool(val) and val != "None" and val is not None
        detail = f"value={repr(val)!r}" if not passed else ""
        add(CheckResult(f"pyproject[{f}]", "BLOCK", passed, detail))

    # description must not be empty or "None"
    desc = project.get("description", "")
    add(CheckResult(
        "pyproject[description] not-empty",
        "BLOCK",
        bool(desc) and desc.strip() not in ("", "None"),
        "" if desc else "description is empty or missing",
    ))

    # URLs
    urls = project.get("urls", {})
    for url_key in ["Homepage", "Repository"]:
        add(CheckResult(
            f"pyproject[urls][{url_key}]",
            "BLOCK",
            url_key in urls,
            "" if url_key in urls else f"missing [project.urls] {url_key}",
        ))

    # Optional-deps: dev group
    opt_deps = data.get("project", {}).get("optional-dependencies", {})
    add(CheckResult(
        "pyproject[optional-dependencies][dev]",
        "SUGGEST",
        "dev" in opt_deps,
    ))

    # pytest config
    pytest_cfg = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    add(CheckResult(
        "pyproject[tool.pytest.ini_options]",
        "SUGGEST",
        bool(pytest_cfg.get("testpaths")),
        "" if pytest_cfg.get("testpaths") else "testpaths not set",
    ))

    # ruff config
    ruff_cfg = data.get("tool", {}).get("ruff", {})
    add(CheckResult(
        "pyproject[tool.ruff]",
        "SUGGEST",
        bool(ruff_cfg),
    ))

    # ── Required files ──
    block_files = ["README.md", ".gitignore", "pyproject.toml"]
    for fname in block_files:
        add(CheckResult(f"file:{fname}", "BLOCK", _file_exists(path, fname)))

    # tests/ directory
    tests_dir = path / "tests"
    add(CheckResult(
        "dir:tests/",
        "BLOCK",
        tests_dir.is_dir(),
        "" if tests_dir.is_dir() else "tests/ directory missing",
    ))

    # Makefile
    add(CheckResult("file:Makefile", "SUGGEST", _file_exists(path, "Makefile")))
    add(CheckResult("file:CHANGELOG.md", "SUGGEST", _file_exists(path, "CHANGELOG.md")))

    # ── CI Workflows ──
    workflows_dir = path / ".github" / "workflows"
    add(CheckResult(
        "ci:test.yml exists",
        "BLOCK",
        (workflows_dir / "test.yml").exists(),
        "" if (workflows_dir / "test.yml").exists() else "create .github/workflows/test.yml",
    ))
    add(CheckResult(
        "ci:publish.yml exists",
        "BLOCK",
        (workflows_dir / "publish.yml").exists(),
    ))

    # Publish gate: publish.yml must have 'needs: test' or 'needs: [test'
    publish_yml = workflows_dir / "publish.yml"
    if publish_yml.exists():
        content = publish_yml.read_text(encoding="utf-8")
        has_gate = (
            "needs: test" in content
            or "needs: [test" in content
            or "needs:\n      - test" in content
        )
        add(CheckResult(
            "ci:publish.yml has needs:test gate",
            "BLOCK",
            has_gate,
            "" if has_gate else "add 'needs: test' to build job in publish.yml",
        ))
    else:
        add(CheckResult("ci:publish.yml has needs:test gate", "BLOCK", False, "publish.yml missing"))

    # test.yml triggers
    test_yml = workflows_dir / "test.yml"
    if test_yml.exists():
        content = test_yml.read_text(encoding="utf-8")
        add(CheckResult(
            "ci:test.yml triggers push+PR",
            "BLOCK",
            "pull_request" in content and "push" in content,
            "" if ("pull_request" in content and "push" in content)
            else "test.yml must trigger on push AND pull_request",
        ))
    else:
        add(CheckResult("ci:test.yml triggers push+PR", "BLOCK", False, "test.yml missing"))

    # ── Tests run ──
    if tests_dir.is_dir():
        passed, detail = _check_test_count(path, min_count=1)
        add(CheckResult("tests:min-1-test", "BLOCK", passed, detail))
    else:
        add(CheckResult("tests:min-1-test", "BLOCK", False, "tests/ missing"))

    return report


# ─────────────────────────────────────────────
# Django App Checks
# ─────────────────────────────────────────────

def check_django_app(path: Path) -> HealthReport:
    report = HealthReport(profile="django-app", path=path)
    add = report.results.append

    # ── Required files ──
    block_files = [
        "Makefile",
        ".env.example",
        "requirements.txt",
        "requirements-test.txt",
    ]
    for fname in block_files:
        add(CheckResult(f"file:{fname}", "BLOCK", _file_exists(path, fname)))

    # Dockerfile (root or docker/app/)
    dockerfile_exists = (
        _file_exists(path, "Dockerfile")
        or _file_exists(path, "docker/app/Dockerfile")
        or _file_exists(path, "docker/Dockerfile")
    )
    add(CheckResult("file:Dockerfile", "BLOCK", dockerfile_exists))

    # docker-compose.prod.yml
    compose_exists = (
        _file_exists(path, "docker-compose.prod.yml")
        or _file_exists(path, "deploy/docker-compose.prod.yml")
    )
    add(CheckResult("file:docker-compose.prod.yml", "BLOCK", compose_exists))

    add(CheckResult("file:CHANGELOG.md", "SUGGEST", _file_exists(path, "CHANGELOG.md")))

    # Makefile contains DJANGO_SETTINGS_MODULE
    if _file_exists(path, "Makefile"):
        add(CheckResult(
            "Makefile:DJANGO_SETTINGS_MODULE",
            "BLOCK",
            _file_contains(path, "Makefile", "DJANGO_SETTINGS_MODULE"),
            "Makefile must set DJANGO_SETTINGS_MODULE for make test",
        ))

    # ── CI Workflows ──
    workflows_dir = path / ".github" / "workflows"
    has_ci = (
        (workflows_dir / "ci.yml").exists()
        or any(workflows_dir.glob("*ci*.yml"))
    ) if workflows_dir.is_dir() else False
    add(CheckResult(
        "ci:ci.yml exists",
        "BLOCK",
        has_ci,
        "" if has_ci else "create .github/workflows/ci.yml",
    ))

    if has_ci and workflows_dir.is_dir():
        ci_files = list(workflows_dir.glob("ci*.yml"))
        if ci_files:
            content = ci_files[0].read_text(encoding="utf-8")
            add(CheckResult(
                "ci:build needs:[ci]",
                "BLOCK",
                "needs: [ci]" in content or "needs: ci" in content or "needs: [test" in content,
                "build job must depend on ci/test job",
            ))

    # Health endpoint
    has_livez = False
    for root, _dirs, files in os.walk(str(path)):
        for fname in files:
            if fname.endswith(".py"):
                fpath = Path(root) / fname
                try:
                    if "livez" in fpath.read_text(encoding="utf-8", errors="ignore"):
                        has_livez = True
                        break
                except OSError:
                    pass
        if has_livez:
            break
    add(CheckResult(
        "django:livez-endpoint",
        "BLOCK",
        has_livez,
        "" if has_livez else "add /livez/ health endpoint",
    ))

    # test settings
    test_settings = (
        _file_exists(path, "config/settings/test.py")
        or _file_exists(path, "src/config/settings/test.py")
        or _file_exists(path, "settings/test.py")
    )
    add(CheckResult(
        "django:test-settings",
        "BLOCK",
        test_settings,
        "" if test_settings else "config/settings/test.py missing",
    ))

    # Tests
    tests_dir = path / "tests"
    if not tests_dir.is_dir():
        # Django apps sometimes have tests spread in apps/
        tests_dir = path / "src"
    if tests_dir.is_dir():
        passed, detail = _check_test_count(path, min_count=10)
        add(CheckResult("tests:min-10-tests", "BLOCK", passed, detail))
    else:
        add(CheckResult("tests:min-10-tests", "BLOCK", False, "no tests directory found"))

    return report


# ─────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────

def _render_report(report: HealthReport, fmt: str = "text") -> None:
    if fmt == "json":
        data = {
            "profile": report.profile,
            "path": str(report.path),
            "ok": report.ok,
            "blocks_failed": len(report.blocks_failed),
            "suggests_failed": len(report.suggests_failed),
            "results": [
                {"name": r.name, "severity": r.severity, "passed": r.passed, "detail": r.detail}
                for r in report.results
            ],
        }
        print(json.dumps(data, indent=2))
        return

    status_icon = "✅" if report.ok else "❌"
    print(f"\n{status_icon} Repo Health Check [{report.profile}] — {report.path}")
    print("=" * 70)

    blocks = [r for r in report.results if r.severity == "BLOCK"]
    suggests = [r for r in report.results if r.severity == "SUGGEST"]

    print("\n■ BLOCK items (must all pass):")
    for r in blocks:
        icon = "✅" if r.passed else "❌"
        detail = f"  → {r.detail}" if r.detail else ""
        print(f"  {icon} {r.name}{detail}")

    print("\n□ SUGGEST items (recommended):")
    for r in suggests:
        icon = "✅" if r.passed else "⚠️"
        detail = f"  → {r.detail}" if r.detail else ""
        print(f"  {icon} {r.name}{detail}")

    print()
    if report.ok:
        print(f"✅ ALL {len(blocks)} BLOCK items passed. Ready to publish/deploy.")
    else:
        print(f"❌ {len(report.blocks_failed)} BLOCK item(s) FAILED. Fix before publish/deploy:")
        for r in report.blocks_failed:
            print(f"   - {r.name}: {r.detail}")
    if report.suggests_failed:
        print(f"⚠️  {len(report.suggests_failed)} SUGGEST item(s) not met (not blocking).")
    print()


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Platform Repo Health Check — verbindlicher Vollständigkeits-Check"
    )
    parser.add_argument(
        "--profile",
        choices=["python-package", "django-app"],
        required=True,
        help="Profil: 'python-package' oder 'django-app'",
    )
    parser.add_argument(
        "--path",
        default=".",
        help="Pfad zum Repo (default: aktuelles Verzeichnis)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Ausgabe-Format (default: text)",
    )
    parser.add_argument(
        "--owner",
        default="",
        help="GitHub Owner (optional, für GitHub-Repo-Metadaten-Check)",
    )
    parser.add_argument(
        "--repo",
        default="",
        help="GitHub Repo-Name (optional, für GitHub-Repo-Metadaten-Check)",
    )

    args = parser.parse_args()
    path = Path(args.path).resolve()

    if not path.exists():
        print(f"ERROR: path does not exist: {path}", file=sys.stderr)
        sys.exit(2)

    if args.profile == "python-package":
        report = check_python_package(path)
    else:
        report = check_django_app(path)

    _render_report(report, fmt=args.format)

    if args.owner and args.repo:
        print(f"NOTE: GitHub Repo description check requires manual verification:")
        print(f"  https://github.com/{args.owner}/{args.repo}")
        print(f"  Repo > Settings ⚙️ > About > Description (must not be empty)")

    sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
