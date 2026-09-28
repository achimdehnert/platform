"""Tests fuer tools/pypi_coldstart_watch.py — reine Logik (#3575 K1/K2).

Die Remote-Erhebung und der Eval sind bewusst nicht gemockt: der erzwungene
Dry-Run im PR (pypi-coldstart-watch.yml) ist deren Beweis. Hier haengt, was
den Loop ereignisgesteuert macht: Fingerprint, Faelligkeit, Zustand, Budget.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import pathlib

_SPEC = importlib.util.spec_from_file_location(
    "pypi_coldstart_watch",
    pathlib.Path(__file__).resolve().parents[1] / "pypi_coldstart_watch.py",
)
m = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(m)

AGENTS_OK = """# iil-x — Agent-Kontext

> Schema: pkg-agents-v1

## Zweck

x

## Setup & Test (Einstiegskommando)

```bash
make setup && make test
```

## Public API

- `x`

## Architektur-Constraints

- y

## Release

z
"""


def _row(repo: str, k2: str, k1: str = m.K1_OK) -> dict:
    return {
        "repo": repo,
        "org": "iilgmbh",
        "fingerprint": "f",
        "k1": k1,
        "k1_problems": [],
        "k2": k2,
    }


def test_should_fingerprint_missing_files_as_dash_in_stable_order():
    fp = m.fingerprint({"pyproject.toml": "c", "AGENTS.md": "a"})
    assert fp == "AGENTS.md=a|Makefile=-|pyproject.toml=c"


def test_should_flag_missing_agents_md_as_k1_fehlt():
    status, problems = m.k1_status(None)
    assert status == m.K1_MISSING
    assert problems


def test_should_accept_schema_conform_agents_md():
    assert m.k1_status(AGENTS_OK) == (m.K1_OK, [])


def test_should_report_schema_violation_with_reason():
    status, problems = m.k1_status("# x\n\nkein Marker\n")
    assert status == m.K1_DRIFT
    assert any("Schema-Marker" in p for p in problems)


def test_should_mark_unknown_package_as_neu_and_changed_fingerprint_as_geaendert():
    assert m.k2_status(None, "f1") == m.K2_NEW
    assert m.k2_status({"fingerprint": "f1"}, "f1") == m.K2_CURRENT
    assert m.k2_status({"fingerprint": "f0"}, "f1") == m.K2_CHANGED


def test_should_roundtrip_state_through_section_comment():
    state = {
        "aifw": {
            "fingerprint": "f",
            "result": "PASS",
            "date": "2026-09-27",
            "run_id": "1",
        }
    }
    body = "## Cold-Start\n```\nreport\n```\n" + m.render_state(state) + "\n"
    assert m.parse_state(body) == state


def test_should_treat_missing_or_broken_state_as_empty():
    assert m.parse_state(None) == {}
    assert m.parse_state("kein Zustand hier") == {}
    assert m.parse_state("<!-- coldstart-state:{kaputt -->") == {}


def test_should_select_only_due_packages_new_first_within_budget():
    rows = [
        _row("b", m.K2_CHANGED),
        _row("c", m.K2_CURRENT),
        _row("a", m.K2_NEW),
        _row("d", m.K2_NEW),
    ]
    chosen = m.select_for_eval(rows, max_evals=2, force_all=False)
    assert [r["repo"] for r in chosen] == ["a", "d"]


def test_should_select_everything_when_forced():
    rows = [_row("b", m.K2_CURRENT), _row("a", m.K2_CURRENT)]
    assert [r["repo"] for r in m.select_for_eval(rows, 10, True)] == ["a", "b"]


def test_should_render_counts_and_remaining_due_when_budget_exhausted():
    rows = [
        _row("a", m.K2_NEW),
        _row("b", m.K2_CHANGED),
        _row("c", m.K2_CURRENT),
        _row("d", m.K2_NEW, m.K1_DRIFT),
    ]
    rows[3]["k1_problems"] = ["Schema-Marker fehlt"]
    evaluated = {"a": {"result": "PASS", "gen_drift": False}}
    text = m.render_report(rows, dt.date(2026, 9, 27), evaluated, budget_left=0)
    assert "4 aktiv-Pakete" in text
    assert "K1 Kontextdatei: 3 konform · 1 Schema-Verstoss · 0 fehlt" in text
    assert (
        "3 faellig (neu 2, geaendert 1), 1 bewertet in diesem Lauf (1 PASS / 0 FAIL), 2 weiter faellig — Budget erschoepft"
        in text
    )
    assert "d: K1 schema-verstoss: Schema-Marker fehlt · K2 neu — faellig" in text
    assert "a: K2 PASS" in text


def test_should_count_unresolved_packages_as_not_checkable():
    rows = [_row("a", m.K2_CURRENT), {"repo": "z", "unresolved": True}]
    text = m.render_report(rows, dt.date(2026, 9, 27), {}, budget_left=6)
    assert "1 nicht pruefbar" in text
    assert "z: ORG NICHT AUFLÖSBAR (nicht pruefbar)" in text
