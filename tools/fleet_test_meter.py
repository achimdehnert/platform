#!/usr/bin/env python3
"""Fleet-Test-Meter — Ist-Zustand des Testens über alle Repos (platform#2428, Kriterium 1).

Misst pro Git-Repo unter ``--root`` (Default ``~/github``) deterministisch:

- ``test_files``     Anzahl ``test_*.py`` / ``*_test.py`` (ohne venv/node_modules/vendor/.git — Fremdcode zählt nicht)
- ``src_py``         Anzahl ``.py`` außerhalb tests/, migrations/, venv
- ``make_test``      Makefile hat Target ``test``
- ``testkit_pin``    Versionsband von ``iil-testkit`` aus pyproject/requirements (oder ``-``)
- ``coverage``       ``coverage_threshold`` aus Workflows bzw. ``fail_under`` aus Config (oder ``-``)
- ``ci_test``        ``shared:<workflow>@<ref>`` · ``own-pytest`` (pytest oder direkter
                     ``test_*.py``-Start in einem run-Step) · ``wf-ohne-test`` · ``keiner``
- ``markers``        Marker-Schema: ``kanonisch`` · ``reqid`` (Traceability-IDs wie ``f1``) ·
                     ``gemischt`` · ``-``
- ``contract_tests`` Anzahl ``@pytest.mark.contract`` — 0 heißt: der shared-ci Contract-Job
                     ist in diesem Repo leer-grün (exit 5, bewusst so; sichtbar machen statt härten)
- ``last_commit``    Datum des letzten Commits (``git log -1``)

Befunde (Sektion „Verletzungen" im Report):

- **B1 Test ohne Leser**: ``test_files > 0`` und ``ci_test`` in {``wf-ohne-test``, ``keiner``},
  außer das Repo steht mit Begründung + Issue in ``--exceptions``
  (Default ``governance/tests/fleet-test-exceptions.json``).
- **B2 Pin veraltet**: ``testkit_pin`` gesetzt, aber Untergrenze < ``--min-testkit`` (Default 0.6.0).

Verlinkte Worktrees (``.git`` ist eine Datei) werden übersprungen — sie doppeln ihr Haupt-Repo.

Exit-Codes: 0 = keine Verletzung · 1 = ≥1 Verletzung · 2 = Aufruffehler

Usage:
    python3 tools/fleet_test_meter.py --report docs/audits/fleet-test-meter-2026-08-29.md
    python3 tools/fleet_test_meter.py --json /tmp/meter.json --no-git
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "site-packages",
    "__pycache__",
    ".tox",
    ".mypy_cache",
}
SRC_SKIP_DIRS = SKIP_DIRS | {"tests", "test", "migrations"}
TEST_FILE_RE = re.compile(r"^(test_.*|.*_test)\.py$")
PIN_RE = re.compile(
    r"""iil[-_]testkit(?:\[[^\]]*\])?\s*(?:=\s*)?["']?\s*([<>=!~]{1,2}\s*\d[^"'\s,\]]*(?:,\s*[<>=!~]{1,2}\s*\d[^"'\s,\]]*)*)"""
)
PIN_LOWER_RE = re.compile(r">=\s*(\d+(?:\.\d+)*)")
THRESHOLD_RE = re.compile(r"coverage_threshold:\s*['\"]?(\d+)")
FAIL_UNDER_RE = re.compile(r"fail[_-]under\s*[=:]\s*(\d+)")
SHARED_USES_RE = re.compile(
    r"uses:\s*[^/\s]+/(shared-ci|platform)/\.github/workflows/(_ci-[a-z]+)\.yml@(\S+)"
)
# Ein Testlauf im Workflow ist ein pytest-Aufruf ODER der direkte Start einer test_*.py
# (Skript-Tests wie robo-lab `python sim/test_stream_gate.py`).
PYTEST_LINE_RE = re.compile(
    r"^\s*(?:-\s*)?(?:run:\s*)?(?:\|)?.*(?:\bpytest\b|\btest_\w+\.py\b)", re.MULTILINE
)
MARKER_RE = re.compile(r"@pytest\.mark\.([A-Za-z_][A-Za-z0-9_]*)")
REQID_MARKER_RE = re.compile(r"^[a-z]\d+$")
PYTEST_BUILTIN = {
    "parametrize",
    "skip",
    "skipif",
    "xfail",
    "usefixtures",
    "filterwarnings",
    "django_db",
    "asyncio",
    "anyio",
    "no_naming_convention",
}
CANONICAL_MARKERS = {"unit", "integration", "contract", "e2e", "slow"}


@dataclass
class RepoRow:
    repo: str
    last_commit: str = "-"
    test_files: int = 0
    src_py: int = 0
    make_test: bool = False
    testkit_pin: str = "-"
    coverage: str = "-"
    ci_test: str = "keiner"
    markers: str = "-"
    contract_tests: int = 0
    exception: str = ""
    findings: list[str] = field(default_factory=list)


def _iter_files(root: Path, skip: set[str]):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in skip)
        for name in sorted(filenames):
            yield Path(dirpath) / name


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(p) for p in text.split("."))


def _last_commit(repo: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "log", "-1", "--format=%cs"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "-"
    return out.stdout.strip() or "-"


def _testkit_pin(repo: Path) -> str:
    candidates = [
        repo / "pyproject.toml",
        *sorted(repo.glob("requirements*.txt")),
        *sorted(repo.glob("requirements/*.txt")),
    ]
    for path in candidates:
        m = PIN_RE.search(_read(path))
        if m:
            return m.group(1).replace(" ", "")
    return "-"


def _coverage(repo: Path) -> str:
    values: list[str] = []
    for wf in sorted((repo / ".github" / "workflows").glob("*.yml")):
        values += THRESHOLD_RE.findall(_read(wf))
    if values:
        return (
            values[0]
            if len(set(values)) == 1
            else "/".join(sorted(set(values), key=int))
        )
    for cfg in (repo / "pyproject.toml", repo / ".coveragerc", repo / "setup.cfg"):
        m = FAIL_UNDER_RE.search(_read(cfg))
        if m:
            return m.group(1)
    return "-"


def _ci_test(repo: Path) -> str:
    wf_dir = repo / ".github" / "workflows"
    workflows = sorted(wf_dir.glob("*.yml")) + sorted(wf_dir.glob("*.yaml"))
    if not workflows:
        return "keiner"
    shared: list[str] = []
    own = False
    for wf in workflows:
        text = _read(wf)
        for host, name, ref in SHARED_USES_RE.findall(text):
            shared.append(
                f"{name}@{ref}" if host == "shared-ci" else f"platform/{name}@{ref}"
            )
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or "install" in stripped:
                continue
            if PYTEST_LINE_RE.match(line):
                own = True
    if shared:
        return "shared:" + "+".join(sorted(set(shared)))
    if own:
        return "own-pytest"
    return "wf-ohne-test"


def _markers(repo: Path) -> tuple[str, int]:
    """Marker-Schema und Anzahl ``@pytest.mark.contract``-Stellen (0 = Contract-Job ist leer-grün)."""
    names: set[str] = set()
    contract = 0
    for path in _iter_files(repo, SKIP_DIRS):
        if path.suffix == ".py" and TEST_FILE_RE.match(path.name):
            found = MARKER_RE.findall(_read(path))
            names.update(found)
            contract += found.count("contract")
    names -= PYTEST_BUILTIN
    if not names:
        return "-", contract
    reqid = {n for n in names if REQID_MARKER_RE.match(n)}
    canonical = names & CANONICAL_MARKERS
    if reqid and canonical:
        return "gemischt", contract
    if reqid:
        return "reqid", contract
    return ("kanonisch" if canonical else "frei"), contract


def scan_repo(repo: Path, *, use_git: bool) -> RepoRow:
    row = RepoRow(repo=repo.name)
    if use_git:
        row.last_commit = _last_commit(repo)
    for path in _iter_files(repo, SKIP_DIRS):
        if path.suffix == ".py" and TEST_FILE_RE.match(path.name):
            row.test_files += 1
    for path in _iter_files(repo, SRC_SKIP_DIRS):
        if path.suffix == ".py" and not TEST_FILE_RE.match(path.name):
            row.src_py += 1
    row.make_test = bool(re.search(r"^test:", _read(repo / "Makefile"), re.MULTILINE))
    row.testkit_pin = _testkit_pin(repo)
    row.coverage = _coverage(repo)
    row.ci_test = _ci_test(repo)
    row.markers, row.contract_tests = _markers(repo)
    return row


def find_repos(root: Path) -> tuple[list[Path], list[str]]:
    repos, skipped = [], []
    for child in sorted(root.iterdir()):
        git = child / ".git"
        if git.is_dir():
            repos.append(child)
        elif git.is_file():
            skipped.append(child.name)
    return repos, skipped


def apply_findings(
    rows: list[RepoRow], exceptions: dict[str, dict], min_testkit: str
) -> None:
    min_v = _version_tuple(min_testkit)
    for row in rows:
        exc = exceptions.get(row.repo)
        if exc:
            row.exception = (
                f"{exc.get('reason', '?')} ({exc.get('issue', 'kein Issue')})"
            )
        if row.test_files > 0 and row.ci_test in {"wf-ohne-test", "keiner"} and not exc:
            row.findings.append("B1 Test ohne Leser")
        if row.testkit_pin != "-":
            m = PIN_LOWER_RE.search(row.testkit_pin)
            if not m or _version_tuple(m.group(1)) < min_v:
                row.findings.append(f"B2 Pin < {min_testkit}")


def render_report(
    rows: list[RepoRow], skipped: list[str], *, root: Path, min_testkit: str
) -> str:
    with_tests = [r for r in rows if r.test_files > 0]
    pinned = [r for r in rows if r.testkit_pin != "-"]
    pinned_ok = [r for r in pinned if not any(f.startswith("B2") for f in r.findings)]
    violations = [r for r in rows if r.findings]
    lines = [
        "# Fleet-Test-Meter",
        "",
        f"Quelle: `tools/fleet_test_meter.py --root {root}` · Auftrag platform#2428 Kriterium 1",
        "",
        "## Aggregate",
        "",
        "| Kennzahl | Wert |",
        "|---|---|",
        f"| Repos gescannt | {len(rows)} |",
        f"| davon mit Tests | {len(with_tests)} |",
        f"| `make test` | {sum(r.make_test for r in rows)} |",
        f"| testkit-Pin ≥ {min_testkit} | {len(pinned_ok)}/{len(pinned)} |",
        f"| Coverage-Schwelle gesetzt | {sum(r.coverage != '-' for r in rows)} |",
        f"| shared-ci-Nutzer | {sum(r.ci_test.startswith('shared:') for r in rows)} |",
        f"| Marker-Schema reqid/gemischt | {sum(r.markers in {'reqid', 'gemischt'} for r in rows)} |",
        f"| Repos mit ≥1 Contract-Test | {sum(r.contract_tests > 0 for r in rows)} |",
        f"| Verletzungen | {len(violations)} |",
        f"| übersprungene Worktrees | {', '.join(skipped) or '—'} |",
        "",
        "## Verletzungen",
        "",
    ]
    if violations:
        lines += ["| Repo | Befund | Tests | CI | Pin |", "|---|---|---|---|---|"]
        lines += [
            f"| {r.repo} | {'; '.join(r.findings)} | {r.test_files} | {r.ci_test} | {r.testkit_pin} |"
            for r in violations
        ]
    else:
        lines.append("keine")
    lines += ["", "## Ausnahmen (begründet)", ""]
    exc_rows = [r for r in rows if r.exception]
    lines += [f"- {r.repo}: {r.exception}" for r in exc_rows] or ["keine"]
    lines += [
        "",
        "## Alle Repos",
        "",
        "| Repo | Commit | Tests | Src | make | Pin | Cov | CI | Marker |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(rows, key=lambda x: (-x.test_files, x.repo)):
        lines.append(
            f"| {r.repo} | {r.last_commit} | {r.test_files} | {r.src_py} | "
            f"{'ja' if r.make_test else '-'} | {r.testkit_pin} | {r.coverage} | {r.ci_test} | {r.markers} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(os.environ.get("GITHUB_DIR", Path.home() / "github")),
    )
    parser.add_argument(
        "--exceptions",
        type=Path,
        default=Path(__file__).resolve().parent.parent
        / "governance"
        / "tests"
        / "fleet-test-exceptions.json",
    )
    parser.add_argument("--min-testkit", default="0.6.0")
    parser.add_argument("--report", type=Path, help="Markdown-Report schreiben")
    parser.add_argument(
        "--json", dest="json_out", type=Path, help="JSON-Rohdaten schreiben"
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="kein git log (schneller, last_commit='-')",
    )
    args = parser.parse_args(argv)

    if not args.root.is_dir():
        print(f"Aufruffehler: --root {args.root} ist kein Verzeichnis", file=sys.stderr)
        return 2
    exceptions: dict[str, dict] = {}
    if args.exceptions.is_file():
        try:
            exceptions = json.loads(args.exceptions.read_text(encoding="utf-8")).get(
                "repos", {}
            )
        except (OSError, ValueError) as exc:
            print(f"Aufruffehler: {args.exceptions}: {exc}", file=sys.stderr)
            return 2

    repos, skipped = find_repos(args.root)
    rows = [scan_repo(repo, use_git=not args.no_git) for repo in repos]
    apply_findings(rows, exceptions, args.min_testkit)

    report = render_report(rows, skipped, root=args.root, min_testkit=args.min_testkit)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
    if args.json_out:
        args.json_out.write_text(
            json.dumps([asdict(r) for r in rows], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    if not args.report and not args.json_out:
        sys.stdout.write(report)
    violations = sum(1 for r in rows if r.findings)
    print(
        f"fleet-test-meter: {len(rows)} Repos, {violations} Verletzung(en)",
        file=sys.stderr,
    )
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
