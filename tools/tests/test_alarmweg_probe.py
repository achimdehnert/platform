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
    # Positivkontrolle: die Pruefung oben ist nur dann aussagekraeftig, wenn das
    # Register ueberhaupt verschiedene Probe-Klassen kennt — waeren alle Kanaele
    # `workflow`, koennte `fehlend == []` auch bei kaputter Logik gruen sein.
    # Frueher stand hier `probe == "keine"`; seit dem Rueckbau der beiden toten
    # Host-Kanaele (2026-08-30/31) gibt es keinen solchen Kanal mehr, und das ist
    # Fortschritt, kein Defekt. Geprueft wird deshalb die Vielfalt, nicht ein Wert.
    klassen = {v.get("probe") for v in kanaele.values()}
    assert len(klassen) >= 2, f"nur eine Probe-Klasse im Register: {klassen}"


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


# ── Klasse "zurueckgebaut" (platform#2486) ───────────────────────────────────
# Ein bewusst abgeschalteter Kanal ist keine Luecke. Damit daraus kein bequemer
# Stummschalter wird, verlangt die Klasse zwei Belege — sonst liesse sich
# "N von M belegt" durch Umschreiben gruen machen statt durch Arbeit.
_JETZT = datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)


def _rueckbau(**extra):
    k = {"art": "mail", "probe": "zurueckgebaut"}
    k.update(extra)
    return {"tot": k}


def test_should_accept_decommissioned_channel_with_both_proofs():
    u = ap.beurteile(
        _rueckbau(zurueckgebaut_am="2026-08-30", ersetzt_durch="Phase 0.7.11"),
        [],
        _JETZT,
    )
    assert u[0]["vorhanden"] is True
    assert u[0]["zurueckgebaut"] is True


def test_should_reject_decommissioned_channel_without_proof():
    for unvollstaendig in (
        {},
        {"zurueckgebaut_am": "2026-08-30"},
        {"ersetzt_durch": "Phase 0.7.11"},
    ):
        u = ap.beurteile(_rueckbau(**unvollstaendig), [], _JETZT)
        assert u[0]["vorhanden"] is False, unvollstaendig
        assert "unbelegt" in u[0]["grund"]


def test_should_keep_decommissioned_channels_out_of_the_denominator():
    kanaele = {
        "lebt": {"art": "mail", "probe": "keine"},
        "tot": {
            "art": "mail",
            "probe": "zurueckgebaut",
            "zurueckgebaut_am": "2026-08-30",
            "ersetzt_durch": "Phase 0.7.11",
        },
    }
    zeile = ap.kurzzeile(ap.beurteile(kanaele, [], _JETZT))
    assert "1 von 1 Alarmwegen NICHT vorhanden" in zeile
    assert "1 zurueckgebaut" in zeile


def test_should_not_let_decommissioning_turn_a_real_gap_green():
    # Der Rueckbau darf den Exit-Code nur fuer sich selbst entschaerfen.
    kanaele = {
        "echt-kaputt": {"art": "mail", "probe": "keine"},
        "tot": {
            "art": "mail",
            "probe": "zurueckgebaut",
            "zurueckgebaut_am": "2026-08-30",
            "ersetzt_durch": "Phase 0.7.11",
        },
    }
    assert ap.exit_code(ap.beurteile(kanaele, [], _JETZT)) != 0
