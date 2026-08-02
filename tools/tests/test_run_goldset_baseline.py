"""run_goldset_baseline: Aggregation, Prompt-Aufbau und Konfigurations-Aufloesung.

Das Werkzeug erzeugt die Kostenbasis, gegen die spaetere Routing-Entscheidungen
gemessen werden (ADR-177). Ein Fehler in der Aggregation faellt nicht auf — er
verschiebt nur den Vergleichsmassstab, und zwar dauerhaft. Deshalb liegt der
Schwerpunkt auf `_aggregate`: Zaehlung, Mittelwerte und die Frage, was bei
fehlenden Feldern passiert.

Kein Netz, keine Datenbank: getestet wird die Auswertung, nicht die Anbindung.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "run_goldset_baseline.py"
_spec = importlib.util.spec_from_file_location("run_goldset_baseline", _SRC)
gb = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = gb
_spec.loader.exec_module(gb)


def ergebnis(**over):
    basis = {
        "task_type": "feature",
        "success": True,
        "cost_usd": 0.10,
        "prompt_tokens": 4000,
        "completion_tokens": 3000,
        "duration_ms": 1000,
    }
    basis.update(over)
    return basis


# --- _aggregate --------------------------------------------------------------


def test_should_return_an_empty_aggregate_for_no_results():
    assert gb._aggregate([]) == {}


def test_should_group_results_by_task_type():
    agg = gb._aggregate([
        ergebnis(task_type="feature"),
        ergebnis(task_type="feature"),
        ergebnis(task_type="bugfix"),
    ])

    assert sorted(agg) == ["bugfix", "feature"]
    assert agg["feature"]["count"] == 2
    assert agg["bugfix"]["count"] == 1


def test_should_count_success_and_failure_separately():
    agg = gb._aggregate([
        ergebnis(success=True), ergebnis(success=True), ergebnis(success=False),
    ])

    assert (agg["feature"]["success"], agg["feature"]["fail"]) == (2, 1)


def test_should_treat_a_missing_success_flag_as_failure():
    agg = gb._aggregate([{"task_type": "feature"}])

    assert agg["feature"]["fail"] == 1


def test_should_bucket_a_result_without_task_type_as_unknown():
    agg = gb._aggregate([{"success": True}])

    assert list(agg) == ["unknown"]


def test_should_sum_costs_and_tokens():
    agg = gb._aggregate([
        ergebnis(cost_usd=0.10, prompt_tokens=100, completion_tokens=50),
        ergebnis(cost_usd=0.20, prompt_tokens=200, completion_tokens=70),
    ])["feature"]

    assert agg["total_cost_usd"] == pytest.approx(0.30)
    assert agg["total_prompt_tokens"] == 300
    assert agg["total_completion_tokens"] == 120


def test_should_default_missing_numeric_fields_to_zero():
    agg = gb._aggregate([{"task_type": "feature", "success": True}])["feature"]

    assert (agg["total_cost_usd"], agg["total_prompt_tokens"]) == (0.0, 0)


def test_should_compute_the_average_cost_per_task():
    agg = gb._aggregate([
        ergebnis(cost_usd=0.10), ergebnis(cost_usd=0.30),
    ])["feature"]

    assert agg["avg_cost_usd"] == pytest.approx(0.20)


def test_should_compute_the_average_duration_as_an_integer():
    """Ganzzahlige Division ist Absicht — Millisekunden mit Nachkomma taeuschen
    eine Genauigkeit vor, die die Messung nicht hat."""
    agg = gb._aggregate([
        ergebnis(duration_ms=1000), ergebnis(duration_ms=1001),
    ])["feature"]

    assert agg["avg_duration_ms"] == 1000
    assert isinstance(agg["avg_duration_ms"], int)


def test_should_keep_the_two_task_types_independent():
    agg = gb._aggregate([
        ergebnis(task_type="feature", cost_usd=1.0),
        ergebnis(task_type="bugfix", cost_usd=0.0),
    ])

    assert agg["feature"]["total_cost_usd"] == pytest.approx(1.0)
    assert agg["bugfix"]["total_cost_usd"] == pytest.approx(0.0)


# --- _build_prompt -----------------------------------------------------------


def test_should_include_the_task_description_in_the_prompt():
    text = gb._build_prompt({"description": "Rechnungslauf reparieren"})

    assert "Rechnungslauf reparieren" in text


def test_should_fill_defaults_for_missing_task_fields():
    text = gb._build_prompt({"description": "x"})

    assert "Repo: unknown" in text
    assert "Type: feature" in text
    assert "Complexity: moderate" in text


def test_should_use_the_given_values_over_the_defaults():
    text = gb._build_prompt(
        {"description": "x", "repo": "risk-hub", "task_type": "bugfix", "complexity": "hard"}
    )

    assert "Repo: risk-hub" in text and "Type: bugfix" in text and "Complexity: hard" in text


# --- _get_db_url -------------------------------------------------------------


def test_should_prefer_the_orchestrator_url_over_the_mcp_one(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_DATABASE_URL", "postgres://a")
    monkeypatch.setenv("ORCHESTRATOR_MCP_MEMORY_DB_URL", "postgres://b")

    assert gb._get_db_url() == "postgres://a"


def test_should_fall_back_to_the_mcp_url(monkeypatch):
    monkeypatch.delenv("ORCHESTRATOR_DATABASE_URL", raising=False)
    monkeypatch.setenv("ORCHESTRATOR_MCP_MEMORY_DB_URL", "postgres://b")

    assert gb._get_db_url() == "postgres://b"


def test_should_exit_2_when_no_database_url_is_configured(monkeypatch):
    monkeypatch.delenv("ORCHESTRATOR_DATABASE_URL", raising=False)
    monkeypatch.delenv("ORCHESTRATOR_MCP_MEMORY_DB_URL", raising=False)

    with pytest.raises(SystemExit) as exc:
        gb._get_db_url()

    assert exc.value.code == 2


# --- _load_goldset -----------------------------------------------------------


def test_should_load_a_goldset_file(tmp_path):
    p = tmp_path / "goldset.yaml"
    p.write_text("tasks:\n  - id: t1\n    description: Beispiel\n", encoding="utf-8")

    daten = gb._load_goldset(p)

    assert daten["tasks"][0]["id"] == "t1"
