#!/usr/bin/env python3
"""
ADR-022 Repository Consistency Checker.

Checks all platform repositories for ADR-022 compliance:
- Docker Compose: IMAGE_TAG, env_file, healthcheck (127.0.0.1, /livez/)
- Dockerfile: OCI Labels, HEALTHCHECK, non-root USER
- CI/CD: Platform reusable workflows, health_url /livez/
- Health endpoints: HEALTH_PATHS, csrf_exempt, require_GET
- Deploy script: deployment/scripts/deploy-remote.sh exists
- Config: manage.py settings, config/wsgi.py, config/urls.py

Usage:
    python repo_checker.py                        # Check all repos
    python repo_checker.py /path/to/repo          # Check single repo
    python repo_checker.py --json                  # JSON output
    python repo_checker.py --repos-dir /home/user/github  # Custom base dir
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class Severity(str, Enum):
    """Check result severity."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    OK = "ok"
    SKIP = "skip"


@dataclass
class CheckResult:
    """Single check result."""

    category: str
    check: str
    severity: Severity
    message: str
    file: str = ""
    line: int = 0


@dataclass
class RepoReport:
    """Full report for one repository."""

    repo: str
    path: str
    results: list[CheckResult] = field(default_factory=list)

    @property
    def errors(self) -> int:
        return sum(1 for r in self.results if r.severity == Severity.ERROR)

    @property
    def warnings(self) -> int:
        return sum(1 for r in self.results if r.severity == Severity.WARNING)

    @property
    def ok_count(self) -> int:
        return sum(1 for r in self.results if r.severity == Severity.OK)


# ─────────────────────────────────────────────────────────────────────────────
# Config: Load from registry/repos.yaml (Single Source of Truth — ADR-022)
# ─────────────────────────────────────────────────────────────────────────────

_REGISTRY_PATH = Path(__file__).parent.parent / "registry" / "repos.yaml"

_NONROOT_EXEMPT: dict[str, dict] = {
    "bfagent": {"nonroot_exempt": True, "nonroot_reason": "Python 3.11 risk"},
}


def _load_repo_config() -> dict[str, dict]:
    """Load REPO_CONFIG from registry/repos.yaml (Single Source of Truth).

    Falls back gracefully if pyyaml is unavailable or file missing.
    Only includes repos with type in (django, python).
    """
    try:
        import yaml
    except ImportError:
        sys.stderr.write("Warning: pyyaml not installed, REPO_CONFIG empty\n")
        return {}

    if not _REGISTRY_PATH.exists():
        sys.stderr.write(f"Warning: {_REGISTRY_PATH} not found\n")
        return {}

    try:
        data = yaml.safe_load(_REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        sys.stderr.write(f"Warning: failed to parse repos.yaml: {exc}\n")
        return {}

    config: dict[str, dict] = {}
    for domain in data.get("domains", []):
        for sys_entry in domain.get("systems", []):
            repo = sys_entry.get("repo") or sys_entry.get("name")
            repo_type = sys_entry.get("type", "django")
            if repo_type not in ("django", "python"):
                continue
            entry: dict = {
                "type": repo_type,
                "deployed": sys_entry.get("deployed", False),
                "dockerfile": sys_entry.get("dockerfile", "Dockerfile"),
                "compose": sys_entry.get("compose", "docker-compose.prod.yml"),
            }
            entry.update(_NONROOT_EXEMPT.get(repo, {}))
            config[repo] = entry
    return config


REPO_CONFIG: dict[str, dict] = _load_repo_config()


# ─────────────────────────────────────────────────────────────────────────────
# File helpers
# ─────────────────────────────────────────────────────────────────────────────


def read_file(path: Path) -> Optional[str]:
    """Read file contents, return None if not found."""
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError):
        return None


def find_files(repo_path: Path, pattern: str) -> list[Path]:
    """Find files matching glob pattern."""
    return list(repo_path.glob(pattern))


def grep_lines(
    content: str, pattern: str, flags: int = re.IGNORECASE
) -> list[tuple[int, str]]:
    """Return (line_number, line) tuples matching regex pattern."""
    matches = []
    for i, line in enumerate(content.splitlines(), 1):
        if re.search(pattern, line, flags):
            matches.append((i, line.strip()))
    return matches


def _get_continuation_block(content: str, start_idx: int) -> str:
    """Collect a block of lines starting at start_idx, following \\ continuations."""
    lines = content.splitlines()
    block_lines: list[str] = []
    idx = start_idx
    while idx < len(lines):
        line = lines[idx]
        block_lines.append(line)
        if not line.rstrip().endswith("\\"):
            break
        idx += 1
    return "\n".join(block_lines)


# ─────────────────────────────────────────────────────────────────────────────
# Individual Checks
# ─────────────────────────────────────────────────────────────────────────────


def check_compose(repo_path: Path, config: dict) -> list[CheckResult]:
    """Check docker-compose.prod.yml for ADR-022 compliance."""
    results: list[CheckResult] = []
    cat = "compose"
    compose_file = config.get("compose", "docker-compose.prod.yml")
    path = repo_path / compose_file

    content = read_file(path)
    if content is None:
        results.append(CheckResult(
            cat, "file_exists", Severity.ERROR,
            f"{compose_file} not found", str(path),
        ))
        return results

    results.append(CheckResult(
        cat, "file_exists", Severity.OK,
        f"{compose_file} exists", str(path),
    ))

    # Check IMAGE_TAG standardization
    legacy_tags = grep_lines(
        content,
        r"\$\{(?!IMAGE_TAG|MCPHUB_IMAGE_TAG|LLM_GATEWAY_TAG)[A-Z_]*IMAGE_TAG",
    )
    if legacy_tags:
        for ln, line in legacy_tags:
            results.append(CheckResult(
                cat, "image_tag", Severity.ERROR,
                f"Legacy IMAGE_TAG variant: {line}",
                str(path), ln,
            ))
    else:
        results.append(CheckResult(
            cat, "image_tag", Severity.OK,
            "IMAGE_TAG standardized", str(path),
        ))

    # Check healthcheck uses 127.0.0.1 (not localhost)
    localhost_hc = grep_lines(content, r"localhost.*8000.*livez")
    if localhost_hc:
        for ln, line in localhost_hc:
            results.append(CheckResult(
                cat, "hc_ip", Severity.ERROR,
                "Healthcheck uses 'localhost' instead of '127.0.0.1'",
                str(path), ln,
            ))
    else:
        ip_hc = grep_lines(content, r"127\.0\.0\.1.*8000.*livez")
        if ip_hc:
            results.append(CheckResult(
                cat, "hc_ip", Severity.OK,
                "Healthcheck uses 127.0.0.1", str(path),
            ))

    # Check healthcheck uses /livez/
    hc_lines = grep_lines(content, r"healthcheck|test.*CMD")
    livez_found = any("livez" in line for _, line in hc_lines)
    if hc_lines and not livez_found:
        results.append(CheckResult(
            cat, "hc_livez", Severity.ERROR,
            "Healthcheck does not use /livez/ endpoint", str(path),
        ))
    elif livez_found:
        results.append(CheckResult(
            cat, "hc_livez", Severity.OK,
            "Healthcheck uses /livez/", str(path),
        ))

    # Check healthcheck uses python urllib (not curl)
    curl_hc = grep_lines(content, r"curl.*livez|curl.*health")
    if curl_hc:
        for ln, line in curl_hc:
            results.append(CheckResult(
                cat, "hc_urllib", Severity.WARNING,
                f"Healthcheck uses curl instead of python urllib: {line}",
                str(path), ln,
            ))

    # Check env_file usage
    env_file_lines = grep_lines(content, r"^\s*env_file:")
    env_interp = grep_lines(content, r"^\s+\$\{[A-Z_]+")
    if not env_file_lines and env_interp:
        results.append(CheckResult(
            cat, "env_file", Severity.WARNING,
            "No env_file directive; uses environment: with ${VAR} interpolation",
            str(path),
        ))
    elif env_file_lines:
        env_prod = grep_lines(content, r"\.env\.prod")
        if env_prod:
            results.append(CheckResult(
                cat, "env_file", Severity.OK,
                "Uses env_file: .env.prod", str(path),
            ))
        else:
            env_plain = grep_lines(content, r"- \.env\s*$")
            if env_plain:
                results.append(CheckResult(
                    cat, "env_file", Severity.WARNING,
                    "Uses .env instead of .env.prod",
                    str(path),
                ))

    return results


def check_dockerfile(repo_path: Path, config: dict) -> list[CheckResult]:
    """Check Dockerfile for ADR-022 compliance."""
    results: list[CheckResult] = []
    cat = "dockerfile"
    dockerfile = config.get("dockerfile", "Dockerfile")
    path = repo_path / dockerfile

    content = read_file(path)
    if content is None:
        results.append(CheckResult(
            cat, "file_exists", Severity.ERROR,
            f"{dockerfile} not found", str(path),
        ))
        return results

    # OCI Labels
    oci_labels = grep_lines(content, r"org\.opencontainers\.image\.")
    if len(oci_labels) >= 2:
        results.append(CheckResult(
            cat, "oci_labels", Severity.OK,
            f"OCI Labels present ({len(oci_labels)} found)", str(path),
        ))
    elif oci_labels:
        results.append(CheckResult(
            cat, "oci_labels", Severity.WARNING,
            "Only 1 OCI Label (need source + description)", str(path),
        ))
    else:
        results.append(CheckResult(
            cat, "oci_labels", Severity.ERROR,
            "No OCI Labels found", str(path),
        ))

    # HEALTHCHECK (may span multiple lines via backslash)
    hc = grep_lines(content, r"^HEALTHCHECK")
    if hc:
        # Collect continuation lines (HEALTHCHECK ... \ \n    CMD ...)
        hc_block = _get_continuation_block(content, hc[0][0] - 1)
        if "127.0.0.1" in hc_block and "livez" in hc_block:
            results.append(CheckResult(
                cat, "healthcheck", Severity.OK,
                "HEALTHCHECK with 127.0.0.1 and /livez/", str(path),
            ))
        elif "livez" not in hc_block:
            results.append(CheckResult(
                cat, "healthcheck", Severity.ERROR,
                "HEALTHCHECK does not use /livez/", str(path),
            ))
        elif "127.0.0.1" not in hc_block:
            results.append(CheckResult(
                cat, "healthcheck", Severity.WARNING,
                "HEALTHCHECK does not use 127.0.0.1", str(path),
            ))
    else:
        results.append(CheckResult(
            cat, "healthcheck", Severity.ERROR,
            "No HEALTHCHECK directive", str(path),
        ))

    # Non-root USER
    user_lines = grep_lines(content, r"^USER\s+(?!root)")
    nonroot_exempt = config.get("nonroot_exempt", False)
    if user_lines:
        results.append(CheckResult(
            cat, "nonroot_user", Severity.OK,
            f"Non-root USER: {user_lines[-1][1]}", str(path),
        ))
    elif nonroot_exempt:
        reason = config.get("nonroot_reason", "exempt")
        results.append(CheckResult(
            cat, "nonroot_user", Severity.INFO,
            f"Non-root USER exempt: {reason}", str(path),
        ))
    else:
        results.append(CheckResult(
            cat, "nonroot_user", Severity.WARNING,
            "No non-root USER directive", str(path),
        ))

    return results


def check_cicd(repo_path: Path, config: dict) -> list[CheckResult]:
    """Check CI/CD workflows for platform reusable workflow usage."""
    results: list[CheckResult] = []
    cat = "cicd"

    workflow_dir = repo_path / ".github" / "workflows"
    if not workflow_dir.exists():
        results.append(CheckResult(
            cat, "workflows_dir", Severity.ERROR,
            ".github/workflows/ not found", str(workflow_dir),
        ))
        return results

    workflows = list(workflow_dir.glob("*.yml")) + list(
        workflow_dir.glob("*.yaml")
    )
    if not workflows:
        results.append(CheckResult(
            cat, "workflows_exist", Severity.ERROR,
            "No workflow files found", str(workflow_dir),
        ))
        return results

    is_deployed = config.get("deployed", True)
    platform_refs_found = False
    health_url_ok = False

    for wf in workflows:
        content = read_file(wf)
        if content is None:
            continue

        # Check for platform reusable workflows
        platform_refs = grep_lines(
            content, r"achimdehnert/platform/.*@v\d+"
        )
        if platform_refs:
            platform_refs_found = True
            results.append(CheckResult(
                cat, "platform_workflows", Severity.OK,
                f"Uses platform reusable workflows ({len(platform_refs)} refs)",
                str(wf),
            ))

        # Check health_url
        health_urls = grep_lines(content, r"health_url:")
        for ln, line in health_urls:
            if "/livez/" in line:
                health_url_ok = True
                results.append(CheckResult(
                    cat, "health_url", Severity.OK,
                    f"health_url uses /livez/: {line}", str(wf), ln,
                ))
            else:
                results.append(CheckResult(
                    cat, "health_url", Severity.ERROR,
                    f"health_url not /livez/: {line}", str(wf), ln,
                ))

    if is_deployed and not platform_refs_found:
        results.append(CheckResult(
            cat, "platform_workflows", Severity.WARNING,
            "No platform reusable workflow references found",
            str(workflow_dir),
        ))

    if is_deployed and not health_url_ok:
        has_health_url = any(
            grep_lines(read_file(wf) or "", r"health_url:")
            for wf in workflows
        )
        if has_health_url:
            results.append(CheckResult(
                cat, "health_url", Severity.ERROR,
                "health_url defined but not using /livez/",
                str(workflow_dir),
            ))

    return results


def check_health_endpoints(
    repo_path: Path, config: dict
) -> list[CheckResult]:
    """Check health endpoint implementation."""
    results: list[CheckResult] = []
    cat = "health"

    # Search for healthz.py or health views
    healthz_files = (
        find_files(repo_path, "**/healthz.py")
        + find_files(repo_path, "**/health.py")
    )
    # Exclude test files and venvs
    healthz_files = [
        f for f in healthz_files
        if ".venv" not in str(f)
        and "test" not in str(f).lower()
        and "__pycache__" not in str(f)
        and "site-packages" not in str(f)
        and "node_modules" not in str(f)
    ]
    # For repos with config/healthz.py, prefer that over deep matches
    config_healthz = [f for f in healthz_files if "config/" in str(f)]
    if config_healthz:
        healthz_files = config_healthz

    if not healthz_files:
        # Check views.py for health endpoints
        view_files = find_files(repo_path, "**/views.py")
        view_files = [
            f for f in view_files
            if ".venv" not in str(f) and "__pycache__" not in str(f)
        ]
        health_in_views = False
        for vf in view_files:
            content = read_file(vf)
            if content and ("livez" in content or "HEALTH_PATHS" in content):
                healthz_files = [vf]
                health_in_views = True
                break
        if not health_in_views:
            results.append(CheckResult(
                cat, "health_module", Severity.ERROR,
                "No healthz.py or health views found",
            ))
            return results

    for hf in healthz_files:
        content = read_file(hf)
        if content is None:
            continue

        results.append(CheckResult(
            cat, "health_module", Severity.OK,
            f"Health endpoints in {hf.relative_to(repo_path)}",
            str(hf),
        ))

        # HEALTH_PATHS
        if "HEALTH_PATHS" in content:
            results.append(CheckResult(
                cat, "health_paths", Severity.OK,
                "HEALTH_PATHS frozenset defined", str(hf),
            ))
        else:
            results.append(CheckResult(
                cat, "health_paths", Severity.WARNING,
                "HEALTH_PATHS not defined", str(hf),
            ))

        # csrf_exempt
        csrf_lines = grep_lines(content, r"@csrf_exempt")
        if csrf_lines:
            results.append(CheckResult(
                cat, "csrf_exempt", Severity.OK,
                f"@csrf_exempt on {len(csrf_lines)} views", str(hf),
            ))
        else:
            results.append(CheckResult(
                cat, "csrf_exempt", Severity.ERROR,
                "Health views missing @csrf_exempt", str(hf),
            ))

        # require_GET
        get_lines = grep_lines(content, r"@require_GET")
        if get_lines:
            results.append(CheckResult(
                cat, "require_get", Severity.OK,
                f"@require_GET on {len(get_lines)} views", str(hf),
            ))
        else:
            results.append(CheckResult(
                cat, "require_get", Severity.WARNING,
                "Health views missing @require_GET", str(hf),
            ))

    return results


def check_deploy_script(
    repo_path: Path, config: dict
) -> list[CheckResult]:
    """Check deployment script presence."""
    results: list[CheckResult] = []
    cat = "deploy"

    if not config.get("deployed", True):
        results.append(CheckResult(
            cat, "deploy_script", Severity.SKIP,
            "Not deployed to Hetzner — skipping",
        ))
        return results

    script = repo_path / "deployment" / "scripts" / "deploy-remote.sh"
    if script.exists():
        size = script.stat().st_size
        results.append(CheckResult(
            cat, "deploy_script", Severity.OK,
            f"deploy-remote.sh exists ({size} bytes)", str(script),
        ))
        # Check for IMAGE_TAG standardization
        content = read_file(script)
        if content:
            if 'TAG_VAR="IMAGE_TAG"' in content:
                results.append(CheckResult(
                    cat, "deploy_image_tag", Severity.OK,
                    "deploy-remote.sh uses standardized IMAGE_TAG",
                    str(script),
                ))
            else:
                tag_vars = grep_lines(content, r"TAG_VAR=")
                if tag_vars:
                    results.append(CheckResult(
                        cat, "deploy_image_tag", Severity.ERROR,
                        f"Non-standard TAG_VAR: {tag_vars[0][1]}",
                        str(script), tag_vars[0][0],
                    ))
    else:
        results.append(CheckResult(
            cat, "deploy_script", Severity.ERROR,
            "deployment/scripts/deploy-remote.sh missing", str(script),
        ))

    return results


def check_django_config(
    repo_path: Path, config: dict
) -> list[CheckResult]:
    """Check Django project configuration."""
    results: list[CheckResult] = []
    cat = "config"

    if config.get("type") != "django":
        return results

    # manage.py
    manage = repo_path / "manage.py"
    content = read_file(manage)
    if content:
        if "config.settings" in content:
            results.append(CheckResult(
                cat, "manage_settings", Severity.OK,
                "manage.py uses config.settings", str(manage),
            ))
        elif "tests.settings" in content:
            results.append(CheckResult(
                cat, "manage_settings", Severity.WARNING,
                "manage.py still uses tests.settings", str(manage),
            ))
        else:
            settings_match = re.search(
                r'DJANGO_SETTINGS_MODULE.*["\'](.+?)["\']', content
            )
            if settings_match:
                results.append(CheckResult(
                    cat, "manage_settings", Severity.INFO,
                    f"manage.py uses: {settings_match.group(1)}",
                    str(manage),
                ))

    # config/wsgi.py (may be at root or under src/)
    wsgi_candidates = [
        repo_path / "config" / "wsgi.py",
        repo_path / "src" / "config" / "wsgi.py",
    ]
    wsgi = next((p for p in wsgi_candidates if p.exists()), None)
    if wsgi:
        rel = wsgi.relative_to(repo_path)
        results.append(CheckResult(
            cat, "wsgi", Severity.OK,
            f"{rel} exists", str(wsgi),
        ))
    else:
        results.append(CheckResult(
            cat, "wsgi", Severity.ERROR,
            "config/wsgi.py missing", str(wsgi_candidates[0]),
        ))

    # config/urls.py (may be at root or under src/)
    urls_candidates = [
        repo_path / "config" / "urls.py",
        repo_path / "src" / "config" / "urls.py",
    ]
    urls = next((p for p in urls_candidates if p.exists()), None)
    if urls:
        urls_content = read_file(urls)
        rel = urls.relative_to(repo_path)
        if urls_content and "livez" in urls_content:
            results.append(CheckResult(
                cat, "urls_livez", Severity.OK,
                f"/livez/ route in {rel}", str(urls),
            ))
        elif urls_content:
            results.append(CheckResult(
                cat, "urls_livez", Severity.WARNING,
                f"/livez/ not in {rel}", str(urls),
            ))
    else:
        results.append(CheckResult(
            cat, "urls", Severity.ERROR,
            "config/urls.py missing", str(urls_candidates[0]),
        ))

    return results


# ─────────────────────────────────────────────────────────────────────────────
# ADR-058: Testing infrastructure check
# ─────────────────────────────────────────────────────────────────────────────


def check_testing(repo_path: Path, config: dict) -> list[CheckResult]:
    """Check ADR-058 testing infrastructure compliance."""
    results: list[CheckResult] = []
    cat = "testing"

    # Determine tests directory (tests/ or src/tests/)
    tests_candidates = [repo_path / "tests", repo_path / "src" / "tests"]
    tests_dir = next((p for p in tests_candidates if p.exists()), None)

    if tests_dir is None:
        results.append(CheckResult(
            cat, "tests_dir", Severity.WARNING,
            "No tests/ directory found",
        ))
        return results

    results.append(CheckResult(
        cat, "tests_dir", Severity.OK,
        f"{tests_dir.relative_to(repo_path)} exists",
    ))

    # conftest.py
    conftest = tests_dir / "conftest.py"
    if not conftest.exists():
        results.append(CheckResult(
            cat, "conftest", Severity.WARNING,
            "tests/conftest.py missing",
            str(conftest),
        ))
    else:
        content = read_file(conftest)
        if content and "platform_context.testing" in content:
            results.append(CheckResult(
                cat, "conftest_platform", Severity.OK,
                "conftest.py imports platform_context.testing",
                str(conftest),
            ))
        else:
            results.append(CheckResult(
                cat, "conftest_platform", Severity.WARNING,
                "conftest.py does not import platform_context.testing"
                " (ADR-058)",
                str(conftest),
            ))

    # test_auth.py
    test_auth = tests_dir / "test_auth.py"
    if not test_auth.exists():
        results.append(CheckResult(
            cat, "test_auth", Severity.WARNING,
            "tests/test_auth.py missing — auth/access control tests"
            " required (ADR-058 A2)",
            str(test_auth),
        ))
    else:
        content = read_file(test_auth)
        if content and "assert_login_required" in content:
            results.append(CheckResult(
                cat, "test_auth", Severity.OK,
                "test_auth.py uses assert_login_required",
                str(test_auth),
            ))
        else:
            results.append(CheckResult(
                cat, "test_auth", Severity.WARNING,
                "test_auth.py exists but does not use assert_login_required",
                str(test_auth),
            ))

    # requirements-test.txt
    req_test_candidates = [
        repo_path / "requirements-test.txt",
        repo_path / "requirements" / "test.txt",
        repo_path / "requirements" / "dev.txt",
    ]
    req_test = next((p for p in req_test_candidates if p.exists()), None)
    if req_test is None:
        results.append(CheckResult(
            cat, "requirements_test", Severity.WARNING,
            "No requirements-test.txt found (ADR-058)",
        ))
    else:
        content = read_file(req_test)
        if content and "platform-context" in content:
            results.append(CheckResult(
                cat, "requirements_platform", Severity.OK,
                f"platform-context[testing] in"
                f" {req_test.relative_to(repo_path)}",
                str(req_test),
            ))
        else:
            results.append(CheckResult(
                cat, "requirements_platform", Severity.WARNING,
                f"{req_test.relative_to(repo_path)}"
                " missing platform-context[testing] (ADR-058)",
                str(req_test),
            ))

    # pyproject.toml pytest config
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        content = read_file(pyproject)
        if content and "pytest.ini_options" in content:
            results.append(CheckResult(
                cat, "pytest_config", Severity.OK,
                "pyproject.toml has [tool.pytest.ini_options]",
                str(pyproject),
            ))
        else:
            results.append(CheckResult(
                cat, "pytest_config", Severity.WARNING,
                "pyproject.toml missing [tool.pytest.ini_options]",
                str(pyproject),
            ))

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestration
# ─────────────────────────────────────────────────────────────────────────────


def check_repo(repo_path: Path, repo_name: str = "") -> RepoReport:
    """Run all checks on a repository."""
    if not repo_name:
        repo_name = repo_path.name

    config = REPO_CONFIG.get(repo_name, {
        "type": "django",
        "deployed": True,
        "dockerfile": "Dockerfile",
        "compose": "docker-compose.prod.yml",
    })

    report = RepoReport(repo=repo_name, path=str(repo_path))

    report.results.extend(check_compose(repo_path, config))
    report.results.extend(check_dockerfile(repo_path, config))
    report.results.extend(check_cicd(repo_path, config))
    report.results.extend(check_health_endpoints(repo_path, config))
    report.results.extend(check_deploy_script(repo_path, config))
    report.results.extend(check_django_config(repo_path, config))
    report.results.extend(check_testing(repo_path, config))

    return report


def check_all_repos(base_dir: Path) -> list[RepoReport]:
    """Check all known repos under base directory."""
    reports = []
    for repo_name in REPO_CONFIG:
        repo_path = base_dir / repo_name
        if repo_path.exists():
            reports.append(check_repo(repo_path, repo_name))
        else:
            report = RepoReport(repo=repo_name, path=str(repo_path))
            report.results.append(CheckResult(
                "repo", "exists", Severity.ERROR,
                f"Repository directory not found: {repo_path}",
            ))
            reports.append(report)
    return reports


# ─────────────────────────────────────────────────────────────────────────────
# Output formatting
# ─────────────────────────────────────────────────────────────────────────────

SEVERITY_ICONS = {
    Severity.ERROR: "❌",
    Severity.WARNING: "⚠️ ",
    Severity.INFO: "ℹ️ ",
    Severity.OK: "✅",
    Severity.SKIP: "⏭️ ",
}

SEVERITY_COLORS = {
    Severity.ERROR: "\033[91m",
    Severity.WARNING: "\033[93m",
    Severity.INFO: "\033[94m",
    Severity.OK: "\033[92m",
    Severity.SKIP: "\033[90m",
}
RESET = "\033[0m"


def format_report_text(
    reports: list[RepoReport], use_color: bool = True
) -> str:
    """Format reports as human-readable text."""
    lines: list[str] = []
    total_errors = sum(r.errors for r in reports)
    total_warnings = sum(r.warnings for r in reports)
    total_ok = sum(r.ok_count for r in reports)

    lines.append("=" * 70)
    lines.append("  ADR-022 Repository Consistency Check")
    lines.append("=" * 70)
    lines.append("")

    for report in reports:
        header = f"── {report.repo} "
        header += "─" * (66 - len(header))
        if report.errors:
            header += f" [{report.errors}E]"
        lines.append(header)

        # Group by category
        categories: dict[str, list[CheckResult]] = {}
        for r in report.results:
            categories.setdefault(r.category, []).append(r)

        for cat_name, checks in categories.items():
            for check in checks:
                icon = SEVERITY_ICONS[check.severity]
                if use_color:
                    color = SEVERITY_COLORS[check.severity]
                    line = f"  {icon} {color}[{cat_name}]{RESET} {check.message}"
                else:
                    line = f"  {icon} [{cat_name}] {check.message}"
                if check.file and check.line:
                    short = Path(check.file).name
                    line += f"  ({short}:{check.line})"
                lines.append(line)

        lines.append("")

    # Summary
    lines.append("=" * 70)
    lines.append(f"  Summary: {total_ok} OK, {total_warnings} warnings, "
                 f"{total_errors} errors across {len(reports)} repos")
    lines.append("=" * 70)

    return "\n".join(lines)


def format_report_json(reports: list[RepoReport]) -> str:
    """Format reports as JSON."""
    data = {
        "repos": [
            {
                "name": r.repo,
                "path": r.path,
                "errors": r.errors,
                "warnings": r.warnings,
                "ok": r.ok_count,
                "results": [
                    {
                        "category": c.category,
                        "check": c.check,
                        "severity": c.severity.value,
                        "message": c.message,
                        "file": c.file,
                        "line": c.line,
                    }
                    for c in r.results
                ],
            }
            for r in reports
        ],
        "summary": {
            "total_repos": len(reports),
            "total_errors": sum(r.errors for r in reports),
            "total_warnings": sum(r.warnings for r in reports),
            "total_ok": sum(r.ok_count for r in reports),
        },
    }
    return json.dumps(data, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# MCP integration function (called from orchestrator_mcp)
# ─────────────────────────────────────────────────────────────────────────────


def run_check(
    repo: str = "all",
    repos_dir: str = "/home/dehnert/github",
    output_format: str = "text",
) -> str:
    """
    Entry point for MCP tool integration.

    Args:
        repo: Repository name or 'all'
        repos_dir: Base directory containing all repos
        output_format: 'text' or 'json'

    Returns:
        Formatted report string
    """
    base = Path(repos_dir)
    if repo == "all":
        reports = check_all_repos(base)
    else:
        repo_path = base / repo
        reports = [check_repo(repo_path, repo)]

    if output_format == "json":
        return format_report_json(reports)
    return format_report_text(reports, use_color=False)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ADR-022 Repository Consistency Checker",
    )
    parser.add_argument(
        "repo_path",
        nargs="?",
        help="Path to a single repo (default: check all known repos)",
    )
    parser.add_argument(
        "--repos-dir",
        default=os.environ.get("REPOS_DIR", "/home/dehnert/github"),
        help="Base directory containing repos (default: /home/dehnert/github)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    args = parser.parse_args()

    if args.repo_path:
        repo_path = Path(args.repo_path).resolve()
        reports = [check_repo(repo_path)]
    else:
        reports = check_all_repos(Path(args.repos_dir))

    if args.json:
        print(format_report_json(reports))
    else:
        use_color = not args.no_color and sys.stdout.isatty()
        print(format_report_text(reports, use_color=use_color))

    total_errors = sum(r.errors for r in reports)
    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
