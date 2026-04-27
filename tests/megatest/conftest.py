"""conftest.py — Megatest: Platform-weiter Hardcoding-Guard als pytest-Suite.

Konzept: Ratchet-Pattern
  - Jeder Repo hat ein Violations-Budget (budgets.toml)
  - Test FAILED wenn aktuelle Violations > Budget  (Regression!)
  - Test PASSED wenn aktuelle Violations <= Budget
  - Budget = 0: "clean" — jede neue Violation bricht CI
  - Budget > 0: Grace-Period, soll über Zeit auf 0 sinken

Ausführung:
  cd platform
  pytest tests/megatest/ -v
  pytest tests/megatest/ -v -k coach-hub
  pytest tests/megatest/ -v --tb=short --category VERMEIDBAR
  pytest tests/megatest/ --update-budgets   # Budgets auf aktuellen Stand setzen
"""
from __future__ import annotations

import os
import re
import sys
import tomllib
from pathlib import Path
from typing import NamedTuple

import pytest

# Pfad zum Scanner
_SCRIPTS = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))

from check_hardcoded_urls import RepoResult, find_all_repos, scan_repo  # noqa: E402

GITHUB_ROOT = Path(os.environ.get("GITHUB_DIR", Path.home() / "github"))
BUDGETS_FILE = Path(__file__).parent / "budgets.toml"


# ── Budget-Laden ──────────────────────────────────────────────────────────────

class Budget(NamedTuple):
    total: int
    per_rule: dict[str, int]


def load_budgets() -> dict[str, Budget]:
    with open(BUDGETS_FILE, "rb") as f:
        data = tomllib.load(f)

    budgets: dict[str, Budget] = {}
    raw = data.get("budgets", {})
    rule_raw = data.get("rule_budgets", {})

    for repo, total in raw.items():
        per_rule: dict[str, int] = {}
        for key, val in rule_raw.items():
            r_repo, _, rule_id = key.partition(".")
            if r_repo == repo:
                per_rule[rule_id] = val
        budgets[repo] = Budget(total=total, per_rule=per_rule)

    return budgets


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def all_repos() -> list[Path]:
    budget_repos = set(load_budgets().keys())
    return find_all_repos(GITHUB_ROOT, include_only=budget_repos)


@pytest.fixture(scope="session")
def budgets() -> dict[str, Budget]:
    return load_budgets()


@pytest.fixture(scope="session")
def scan_results(all_repos: list[Path]) -> dict[str, RepoResult]:
    """Scannt alle Repos einmalig (session-scoped → kein Doppel-Scan)."""
    return {r.name if r.name != "src" else r.parent.name: scan_repo(r)
            for r in all_repos}


# ── Parametrize-Helper ────────────────────────────────────────────────────────

def get_repo_names() -> list[str]:
    """Alle Repos lesen ohne session-fixture (für pytest.mark.parametrize)."""
    budget_repos = set(load_budgets().keys())
    return [
        r.name if r.name != "src" else r.parent.name
        for r in find_all_repos(GITHUB_ROOT, include_only=budget_repos)
    ]


ALL_REPO_NAMES = get_repo_names()


# ── CLI-Option ────────────────────────────────────────────────────────────────

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-budgets",
        action="store_true",
        default=False,
        help="Budgets.toml mit aktuellem Stand überschreiben (kein Fail).",
    )
    parser.addoption(
        "--category",
        default="VERMEIDBAR",
        help="Kategorie filtern: VERMEIDBAR (default) oder INFO.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "megatest: Platform-weiter Hardcoding-Megatest",
    )


# ── Budget-Update-Writer ───────────────────────────────────────────────────────

_budget_updates: dict[str, int] = {}


def record_budget_update(repo_name: str, count: int) -> None:
    """Aus test_hardcoding.py aufgerufen wenn --update-budgets aktiv."""
    _budget_updates[repo_name] = count


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:  # noqa: ARG001
    """Nach Test-Session: budgets.toml mit aktuellen Counts überschreiben."""
    if not session.config.getoption("--update-budgets", default=False):
        return
    if not _budget_updates:
        return

    raw = BUDGETS_FILE.read_text(encoding="utf-8")

    def _replace(m: re.Match) -> str:
        repo = m.group(1)
        new_val = _budget_updates.get(repo)
        if new_val is None:
            return m.group(0)
        padding = m.group(2)
        return f'"{repo}"{padding}= {new_val}'

    updated = re.sub(
        r'"([^"]+)"(\s*)= \d+',
        _replace,
        raw,
    )
    BUDGETS_FILE.write_text(updated, encoding="utf-8")
    print(f"\n✅ budgets.toml aktualisiert ({len(_budget_updates)} Repos)")
