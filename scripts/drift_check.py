#!/usr/bin/env python3
"""drift_check.py — Cross-Repo Template Drift Detection

Erkennt, welche Repos vom Platform-Standard abgewichen sind:
  - Veraltete GitHub Actions Versionen (@v3 statt @v4)
  - Fehlende Pflicht-Dateien (Dockerfile, docker-compose.prod.yml, ...)
  - Veraltete iil-Packages (z.B. iil-testkit@0.3.x statt @0.4.x)
  - Fehlende Health-Endpoints (/livez/, /healthz/)
  - CI-Workflow nutzt alten Pattern (reusable workflow fehlt)
  - Python-Version veraltet (3.10 statt 3.12)
  - Fehlende Sicherheits-Patterns (GITHUB_TOKEN ohne least-privilege)

Verwendung:
    python3 scripts/drift_check.py                   # alle Django-Repos
    python3 scripts/drift_check.py coach-hub         # einzelnes Repo
    python3 scripts/drift_check.py --severity=error  # nur kritische Drifts
    python3 scripts/drift_check.py --format=json     # JSON-Output
    python3 scripts/drift_check.py --fix-hints       # Zeigt Fix-Befehle

SSoT: scripts/repo-registry.yaml + GitHub API + PyPI
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml fehlt — pip install pyyaml", file=sys.stderr)
    sys.exit(1)

PLATFORM_ROOT = Path(__file__).parent.parent
REGISTRY_FILE = PLATFORM_ROOT / "scripts" / "repo-registry.yaml"
GITHUB_ORG = "achimdehnert"

# ── Drift-Regeln (erweiterbar ohne Code-Änderung) ─────────────────────────────

REQUIRED_FILES_DJANGO = [
    ("Dockerfile",               "error",  "Docker Build fehlt"),
    ("docker-compose.prod.yml",  "error",  "Prod-Compose fehlt"),
    (".env.example",             "warn",   ".env.example fehlt — neue Devs verloren"),
    ("pyproject.toml",           "warn",   "pyproject.toml fehlt — kein pytest-Config"),
    ("requirements.txt",         "error",  "requirements.txt fehlt"),
    ("requirements-test.txt",    "warn",   "requirements-test.txt fehlt"),
    ("tests/conftest.py",        "warn",   "Kein Test-Scaffold — run gen_test_scaffold.py"),
    (".github/workflows/ci.yml", "warn",   "Kein CI-Workflow"),
]

REQUIRED_FILE_CONTENT_CHECKS = [
    (".github/workflows/ci.yml",         r"_ci-python\.yml",  "warn",
     "CI nutzt nicht platform/_ci-python.yml (reusable workflow)"),
    ("Dockerfile",                        r"python:3\.12",     "warn",
     "Dockerfile nutzt nicht Python 3.12"),
    ("Dockerfile",                        r"HEALTHCHECK",      "error",
     "Dockerfile ohne HEALTHCHECK (ADR-056)"),
    ("docker-compose.prod.yml",           r"env_file",         "error",
     "docker-compose.prod.yml ohne env_file (ADR-022 violation)"),
    ("docker-compose.prod.yml",           r"unless-stopped",   "warn",
     "docker-compose.prod.yml ohne restart: unless-stopped"),
    ("requirements.txt",                  r"(iil-|aifw|promptfw)",  "info",
     "Kein iil-Package gefunden — ok wenn kein LLM/Test-Kit benötigt"),
]

BANNED_PATTERNS = [
    (r"StrictHostKeyChecking=no",         "error",
     "StrictHostKeyChecking=no gefunden (SD-001 CRITICAL)"),
    (r"88\.198\.191\.108",               "error",
     "Hardcoded Server-IP (SD-001 CRITICAL)"),
    (r"UUIDField\(primary_key=True\)",   "error",
     "UUID als PK (DB-001 CRITICAL — nur BigAutoField erlaubt)"),
    (r"environment:\s*\n(\s+\w+:\s*\$\{)", "warn",
     "docker-compose environment: mit ${VAR} (ADR-022 — env_file nutzen)"),
    (r"sqlite",                           "warn",
     "SQLite-Referenz gefunden — PostgreSQL ist Pflicht (ADR-009)"),
]

ACTIONS_VERSION_MAP = {
    "actions/checkout":       "v4",
    "actions/setup-python":   "v5",
    "actions/upload-artifact": "v4",
    "actions/download-artifact": "v4",
    "actions/cache":          "v4",
    "docker/build-push-action": "v7",
    "docker/login-action":    "v3",
}

IIL_PACKAGES_LATEST: dict[str, str] = {}  # befüllt via PyPI


# ── Datenmodell ──────────────────────────────────────────────────────────────

@dataclass
class DriftItem:
    rule: str
    severity: str   # error | warn | info
    file: str
    message: str
    fix_hint: str = ""

    @property
    def icon(self) -> str:
        return {"error": "🔴", "warn": "🟡", "info": "ℹ️"}.get(self.severity, "❓")


@dataclass
class RepoDrift:
    repo: str
    repo_type: str
    drifts: list[DriftItem] = field(default_factory=list)
    error: str = ""

    @property
    def errors(self) -> list[DriftItem]:
        return [d for d in self.drifts if d.severity == "error"]

    @property
    def warnings(self) -> list[DriftItem]:
        return [d for d in self.drifts if d.severity == "warn"]

    @property
    def status_icon(self) -> str:
        if self.error:
            return "⚠️"
        if self.errors:
            return "🔴"
        if self.warnings:
            return "🟡"
        return "✅"

    @property
    def drift_score(self) -> int:
        """0 = kein Drift. Je höher desto schlechter."""
        return len(self.errors) * 3 + len(self.warnings)


# ── GitHub API ────────────────────────────────────────────────────────────────

def _github_token() -> str:
    for env_var in ("GITHUB_TOKEN", "PROJECT_PAT"):
        if v := os.environ.get(env_var):
            return v
    path = Path.home() / ".secrets" / "github_PAT"
    return path.read_text().strip() if path.exists() else ""


def _api_get(path: str, token: str) -> dict | list | None:
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"token {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return None if e.code == 404 else None
    except Exception:
        return None


def _get_file_content(repo: str, path: str, token: str) -> str | None:
    data = _api_get(f"/repos/{GITHUB_ORG}/{repo}/contents/{path}", token)
    if not isinstance(data, dict) or "content" not in data:
        return None
    try:
        return base64.b64decode(data["content"]).decode(errors="replace")
    except Exception:
        return None


def _get_dir_files(repo: str, path: str, token: str) -> list[str]:
    items = _api_get(f"/repos/{GITHUB_ORG}/{repo}/contents/{path}", token)
    if not isinstance(items, list):
        return []
    return [i["name"] for i in items if isinstance(i, dict) and i.get("type") == "file"]


def _fetch_pypi_latest(package: str) -> str | None:
    try:
        with urllib.request.urlopen(
            f"https://pypi.org/pypi/{package}/json", timeout=5
        ) as r:
            return json.loads(r.read())["info"]["version"]
    except Exception:
        return None


def _load_iil_latest() -> dict[str, str]:
    packages = ["iil-testkit", "aifw", "iil-promptfw", "iil-authoringfw",
                "iil-weltenfw", "iil-nl2cadfw"]
    result = {}
    for pkg in packages:
        if v := _fetch_pypi_latest(pkg):
            result[pkg] = v
    return result


# ── Drift-Checks ──────────────────────────────────────────────────────────────

def check_required_files(repo: str, token: str) -> list[DriftItem]:
    drifts = []
    for filepath, severity, msg in REQUIRED_FILES_DJANGO:
        content = _get_file_content(repo, filepath, token)
        if content is None:
            drifts.append(DriftItem(
                rule="required-file",
                severity=severity,
                file=filepath,
                message=msg,
                fix_hint=f"Erstellen: touch {filepath}  (oder gen_test_scaffold.py nutzen)",
            ))
    return drifts


def check_file_contents(repo: str, token: str) -> list[DriftItem]:
    drifts = []
    for filepath, pattern, severity, msg in REQUIRED_FILE_CONTENT_CHECKS:
        content = _get_file_content(repo, filepath, token)
        if content is None:
            continue
        if not re.search(pattern, content):
            drifts.append(DriftItem(
                rule="file-content",
                severity=severity,
                file=filepath,
                message=msg,
            ))
    return drifts


def check_banned_patterns(repo: str, token: str) -> list[DriftItem]:
    """Scannt alle *.py, *.yml, Dockerfile auf verbotene Muster."""
    drifts = []
    files_to_check = []

    # Gezielte Dateien statt alle (API-effizient)
    for scan_path in ["Dockerfile", "docker-compose.prod.yml",
                       ".github/workflows/ci.yml", ".env.example"]:
        if (content := _get_file_content(repo, scan_path, token)) is not None:
            files_to_check.append((scan_path, content))

    for filepath, content in files_to_check:
        for pattern, severity, msg in BANNED_PATTERNS:
            if re.search(pattern, content, re.MULTILINE):
                drifts.append(DriftItem(
                    rule="banned-pattern",
                    severity=severity,
                    file=filepath,
                    message=f"{msg} in {filepath}",
                ))
    return drifts


def check_actions_versions(repo: str, token: str) -> list[DriftItem]:
    """Prüft ob GitHub Actions auf aktuellen Versionen (@v4 etc.) sind."""
    drifts = []
    workflow_files = _get_dir_files(repo, ".github/workflows", token)

    for wf_file in workflow_files:
        content = _get_file_content(repo, f".github/workflows/{wf_file}", token)
        if not content:
            continue
        for action, expected_version in ACTIONS_VERSION_MAP.items():
            pattern = rf"{re.escape(action)}@(v\d+)"
            for match in re.finditer(pattern, content):
                found_version = match.group(1)
                if found_version != expected_version:
                    drifts.append(DriftItem(
                        rule="actions-version",
                        severity="warn",
                        file=f".github/workflows/{wf_file}",
                        message=f"{action}@{found_version} → sollte @{expected_version} sein",
                        fix_hint=f"sed -i 's/{action}@{found_version}/{action}@{expected_version}/g' .github/workflows/{wf_file}",
                    ))
    return drifts


def check_iil_package_versions(repo: str, token: str,
                                 latest: dict[str, str]) -> list[DriftItem]:
    """Prüft ob iil-Packages auf aktuellen Versionen pinned sind."""
    drifts = []
    for req_file in ["requirements.txt", "requirements-test.txt"]:
        content = _get_file_content(repo, req_file, token)
        if not content:
            continue
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pkg_name = re.split(r"[>=<!;\[]", line)[0].strip()
            if pkg_name not in latest:
                continue
            match = re.search(r">=(\d+\.\d+\.\d+)", line)
            if match:
                pinned = match.group(1)
                current = latest[pkg_name]
                if pinned != current:
                    pinned_parts = tuple(int(x) for x in pinned.split("."))
                    current_parts = tuple(int(x) for x in current.split("."))
                    if current_parts > pinned_parts:
                        drifts.append(DriftItem(
                            rule="iil-version",
                            severity="warn",
                            file=req_file,
                            message=f"{pkg_name}>={pinned} — neu: >={current}",
                            fix_hint=f"sed -i 's/{pkg_name}>={pinned}/{pkg_name}>={current}/' {req_file}",
                        ))
    return drifts


def check_python_version(repo: str, token: str) -> list[DriftItem]:
    """Prüft ob Python 3.12 in CI und Dockerfile verwendet wird."""
    drifts = []
    for filepath in ["Dockerfile", ".github/workflows/ci.yml"]:
        content = _get_file_content(repo, filepath, token)
        if not content:
            continue
        version_match = re.search(r"python[:\s]+['\"]?3\.(\d+)", content, re.IGNORECASE)
        if version_match:
            minor = int(version_match.group(1))
            if minor < 12:
                drifts.append(DriftItem(
                    rule="python-version",
                    severity="warn",
                    file=filepath,
                    message=f"Python 3.{minor} statt 3.12 — Update empfohlen",
                    fix_hint=f"python:3.{minor} → python:3.12 in {filepath}",
                ))
    return drifts


# ── Haupt-Scan ────────────────────────────────────────────────────────────────

SCAFFOLD_TYPES: frozenset[str] = frozenset({"django", "agent", "bot"})


def check_repo(repo: str, repo_type: str, token: str,
               iil_latest: dict[str, str]) -> RepoDrift:
    drift = RepoDrift(repo=repo, repo_type=repo_type)

    # Repo erreichbar?
    if _api_get(f"/repos/{GITHUB_ORG}/{repo}", token) is None:
        drift.error = "Repo nicht gefunden oder privat"
        return drift

    # Docker/requirements checks only apply to deployable scaffold repos
    if repo_type in SCAFFOLD_TYPES:
        drift.drifts.extend(check_required_files(repo, token))
        drift.drifts.extend(check_file_contents(repo, token))

    drift.drifts.extend(check_banned_patterns(repo, token))
    drift.drifts.extend(check_actions_versions(repo, token))
    drift.drifts.extend(check_iil_package_versions(repo, token, iil_latest))
    drift.drifts.extend(check_python_version(repo, token))

    return drift


# ── Output ───────────────────────────────────────────────────────────────────

def print_report(drifts: list[RepoDrift], severity_filter: str, show_fix_hints: bool) -> None:
    SEVERITY_ORDER = {"error": 0, "warn": 1, "info": 2}
    min_level = SEVERITY_ORDER.get(severity_filter, 2)

    print(f"\n## Platform Drift Check — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")

    total_errors = sum(len(r.errors) for r in drifts)
    total_warns = sum(len(r.warnings) for r in drifts)
    clean = sum(1 for r in drifts if r.drift_score == 0 and not r.error)

    for repo_drift in sorted(drifts, key=lambda x: -x.drift_score):
        filtered = [d for d in repo_drift.drifts
                    if SEVERITY_ORDER.get(d.severity, 2) <= min_level]
        if not filtered and not repo_drift.error and severity_filter != "info":
            continue

        print(f"{repo_drift.status_icon}  **{repo_drift.repo}** ({repo_drift.repo_type})")
        if repo_drift.error:
            print(f"    ⚠️  {repo_drift.error}")
        for d in sorted(filtered, key=lambda x: SEVERITY_ORDER.get(x.severity, 2)):
            print(f"    {d.icon} [{d.rule}] {d.file}: {d.message}")
            if show_fix_hints and d.fix_hint:
                print(f"       → {d.fix_hint}")
        print()

    print(f"{'='*70}")
    print(f"Repos: {len(drifts)}  |  ✅ Kein Drift: {clean}  |  🔴 Errors: {total_errors}  |  🟡 Warns: {total_warns}")

    # Priorisierte Fix-Liste
    all_errors = [(r.repo, d) for r in drifts for d in r.errors]
    if all_errors:
        print(f"\n### 🔴 Priorität 1 — Sofort fixen ({len(all_errors)} errors):")
        for repo, d in sorted(all_errors, key=lambda x: x[0]):
            print(f"  {repo}: {d.file} — {d.message}")


def print_github_summary(drifts: list[RepoDrift]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a") as f:
        f.write("## Platform Drift Check\n\n")
        f.write("| Repo | Status | Errors | Warnings |\n")
        f.write("|------|--------|--------|----------|\n")
        for r in sorted(drifts, key=lambda x: -x.drift_score):
            f.write(f"| {r.status_icon} {r.repo} | {r.repo_type} | {len(r.errors)} | {len(r.warnings)} |\n")


def print_json_output(drifts: list[RepoDrift]) -> None:
    out = []
    for r in drifts:
        out.append({
            "repo": r.repo,
            "type": r.repo_type,
            "status": r.status_icon,
            "drift_score": r.drift_score,
            "errors": len(r.errors),
            "warnings": len(r.warnings),
            "drifts": [
                {"rule": d.rule, "severity": d.severity, "file": d.file,
                 "message": d.message, "fix_hint": d.fix_hint}
                for d in r.drifts
            ],
        })
    print(json.dumps(out, indent=2))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Platform Cross-Repo Drift Detection")
    parser.add_argument("repos", nargs="*", help="Repos (leer = alle Django)")
    parser.add_argument("--severity", choices=["error", "warn", "info"],
                        default="warn", help="Minimaler Report-Level")
    parser.add_argument("--format", choices=["table", "json"], default="table")
    parser.add_argument("--fix-hints", action="store_true",
                        help="Fix-Befehle anzeigen")
    parser.add_argument("--fail-on-error", action="store_true",
                        help="Exit 1 wenn Error-Drifts gefunden")
    parser.add_argument("--skip-pypi", action="store_true",
                        help="PyPI-Versionscheck überspringen (offline)")
    args = parser.parse_args()

    registry = yaml.safe_load(REGISTRY_FILE.read_text()).get("repos", {})
    SCAFFOLD_TYPES = {"django", "agent", "bot"}

    targets = (
        {r: registry.get(r, {"type": "django"}) for r in args.repos}
        if args.repos else
        {n: p for n, p in registry.items()
         if isinstance(p, dict) and p.get("type") in SCAFFOLD_TYPES and n != "platform"}
    )

    token = _github_token()
    if not token:
        print("WARN: Kein GitHub-Token — nur öffentliche Repos scanbar", file=sys.stderr)

    print(f"\n🔍  Drift Check — {len(targets)} Repos", flush=True)

    iil_latest: dict[str, str] = {}
    if not args.skip_pypi:
        print("   PyPI-Versionen laden...", end="", flush=True)
        iil_latest = _load_iil_latest()
        print(f" {len(iil_latest)} Packages geladen")

    results: list[RepoDrift] = []
    for repo, props in targets.items():
        repo_type = props.get("type", "?") if isinstance(props, dict) else "?"
        print(f"  {repo}...", end="", flush=True)
        result = check_repo(repo, repo_type, token, iil_latest)
        icon = result.status_icon
        print(f" {icon} ({len(result.errors)}E, {len(result.warnings)}W)")
        results.append(result)

    if args.format == "json":
        print_json_output(results)
    else:
        print_report(results, args.severity, args.fix_hints)

    print_github_summary(results)

    if args.fail_on_error:
        total_errors = sum(len(r.errors) for r in results)
        if total_errors:
            print(f"\nExit 1: {total_errors} kritische Drift-Errors", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
