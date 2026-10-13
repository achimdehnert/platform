"""Tests für tools/routine_berichte.py (#3887: Routine-Berichte im Sitzungsstart lesen).

`--eingabe` ersetzt gh durch eine Fixture, `--jetzt` die Uhr. Die Routinen-Liste
kommt aus einer Test-Konfiguration, nicht aus registry/ — die echte Datei wird
nur auf Form geprueft.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "routine_berichte.py"
sys.path.insert(0, str(SCRIPT.parent))

import routine_berichte  # noqa: E402

REPO = "demo/repo"
JETZT = "2026-10-13T08:00:00+00:00"
KONFIG = {
    "repo": REPO,
    "neu_stunden": 26,
    "routinen": [
        {"name": "drift", "ausgang": {"label": "drift"}, "still_stunden": 50, "befund": True,
         "kopf_muster": "^## Drift-Report", "ruhe_muster": "keine Funde"},
        {"name": "abgleich", "ausgang": {"issue": 7}, "still_stunden": 50, "befund": True,
         "ruhe_muster": "[Kk]ein Drift"},
        {"name": "briefing", "ausgang": {"issue": 9}, "still_stunden": 80, "befund": False},
        {"name": "pr-prep", "ausgang": None, "grund": "kommentiert PRs"},
    ],
}


def _kommentar(issue: int, zeit: str, body: str, n: int = 1) -> dict:
    return {"issue_url": f"https://api.github.com/repos/{REPO}/issues/{issue}", "created_at": zeit,
            "body": body, "html_url": f"https://github.com/{REPO}/issues/{issue}#issuecomment-{n}"}


def _daten(kommentare: list[dict], drift_issues: list[dict] | None = None) -> dict:
    offen = drift_issues if drift_issues is not None else [
        {"number": 5, "created_at": "2026-08-01T00:00:00Z", "body": "## Drift-Report alt",
         "html_url": f"https://github.com/{REPO}/issues/5"}]
    return {"issues": {"drift": offen}, "kommentare": kommentare}


def _ruhige_basis() -> list[dict]:
    return [
        _kommentar(5, "2026-10-13T05:00:00Z", "## Drift-Report\nkeine Funde", 1),
        _kommentar(7, "2026-10-13T05:00:00Z", "kein Drift", 2),
        _kommentar(9, "2026-10-13T06:00:00Z", "## Briefing", 3),
    ]


def _bewerte(daten: dict) -> tuple[int, str]:
    return routine_berichte.bewerte(KONFIG, daten, routine_berichte._zeit(JETZT))


def test_should_report_fresh_finding_with_link():
    kommentare = _ruhige_basis()
    kommentare[0] = _kommentar(5, "2026-10-13T05:00:00Z", "## Drift-Report\n| repo | archiviert |", 11)
    rc, zeile = _bewerte(_daten(kommentare))
    assert rc == 1
    assert "drift → https://github.com/demo/repo/issues/5#issuecomment-11" in zeile


def test_should_flag_routine_as_silent_when_last_report_is_old():
    kommentare = _ruhige_basis()
    kommentare[1] = _kommentar(7, "2026-10-10T05:00:00Z", "kein Drift", 2)
    rc, zeile = _bewerte(_daten(kommentare))
    assert rc == 1
    assert "abgleich still seit >50 h" in zeile
    assert "neue Routine-Berichte" not in zeile


def test_should_stay_quiet_when_reports_match_rest_pattern():
    rc, zeile = _bewerte(_daten(_ruhige_basis()))
    assert rc == 0, zeile
    assert zeile.startswith("keine neuen Routine-Berichte (3 Routinen gelesen")


def test_should_ignore_old_finding_outside_window():
    kommentare = _ruhige_basis()
    kommentare.append(_kommentar(5, "2026-10-11T05:00:00Z", "## Drift-Report\n| alt |", 12))
    rc, _ = _bewerte(_daten(kommentare))
    assert rc == 0


def test_should_ignore_comment_without_routine_header():
    kommentare = _ruhige_basis()
    kommentare.append(_kommentar(5, "2026-10-13T07:00:00Z", "Sitzung: F1 erledigt", 13))
    rc, _ = _bewerte(_daten(kommentare))
    assert rc == 0


def test_should_not_report_briefing_content_as_finding():
    kommentare = _ruhige_basis()
    kommentare[2] = _kommentar(9, "2026-10-13T06:00:00Z", "## Briefing\n3 PRs warten", 3)
    rc, _ = _bewerte(_daten(kommentare))
    assert rc == 0


def test_should_count_newly_opened_label_issue_as_report():
    neu = {"number": 20, "created_at": "2026-10-13T05:30:00Z", "body": "## Drift-Report\nneu",
           "html_url": f"https://github.com/{REPO}/issues/20"}
    rc, zeile = _bewerte(_daten(_ruhige_basis(), drift_issues=[neu]))
    assert rc == 1
    assert "drift → https://github.com/demo/repo/issues/20" in zeile


def test_should_not_call_silent_when_label_has_no_open_issue():
    kommentare = [k for k in _ruhige_basis() if not k["issue_url"].endswith("/5")]
    rc, zeile = _bewerte(_daten(kommentare, drift_issues=[]))
    assert rc == 0, zeile


def test_should_exit_with_code_and_print_one_line_via_cli(tmp_path):
    konfig = tmp_path / "k.json"
    konfig.write_text(json.dumps(KONFIG), encoding="utf-8")
    eingabe = tmp_path / "e.json"
    kommentare = _ruhige_basis()
    kommentare[1] = _kommentar(7, "2026-10-13T05:00:00Z", "Drift gefunden: #3812", 2)
    eingabe.write_text(json.dumps(_daten(kommentare)), encoding="utf-8")
    res = subprocess.run([sys.executable, str(SCRIPT), "--konfig", str(konfig), "--eingabe", str(eingabe),
                          "--jetzt", JETZT], capture_output=True, text=True, timeout=15)
    assert res.returncode == 1, res.stderr
    assert len(res.stdout.strip().splitlines()) == 1
    assert "abgleich → https://github.com/demo/repo/issues/7#issuecomment-2" in res.stdout


def test_should_report_unreadable_config_as_not_checkable(tmp_path):
    kaputt = tmp_path / "k.json"
    kaputt.write_text("{}", encoding="utf-8")
    res = subprocess.run([sys.executable, str(SCRIPT), "--konfig", str(kaputt), "--eingabe", str(kaputt)],
                         capture_output=True, text=True, timeout=15)
    assert res.returncode == 2
    assert res.stdout.startswith("nicht pruefbar")


def test_should_keep_registry_file_well_formed():
    konfig = routine_berichte.lade_konfig()
    namen = [r["name"] for r in konfig["routinen"]]
    assert len(namen) == len(set(namen))
    for r in konfig["routinen"]:
        assert r.get("ausgang") or r.get("grund"), f"{r['name']}: weder Ausgang noch Grund"
