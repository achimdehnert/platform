#!/usr/bin/env python3
"""
Hardcode Scanner — findet hardcodierte Werte über alle Platform-Repos.

Kategorien:
  IP       — Server-IPs (Prod, Dev)
  PORT     — Hardcodierte Ports in Code (nicht in compose/config)
  SECRET   — Secrets/Passwörter direkt im Code
  URL      — Hardcodierte URLs (nicht via settings/env)
  PATH     — Absolute Pfade (/opt/, /home/) in Code
  DOMAIN   — Hardcodierte Domains
  ENUM     — Hardcodierte Werte in Python Enum-Klassen

Ausführen:
  python3 scripts/hardcode_scanner.py                    # alle Repos (auto-discovery)
  python3 scripts/hardcode_scanner.py --repo dev-hub     # einzelnes Repo
  python3 scripts/hardcode_scanner.py --severity high    # nur kritische
  python3 scripts/hardcode_scanner.py --format json      # JSON-Output
  python3 scripts/hardcode_scanner.py --list-repos       # zeigt gefundene Repos

Noqa-Support:
  Zeile mit  # noqa: hardcode  → wird vom Scanner ignoriert
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal

# =============================================================================
# Konfiguration
# =============================================================================

BASE_DIR = Path(__file__).parent.parent.parent  # /home/deploy/projects/

# Verzeichnisse die KEIN Repo sind (im BASE_DIR vorhanden aber ignorieren)
_NON_REPO_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "_archive",
    "vendor",
}


def discover_repos(base_dir: Path) -> list[str]:
    """Findet alle Git-Repos in base_dir automatisch — keine hardcodierte Liste."""
    repos = []
    if not base_dir.exists():
        return repos
    for entry in sorted(base_dir.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name in _NON_REPO_DIRS or entry.name.startswith("."):
            continue
        if (entry / ".git").exists():
            repos.append(entry.name)
    return repos


# Dateitypen die gescannt werden
SCAN_EXTENSIONS = {
    ".py",
    ".yml",
    ".yaml",
    ".toml",
    ".conf",
    ".sh",
    ".html",
    ".js",
    ".ts",
}

# Verzeichnisse die ignoriert werden
IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    "migrations",  # Django migrations — oft legitime Werte
    "_archive",
    "vendor",
}

# Dateien die ignoriert werden
IGNORE_FILES = {
    "poetry.lock",
    "package-lock.json",
    "yarn.lock",
    "*.min.js",
    "*.min.css",
}

Severity = Literal["critical", "high", "medium", "low"]

NOQA_MARKER = "noqa: hardcode"


@dataclass
class Finding:
    repo: str
    file: str
    line: int
    category: str
    severity: Severity
    pattern: str
    match: str
    context: str
    suggestion: str


# =============================================================================
# Pattern-Definitionen
# =============================================================================

PATTERNS: list[dict] = [
    # ── IP-Adressen ──────────────────────────────────────────────────────────
    {
        "category": "IP",
        "severity": "critical",
        "pattern": r"88\.198\.191\.108",
        "description": "Prod-Server IP hardcodiert",
        "suggestion": "→ DEPLOY_HOST env var oder settings.PROD_HOST",
        "exclude_files": {"adr-review-checklist.md", "ADR-021"},
        "exclude_dirs": {"docs/adr", "docs/templates"},
    },
    {
        "category": "IP",
        "severity": "high",
        "pattern": r"46\.225\.113\.1(?!\d)",
        "description": "Dev-Server IP hardcodiert",
        "suggestion": "→ DEPLOY_HOST env var",
        "exclude_dirs": {"docs/adr", "docs/templates"},
    },
    {
        "category": "IP",
        "severity": "medium",
        "pattern": r"127\.0\.0\.1:\d{4}",
        "description": "Localhost mit Port hardcodiert",
        "suggestion": "→ settings.INTERNAL_HOST oder env var",
        "exclude_files": {"docker-compose", "conftest", "test_"},
    },
    # ── Ports ─────────────────────────────────────────────────────────────────
    {
        "category": "PORT",
        "severity": "high",
        "pattern": r"['\"](?:http|https)://(?:localhost|127\.0\.0\.1):(\d{4,5})['\"]",
        "description": "Hardcodierte localhost-URL mit Port",
        "suggestion": "→ settings.BASE_URL oder env var",
        "exclude_files": {"test_", "conftest", "docker-compose"},
    },
    {
        "category": "PORT",
        "severity": "medium",
        "pattern": r"port\s*=\s*['\"]?(?!80(?!\d)|443(?!\d))\d{4,5}['\"]?",
        "description": "Hardcodierter Port-Wert",
        "suggestion": "→ config('PORT', cast=int) oder env var",
        "exclude_files": {"docker-compose", "compose", ".conf"},
        "exclude_dirs": {"docs"},
    },
    # ── Secrets & Credentials ─────────────────────────────────────────────────
    {
        "category": "SECRET",
        "severity": "critical",
        "pattern": r"(?:secret_key|SECRET_KEY)\s*=\s*['\"][^'\"\$\{]{8,}['\"]",
        "description": "SECRET_KEY hardcodiert",
        "suggestion": "→ config('SECRET_KEY') via python-decouple",
        "exclude_patterns": ["insecure-dev", "change-in-prod", "test", "example"],
    },
    {
        "category": "SECRET",
        "severity": "critical",
        "pattern": r"(?:password|PASSWORD|passwd)\s*=\s*['\"][^'\"\$\{]{3,}['\"]",
        "description": "Passwort hardcodiert",
        "suggestion": "→ config('DB_PASSWORD') oder env var",
        "exclude_patterns": [
            "password1",
            "IAmSensitive",
            "tiger",
            "example",
            "placeholder",
            "your_",
        ],
        "exclude_dirs": {".venv", "venv", "node_modules"},
        "exclude_files": {"test_", "conftest"},
    },
    {
        "category": "SECRET",
        "severity": "critical",
        "pattern": r"(?:api_key|API_KEY|apikey)\s*=\s*['\"][A-Za-z0-9_\-]{16,}['\"]",
        "description": "API-Key hardcodiert",
        "suggestion": "→ config('API_KEY') via python-decouple",
        "exclude_patterns": ["your_api_key", "example", "placeholder"],
    },
    {
        "category": "SECRET",
        "severity": "high",
        "pattern": r"ghp_[A-Za-z0-9]{36}",
        "description": "GitHub Personal Access Token im Code",
        "suggestion": "→ GitHub Secret + env var",
    },
    {
        "category": "SECRET",
        "severity": "high",
        "pattern": r"(?:token|TOKEN)\s*=\s*['\"][A-Za-z0-9_\-\.]{20,}['\"]",
        "description": "Token hardcodiert",
        "suggestion": "→ config('TOKEN') via python-decouple",
        "exclude_patterns": ["your_token", "example", "placeholder", "csrf", "AH6AG"],
        "exclude_files": {"test_", "conftest"},
    },
    # ── URLs ──────────────────────────────────────────────────────────────────
    {
        "category": "URL",
        "severity": "high",
        "pattern": r"['\"]https?://(?:devhub|nl2cad|trading-hub|iil\.pet)[^'\"]*['\"]",
        "description": "Produktions-URL hardcodiert",
        "suggestion": "→ settings.BASE_URL oder ALLOWED_HOSTS",
        "exclude_dirs": {"docs", ".windsurf"},
        "exclude_files": {"docker-compose", "nginx", ".conf", "ADR-"},
    },
    {
        "category": "URL",
        "severity": "medium",
        "pattern": r"['\"]https://github\.com/achimdehnert/[^'\"]+['\"]",
        "description": "GitHub-Repo-URL hardcodiert",
        "suggestion": "→ settings.GITHUB_REPO oder env var",
        "exclude_dirs": {"docs", ".windsurf", "templates"},
        "exclude_files": {"README", "ADR-", "seed_"},
    },
    # ── Absolute Pfade ────────────────────────────────────────────────────────
    {
        "category": "PATH",
        "severity": "high",
        "pattern": r"['\"/]/opt/[a-z][a-z0-9\-]+/",
        "description": "Absoluter /opt/-Pfad hardcodiert",
        "suggestion": "→ DEPLOY_PATH env var oder settings.DEPLOY_BASE",
        "exclude_dirs": {"docs/adr", "docs/templates"},
        "exclude_files": {"docker-compose", "nginx", ".conf", "ADR-"},
    },
    {
        "category": "PATH",
        "severity": "medium",
        "pattern": r"['\"/]/home/(?:deploy|github-runner)/[^'\"]{5,}",
        "description": "Absoluter /home/-Pfad hardcodiert",
        "suggestion": "→ HOME env var oder relative Pfade",
        "exclude_dirs": {"docs", ".windsurf"},
        "exclude_files": {"docker-compose", ".conf", "ADR-", "register-runner"},
    },
    # ── Domains ───────────────────────────────────────────────────────────────
    {
        "category": "DOMAIN",
        "severity": "medium",
        "pattern": r"(?:ALLOWED_HOSTS|CORS_ALLOWED_ORIGINS)\s*=\s*\[.*?['\"](?!localhost)[a-z0-9\.\-]+\.[a-z]{2,}['\"]",
        "description": "Domain in ALLOWED_HOSTS hardcodiert",
        "suggestion": "→ config('ALLOWED_HOSTS', cast=Csv())",
        "exclude_files": {"settings_test", "test_"},
    },
    {
        "category": "DOMAIN",
        "severity": "low",
        "pattern": r"['\"]achimdehnert['\"]",
        "description": "GitHub-Username hardcodiert",
        "suggestion": "→ settings.GITHUB_ORG oder env var GITHUB_ORG",
        "exclude_dirs": {"docs", ".windsurf", "scripts"},
        "exclude_files": {"ADR-", "README", "seed_", "populate_"},
    },
    # ── Enum-Werte ────────────────────────────────────────────────────────────
    # Erkennt hardcodierte IPs, Ports, URLs, Secrets als Enum-Member-Werte
    {
        "category": "ENUM",
        "severity": "critical",
        "pattern": r"(?:^|\s)[A-Z_]+\s*=\s*['\"](?:88\.198\.191\.108|46\.225\.113\.1)['\"]\s*(?:#.*)?$",
        "description": "Server-IP als Enum-Wert hardcodiert",
        "suggestion": "→ Enum-Wert aus env var beziehen oder settings.PROD_HOST",
        "context": "enum",
    },
    {
        "category": "ENUM",
        "severity": "critical",
        "pattern": r"(?:^|\s)[A-Z_]+\s*=\s*['\"](?:sk-ant-api|AIzaSy|gsk_)[A-Za-z0-9_\-]{10,}['\"]\s*(?:#.*)?$",
        "description": "API-Key als Enum-Wert hardcodiert",
        "suggestion": "→ Enum-Wert niemals Credentials enthalten — env var verwenden",
        "context": "enum",
    },
    {
        "category": "ENUM",
        "severity": "high",
        "pattern": r"(?:^|\s)[A-Z_]+\s*=\s*['\"]https?://(?:localhost|127\.0\.0\.1|88\.198|46\.225):[0-9]{4,5}[^'\"]*['\"]\s*(?:#.*)?$",
        "description": "Hardcodierte URL/IP mit Port als Enum-Wert",
        "suggestion": "→ Enum-Wert aus settings.BASE_URL oder env var",
        "context": "enum",
    },
    {
        "category": "ENUM",
        "severity": "high",
        "pattern": r"(?:^|\s)[A-Z_]+\s*=\s*['\"]['\"]\s*#\s*TODO.*hardcod",
        "description": "Leerer Enum-Wert mit Hardcoding-TODO",
        "suggestion": "→ env var oder settings-Wert verwenden",
        "context": "enum",
    },
    {
        "category": "ENUM",
        "severity": "medium",
        "pattern": r"(?:^|\s)[A-Z_]+\s*=\s*['\"][0-9]{4,5}['\"]\s*(?:#.*)?$",
        "description": "Numerischer Port/ID als Enum-Wert hardcodiert",
        "suggestion": "→ Enum-Wert aus config('PORT', cast=int) oder settings",
        "context": "enum",
        "exclude_patterns": ["test", "example", "sample", "dummy", "fake"],
        "exclude_files": {"test_", "conftest", "migrations"},
    },
]


# =============================================================================
# Scanner
# =============================================================================


def should_skip_file(path: Path, pattern_cfg: dict) -> bool:
    """Prüft ob eine Datei für dieses Pattern übersprungen werden soll."""
    name = path.name
    path_str = str(path)

    for excl_dir in pattern_cfg.get("exclude_dirs", set()):
        if excl_dir in path_str:
            return True

    for excl_file in pattern_cfg.get("exclude_files", set()):
        if excl_file in name:
            return True

    return False


def _is_inside_enum(lines: list[str], line_idx: int) -> bool:
    """Heuristik: prüft ob die Zeile innerhalb einer Python Enum-Klasse liegt."""
    # Rückwärts suchen nach 'class Foo(... Enum ...)'
    for i in range(line_idx - 1, max(line_idx - 60, -1), -1):
        stripped = lines[i].strip()
        # Einrückungstiefe der aktuellen Zeile vs. class-Zeile
        if re.match(r"^class\s+\w+\s*\(", stripped):
            if re.search(
                r"\bEnum\b|\bIntEnum\b|\bStrEnum\b|\bTextChoices\b|\bIntegerChoices\b",
                stripped,
            ):
                return True
            return False
    return False


def scan_file(repo: str, file_path: Path, repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, PermissionError):
        return findings

    lines = content.splitlines()
    rel_path = str(file_path.relative_to(repo_root))

    for pattern_cfg in PATTERNS:
        if should_skip_file(file_path, pattern_cfg):
            continue

        requires_enum_context = pattern_cfg.get("context") == "enum"
        regex = re.compile(pattern_cfg["pattern"], re.IGNORECASE | re.MULTILINE)

        for i, line in enumerate(lines, 1):
            # Scanner-noqa: Zeile mit NOQA_MARKER explizit ignorieren
            if NOQA_MARKER in line:
                continue

            # Kommentare und Docstrings überspringen (vereinfacht)
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue

            # Enum-Context-Check: nur matchen wenn innerhalb einer Enum-Klasse
            if requires_enum_context and not _is_inside_enum(lines, i - 1):
                continue

            match = regex.search(line)
            if not match:
                continue

            matched_text = match.group(0)

            # Exclude-Patterns prüfen
            exclude_ok = False
            for excl in pattern_cfg.get("exclude_patterns", []):
                if excl.lower() in matched_text.lower() or excl.lower() in line.lower():
                    exclude_ok = True
                    break
            if exclude_ok:
                continue

            findings.append(
                Finding(
                    repo=repo,
                    file=rel_path,
                    line=i,
                    category=pattern_cfg["category"],
                    severity=pattern_cfg["severity"],
                    pattern=pattern_cfg["description"],
                    match=matched_text[:80],
                    context=line.strip()[:120],
                    suggestion=pattern_cfg["suggestion"],
                )
            )

    return findings


def scan_repo(repo: str, base_dir: Path) -> list[Finding]:
    repo_root = base_dir / repo
    if not repo_root.exists():
        return []

    findings: list[Finding] = []

    for file_path in repo_root.rglob("*"):
        if not file_path.is_file():
            continue

        # Ignorierte Verzeichnisse (exakter Name)
        if any(part in IGNORE_DIRS for part in file_path.parts):
            continue

        # Ignorierte Verzeichnisse (Suffix-Pattern: *-ci-test, *-venv, site-packages)
        if any(
            part == "site-packages"
            or part.endswith("-ci-test")
            or part.endswith("-venv")
            or part.endswith(".egg-info")
            for part in file_path.parts
        ):
            continue

        # Nur relevante Dateitypen
        if file_path.suffix not in SCAN_EXTENSIONS:
            continue

        findings.extend(scan_file(repo, file_path, repo_root))

    return findings


# =============================================================================
# Report
# =============================================================================

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
SEVERITY_COLORS = {
    "critical": "\033[91m",  # rot
    "high": "\033[93m",  # gelb
    "medium": "\033[94m",  # blau
    "low": "\033[37m",  # grau
}
RESET = "\033[0m"


def print_report(findings: list[Finding], use_color: bool = True) -> None:
    from datetime import date

    sev_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    cat_counts: dict[str, int] = {}
    repo_counts: dict[str, int] = {}

    for f in findings:
        sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1
        cat_counts[f.category] = cat_counts.get(f.category, 0) + 1
        repo_counts[f.repo] = repo_counts.get(f.repo, 0) + 1

    print(f"\n{'=' * 72}")
    print(f"HARDCODE SCANNER REPORT — {date.today()}")
    print(f"{'=' * 72}")
    print(f"  Total findings : {len(findings)}")
    print(f"  Critical       : {sev_counts.get('critical', 0)}")
    print(f"  High           : {sev_counts.get('high', 0)}")
    print(f"  Medium         : {sev_counts.get('medium', 0)}")
    print(f"  Low            : {sev_counts.get('low', 0)}")
    print()

    if repo_counts:
        print("── Per Repo ─────────────────────────────────────────────────────────")
        for repo, count in sorted(repo_counts.items(), key=lambda x: -x[1]):
            print(f"  {repo:20} {count:3} findings")
        print()

    if cat_counts:
        print("── Per Kategorie ────────────────────────────────────────────────────")
        for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
            print(f"  {cat:10} {count:3} findings")
        print()

    print("── Findings (sortiert nach Severity) ───────────────────────────────")
    sorted_findings = sorted(
        findings, key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.repo, f.file)
    )

    current_repo = None
    for f in sorted_findings:
        if f.repo != current_repo:
            print(f"\n  [{f.repo}]")
            current_repo = f.repo

        color = SEVERITY_COLORS.get(f.severity, "") if use_color else ""
        reset = RESET if use_color else ""
        print(
            f"  {color}[{f.severity.upper():8}]{reset} {f.category:8} {f.file}:{f.line}"
        )
        print(f"             Pattern : {f.pattern}")
        print(f"             Match   : {f.match}")
        print(f"             Fix     : {f.suggestion}")

    print(f"\n{'=' * 72}")
    if sev_counts.get("critical", 0) > 0:
        print("⚠  CRITICAL findings gefunden — sofort beheben!")
    elif sev_counts.get("high", 0) > 0:
        print("!  HIGH findings gefunden — im nächsten Sprint beheben.")
    else:
        print("✓  Keine kritischen Hardcoding-Probleme gefunden.")
    print(f"{'=' * 72}\n")


def print_json(findings: list[Finding]) -> None:
    print(json.dumps([asdict(f) for f in findings], indent=2))


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hardcode Scanner — findet hardcodierte Werte über alle Platform-Repos."
    )
    parser.add_argument("--repo", help="Nur dieses Repo scannen (z.B. dev-hub)")
    parser.add_argument(
        "--severity",
        choices=["critical", "high", "medium", "low"],
        help="Nur Findings ab dieser Severity anzeigen",
    )
    parser.add_argument(
        "--category",
        choices=["IP", "PORT", "SECRET", "URL", "PATH", "DOMAIN", "ENUM"],
        help="Nur diese Kategorie anzeigen",
    )
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument(
        "--base-dir",
        default=str(BASE_DIR),
        help=f"Basis-Verzeichnis der Repos (default: {BASE_DIR})",
    )
    parser.add_argument(
        "--list-repos",
        action="store_true",
        help="Zeigt alle auto-entdeckten Repos und beendet sich",
    )
    args = parser.parse_args()

    if args.list_repos:
        base_dir = Path(args.base_dir)
        found = discover_repos(base_dir)
        print(f"Auto-discovered {len(found)} repos in {base_dir}:")
        for r in found:
            print(f"  - {r}")
        return 0

    base_dir = Path(args.base_dir)
    repos = [args.repo] if args.repo else discover_repos(base_dir)

    all_findings: list[Finding] = []
    for repo in repos:
        repo_findings = scan_repo(repo, base_dir)
        all_findings.extend(repo_findings)

    # Filter
    if args.severity:
        min_sev = SEVERITY_ORDER[args.severity]
        all_findings = [
            f for f in all_findings if SEVERITY_ORDER.get(f.severity, 9) <= min_sev
        ]
    if args.category:
        all_findings = [f for f in all_findings if f.category == args.category]

    if args.format == "json":
        print_json(all_findings)
    else:
        print_report(all_findings, use_color=not args.no_color)

    # Exit-Code: 1 wenn critical/high gefunden
    critical_high = sum(1 for f in all_findings if f.severity in ("critical", "high"))
    return 1 if critical_high > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
