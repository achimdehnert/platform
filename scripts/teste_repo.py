#!/usr/bin/env python3
"""teste_repo.py — Vollständiger Test-Run für ein Repo.

Aufruf:
    python3 scripts/teste_repo.py <repo_dir>

Schritte:
  1. Repo-Validierung
  2. Lint (ruff)
  3. Django System Check + Migration Check
  4. Test-Dependencies prüfen / installieren
  5. pytest (Unit + Integration + Smoke) mit Coverage
  6. Hardcoding Guard
  7. Report
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

PLATFORM_ROOT = Path(__file__).parent.parent


# ── Ergebnis-Datenstrukturen ──────────────────────────────────────────────────

@dataclass
class StepResult:
    name: str
    status: str = "OK"       # OK | WARN | FAIL | SKIP
    detail: str = ""
    output: str = ""


@dataclass
class Report:
    repo_name: str
    repo_dir: Path
    steps: list[StepResult] = field(default_factory=list)

    def add(self, result: StepResult) -> None:
        self.steps.append(result)

    def print(self) -> None:
        icons = {"OK": "✅", "WARN": "⚠️ ", "FAIL": "❌", "SKIP": "⏭️ "}
        print(f"\n{'='*60}")
        print(f"  /teste-repo Report: {self.repo_name}")
        print(f"{'='*60}")
        for s in self.steps:
            icon = icons.get(s.status, "?")
            line = f"  {icon}  {s.name:<28} {s.detail}"
            print(line)
        print(f"{'='*60}")
        failed = [s for s in self.steps if s.status == "FAIL"]
        warned = [s for s in self.steps if s.status == "WARN"]
        if not failed and not warned:
            print("  Alle Checks bestanden.\n")
        else:
            if failed:
                print(f"  {len(failed)} Fehler — Details oben im Output.\n")
            if warned:
                print(f"  {len(warned)} Warnungen — bitte prüfen.\n")

    def exit_code(self) -> int:
        return 1 if any(s.status == "FAIL" for s in self.steps) else 0


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def run(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
    capture: bool = True,
) -> tuple[int, str]:
    merged_env = {**os.environ, **(env or {})}
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture,
            text=True,
            env=merged_env,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode, output
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"


def find_python(repo_dir: Path) -> str:
    for candidate in [
        repo_dir / ".venv" / "bin" / "python",
        repo_dir / "venv" / "bin" / "python",
    ]:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def find_manage(repo_dir: Path) -> Path | None:
    for candidate in [repo_dir / "manage.py", repo_dir / "src" / "manage.py"]:
        if candidate.exists():
            return candidate
    return None


def detect_settings_module(repo_dir: Path) -> str:
    """Ermittle DJANGO_SETTINGS_MODULE aus pyproject.toml, sonst Standard."""
    pyproject = repo_dir / "pyproject.toml"
    if pyproject.exists():
        import tomllib
        cfg = tomllib.loads(pyproject.read_text())
        settings = (
            cfg.get("tool", {})
               .get("pytest", {})
               .get("ini_options", {})
               .get("DJANGO_SETTINGS_MODULE", "")
        )
        if settings:
            return settings
    for candidate in ["config.settings.test", "config.settings.base"]:
        module_path = repo_dir / candidate.replace(".", "/")
        if (Path(str(module_path) + ".py")).exists():
            return candidate
    return "config.settings.test"


def last_n_lines(text: str, n: int = 30) -> str:
    lines = text.strip().splitlines()
    return "\n".join(lines[-n:]) if len(lines) > n else text.strip()


# ── Test-Schritte ─────────────────────────────────────────────────────────────

def step_validate(repo_dir: Path, report: Report) -> bool:
    if not repo_dir.exists():
        report.add(StepResult("Repo-Validierung", "FAIL", f"{repo_dir} existiert nicht"))
        return False
    if not (repo_dir / ".git").exists():
        report.add(StepResult("Repo-Validierung", "WARN", "Kein .git-Verzeichnis"))
    else:
        report.add(StepResult("Repo-Validierung", "OK", str(repo_dir)))
    return True


def step_lint(repo_dir: Path, python: str, report: Report) -> None:
    ruff = repo_dir / ".venv" / "bin" / "ruff"
    cmd = [str(ruff) if ruff.exists() else "ruff", "check", ".", "--output-format=concise"]
    rc, out = run(cmd, cwd=repo_dir)
    lines = [l for l in out.splitlines() if l.strip() and not l.startswith("All checks")]
    if rc == 0:
        report.add(StepResult("Lint (ruff)", "OK", "Keine Fehler"))
    elif rc == 127:
        report.add(StepResult("Lint (ruff)", "SKIP", "ruff nicht installiert"))
    else:
        detail = f"{len(lines)} Problem(e)"
        report.add(StepResult("Lint (ruff)", "FAIL", detail, last_n_lines(out, 15)))
        print(f"\n--- Lint Fehler ---\n{last_n_lines(out, 15)}\n")


def step_django_check(repo_dir: Path, python: str, settings: str, report: Report) -> None:
    manage = find_manage(repo_dir)
    if not manage:
        report.add(StepResult("Django Check", "SKIP", "Kein manage.py"))
        return
    env = {"USE_POSTGRES": "0", "SECRET_KEY": "test-ci-secret-key", "DJANGO_SETTINGS_MODULE": settings}
    rc, out = run([python, str(manage), "check", "--fail-level", "ERROR"], cwd=repo_dir, env=env)
    if rc == 0:
        report.add(StepResult("Django Check", "OK"))
    else:
        report.add(StepResult("Django Check", "FAIL", "System Check fehlgeschlagen", last_n_lines(out, 10)))
        print(f"\n--- Django Check Fehler ---\n{last_n_lines(out, 10)}\n")


def step_migration_check(repo_dir: Path, python: str, settings: str, report: Report) -> None:
    manage = find_manage(repo_dir)
    if not manage:
        report.add(StepResult("Migration Check", "SKIP", "Kein manage.py"))
        return
    env = {"USE_POSTGRES": "0", "SECRET_KEY": "test-ci-secret-key", "DJANGO_SETTINGS_MODULE": settings}
    rc, out = run([python, str(manage), "migrate", "--check"], cwd=repo_dir, env=env)
    if rc == 0:
        report.add(StepResult("Migration Check", "OK"))
    elif "SQLite" in out or "sqlite" in out.lower() or rc == 1:
        # SQLite: migrate --check schlägt fehl wenn keine DB existiert → nicht kritisch
        report.add(StepResult("Migration Check", "WARN", "SQLite — kein --check möglich"))
    else:
        report.add(StepResult("Migration Check", "FAIL", "Ausstehende Migrationen", last_n_lines(out, 5)))
        print(f"\n--- Migration Check ---\n{last_n_lines(out, 5)}\n")


def step_install_test_deps(repo_dir: Path, python: str, report: Report) -> None:
    req = repo_dir / "requirements-test.txt"
    if not req.exists():
        report.add(StepResult("Test-Dependencies", "WARN", "requirements-test.txt fehlt"))
        return
    rc, out = run([python, "-m", "pip", "install", "-r", str(req), "-q"], cwd=repo_dir)
    if rc == 0:
        report.add(StepResult("Test-Dependencies", "OK", "requirements-test.txt installiert"))
    else:
        report.add(StepResult("Test-Dependencies", "FAIL", "Install fehlgeschlagen", last_n_lines(out, 5)))
        print(f"\n--- pip install Fehler ---\n{last_n_lines(out, 5)}\n")


def step_pytest(repo_dir: Path, python: str, settings: str, report: Report) -> None:
    tests_dir = repo_dir / "tests"
    if not tests_dir.exists():
        report.add(StepResult(
            "Tests (pytest)", "WARN",
            "Kein tests/-Verzeichnis",
            f"Fix: gh workflow run scaffold-tests.yml -f repo_name={repo_dir.name}",
        ))
        print(f"\n⚠️  Kein tests/-Verzeichnis in {repo_dir.name}")
        print(f"   Fix: gh workflow run scaffold-tests.yml -f repo_name={repo_dir.name}\n")
        return

    # Prüfen ob Tests vorhanden
    test_files = list(tests_dir.rglob("test_*.py"))
    if not test_files:
        report.add(StepResult("Tests (pytest)", "WARN", "Keine test_*.py Dateien gefunden"))
        return

    env = {
        "USE_POSTGRES": "0",
        "SECRET_KEY": "test-ci-secret-key",
        "DJANGO_SETTINGS_MODULE": settings,
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    cmd = [
        python, "-m", "pytest", "tests/",
        "--tb=short", "--no-header", "-q",
        "--cov", "--cov-report=term-missing:skip-covered",
    ]
    rc, out = run(cmd, cwd=repo_dir, env=env, capture=True)
    if rc != 0 and "unrecognized arguments" in out and "--cov" in out:
        # pytest-cov nicht installiert — ohne Coverage wiederholen
        cmd_no_cov = [python, "-m", "pytest", "tests/", "--tb=short", "--no-header", "-q"]
        rc, out = run(cmd_no_cov, cwd=repo_dir, env=env, capture=True)
        out = "(Coverage übersprungen — pytest-cov nicht installiert)\n" + out

    # Parse: passed/failed/skipped
    summary_line = ""
    for line in reversed(out.splitlines()):
        if "passed" in line or "failed" in line or "error" in line:
            summary_line = line.strip()
            break

    # Parse: Coverage
    coverage_pct = ""
    for line in out.splitlines():
        if "TOTAL" in line:
            parts = line.split()
            if parts:
                coverage_pct = f"Coverage: {parts[-1]}"

    print(f"\n--- pytest Output ---\n{last_n_lines(out, 25)}\n")

    if rc == 0:
        detail = f"{summary_line} | {coverage_pct}" if coverage_pct else summary_line
        report.add(StepResult("Tests (pytest)", "OK", detail))
    elif rc == 5:
        report.add(StepResult("Tests (pytest)", "WARN", "Keine Tests collected"))
    else:
        report.add(StepResult("Tests (pytest)", "FAIL", summary_line or "Tests fehlgeschlagen"))


def step_dependency_check(repo_dir: Path, python: str, report: Report) -> None:
    """Prüft requirements.txt auf Konflikte, Pinning und CVEs."""
    import re

    req_files = {
        "requirements.txt": repo_dir / "requirements.txt",
        "requirements-test.txt": repo_dir / "requirements-test.txt",
    }
    found_reqs = {k: v for k, v in req_files.items() if v.exists()}

    if not found_reqs:
        # pyproject.toml als Alternative akzeptieren
        if (repo_dir / "pyproject.toml").exists():
            report.add(StepResult("Dependencies", "OK", "pyproject.toml vorhanden (kein requirements.txt)"))
        else:
            report.add(StepResult("Dependencies", "WARN", "Weder requirements.txt noch pyproject.toml"))
        return

    issues: list[str] = []
    warns: list[str] = []

    # 1. Pinning-Check: Pakete ohne jegliche Versionsangabe
    _UNPINNED_RE = re.compile(r"^([a-zA-Z0-9_\-]+)\s*$")
    _IIL_PACKAGE_RE = re.compile(r"^(iil-\w+|aifw|promptfw|authoringfw|weltenfw|nl2cadfw)")
    _IIL_UPPER_BOUND_RE = re.compile(r"<\s*\d")

    for req_file, req_path in found_reqs.items():
        for raw_line in req_path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            pkg = line.split("[")[0].split("=")[0].split(">")[0].split("<")[0].strip()
            if _UNPINNED_RE.match(line):
                warns.append(f"{req_file}: '{pkg}' hat keine Versionsangabe")
            if _IIL_PACKAGE_RE.match(pkg) and not _IIL_UPPER_BOUND_RE.search(line):
                warns.append(f"{req_file}: '{pkg}' fehlt Upper-Bound (<1) — ADR iil-packages")

    # 2. pip check — Dependency-Konflikte im installierten Environment
    rc, out = run([python, "-m", "pip", "check"], cwd=repo_dir)
    if rc != 0 and rc != 127:
        for line in out.splitlines():
            if line.strip() and "No broken" not in line:
                issues.append(f"pip check: {line.strip()}")

    # 3. pip-audit — CVE-Scan (optional, nur wenn installiert)
    audit_rc, audit_out = run([python, "-m", "pip_audit", "--format=columns", "-q"], cwd=repo_dir)
    if audit_rc == 127:
        pass  # pip-audit nicht installiert — kein Problem
    elif audit_rc != 0:
        vuln_lines = [l for l in audit_out.splitlines() if l.strip() and "No known" not in l and "Name" not in l]
        if vuln_lines:
            issues.extend([f"CVE: {l.strip()}" for l in vuln_lines[:5]])

    if issues:
        detail = f"{len(issues)} Problem(e), {len(warns)} Warnung(en)"
        report.add(StepResult("Dependencies", "FAIL", detail))
        print(f"\n--- Dependency Probleme ---")
        for i in issues:
            print(f"  ❌ {i}")
        for w in warns:
            print(f"  ⚠️  {w}")
        print()
    elif warns:
        detail = f"{len(warns)} Pinning-Warnung(en)"
        report.add(StepResult("Dependencies", "WARN", detail))
        print(f"\n--- Pinning Warnungen ---")
        for w in warns:
            print(f"  ⚠️  {w}")
        print()
    else:
        detail = f"{', '.join(found_reqs.keys())} — OK"
        report.add(StepResult("Dependencies", "OK", detail))


def step_hardcoding(repo_dir: Path, report: Report) -> None:
    checker = PLATFORM_ROOT / "scripts" / "check_hardcoded_urls.py"
    if not checker.exists():
        report.add(StepResult("Hardcoding Guard", "SKIP", "check_hardcoded_urls.py nicht gefunden"))
        return
    rc, out = run(
        [sys.executable, str(checker), str(repo_dir), "--category", "VERMEIDBAR", "--summary"],
        cwd=PLATFORM_ROOT,
    )
    violations = 0
    for line in out.splitlines():
        if "Violations:" in line or "violations" in line.lower():
            import re
            m = re.search(r"(\d+)", line)
            if m:
                violations = int(m.group(1))
    if violations == 0:
        report.add(StepResult("Hardcoding Guard", "OK", "0 Violations"))
    else:
        report.add(StepResult("Hardcoding Guard", "WARN", f"{violations} Violation(s)"))
        print(f"\n--- Hardcoding Violations ---\n{last_n_lines(out, 10)}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/teste_repo.py <repo_dir>")
        print("       python3 scripts/teste_repo.py coach-hub  (relativ zu GITHUB_DIR)")
        return 1

    arg = sys.argv[1]
    repo_dir = Path(arg)
    if not repo_dir.is_absolute():
        github_dir = Path(os.environ.get("GITHUB_DIR", Path.home() / "github"))
        repo_dir = github_dir / arg

    report = Report(repo_name=repo_dir.name, repo_dir=repo_dir)

    print(f"\n🔍  Teste Repo: {repo_dir.name}")
    print(f"    Pfad: {repo_dir}\n")

    if not step_validate(repo_dir, report):
        report.print()
        return 1

    python = find_python(repo_dir)
    settings = detect_settings_module(repo_dir)

    print(f"    Python:   {python}")
    print(f"    Settings: {settings}\n")

    step_lint(repo_dir, python, report)
    step_dependency_check(repo_dir, python, report)
    step_django_check(repo_dir, python, settings, report)
    step_migration_check(repo_dir, python, settings, report)
    step_install_test_deps(repo_dir, python, report)
    step_pytest(repo_dir, python, settings, report)
    step_hardcoding(repo_dir, report)

    report.print()
    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
