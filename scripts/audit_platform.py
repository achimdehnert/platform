#!/usr/bin/env python3
"""audit_platform.py — Cross-Repo Platform Audit

Scannt alle Django-Repos aus repo-registry.yaml und liefert:
  - Inventory: Tests, Workflows, URLs, Services pro Repo
  - Health: /livez/ Checks auf Prod-URLs
  - Test-Run: ruft teste_repo.py pro Repo auf (opt-in via --run-tests)
  - PostgreSQL: speichert Ergebnisse (opt-in via --store-db)

Verwendung:
    python3 scripts/audit_platform.py                   # API-Scan alle Repos
    python3 scripts/audit_platform.py coach-hub         # einzelnes Repo
    python3 scripts/audit_platform.py --run-tests       # + pytest pro Repo (langsam)
    python3 scripts/audit_platform.py --health          # + /livez/ Prod-Check
    python3 scripts/audit_platform.py --store-db        # + in PostgreSQL speichern
    python3 scripts/audit_platform.py --format=json     # JSON statt Tabelle

SSoT: scripts/repo-registry.yaml (Repo-Liste)
      PyPI iil-testkit (Test-Versions-Referenz)
      PostgreSQL platform_audit_run (History)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass, field
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
GITHUB_DIR = Path(os.environ.get("GITHUB_DIR", Path.home() / "github"))

SCAFFOLD_TYPES = {"django", "agent", "bot"}
HEALTH_TIMEOUT = 5

# ── Datenmodell ──────────────────────────────────────────────────────────────

@dataclass
class RepoAudit:
    repo: str
    repo_type: str
    prod_url: str = ""

    # Inventory
    has_scaffold: bool = False        # tests/conftest.py vorhanden
    has_req_test: bool = False        # requirements-test.txt vorhanden
    has_pyproject: bool = False       # pyproject.toml vorhanden
    workflow_count: int = 0           # .github/workflows/*.yml Anzahl
    test_file_count: int = 0          # tests/test_*.py Anzahl
    url_count: int = 0                # URL-Patterns (urls.py Zeilen als Proxy)
    service_count: int = 0            # services.py Dateien

    # Health
    health_status: int = -1           # HTTP Status /livez/ (-1 = nicht geprüft)
    health_ms: int = -1               # Response-Zeit in ms

    # Test-Run
    tests_run: bool = False
    tests_passed: bool | None = None
    tests_exit_code: int = -1

    # Meta
    error: str = ""
    scanned_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def inventory_score(self) -> int:
        """0-5 Punkte: wie vollständig ist die Test-Infrastruktur?"""
        return sum([
            self.has_scaffold,
            self.has_req_test,
            self.has_pyproject,
            self.workflow_count > 0,
            self.test_file_count > 0,
        ])

    @property
    def status_icon(self) -> str:
        if self.error:
            return "⚠️"
        if self.tests_run:
            return "✅" if self.tests_passed else "❌"
        return "🟡" if self.inventory_score >= 3 else "🔴"


# ── GitHub API ────────────────────────────────────────────────────────────────

def _github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("PROJECT_PAT")
    if not token:
        path = Path.home() / ".secrets" / "github_PAT"
        if path.exists():
            token = path.read_text().strip()
    if not token:
        print("WARN: Kein GitHub-Token — Rate-Limit trifft ggf. an", file=sys.stderr)
    return token or ""


def _api_get(path: str, token: str) -> dict | list | None:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"token {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        print(f"  API {path}: HTTP {e.code}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  API {path}: {e}", file=sys.stderr)
        return None


def _file_exists(repo: str, path: str, token: str) -> bool:
    return _api_get(
        f"/repos/{GITHUB_ORG}/{repo}/contents/{path}", token
    ) is not None


def _count_files(repo: str, path: str, pattern: str, token: str) -> int:
    items = _api_get(f"/repos/{GITHUB_ORG}/{repo}/contents/{path}", token)
    if not isinstance(items, list):
        return 0
    return sum(1 for i in items if isinstance(i, dict) and i.get("name", "").endswith(pattern))


def _count_url_lines(repo: str, token: str) -> int:
    """Zählt urls.py Zeilen als Proxy für URL-Pattern-Anzahl."""
    content = _api_get(f"/repos/{GITHUB_ORG}/{repo}/contents/config/urls.py", token)
    if not content or not isinstance(content, dict):
        content = _api_get(f"/repos/{GITHUB_ORG}/{repo}/contents/urls.py", token)
    if not content or not isinstance(content, dict):
        return 0
    import base64
    try:
        text = base64.b64decode(content.get("content", "")).decode(errors="replace")
        return sum(1 for line in text.splitlines() if "path(" in line or "re_path(" in line)
    except Exception:
        return 0


def scan_via_api(repo: str, repo_type: str, prod_url: str, token: str) -> RepoAudit:
    audit = RepoAudit(repo=repo, repo_type=repo_type, prod_url=prod_url)

    # Repo existiert?
    meta = _api_get(f"/repos/{GITHUB_ORG}/{repo}", token)
    if meta is None:
        audit.error = "Repo nicht gefunden (private oder gelöscht)"
        return audit

    audit.has_scaffold = _file_exists(repo, "tests/conftest.py", token)
    audit.has_req_test = _file_exists(repo, "requirements-test.txt", token)
    audit.has_pyproject = _file_exists(repo, "pyproject.toml", token)
    audit.workflow_count = _count_files(repo, ".github/workflows", ".yml", token)
    audit.test_file_count = _count_files(repo, "tests", ".py", token)
    audit.url_count = _count_url_lines(repo, token)

    # services.py zählen — apps/*/services.py
    apps_dir = _api_get(f"/repos/{GITHUB_ORG}/{repo}/contents/apps", token)
    if isinstance(apps_dir, list):
        for app in apps_dir:
            if isinstance(app, dict) and app.get("type") == "dir":
                if _file_exists(repo, f"apps/{app['name']}/services.py", token):
                    audit.service_count += 1

    return audit


# ── Lokaler Scan (wenn GITHUB_DIR vorhanden) ─────────────────────────────────

def scan_local(repo_dir: Path, repo: str, repo_type: str, prod_url: str) -> RepoAudit:
    audit = RepoAudit(repo=repo, repo_type=repo_type, prod_url=prod_url)

    if not repo_dir.exists():
        audit.error = f"Lokaler Pfad nicht gefunden: {repo_dir}"
        return audit

    audit.has_scaffold = (repo_dir / "tests" / "conftest.py").exists()
    audit.has_req_test = (repo_dir / "requirements-test.txt").exists()
    audit.has_pyproject = (repo_dir / "pyproject.toml").exists()

    workflows_dir = repo_dir / ".github" / "workflows"
    audit.workflow_count = len(list(workflows_dir.glob("*.yml"))) if workflows_dir.exists() else 0

    tests_dir = repo_dir / "tests"
    audit.test_file_count = len(list(tests_dir.rglob("test_*.py"))) if tests_dir.exists() else 0

    # URL-Patterns zählen
    for urls_path in [repo_dir / "config" / "urls.py", repo_dir / "urls.py"]:
        if urls_path.exists():
            text = urls_path.read_text(errors="replace")
            audit.url_count = sum(1 for l in text.splitlines() if "path(" in l or "re_path(" in l)
            break

    # services.py zählen
    apps_dir = repo_dir / "apps"
    if apps_dir.exists():
        audit.service_count = sum(1 for p in apps_dir.glob("*/services.py"))

    return audit


# ── Health Check ──────────────────────────────────────────────────────────────

def check_health(audit: RepoAudit, local_port: int | None = None,
                 health_path: str = "/livez/") -> None:
    if not audit.prod_url and not local_port:
        return
    path = health_path if health_path else "/livez/"
    if not path.startswith("/"):
        path = f"/{path}"
    # Self-Hosted Runner läuft auf dem Server: localhost:PORT direkt prüfen
    # → umgeht Cloudflare-Blocks (403) auf öffentlichen URLs
    if local_port:
        url = f"http://127.0.0.1:{local_port}{path}"
    else:
        url = f"https://{audit.prod_url}{path}"
    t0 = time.monotonic()
    # Erst urllib versuchen, dann curl als Fallback (Proxy/ALLOWED_HOSTS-Workaround)
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url, timeout=HEALTH_TIMEOUT) as resp:
            audit.health_status = resp.status
            audit.health_ms = int((time.monotonic() - t0) * 1000)
        return
    except urllib.error.HTTPError as e:
        audit.health_status = e.code
        audit.health_ms = -1
        return
    except Exception as e:
        urllib_err = str(e)

    # Fallback: curl (funktioniert zuverlässig auf Self-Hosted Runner)
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "--max-time", "5", url],
            capture_output=True, text=True, timeout=10,
        )
        code_str = result.stdout.strip()
        code = int(code_str) if code_str.isdigit() else 0
        audit.health_status = code
        audit.health_ms = int((time.monotonic() - t0) * 1000)
        if code == 0:
            print(f"  HEALTH-WARN {audit.repo} ({url}): urllib={urllib_err!r} curl_exit={result.returncode}",
                  file=sys.stderr)
    except Exception as e:
        audit.health_status = 0
        audit.health_ms = -1
        print(f"  HEALTH-WARN {audit.repo} ({url}): urllib={urllib_err!r} curl_exc={e}",
              file=sys.stderr)


# ── Test-Run ──────────────────────────────────────────────────────────────────

def run_tests(audit: RepoAudit, repo_dir: Path) -> None:
    if not repo_dir.exists():
        audit.error = f"Kein lokaler Pfad für Test-Run: {repo_dir}"
        return
    teste_script = PLATFORM_ROOT / "scripts" / "teste_repo.py"
    if not teste_script.exists():
        audit.error = "teste_repo.py nicht gefunden"
        return

    python = _find_python(repo_dir)
    result = subprocess.run(
        [python, str(teste_script), str(repo_dir)],
        capture_output=True, text=True, timeout=300,
    )
    audit.tests_run = True
    audit.tests_exit_code = result.returncode
    audit.tests_passed = result.returncode == 0


def _find_python(repo_dir: Path) -> str:
    for candidate in [
        repo_dir / ".venv" / "bin" / "python",
        repo_dir / "venv" / "bin" / "python",
    ]:
        if candidate.exists():
            return str(candidate)
    return sys.executable


# ── PostgreSQL Store ──────────────────────────────────────────────────────────

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS platform_audit_run (
    id          BIGSERIAL PRIMARY KEY,
    scanned_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    repo        VARCHAR(100) NOT NULL,
    repo_type   VARCHAR(50),
    prod_url    VARCHAR(200),
    has_scaffold        BOOLEAN,
    has_req_test        BOOLEAN,
    has_pyproject       BOOLEAN,
    workflow_count      INT,
    test_file_count     INT,
    url_count           INT,
    service_count       INT,
    health_status       INT,
    health_ms           INT,
    tests_run           BOOLEAN,
    tests_passed        BOOLEAN,
    tests_exit_code     INT,
    inventory_score     INT,
    error               TEXT
);
CREATE INDEX IF NOT EXISTS idx_platform_audit_repo_time
    ON platform_audit_run (repo, scanned_at DESC);
"""

def store_in_db(audits: list[RepoAudit]) -> None:
    try:
        import psycopg2
    except ImportError:
        print("WARN: psycopg2 fehlt — pip install psycopg2-binary", file=sys.stderr)
        return

    dsn = os.environ.get("DATABASE_URL") or os.environ.get("PLATFORM_AUDIT_DSN")
    if not dsn:
        print("WARN: DATABASE_URL fehlt — kein PostgreSQL-Store", file=sys.stderr)
        return

    try:
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute(_CREATE_TABLE_SQL)
        for a in audits:
            cur.execute(
                """INSERT INTO platform_audit_run
                   (repo, repo_type, prod_url, has_scaffold, has_req_test, has_pyproject,
                    workflow_count, test_file_count, url_count, service_count,
                    health_status, health_ms, tests_run, tests_passed, tests_exit_code,
                    inventory_score, error, scanned_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (a.repo, a.repo_type, a.prod_url, a.has_scaffold, a.has_req_test,
                 a.has_pyproject, a.workflow_count, a.test_file_count, a.url_count,
                 a.service_count, a.health_status, a.health_ms, a.tests_run,
                 a.tests_passed, a.tests_exit_code, a.inventory_score, a.error,
                 a.scanned_at),
            )
        conn.commit()
        print(f"\n✅  {len(audits)} Einträge in PostgreSQL gespeichert.")
    except Exception as e:
        print(f"WARN: PostgreSQL-Store fehlgeschlagen: {e}", file=sys.stderr)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ── Output ───────────────────────────────────────────────────────────────────

def _health_str(audit: RepoAudit) -> str:
    if audit.health_status == -1:
        return "—"
    if audit.health_status == 200:
        return f"✅ {audit.health_ms}ms"
    return f"❌ {audit.health_status}"


def print_table(audits: list[RepoAudit]) -> None:
    print("\n## Platform Audit — " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    print()
    header = f"{'':2} {'Repo':<28} {'Typ':<8} {'Inv':>3} {'Tests':>5} {'Wflows':>6} {'URLs':>5} {'Svc':>4} {'Health':<12} {'Fehler'}"
    print(header)
    print("-" * len(header))

    for a in sorted(audits, key=lambda x: (x.status_icon != "✅", x.inventory_score < 3, x.repo)):
        test_str = (
            f"{'✅' if a.tests_passed else '❌'} (exit {a.tests_exit_code})"
            if a.tests_run else f"{a.test_file_count:>3} file(s)"
        )
        print(
            f"{a.status_icon:2} {a.repo:<28} {a.repo_type:<8} "
            f"{a.inventory_score:>3}/5 {test_str:<14} "
            f"{a.workflow_count:>4}  {a.url_count:>4} {a.service_count:>4}  "
            f"{_health_str(a):<12} {a.error[:40] if a.error else ''}"
        )

    total = len(audits)
    scaffolded = sum(1 for a in audits if a.has_scaffold)
    tested = sum(1 for a in audits if a.tests_passed is True)
    healthy = sum(1 for a in audits if a.health_status == 200)

    print(f"\n{'='*80}")
    print(f"Gesamt: {total} Repos  |  Scaffold: {scaffolded}/{total}  |  "
          f"Tests grün: {tested}/{sum(1 for a in audits if a.tests_run)}  |  "
          f"Health OK: {healthy}/{sum(1 for a in audits if a.health_status != -1)}")

    missing = [a.repo for a in audits if not a.has_scaffold]
    if missing:
        print(f"\n⚠️  Ohne Test-Scaffold ({len(missing)}):")
        for r in missing:
            print(f"   • {r}  →  python3 scripts/gen_test_scaffold.py {r}")


def print_json(audits: list[RepoAudit]) -> None:
    print(json.dumps([asdict(a) | {"inventory_score": a.inventory_score} for a in audits], indent=2))


def print_github_summary(audits: list[RepoAudit]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a") as f:
        f.write("## Platform Audit\n\n")
        f.write("| Repo | Typ | Inv | Tests | Workflows | Health |\n")
        f.write("|------|-----|-----|-------|-----------|--------|\n")
        for a in sorted(audits, key=lambda x: x.repo):
            test_cell = "✅" if a.tests_passed else ("❌" if a.tests_run else f"{a.test_file_count} files")
            f.write(f"| {a.status_icon} {a.repo} | {a.repo_type} | {a.inventory_score}/5 | "
                    f"{test_cell} | {a.workflow_count} | {_health_str(a)} |\n")
        f.write(f"\n**Repos:** {len(audits)} | "
                f"**Scaffold:** {sum(1 for a in audits if a.has_scaffold)}/{len(audits)}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def load_registry() -> dict:
    return yaml.safe_load(REGISTRY_FILE.read_text())


def main() -> int:
    parser = argparse.ArgumentParser(description="Platform Cross-Repo Audit")
    parser.add_argument("repos", nargs="*", help="Einzelne Repos (leer = alle Django-Repos)")
    parser.add_argument("--run-tests", action="store_true",
                        help="pytest via teste_repo.py pro Repo ausführen (langsam)")
    parser.add_argument("--health", action="store_true",
                        help="/livez/ Prod-Check pro Repo")
    parser.add_argument("--store-db", action="store_true",
                        help="Ergebnisse in PostgreSQL speichern (DATABASE_URL erforderlich)")
    parser.add_argument("--local", action="store_true",
                        help=f"Lokale Repos aus GITHUB_DIR={GITHUB_DIR} scannen statt GitHub API")
    parser.add_argument("--format", choices=["table", "json"], default="table")
    parser.add_argument("--fail-on-missing-scaffold", action="store_true",
                        help="Exit 1 wenn Repos ohne Test-Scaffold existieren")
    args = parser.parse_args()

    registry = load_registry()
    all_repos = registry.get("repos", {})

    # Ziel-Repos bestimmen
    if args.repos:
        targets = {r: all_repos.get(r, {"type": "django"}) for r in args.repos}
    else:
        targets = {
            name: props for name, props in all_repos.items()
            if isinstance(props, dict) and props.get("type") in SCAFFOLD_TYPES
            and name != "platform"
        }

    print(f"\n🔍  Platform Audit — {len(targets)} Repos\n")

    token = _github_token()
    audits: list[RepoAudit] = []

    for repo, props in targets.items():
        repo_type = props.get("type", "?") if isinstance(props, dict) else "?"
        prod_url = props.get("prod_url", "") if isinstance(props, dict) else ""
        local_port = props.get("port") if isinstance(props, dict) else None
        health_path = props.get("health", "/livez/") if isinstance(props, dict) else "/livez/"
        repo_dir = GITHUB_DIR / repo

        print(f"  {'[local]' if args.local and repo_dir.exists() else '[api]  '} {repo}...", end="", flush=True)

        if args.local and repo_dir.exists():
            audit = scan_local(repo_dir, repo, repo_type, prod_url)
        else:
            audit = scan_via_api(repo, repo_type, prod_url, token)

        if args.health:
            check_health(audit, local_port=local_port, health_path=health_path)

        if args.run_tests:
            run_tests(audit, repo_dir)

        icon = audit.status_icon
        inv = f"{audit.inventory_score}/5"
        print(f" {icon} inv={inv}" + (f" err={audit.error[:30]}" if audit.error else ""))
        audits.append(audit)

    # Output
    if args.format == "json":
        print_json(audits)
    else:
        print_table(audits)

    print_github_summary(audits)

    if args.store_db:
        store_in_db(audits)

    # Exit-Code
    if args.fail_on_missing_scaffold:
        missing = [a for a in audits if not a.has_scaffold and not a.error]
        if missing:
            print(f"\nExit 1: {len(missing)} Repos ohne Scaffold", file=sys.stderr)
            return 1

    failed_tests = [a for a in audits if a.tests_run and not a.tests_passed]
    if failed_tests:
        print(f"\nExit 1: {len(failed_tests)} Test-Failures", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
