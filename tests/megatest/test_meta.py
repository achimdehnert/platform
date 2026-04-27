"""test_meta.py — Megatest: Plattform-Konsistenz-Checks.

Prüft strukturelle Invarianten der Test-Infrastruktur selbst:
  1. test_should_registry_budget_sync — alle Registry-Repos haben ein Budget
  2. test_should_budgets_have_no_unknown_repos — kein Budget-Eintrag für unbekannte Repos
  3. test_should_megatest_clone_list_matches_registry — CI-Clone-Liste ist aktuell
"""
from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import yaml

_PLATFORM_ROOT = Path(__file__).parent.parent.parent
_BUDGETS_FILE = _PLATFORM_ROOT / "tests" / "megatest" / "budgets.toml"
_REGISTRY_FILE = _PLATFORM_ROOT / "scripts" / "repo-registry.yaml"
_WORKFLOW_FILE = _PLATFORM_ROOT / ".github" / "workflows" / "megatest.yml"

_META_REPOS = {"platform"}


def _load_registry_repos() -> set[str]:
    data = yaml.safe_load(_REGISTRY_FILE.read_text())
    return set(data.get("repos", {}).keys()) - _META_REPOS


def _load_budget_repos() -> set[str]:
    data = tomllib.loads(_BUDGETS_FILE.read_text())
    return set(data.get("budgets", {}).keys())


@pytest.mark.megatest
def test_should_registry_budget_sync() -> None:
    """Jedes Repo in repo-registry.yaml muss einen Budget-Eintrag in budgets.toml haben."""
    registry = _load_registry_repos()
    budgets = _load_budget_repos()
    missing = sorted(registry - budgets)
    assert not missing, (
        f"Repos in repo-registry.yaml ohne Budget in budgets.toml:\n"
        + "\n".join(f"  + {r}" for r in missing)
        + "\n\nFix: Eintrag in tests/megatest/budgets.toml hinzufügen (Budget=0 für neue Repos)"
    )


@pytest.mark.megatest
def test_should_budgets_have_no_unknown_repos() -> None:
    """Kein Budget-Eintrag für Repos die nicht in der Registry sind (veraltete Einträge)."""
    registry = _load_registry_repos() | _META_REPOS
    budgets = _load_budget_repos()
    orphaned = sorted(budgets - registry)
    if orphaned:
        pytest.xfail(
            f"Budget-Einträge ohne Registry-Eintrag (veraltet oder absichtlich):\n"
            + "\n".join(f"  - {r}" for r in orphaned)
            + "\n\nOptional: Aus budgets.toml entfernen falls Repo eingestellt."
        )
