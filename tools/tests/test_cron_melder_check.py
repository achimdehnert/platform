"""Tests für den Blinde-Melder-Check (platform#1508, tools/cron_melder_check.py).

Reine Funktionen, kein Netz: `geplante_workflows()` liest lokale Dateien,
`rote_serien()` bekommt die Lauf-Liste übergeben.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

_SRC = pathlib.Path(__file__).resolve().parents[1] / "cron_melder_check.py"
_spec = importlib.util.spec_from_file_location("cron_melder_check", _SRC)
cmc = importlib.util.module_from_spec(_spec)
sys.modules["cron_melder_check"] = cmc
_spec.loader.exec_module(cmc)


def _lauf(zeit, conclusion="failure", name="Melder", status="completed"):
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "created_at": zeit,
        "html_url": f"https://example.invalid/{zeit}",
    }


# --- geplante_workflows ------------------------------------------------------


def _schreibe(tmp_path, dateiname, inhalt):
    (tmp_path / dateiname).write_text(inhalt, encoding="utf-8")


def test_should_collect_only_scheduled_workflows(tmp_path):
    _schreibe(
        tmp_path,
        "cron.yml",
        "name: Melder\non:\n  schedule:\n    - cron: '0 5 * * *'\n",
    )
    _schreibe(tmp_path, "pr.yml", "name: Nur PR\non:\n  pull_request:\n")
    melder, befund = cmc.geplante_workflows(tmp_path)
    assert melder == {"Melder": tmp_path / "cron.yml"}
    assert befund == {}


def test_should_report_red_is_a_finding_workflows_separately(tmp_path):
    """Ein roter Lauf ist dort ein FUND, kein Defekt — aber er darf nicht verschwinden.

    Frueher gab `geplante_workflows` markierte Workflows gar nicht zurueck. Damit
    waren die offenen Drift-Funde von Registry-Live-Reconcile seit 2026-07-21
    unsichtbar. Sie gehoeren in die zweite Menge, nicht in den Papierkorb.
    """
    _schreibe(
        tmp_path,
        "reconcile.yml",
        "# ROT-IST-BEFUND — absichtlich rot bei Drift\n"
        "name: Reconcile\non:\n  schedule:\n    - cron: '17 5 * * *'\n",
    )
    melder, befund = cmc.geplante_workflows(tmp_path)
    assert melder == {}
    assert befund == {"Reconcile": tmp_path / "reconcile.yml"}


def test_should_read_yaml_extension_too(tmp_path):
    _schreibe(
        tmp_path,
        "x.yaml",
        "name: Melder Y\non:\n  schedule:\n    - cron: '0 1 * * *'\n",
    )
    assert "Melder Y" in cmc.geplante_workflows(tmp_path)[0]


def test_should_strip_quotes_from_workflow_name(tmp_path):
    _schreibe(
        tmp_path,
        "q.yml",
        "name: \"Melder Z\"\non:\n  schedule:\n    - cron: '0 1 * * *'\n",
    )
    assert "Melder Z" in cmc.geplante_workflows(tmp_path)[0]


# --- rote_serien -------------------------------------------------------------


def test_should_report_workflow_red_for_the_whole_window():
    runs = [_lauf(f"2026-07-2{i}T06:00:00Z") for i in range(3, 8)]
    befunde = cmc.rote_serien(runs, 3)
    assert befunde["Melder"]["serie"] == 5
    assert befunde["Melder"]["seit"] == "2026-07-23"


def test_should_stay_silent_on_a_single_red_run():
    """Ein Ausrutscher ist kein blinder Melder — sonst Alarm-Müdigkeit."""
    runs = [
        _lauf("2026-07-28T06:00:00Z"),
        _lauf("2026-07-27T06:00:00Z", "success"),
        _lauf("2026-07-26T06:00:00Z", "success"),
    ]
    assert cmc.rote_serien(runs, 3) == {}


def test_should_stay_silent_below_threshold():
    runs = [_lauf("2026-07-28T06:00:00Z"), _lauf("2026-07-27T06:00:00Z")]
    assert cmc.rote_serien(runs, 3) == {}


def test_should_sort_runs_itself_and_not_trust_input_order():
    runs = [
        _lauf("2026-07-20T06:00:00Z", "success"),
        _lauf("2026-07-28T06:00:00Z"),
        _lauf("2026-07-26T06:00:00Z"),
        _lauf("2026-07-27T06:00:00Z"),
    ]
    befunde = cmc.rote_serien(runs, 3)
    assert befunde["Melder"]["serie"] == 3
    assert befunde["Melder"]["letzter"] == "2026-07-28T06:00"


def test_should_ignore_runs_still_in_progress():
    """Ein laufender Lauf sagt nichts aus und darf die Serie nicht auffüllen."""
    runs = [
        _lauf("2026-07-28T06:00:00Z", None, status="in_progress"),
        _lauf("2026-07-27T06:00:00Z"),
        _lauf("2026-07-26T06:00:00Z"),
    ]
    assert cmc.rote_serien(runs, 3) == {}


def test_should_separate_workflows_from_each_other():
    runs = [_lauf(f"2026-07-2{i}T06:00:00Z", name="A") for i in range(3, 7)]
    runs += [_lauf(f"2026-07-2{i}T07:00:00Z", "success", name="B") for i in range(3, 7)]
    befunde = cmc.rote_serien(runs, 3)
    assert set(befunde) == {"A"}


def test_should_report_cancelled_run_as_not_red():
    """`cancelled` ist kein failure — sonst wird jede Concurrency-Abbruchkette rot."""
    runs = [
        _lauf("2026-07-28T06:00:00Z", "cancelled"),
        _lauf("2026-07-27T06:00:00Z"),
        _lauf("2026-07-26T06:00:00Z"),
    ]
    assert cmc.rote_serien(runs, 3) == {}
