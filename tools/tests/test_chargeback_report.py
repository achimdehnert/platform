"""Tests fuer tools/chargeback_report.py — Kostenumlage je App (ADR-292)."""

import importlib.util
import json
import pathlib
import sys

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "chargeback_report",
    pathlib.Path(__file__).resolve().parents[1] / "chargeback_report.py",
)
cb = importlib.util.module_from_spec(_SPEC)
sys.modules["chargeback_report"] = cb
_SPEC.loader.exec_module(cb)


def test_should_strip_role_suffix_to_get_app():
    assert cb.app_of("risk_hub_web") == "risk-hub"
    assert cb.app_of("risk_hub_db") == "risk-hub"
    assert cb.app_of("writing_hub_worker") == "writing-hub"


def test_should_prefer_longest_suffix_over_shorter_one():
    # "_orchestrator_http" darf nicht als "_http" o.ae. zerfallen; das Muster
    # war der Grund fuer die Sortierung in ROLE_SUFFIXES.
    assert cb.app_of("mcp_hub_orchestrator_http") == "mcp-hub"


def test_should_keep_name_when_no_known_role_suffix():
    assert cb.app_of("solo") == "solo"


@pytest.mark.parametrize(
    "text,expected",
    [("451.8MiB", 451.8), ("1.5GiB", 1536.0), ("512KiB", 0.5), (42, 42.0)],
)
def test_should_parse_docker_stats_memory_units(text, expected):
    assert cb.parse_mem(text) == pytest.approx(expected)


def test_should_reject_unknown_memory_unit():
    with pytest.raises(ValueError):
        cb.parse_mem("12 Sack Reis")


def _fixture():
    return {
        "hosts": {
            "h1": {
                "price_eur_month": 100.0,
                "ram_gib": 8,
                "containers": {
                    "a_web": "600MiB",
                    "a_db": "400MiB",
                    "b_web": "1000MiB",
                    "mon_cadvisor": "100MiB",
                },
            }
        }
    }


def test_should_split_cost_by_memory_share():
    rows = cb.compute(_fixture())
    by_app = {r["app"]: r for r in rows}
    # a = 1000 MiB, b = 1000 MiB -> je 50 % und je 50,00 EUR
    assert by_app["a"]["eur_month"] == pytest.approx(50.0)
    assert by_app["b"]["eur_month"] == pytest.approx(50.0)
    assert by_app["a"]["share_pct"] == pytest.approx(50.0)


def test_should_distribute_full_host_price_including_idle_capacity():
    # Der Host ist nur zu ~25 % belegt; der volle Preis wird trotzdem verteilt,
    # weil er unabhaengig von der Auslastung bezahlt wird.
    rows = cb.compute(_fixture())
    apps = [r for r in rows if r["app"] != "_SUMME"]
    assert sum(r["eur_month"] for r in apps) == pytest.approx(100.0)


def test_should_exclude_infra_containers_from_apps_but_report_them():
    rows = cb.compute(_fixture())
    assert "mon" not in {r["app"] for r in rows}
    summe = next(r for r in rows if r["app"] == "_SUMME")
    assert summe["infra_mib"] == pytest.approx(100.0)
    # 2000 MiB Apps + 100 MiB Infra von 8192 MiB
    assert summe["belegt_pct"] == pytest.approx(25.6, abs=0.1)


def test_should_skip_host_without_any_app_container():
    data = {
        "hosts": {
            "leer": {
                "price_eur_month": 10.0,
                "ram_gib": 4,
                "containers": {"mon_cadvisor": "5MiB"},
            }
        }
    }
    assert cb.compute(data) == []


def test_should_render_markdown_table_with_one_row_per_app():
    md = cb.to_markdown(cb.compute(_fixture()))
    assert "| a | 1000 | 50.0 % | 50.00 |" in md
    assert "_SUMME" not in md
    assert "Leerstand" in md


def test_should_run_end_to_end_from_file(tmp_path, capsys):
    path = tmp_path / "in.json"
    path.write_text(json.dumps(_fixture()), encoding="utf-8")
    assert cb.main([str(path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["host"] == "h1"
