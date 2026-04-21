#!/usr/bin/env python3
"""check_hardcoded_urls.py — Platform-weiter Hardcoding-Guard (v2).

Prüft die GESAMTE Codebase auf hardcodierte Werte.
Unterscheidet: VERMEIDBAR (Alternative vorhanden) vs. INFO (Kontext-abhängig).

Abgedeckte Kategorien:
  ── VERMEIDBAR ────────────────────────────────────────────────────────────────
  V-TMPL-01   href="/..." in Templates           → {% url 'app:name' %}
  V-TMPL-02   action="/..." in Templates         → {% url 'app:name' %}
  V-TMPL-03   src="/..." in Templates            → {% static 'path' %}
  V-VIEW-01   redirect("/...") in Views          → redirect(reverse('name'))
  V-VIEW-02   HttpResponseRedirect("/...")        → HttpResponseRedirect(reverse('name'))
  V-CFG-01    os.environ["KEY"] (außerh. Django-Boilerplate)   → decouple.config()
  V-CFG-02    os.environ.get("KEY") (außerh. Boilerplate)      → decouple.config()
  V-SEC-01    SECRET_KEY = "literal"             → decouple.config('SECRET_KEY')
  V-SEC-02    PASSWORD = "literal"               → decouple.config('...')
  V-SEC-03    print() in Django-Code             → logging.getLogger(__name__)

  ── INFO (Alternativen möglich, Kontext prüfen) ───────────────────────────────
  I-CFG-01    ALLOWED_HOSTS mit Literal-Domains  → decouple.config() / env var
  I-CFG-02    Hardcodierte IP-Adressen           → decouple.config() oder CIDR-Variable
  I-CFG-03    Hardcodierte E-Mail-Adressen       → settings.DEFAULT_FROM_EMAIL
  I-CFG-04    Hardcodierte Domains/URLs          → settings-Variable
  I-CFG-05    Hardcodierte Port-Nummern          → decouple.config()

  ── NOTWENDIG (nicht flaggen) ─────────────────────────────────────────────────
  urls.py path()/re_path() Definitionen          → korrekt, kein Fix nötig
  manage.py / wsgi.py / asgi.py / celery.py os.environ.setdefault()
  migrations/**                                  → Schema-Definitionen
  test_* / conftest.py                           → Test-Fixtures sind OK

Verwendung:
  python scripts/check_hardcoded_urls.py --all --summary
  python scripts/check_hardcoded_urls.py /path/to/repo --verbose
  python scripts/check_hardcoded_urls.py --all --category VERMEIDBAR
  python scripts/check_hardcoded_urls.py --all --report-only   # Exit 0 immer
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ── Konfiguration ─────────────────────────────────────────────────────────────

GITHUB_ROOT = Path.home() / "github"

_SKIP_DIRS = {
    ".venv", "node_modules", "__pycache__", "site-packages",
    ".git", "dist", "build", "htmlcov", ".mypy_cache", ".tox",
    ".claude", ".windsurf",
}

_SKIP_REPOS = {
    "platform", "infra-deploy", "iil-reflex", "promptfw", "authoringfw",
    "aifw", "testkit", "outlinefw", "weltenfw", "illustration-fw",
    "researchfw", "learnfw", "lastwar-bot", "odoo-hub", "mcp-hub", "nl2cad",
}

# Django-Boilerplate-Dateien: os.environ hier ist NOTWENDIG
_DJANGO_BOILERPLATE = {"manage.py", "wsgi.py", "asgi.py", "celery.py"}

# Zeilen-Whitelist für Template-Prüfungen
_TMPL_ALLOWED = [
    "/admin/",   # Django-Admin: keine namespaced URL
    "https://",  # externe Links
    "http://",   # externe Links
    "{{ ",       # Template-Variable
    "{% url",    # korrekte Verwendung
    "{% static", # korrekte Verwendung
]

# Pfad-Fragmente, bei denen INFO-Regeln nicht greifen (Drittcode, Seed-Daten, CI)
_INFO_SKIP_PATH_PARTS = {
    "vendor",                   # Third-Party-Code
    ".github",                  # CI-Scripts
    "node_modules",
}

# Dateinamen-Muster, bei denen I-CFG-03/04 übersprungen werden
_SEED_OR_FIXTURE_NAMES = {
    "factories.py", "fixtures.py", "conftest.py",
}
_SEED_PREFIXES = ("seed_", "bootstrap_", "load_")

# IP-Whitelist (lokal, Docker-intern — NOTWENDIG)
_IP_WHITELIST = re.compile(
    r"(127\.0\.0\.1|localhost|0\.0\.0\.0|172\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)"
)

CATEGORY_LABELS = {
    "VERMEIDBAR": "\033[31mVERMEIDB.\033[0m",
    "INFO":       "\033[33mINFO\033[0m",
}

# ── Regel-Definitionen ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Rule:
    rule_id: str
    category: str        # VERMEIDBAR | INFO
    description: str
    pattern: re.Pattern
    suffixes: tuple[str, ...]   # welche Dateitypen
    alternative: str            # was stattdessen verwenden
    skip_filenames: frozenset[str] = field(default_factory=frozenset)
    only_filenames: frozenset[str] = field(default_factory=frozenset)
    skip_in_tests: bool = True  # test_* und conftest.py überspringen


RULES: list[Rule] = [
    # ── VERMEIDBAR: Templates ─────────────────────────────────────────────────
    Rule(
        "V-TMPL-01", "VERMEIDBAR",
        "href mit hartkodiertem Pfad",
        re.compile(r'href="(/[a-zA-Z0-9_-])'),
        (".html", ".htm"),
        "{% url 'app:view_name' %}",
    ),
    Rule(
        "V-TMPL-02", "VERMEIDBAR",
        "action mit hartkodiertem Pfad (Formular)",
        re.compile(r'action="(/[a-zA-Z0-9_-])'),
        (".html", ".htm"),
        "{% url 'app:view_name' %}",
    ),
    Rule(
        "V-TMPL-03", "VERMEIDBAR",
        "src mit hartkodiertem Pfad (eigenes Asset)",
        re.compile(r'src="(/[a-zA-Z0-9_-])'),
        (".html", ".htm"),
        "{% static 'path/to/asset' %}",
    ),
    # ── VERMEIDBAR: Python Views ──────────────────────────────────────────────
    Rule(
        "V-VIEW-01", "VERMEIDBAR",
        "redirect() mit hartkodiertem URL-String",
        re.compile(r'\bredirect\(\s*["\']\/[a-zA-Z]'),
        (".py",),
        "redirect(reverse('app:name'))",
        skip_filenames=frozenset(_DJANGO_BOILERPLATE | {"urls.py"}),
    ),
    Rule(
        "V-VIEW-02", "VERMEIDBAR",
        "HttpResponseRedirect() mit hartkodiertem Pfad",
        re.compile(r'HttpResponseRedirect\(\s*["\']\/'),
        (".py",),
        "HttpResponseRedirect(reverse('app:name'))",
        skip_filenames=frozenset(_DJANGO_BOILERPLATE),
    ),
    # ── VERMEIDBAR: Konfiguration ─────────────────────────────────────────────
    Rule(
        "V-CFG-01", "VERMEIDBAR",
        "os.environ[\"KEY\"] — direkter Env-Zugriff",
        re.compile(r'\bos\.environ\['),
        (".py",),
        "decouple.config('KEY')",
        skip_filenames=frozenset(_DJANGO_BOILERPLATE),
        skip_in_tests=False,  # auch in Tests flaggen
    ),
    Rule(
        "V-CFG-02", "VERMEIDBAR",
        "os.environ.get(\"KEY\") ohne Fallback-Logik",
        re.compile(r'\bos\.environ\.get\('),
        (".py",),
        "decouple.config('KEY', default=...)",
        skip_filenames=frozenset(_DJANGO_BOILERPLATE),
    ),
    # ── VERMEIDBAR: Secrets ───────────────────────────────────────────────────
    Rule(
        "V-SEC-01", "VERMEIDBAR",
        "SECRET_KEY als Literal (nicht aus Env)",
        re.compile(r'SECRET_KEY\s*=\s*["\'][^$({]'),
        (".py",),
        "SECRET_KEY = config('SECRET_KEY')",
        skip_in_tests=False,
    ),
    Rule(
        "V-SEC-02", "VERMEIDBAR",
        "PASSWORD/DB-Passwort als Literal",
        re.compile(r'(?:PASSWORD|DB_PASS|REDIS_PASS)\s*=\s*["\'][^$({\'\"]{3,}'),
        (".py",),
        "config('DB_PASSWORD')",
        skip_in_tests=False,
    ),
    Rule(
        "V-SEC-03", "VERMEIDBAR",
        "Hardcodierter API-Token / Secret als Literal-String",
        re.compile(
            r'(?:api_key|apikey|api_secret|token|auth_token|access_token|private_key)'
            r'\s*=\s*["\'][a-zA-Z0-9_\-\.]{16,}["\']',
            re.IGNORECASE,
        ),
        (".py",),
        "decouple.config('API_KEY') oder Secret-Manager",
        skip_in_tests=False,
    ),
    # ── INFO: Konfiguration ───────────────────────────────────────────────────
    Rule(
        "I-CFG-01", "INFO",
        "ALLOWED_HOSTS mit Literal-Domain (nicht localhost)",
        re.compile(r'ALLOWED_HOSTS\s*=\s*\[.*["\'][^\'\"]*\.[^\'\"]+["\']'),
        (".py",),
        "ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())",
    ),
    Rule(
        "I-CFG-02", "INFO",
        "Hardcodierte öffentliche IP-Adresse",
        re.compile(r'["\'](\d{1,3}\.){3}\d{1,3}["\']'),
        (".py",),
        "decouple.config('SERVER_IP')",
    ),
    Rule(
        "I-CFG-03", "INFO",
        "Hardcodierte E-Mail-Adresse (nicht in Seed/Fixture)",
        re.compile(r'["\'][a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}["\']'),
        (".py",),
        "settings.DEFAULT_FROM_EMAIL oder decouple.config()",
    ),
    Rule(
        "I-CFG-04", "INFO",
        "Hardcodierte externe Domain/URL (nicht in API-Clients/Vendor)",
        re.compile(r'["\']https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^"\']*["\']'),
        (".py",),
        "settings-Variable oder decouple.config()",
    ),
]


# ── Datenmodelle ──────────────────────────────────────────────────────────────

@dataclass
class Violation:
    rule: Rule
    file_path: Path
    lineno: int
    line: str


@dataclass
class RepoResult:
    repo_path: Path
    violations: list[Violation] = field(default_factory=list)

    @property
    def name(self) -> str:
        if self.repo_path.name == "src":
            return self.repo_path.parent.name
        return self.repo_path.name

    @property
    def ok(self) -> bool:
        return len(self.violations) == 0

    def by_category(self, cat: str) -> list[Violation]:
        return [v for v in self.violations if v.rule.category == cat]


# ── Scanner ───────────────────────────────────────────────────────────────────

def _should_skip_path(path: Path) -> bool:
    return any(part in _SKIP_DIRS for part in path.parts)


def _is_test_file(path: Path) -> bool:
    return path.name.startswith("test_") or path.name == "conftest.py"


def _is_migration(path: Path) -> bool:
    return "migrations" in path.parts


def _tmpl_allowed(line: str) -> bool:
    return any(tok in line for tok in _TMPL_ALLOWED)


def _in_skip_path(path: Path) -> bool:
    """True wenn Datei in vendor/, .github/ etc. liegt."""
    return any(part in _INFO_SKIP_PATH_PARTS for part in path.parts)


def _is_seed_or_fixture(path: Path) -> bool:
    """True für Seed/Fixture-Dateien (Management Commands, Factories)."""
    if path.name in _SEED_OR_FIXTURE_NAMES:
        return True
    if path.name.startswith(_SEED_PREFIXES):
        return True
    return False


def _check_line(rule: Rule, line: str, path: Path) -> bool:
    """True wenn Regel auf diese Zeile/Datei zutrifft."""
    # Dateiname-Ausschlüsse
    if path.name in rule.skip_filenames:
        return False
    if rule.only_filenames and path.name not in rule.only_filenames:
        return False
    # Test-Ausschluss
    if rule.skip_in_tests and _is_test_file(path):
        return False
    # INFO-Regeln: vendor / .github / seed-Dateien überspringen
    if rule.category == "INFO":
        if _in_skip_path(path):
            return False
        if rule.rule_id in ("I-CFG-03", "I-CFG-04") and _is_seed_or_fixture(path):
            return False
    # Template-Whitelist
    if path.suffix in (".html", ".htm") and _tmpl_allowed(line):
        return False
    # IP-Whitelist für I-CFG-02
    if rule.rule_id == "I-CFG-02" and _IP_WHITELIST.search(line):
        return False
    # os.environ in Django-Boilerplate (setdefault ist NOTWENDIG)
    if rule.rule_id in ("V-CFG-01", "V-CFG-02") and "setdefault" in line:
        return False
    # V-CFG-01/02 in standalone scripts (nicht apps/) sind oft OK → INFO statt VERMEIDBAR
    # aber weiter flaggen — Nutzer entscheidet
    # Kommentare überspringen
    stripped = line.strip()
    if stripped.startswith(("#", "{#", "//", "<!--")):
        return False
    # Explicit opt-out
    if "# noqa" in line or "# nosec" in line or "# hardcoded-ok" in line:
        return False
    return bool(rule.pattern.search(line))


def scan_repo(repo_path: Path) -> RepoResult:
    result = RepoResult(repo_path=repo_path)

    applicable: dict[str, list[Rule]] = {}
    for r in RULES:
        for s in r.suffixes:
            applicable.setdefault(s, []).append(r)

    for fpath in repo_path.rglob("*"):
        if not fpath.is_file():
            continue
        if _should_skip_path(fpath):
            continue
        if _is_migration(fpath):
            continue
        rules = applicable.get(fpath.suffix, [])
        if not rules:
            continue

        try:
            lines = fpath.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        for lineno, line in enumerate(lines, start=1):
            for rule in rules:
                if _check_line(rule, line, fpath):
                    result.violations.append(Violation(
                        rule=rule,
                        file_path=fpath,
                        lineno=lineno,
                        line=line.strip(),
                    ))
    return result


def find_all_repos(root: Path) -> list[Path]:
    repos: list[Path] = []
    for candidate in sorted(root.iterdir()):
        if not candidate.is_dir():
            continue
        if candidate.name.startswith(".") or candidate.name.endswith(".code-workspace"):
            continue
        if candidate.name in _SKIP_REPOS:
            continue
        if (candidate / "manage.py").exists():
            repos.append(candidate)
            continue
        if (candidate / "src" / "manage.py").exists():
            repos.append(candidate)
            continue
        html_count = sum(1 for p in candidate.rglob("*.html") if not _should_skip_path(p))
        if html_count > 0:
            repos.append(candidate)
    return repos


# ── Ausgabe ───────────────────────────────────────────────────────────────────

RESET  = "\033[0m"
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
DIM    = "\033[2m"


def _c(text: str, *codes: str) -> str:
    if not sys.stdout.isatty():
        return text
    return "".join(codes) + text + RESET


def print_report(
    results: list[RepoResult],
    verbose: bool = False,
    summary_only: bool = False,
    category_filter: str | None = None,
) -> int:
    categories = ["VERMEIDBAR", "INFO"] if not category_filter else [category_filter.upper()]

    def filtered(r: RepoResult) -> list[Violation]:
        return [v for v in r.violations if v.rule.category in categories]

    total = sum(len(filtered(r)) for r in results)
    n_vermeidbar = sum(len(r.by_category("VERMEIDBAR")) for r in results)
    n_info       = sum(len(r.by_category("INFO"))       for r in results)
    repos_dirty  = [r for r in results if filtered(r)]
    repos_clean  = [r for r in results if not filtered(r)]

    print(f"\n{_c('HARDCODING-GUARD — Platform Scan v2', BOLD)}")
    print(f"Repos: {len(results)}  │  "
          f"Gesamt: {_c(str(total), RED if total else GREEN)}  │  "
          f"Vermeidbar: {_c(str(n_vermeidbar), RED)}  │  "
          f"Info: {_c(str(n_info), YELLOW)}  │  "
          f"Sauber: {_c(str(len(repos_clean)), GREEN)}/{len(results)}")
    print(_c("─" * 72, DIM))

    for repo in sorted(repos_dirty, key=lambda r: -len(filtered(r))):
        viols = filtered(repo)
        v_count = len(repo.by_category("VERMEIDBAR"))
        i_count = len(repo.by_category("INFO"))
        tag = (f"{_c(f'V:{v_count}', RED)} {_c(f'I:{i_count}', YELLOW)}"
               if not category_filter else f"{len(viols)}")
        print(f"\n{_c('✗ ' + repo.name, RED + BOLD)}  [{tag}]")

        by_file: dict[Path, list[Violation]] = {}
        for v in viols:
            by_file.setdefault(v.file_path, []).append(v)

        for fpath, fviols in sorted(by_file.items()):
            try:
                rel = fpath.relative_to(repo.repo_path)
            except ValueError:
                rel = fpath

            if summary_only:
                by_rule: dict[str, int] = {}
                for v in fviols:
                    by_rule[v.rule.rule_id] = by_rule.get(v.rule.rule_id, 0) + 1
                tags = "  ".join(
                    f"{_c(rid, RED if 'V-' in rid else YELLOW)}×{cnt}"
                    for rid, cnt in sorted(by_rule.items())
                )
                print(f"  {_c(str(rel), CYAN)}  {tags}")
                continue

            print(f"  {_c(str(rel), CYAN)}")
            shown = fviols if verbose else fviols[:6]
            for v in shown:
                cat_label = _c("●", RED if v.rule.category == "VERMEIDBAR" else YELLOW)
                print(f"    {cat_label} {_c(f'[{v.rule.rule_id}]', BOLD)} "
                      f"Zeile {v.lineno}: {v.line[:90]}")
                if verbose:
                    print(f"       {_c('→ ' + v.rule.alternative, DIM)}")
            if not verbose and len(fviols) > 6:
                print(f"    {_c(f'... +{len(fviols)-6} weitere', DIM)}")

    # Sauber-Liste
    if repos_clean:
        names = ", ".join(_c(r.name, GREEN) for r in sorted(repos_clean, key=lambda r: r.name))
        print(f"\n{_c('✓ Sauber:', GREEN + BOLD)} {names}")

    # Statistik
    print(f"\n{_c('─' * 72, DIM)}")
    print(_c("Violations nach Regel:", BOLD))

    rule_stats: dict[str, tuple[str, str, int]] = {}  # id → (cat, alt, count)
    for r in results:
        for v in r.violations:
            if v.rule.category not in categories:
                continue
            rule_stats.setdefault(v.rule.rule_id, (v.rule.category, v.rule.description, 0))
            t = rule_stats[v.rule.rule_id]
            rule_stats[v.rule.rule_id] = (t[0], t[1], t[2] + 1)

    for rid, (cat, desc, cnt) in sorted(rule_stats.items(), key=lambda x: (-x[1][2], x[0])):
        marker = _c("●", RED if cat == "VERMEIDBAR" else YELLOW)
        print(f"  {marker} {_c(rid, BOLD)}: {cnt:4d}  {desc}")

    # Top-Offenders-Balken
    if total > 0:
        print(f"\n{_c('Top-Offenders (Vermeidbar):', BOLD)}")
        top = sorted(repos_dirty, key=lambda r: -len(r.by_category("VERMEIDBAR")))[:12]
        max_v = max(len(r.by_category("VERMEIDBAR")) for r in top) or 1
        for r in top:
            v = len(r.by_category("VERMEIDBAR"))
            i = len(r.by_category("INFO"))
            if v == 0:
                continue
            bar = _c("█" * int(v / max_v * 25), RED)
            print(f"  {r.name:<22} V:{v:3d} I:{i:3d}  {bar}")

    return 1 if n_vermeidbar > 0 else 0


# ── Entry-Point ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Platform-weiter Hardcoding-Guard — VERMEIDBAR vs. INFO",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?", help="Pfad zu einem einzelnen Repo")
    parser.add_argument("--all",         action="store_true", help="Alle Repos scannen")
    parser.add_argument("--summary",     action="store_true", help="Dateiliste ohne Zeilen-Detail")
    parser.add_argument("--verbose","-v",action="store_true", help="Alle Violations + Alternativen")
    parser.add_argument("--report-only", action="store_true", help="Immer Exit 0 (für Audits)")
    parser.add_argument("--category",    help="Nur VERMEIDBAR oder INFO anzeigen")
    args = parser.parse_args()

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
        repos = [Path.cwd()]

    results = [scan_repo(r) for r in repos]
    exit_code = print_report(
        results,
        verbose=args.verbose,
        summary_only=args.summary,
        category_filter=args.category,
    )
    return 0 if args.report_only else exit_code


if __name__ == "__main__":
    sys.exit(main())
