"""Tests fuer tools/alarmweg_probe.py (KONZ-054 E4).

Der teuerste Fall: `test_should_treat_a_channel_without_probe_as_absent` — ein
Kanal, den ein Skript nennt, ist kein Kanal. 177 Tage `| mail` ohne MTA.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import alarmweg_probe as ap  # noqa: E402

JETZT = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
WURZEL = Path(__file__).resolve().parents[2]


def _k(probe="workflow", tage=10, art="discord-webhook"):
    return {"art": art, "probe": probe, "max_alter_tage": tage}


def _job(kanal, conclusion, vor_tagen):
    t = JETZT - timedelta(days=vor_tagen)
    return {
        "kanal": kanal,
        "conclusion": conclusion,
        "completed_at": t.isoformat().replace("+00:00", "Z"),
    }


def test_should_treat_a_channel_without_probe_as_absent():
    u = ap.beurteile({"mail": _k(probe="keine")}, [], JETZT)
    assert u[0]["vorhanden"] is False and "keine Probe" in u[0]["grund"]


def test_should_accept_a_fresh_successful_probe():
    u = ap.beurteile({"d": _k()}, [_job("d", "success", 3)], JETZT)
    assert u[0]["vorhanden"] is True


def test_should_reject_a_stale_success():
    u = ap.beurteile({"d": _k(tage=10)}, [_job("d", "success", 11)], JETZT)
    assert u[0]["vorhanden"] is False and "> 10 d" in u[0]["grund"]


def test_should_reject_when_the_latest_probe_failed_and_no_success_exists():
    u = ap.beurteile({"d": _k()}, [_job("d", "failure", 1)], JETZT)
    assert u[0]["vorhanden"] is False and "failure" in u[0]["grund"]


def test_should_use_the_newest_success_even_after_a_later_failure():
    jobs = [_job("d", "failure", 1), _job("d", "success", 2)]
    assert ap.beurteile({"d": _k()}, jobs, JETZT)[0]["vorhanden"] is True


def test_should_report_never_probed_channel_as_absent():
    u = ap.beurteile({"d": _k()}, [_job("andere", "success", 1)], JETZT)
    assert u[0]["vorhanden"] is False and "nie geprobt" in u[0]["grund"]


def test_should_be_blind_not_green_when_runs_are_unreadable():
    u = ap.beurteile({"d": _k()}, None, JETZT)
    assert u[0]["vorhanden"] is None
    assert ap.exit_code(u) == ap.EXIT_BLIND
    assert "keine Entwarnung" in ap.kurzzeile(u)


def test_should_exit_1_if_any_channel_is_absent():
    u = ap.beurteile(
        {"a": _k(), "b": _k(probe="keine")}, [_job("a", "success", 1)], JETZT
    )
    assert ap.exit_code(u) == ap.EXIT_BEFUND
    assert "1 von 2" in ap.kurzzeile(u)


def test_should_exit_0_only_when_every_channel_is_proven():
    u = ap.beurteile(
        {"a": _k(), "b": _k()},
        [_job("a", "success", 1), _job("b", "success", 2)],
        JETZT,
    )
    assert ap.exit_code(u) == ap.EXIT_OK
    assert ap.kurzzeile(u) == "2 von 2 Alarmwegen belegt"


def test_should_fail_hard_when_discord_secret_is_missing():
    with pytest.raises(RuntimeError, match="nicht gesetzt"):
        ap.sende_discord("x", None)


def test_should_refuse_to_send_over_a_channel_without_probe():
    with pytest.raises(RuntimeError, match="nicht sendbar"):
        ap.senden("mail", {"mail": _k(probe="keine", art="mail")})


def test_should_load_the_real_register_and_find_every_workflow_job_declared():
    """Jeder Kanal mit probe=workflow braucht einen gleichnamigen Job im Workflow —
    sonst liest --pruefen ins Leere."""
    kanaele = ap.lade_register(WURZEL / "infra" / "alarmwege.yaml")
    wf = yaml.safe_load(
        (WURZEL / ".github" / "workflows" / "alarmweg-probe.yml").read_text()
    )
    jobs = set(wf["jobs"])
    fehlend = [
        k for k, v in kanaele.items() if v.get("probe") == "workflow" and k not in jobs
    ]
    assert fehlend == []
    assert any(v.get("probe") == "keine" for v in kanaele.values())


def test_should_declare_every_discord_user_in_the_repo():
    """Positivkontrolle gegen das Repo: wer DISCORD_WEBHOOK nutzt, steht im Register."""
    kanaele = ap.lade_register(WURZEL / "infra" / "alarmwege.yaml")
    deklariert = set(kanaele["discord-owner"]["genutzt_von"])
    real = {
        str(p.relative_to(WURZEL))
        for p in (WURZEL / ".github" / "workflows").glob("*.yml")
        if "DISCORD_WEBHOOK" in p.read_text() and p.name != "alarmweg-probe.yml"
    }
    assert real <= deklariert
