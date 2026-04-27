"""test_meta.py — Megatest: Plattform-Konsistenz-Checks.

Prüft strukturelle Invarianten der Test-Infrastruktur selbst:
  1. test_should_registry_budget_sync — alle Registry-Repos haben ein Budget
  2. test_should_budgets_have_no_unknown_repos — kein Budget-Eintrag für unbekannte Repos
  3. test_should_repos_have_test_infrastructure — Django-Repos haben tests/conftest.py
"""
from __future__ import annotations

import os
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


@pytest.mark.megatest
def test_should_repos_have_test_infrastructure() -> None:
    """Django-Repos müssen tests/conftest.py haben (iil-testkit Scaffold).

    Prüft GITHUB_ROOT lokal — überspringt Repos die nicht geklont sind.
    Schlägt nicht hart fehl (xfail), aber listet fehlende Repos auf.
    """
    github_root = Path(os.environ.get("GITHUB_DIR", Path.home() / "github"))
    if not github_root.exists():
        pytest.skip(f"GITHUB_ROOT {github_root} nicht vorhanden")

    reg_data = yaml.safe_load(_REGISTRY_FILE.read_text())
    repos = reg_data.get("repos", {})

    SCAFFOLD_TYPES = {"django", "agent", "bot"}
    missing: list[str] = []
    checked: int = 0

    for name, props in repos.items():
        if not isinstance(props, dict):
            continue
        if props.get("type") not in SCAFFOLD_TYPES:
            continue
        repo_path = github_root / name
        if not repo_path.exists():
            continue
        checked += 1
        if not (repo_path / "tests" / "conftest.py").exists():
            missing.append(name)

    if checked == 0:
        pytest.skip("Keine Django-Repos lokal geklont")

    if missing:
        pytest.xfail(
            f"{len(missing)}/{checked} Django-Repos ohne tests/conftest.py:\n"
            + "\n".join(f"  - {r}" for r in sorted(missing))
            + "\n\nFix: scaffold-tests Workflow ausführen oder Scaffold manuell kopieren."
            + "\nVorlage: platform/docs/templates/django_test_scaffold/"
        )
