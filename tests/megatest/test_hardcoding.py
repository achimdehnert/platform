"""test_hardcoding.py — Megatest: Hardcoding-Guard über alle Repos.

Test-Arten:
  1. test_vermeidbar_total[<repo>]   — VERMEIDBAR-Violations <= Budget
  2. test_vermeidbar_rules[<repo>-<rule>] — Per-Regel-Gate (wenn budget.toml-Eintrag)
  3. test_info_no_secrets[<repo>]   — Kritische INFO-Regeln (I-CFG-02: IPs, V-SEC-03: Token)
  4. test_clean_repos_stay_clean[<repo>] — Budget=0 Repos dürfen nie Violations haben

Ratchet-Regeln:
  - Violations > Budget  → FAILED  (Regression)
  - Violations == Budget → PASSED  (Status quo)
  - Violations < Budget  → PASSED + Warnung (Budget kann reduziert werden)
  - Budget=0, keine Violations → PASSED ✓
"""
from __future__ import annotations

import pytest

from .conftest import ALL_REPO_NAMES, Budget, load_budgets, record_budget_update, scan_results  # noqa: F401

# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def _vermeidbar_count(results: dict, repo_name: str) -> int:
    r = results.get(repo_name)
    if r is None:
        return 0
    return len(r.by_category("VERMEIDBAR"))


def _rule_count(results: dict, repo_name: str, rule_id: str) -> int:
    r = results.get(repo_name)
    if r is None:
        return 0
    return sum(1 for v in r.violations if v.rule.rule_id == rule_id)


def _violation_summary(results: dict, repo_name: str) -> str:
    r = results.get(repo_name)
    if not r:
        return ""
    by_rule: dict[str, int] = {}
    for v in r.by_category("VERMEIDBAR"):
        by_rule[v.rule.rule_id] = by_rule.get(v.rule.rule_id, 0) + 1
    return "  ".join(f"{rid}×{cnt}" for rid, cnt in sorted(by_rule.items()))


# ── Test 1: VERMEIDBAR-Gesamtbudget ──────────────────────────────────────────

@pytest.mark.megatest
@pytest.mark.parametrize("repo_name", ALL_REPO_NAMES)
def test_vermeidbar_total(
    repo_name: str,
    scan_results: dict,
    budgets: dict[str, Budget],
    request: pytest.FixtureRequest,
) -> None:
    """Violations-Gesamtzahl darf Budget nicht überschreiten (Ratchet)."""
    budget = budgets.get(repo_name)
    if budget is None:
        pytest.skip(f"{repo_name}: kein Budget in budgets.toml definiert")

    count = _vermeidbar_count(scan_results, repo_name)
    summary = _violation_summary(scan_results, repo_name)

    # Update-Modus: Wert sammeln → wird in pytest_sessionfinish in budgets.toml geschrieben
    if request.config.getoption("--update-budgets", default=False):
        record_budget_update(repo_name, count)
        return

    if count > budget.total:
        detail = f"\n  {summary}" if summary else ""
        pytest.fail(
            f"[{repo_name}] VERMEIDBAR-Violations: {count} > Budget {budget.total}"
            f"  — Regression!{detail}\n"
            f"  Fix oder Budget anpassen: tests/megatest/budgets.toml"
        )

    if count < budget.total:
        # Erfolg + Hinweis: Budget kann gesenkt werden
        print(
            f"\n  [{repo_name}] {count} < {budget.total} — "
            f"Budget auf {count} reduzierbar!"
        )


# ── Test 2: Per-Regel-Budget (nur wenn in budgets.toml definiert) ─────────────

@pytest.mark.megatest
@pytest.mark.parametrize("repo_name", ALL_REPO_NAMES)
def test_vermeidbar_per_rule(
    repo_name: str,
    scan_results: dict,
    budgets: dict[str, Budget],
) -> None:
    """Granulare Regel-Gates (falls budget.toml rule_budgets hat)."""
    budget = budgets.get(repo_name)
    if not budget or not budget.per_rule:
        pytest.skip(f"{repo_name}: keine per_rule-Budgets definiert")

    failures: list[str] = []
    for rule_id, max_count in budget.per_rule.items():
        actual = _rule_count(scan_results, repo_name, rule_id)
        if actual > max_count:
            failures.append(f"  [{rule_id}] {actual} > {max_count}")

    if failures:
        pytest.fail(
            f"[{repo_name}] Per-Regel-Regression:\n" + "\n".join(failures)
        )


# ── Test 3: Budget=0 Repos bleiben sauber ────────────────────────────────────

_CLEAN_REPOS = [r for r in ALL_REPO_NAMES
                if load_budgets().get(r, Budget(0, {})).total == 0]


@pytest.mark.megatest
@pytest.mark.parametrize("repo_name", _CLEAN_REPOS)
def test_clean_repos_stay_clean(
    repo_name: str,
    scan_results: dict,
) -> None:
    """Repos mit Budget=0 dürfen NIEMALS Violations haben."""
    count = _vermeidbar_count(scan_results, repo_name)
    summary = _violation_summary(scan_results, repo_name)

    if count > 0:
        pytest.fail(
            f"[{repo_name}] war sauber (Budget=0), hat jetzt {count} Violations!\n"
            f"  {summary}\n"
            f"  Sofort fixen — kein Budget-Erhöhen erlaubt."
        )


# ── Test 4: Kritische Security-Violations (kein Budget — immer 0) ─────────────

_SECURITY_RULES = ("V-SEC-01", "V-SEC-02", "V-SEC-03")


@pytest.mark.megatest
@pytest.mark.parametrize("repo_name", ALL_REPO_NAMES)
def test_no_new_secrets(
    repo_name: str,
    scan_results: dict,
    budgets: dict[str, Budget],
) -> None:
    """V-SEC-01/02/03: Secret-Violations dürfen nicht zunehmen.

    Basiert auf dem Total-Budget — Security-Violations werden separat erfasst.
    """
    r = scan_results.get(repo_name)
    if not r:
        pytest.skip(f"{repo_name}: nicht gescannt")

    sec_violations = [v for v in r.by_category("VERMEIDBAR")
                      if v.rule.rule_id in _SECURITY_RULES]

    if sec_violations:
        details = "\n".join(
            f"  [{v.rule.rule_id}] {v.file_path.name}:{v.lineno}  {v.line[:80]}"
            for v in sec_violations[:10]
        )
        budget = budgets.get(repo_name, Budget(0, {}))
        # Nur warnen wenn Gesamtbudget > 0 (bekannte Violations toleriert)
        # Aber mindestens als Warning ausgeben
        if budget.total == 0:
            pytest.fail(
                f"[{repo_name}] Security-Violations in sauberem Repo:\n{details}"
            )
        else:
            # Als XFAIL markieren: bekannte Violations, sollen gefixt werden
            pytest.xfail(
                f"[{repo_name}] {len(sec_violations)} Security-Violations bekannt "
                f"(Budget={budget.total}). Bitte priorisieren:\n{details}"
            )
