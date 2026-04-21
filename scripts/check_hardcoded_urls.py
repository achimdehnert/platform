#!/usr/bin/env python3
"""check_hardcoded_urls.py — Platform-weiter Hardcoding-Guard.

Prüft ALLE Repos auf hardcodierte URL-Pfade in Templates und Views.

Verwendung:
    # Einzelnes Repo:
    python scripts/check_hardcoded_urls.py /path/to/repo

    # Alle Repos unter ~/github (inkl. non-Django):
    python scripts/check_hardcoded_urls.py --all

    # Kompakte Zusammenfassung (kein Datei-Detail):
    python scripts/check_hardcoded_urls.py --all --summary

    # Nur Bericht, kein Exit-Code 1 bei Violations (für Audits):
    python scripts/check_hardcoded_urls.py --all --report-only

    # Als pytest-Fixture: conftest.py in jedem Repo:
    #   from platform_scripts import hardcoded_url_tests  # (siehe --pytest-snippet)

Exit-Codes:
    0  Keine Violations
    1  Violations gefunden (für CI)
    2  Fehler (Pfad nicht gefunden etc.)

Abgedeckte Violation-Klassen:
    TEMPLATE-01  href="/..."        ohne {% url %}
    TEMPLATE-02  action="/..."      ohne {% url %}  (Formulare)
    TEMPLATE-03  src="/..."         ohne {% static %}  (eigene Assets)
    PYTHON-01    redirect("/...")   statt reverse()
    PYTHON-02    HttpResponseRedirect("/...") mit literal Pfad
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ── Konfiguration ─────────────────────────────────────────────────────────────

GITHUB_ROOT = Path.home() / "github"

# Pfad-Fragmente, die grundsätzlich übersprungen werden
_SKIP_DIRS = {
    ".venv", "node_modules", "__pycache__", "site-packages",
    ".git", "dist", "build", "htmlcov", ".mypy_cache",
}

# Zeilen-Inhalte, die als korrekt gelten (Whitelist)
_ALLOWED_TOKENS = [
    "/admin/",       # Django-Admin hat keine namespaced URL
    "https://",      # externe Links
    "http://",       # z.B. org.website
    "{{ ",           # Template-Variable als URL-Wert
    "{% url",        # korrekte Verwendung
    "{% static",     # korrekte Verwendung für Assets
]

# Repos ohne Django-Templates / reine Python-Libraries (kein HTML zu prüfen)
_SKIP_REPOS = {
    "platform",         # Infrastruktur-Repo, keine App-Templates
    "infra-deploy",     # nur Shell/Ansible
    "iil-reflex",       # Python-Library
    "promptfw",         # Python-Library
    "authoringfw",      # Python-Library
    "aifw",             # Python-Library
    "testkit",          # Test-Utilities
    "outlinefw",        # Python-Library
    "weltenfw",         # Python-Library
    "illustration-fw",  # Python-Library
    "researchfw",       # Python-Library
    "learnfw",          # Python-Library
    "lastwar-bot",      # Discord-Bot, kein Django
    "odoo-hub",         # Odoo — anderes Template-System
    "mcp-hub",          # MCP-Server, keine Django-Templates
    "nl2cad",           # CLI-Tool
}

# ── Regel-Definitionen ────────────────────────────────────────────────────────

@dataclass
class Rule:
    rule_id: str
    pattern: re.Pattern
    description: str
    file_types: tuple[str, ...]  # z.B. (".html",) oder (".py",)


RULES: list[Rule] = [
    Rule("TEMPLATE-01", re.compile(r'href="(/[a-zA-Z0-9_-])'),    "href mit hartkodiertem Pfad → {% url 'app:name' %}",   (".html",)),
    Rule("TEMPLATE-02", re.compile(r'action="(/[a-zA-Z0-9_-])'),  "action mit hartkodiertem Pfad → {% url 'app:name' %}",  (".html",)),
    Rule("TEMPLATE-03", re.compile(r'src="(/[a-zA-Z0-9_-])'),     "src mit hartkodiertem Pfad → {% static 'path' %}",      (".html",)),
    Rule("PYTHON-01",   re.compile(r'redirect\(\s*["\']\/[a-zA-Z]'),    "redirect() mit hartkodiertem Pfad → reverse()",   (".py",)),
    Rule("PYTHON-02",   re.compile(r'HttpResponseRedirect\(\s*["\']\/'), "HttpResponseRedirect() mit hartkodiertem Pfad",    (".py",)),
]


# ── Datenmodelle ──────────────────────────────────────────────────────────────

@dataclass
class Violation:
    rule_id: str
    description: str
    file_path: Path
    lineno: int
    line: str


@dataclass
class RepoResult:
    repo_path: Path
    violations: list[Violation] = field(default_factory=list)

    @property
    def name(self) -> str:
        # Wenn Repo-Root "src" heißt, Eltern-Verzeichnis als Name verwenden
        if self.repo_path.name == "src":
            return self.repo_path.parent.name
        return self.repo_path.name

    @property
    def ok(self) -> bool:
        return len(self.violations) == 0


# ── Scanner ───────────────────────────────────────────────────────────────────

def _should_skip(path: Path) -> bool:
    return any(part in _SKIP_DIRS for part in path.parts)


def _is_allowed(line: str) -> bool:
    return any(tok in line for tok in _ALLOWED_TOKENS)


def _find_repo_root(path: Path) -> Path | None:
    """Findet Repo-Root anhand von manage.py oder pyproject.toml."""
    for candidate in [path, path.parent, path.parent.parent]:
        if (candidate / "manage.py").exists() or (candidate / "pyproject.toml").exists():
            return candidate
    return None


def scan_repo(repo_path: Path) -> RepoResult:
    result = RepoResult(repo_path=repo_path)

    # Alle zu prüfenden Dateien sammeln
    files: list[Path] = []
    for pattern in ["**/*.html", "**/*.py"]:
        for f in repo_path.rglob(pattern.split("/")[-1]):
            if _should_skip(f):
                continue
            if "migrations" in f.parts:
                continue
            if f.name.startswith("test_") or f.name == "conftest.py":
                continue
            files.append(f)

    applicable_rules = {
        suffix: [r for r in RULES if suffix in r.file_types]
        for suffix in (".html", ".py")
    }

    for fpath in files:
        rules = applicable_rules.get(fpath.suffix, [])
        if not rules:
            continue
        try:
            lines = fpath.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("{#"):
                continue
            if _is_allowed(line):
                continue
            for rule in rules:
                if rule.pattern.search(line):
                    result.violations.append(Violation(
                        rule_id=rule.rule_id,
                        description=rule.description,
                        file_path=fpath,
                        lineno=lineno,
                        line=stripped,
                    ))

    return result


def find_all_repos(root: Path) -> list[Path]:
    """Findet alle Repos mit HTML-Dateien — unabhängig vom Framework.

    Strategie (Priorität):
      1. manage.py im Root          → Django-Standard
      2. manage.py in src/          → Django mit src-Layout
      3. ≥1 .html-Datei im Repo     → beliebiges Framework
    """
    repos: list[Path] = []
    for candidate in sorted(root.iterdir()):
        if not candidate.is_dir():
            continue
        if candidate.name.startswith(".") or candidate.name.endswith(".code-workspace"):
            continue
        if candidate.name in _SKIP_REPOS:
            continue

        # Django mit Standard-Layout
        if (candidate / "manage.py").exists():
            repos.append(candidate)
            continue

        # Django mit src/-Layout
        if (candidate / "src" / "manage.py").exists():
            repos.append(candidate)   # Repo-Root, nicht src/ — für korrekten Namen
            continue

        # Nicht-Django: prüfe ob .html-Dateien vorhanden
        html_count = sum(
            1 for _ in candidate.rglob("*.html")
            if not _should_skip(_)
        )
        if html_count > 0:
            repos.append(candidate)

    return repos


def _resolve_scan_root(repo_path: Path) -> Path:
    """Gibt den tatsächlichen Scan-Einstiegspunkt zurück (ggf. src/)."""
    if (repo_path / "src" / "manage.py").exists():
        return repo_path   # scan gesamtes Repo inkl. src/
    return repo_path


# ── Ausgabe ───────────────────────────────────────────────────────────────────

RESET = "\033[0m"
RED   = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BOLD  = "\033[1m"
DIM   = "\033[2m"


def _color(text: str, code: str) -> str:
    return f"{code}{text}{RESET}" if sys.stdout.isatty() else text


def print_report(results: list[RepoResult], verbose: bool = False, summary_only: bool = False) -> int:
    total_violations = sum(len(r.violations) for r in results)
    total_repos = len(results)
    repos_with_violations = [r for r in results if not r.ok]
    repos_clean = [r for r in results if r.ok]

    print(f"\n{_color('HARDCODING-GUARD — Platform Scan', BOLD)}")
    print(f"Repos geprüft: {total_repos}  |  "
          f"Violations: {_color(str(total_violations), RED if total_violations else GREEN)}  |  "
          f"Sauber: {_color(str(len(repos_clean)), GREEN)}/{total_repos}")
    print("─" * 70)

    # Sortiert nach Anzahl Violations (absteigend)
    for repo_result in sorted(repos_with_violations, key=lambda r: -len(r.violations)):
        print(f"\n{_color('✗ ' + repo_result.name, RED + BOLD)}  "
              f"{_color(f'({len(repo_result.violations)} Violations)', RED)}")

        if summary_only:
            # Nur Dateinamen + Anzahl, keine Zeilen-Details
            by_file: dict[Path, list[Violation]] = {}
            for v in repo_result.violations:
                by_file.setdefault(v.file_path, []).append(v)
            for fpath, viols in sorted(by_file.items()):
                try:
                    rel = fpath.relative_to(repo_result.repo_path)
                except ValueError:
                    rel = fpath
                rule_ids = ", ".join(sorted({v.rule_id for v in viols}))
                print(f"  {_color(str(rel), YELLOW)}  {_color(f'[{rule_ids}] ×{len(viols)}', DIM)}")
            continue

        # Gruppiere nach Datei (Detail-Ausgabe)
        by_file = {}
        for v in repo_result.violations:
            by_file.setdefault(v.file_path, []).append(v)

        for fpath, viols in sorted(by_file.items()):
            try:
                rel = fpath.relative_to(repo_result.repo_path)
            except ValueError:
                rel = fpath
            print(f"  {_color(str(rel), YELLOW)}")
            shown = viols if verbose else viols[:5]
            for v in shown:
                print(f"    {_color(f'[{v.rule_id}]', BOLD)} Zeile {v.lineno}: {v.line[:100]}")
            if not verbose and len(viols) > 5:
                print(f"    {_color(f'... +{len(viols)-5} weitere', DIM)}")

    # Saubere Repos auflisten
    if repos_clean:
        print(f"\n{_color('✓ Sauber:', GREEN + BOLD)} " +
              ", ".join(_color(r.name, GREEN) for r in sorted(repos_clean, key=lambda r: r.name)))

    print("\n" + "─" * 70)
    if total_violations == 0:
        print(_color("✓ Keine Violations gefunden.", GREEN + BOLD))
    else:
        rule_counts: dict[str, int] = {}
        for r in results:
            for v in r.violations:
                rule_counts[v.rule_id] = rule_counts.get(v.rule_id, 0) + 1
        print(_color("Violations nach Typ:", BOLD))
        for rule_id, count in sorted(rule_counts.items()):
            rule_desc = next((r.description for r in RULES if r.rule_id == rule_id), "")
            print(f"  {_color(rule_id, YELLOW)}: {count:4d}  — {rule_desc}")

        # Top-Offenders
        print(f"\n{_color('Top-Offenders:', BOLD)}")
        for r in sorted(repos_with_violations, key=lambda x: -len(x.violations))[:10]:
            bar = "█" * min(len(r.violations) // 5, 30)
            print(f"  {r.name:<25} {len(r.violations):4d}  {_color(bar, RED)}")

    return 1 if total_violations > 0 else 0


def print_pytest_snippet() -> None:
    snippet = '''
# ── In tests/conftest.py einfügen ─────────────────────────────────────────────
# Einbinden des platform-weiten Hardcoding-Guards als pytest-Tests
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "platform" / "scripts"))

from check_hardcoded_urls import RULES, _ALLOWED_TOKENS, _should_skip


def pytest_collect_file(parent, file_path):
    """Registriert alle *.html und apps/**/*.py als Hardcoding-Guard-Tests."""
    import pytest

    if file_path.suffix == ".html":
        return HardcodeFile.from_parent(parent, path=file_path)
    return None
# ──────────────────────────────────────────────────────────────────────────────
'''
    print(snippet)


# ── Entry-Point ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Platform-weiter Hardcoding-Guard für Django-Repos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?", help="Pfad zu einem einzelnen Repo")
    parser.add_argument("--all", action="store_true", help=f"Alle Repos unter {GITHUB_ROOT} scannen")
    parser.add_argument("--summary", action="store_true", help="Nur Zusammenfassung, keine Datei-Details")
    parser.add_argument("--report-only", action="store_true", help="Immer Exit-Code 0 (für Audits)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Alle Violations ausgeben (kein Truncate)")
    parser.add_argument("--pytest-snippet", action="store_true", help="conftest.py-Snippet ausgeben")
    args = parser.parse_args()

    if args.pytest_snippet:
        print_pytest_snippet()
        return 0

    if args.all:
        repos = find_all_repos(GITHUB_ROOT)
        print(f"Scanne {len(repos)} Repos...")
    elif args.path:
        target = Path(args.path).resolve()
        if not target.exists():
            print(f"Fehler: {target} nicht gefunden", file=sys.stderr)
            return 2
        repos = [target]
    else:
        # Kein Argument: aktuelles Verzeichnis
        repos = [Path.cwd()]

    results = [scan_repo(r) for r in repos]
    exit_code = print_report(results, verbose=args.verbose, summary_only=getattr(args, 'summary', False))
    return 0 if args.report_only else exit_code


if __name__ == "__main__":
    sys.exit(main())
